-- ============================================================================
-- WenShanKB MVP Database Schema
-- PostgreSQL 16 + pgvector 扩展
-- 基于 blueprint/管理后台.md 中的表设计
-- ============================================================================

-- 1. 扩展
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- 模糊搜索加速

-- ============================================================================
-- 2. 用户角色体系
-- ============================================================================

CREATE TYPE user_role AS ENUM (
    'super_admin',   -- 超级管理员
    'editor',        -- 内容编辑
    'reviewer',      -- 审核员
    'member',        -- 协会会员
    'user'           -- 普通用户
);

CREATE TYPE user_status AS ENUM ('active', 'disabled', 'pending');

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username        VARCHAR(64)  NOT NULL UNIQUE,
    email           VARCHAR(255) UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    display_name    VARCHAR(128),
    role            user_role NOT NULL DEFAULT 'user',
    status          user_status NOT NULL DEFAULT 'pending',
    avatar_url      TEXT,
    bio             TEXT,                    -- 个人简介
    organization    VARCHAR(256),            -- 所属单位（协会会员填写）
    level           INTEGER NOT NULL DEFAULT 1,  -- 1-5 创作者等级
    contribution_score INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at   TIMESTAMPTZ
);

-- ============================================================================
-- 3. 内容分类
-- ============================================================================

CREATE TABLE categories (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(128) NOT NULL UNIQUE,  -- 如 "01-地理与自然环境"
    display_name    VARCHAR(256) NOT NULL,          -- 如 "地理与自然环境"
    description     TEXT,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    parent_id       INTEGER REFERENCES categories(id),
    icon            VARCHAR(64),                    -- 图标标识
    color           VARCHAR(7),                     -- 主题色 #RRGGBB
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 预设 13 个分类
INSERT INTO categories (name, display_name, sort_order) VALUES
    ('00-总览',        '总览与核心数据',   0),
    ('01-地理与自然环境', '地理与自然环境',   1),
    ('02-历史沿革',     '历史沿革',          2),
    ('03-行政区划',     '行政区划',          3),
    ('04-人口与民族',   '人口与民族',        4),
    ('05-经济发展',     '经济发展',          5),
    ('06-文化旅游',     '文化旅游',          6),
    ('07-特产与资源',   '特产与资源',        7),
    ('08-交通与基础设施','交通与基础设施',    8),
    ('09-政策与治理',   '政策与治理',        9),
    ('10-社会民生',     '社会民生',          10),
    ('synthesis',      '跨分类合成笔记',     11),
    ('ai-hub',         'AI创作赋能中心',     12);

-- ============================================================================
-- 4. 标签
-- ============================================================================

CREATE TABLE tags (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(128) NOT NULL UNIQUE,
    usage_count     INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 5. 笔记（核心表，含全文搜索 + 向量嵌入）
-- ============================================================================

CREATE TYPE note_status AS ENUM ('draft', 'pending_review', 'published', 'archived', 'rejected');
CREATE TYPE note_freshness AS ENUM ('fresh', 'aging', 'stale', 'expired');

CREATE TABLE notes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title           VARCHAR(512) NOT NULL,
    slug            VARCHAR(512) NOT NULL UNIQUE,     -- URL 友好标题
    content         TEXT NOT NULL,                    -- 正文 Markdown
    plain_text      TEXT,                             -- 纯文本（用于全文搜索摘要）
    frontmatter     JSONB NOT NULL DEFAULT '{}',     -- YAML frontmatter 结构化存储

    -- 分类
    category_id     INTEGER REFERENCES categories(id),
    category_path   VARCHAR(512),                     -- 原始路径，如 "06-文化旅游/普者黑旅游攻略"

    -- 状态
    status          note_status NOT NULL DEFAULT 'draft',
    freshness       note_freshness NOT NULL DEFAULT 'fresh',
    freshness_score INTEGER DEFAULT 100,              -- 新鲜度评分 0-100

    -- 统计
    view_count      INTEGER NOT NULL DEFAULT 0,
    like_count      INTEGER NOT NULL DEFAULT 0,
    bookmark_count  INTEGER NOT NULL DEFAULT 0,
    quality_score   REAL DEFAULT 0,                   -- 质量分 0-100

    -- 来源
    source_path     VARCHAR(1024),                    -- Obsidian 源文件路径
    source_type     VARCHAR(32) DEFAULT 'manual',     -- manual / crawler / agent_feedback
    author_id       UUID REFERENCES users(id),

    -- 时间
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at    TIMESTAMPTZ,
    reviewed_at     TIMESTAMPTZ,

    -- 全文搜索
    search_vector   tsvector,

    -- 向量嵌入（pgvector）- 1536 维（text-embedding-3-small）
    embedding       vector(1536),

    -- 附件列表
    attachments     JSONB DEFAULT '[]'                -- [{"name":"...","url":"...","type":"image/png"}]
);

-- 索引
CREATE INDEX idx_notes_status ON notes(status);
CREATE INDEX idx_notes_category ON notes(category_id);
CREATE INDEX idx_notes_created ON notes(created_at DESC);
CREATE INDEX idx_notes_updated ON notes(updated_at DESC);
CREATE INDEX idx_notes_search_vector ON notes USING GIN(search_vector);
CREATE INDEX idx_notes_embedding ON notes USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_notes_frontmatter ON notes USING GIN(frontmatter);
CREATE INDEX idx_notes_slug ON notes(slug);

-- 全文搜索自动更新触发器
CREATE OR REPLACE FUNCTION notes_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('simple', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('simple', COALESCE(NEW.plain_text, '')), 'B');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_notes_search_vector
    BEFORE INSERT OR UPDATE ON notes
    FOR EACH ROW EXECUTE FUNCTION notes_search_vector_update();

-- ============================================================================
-- 6. 笔记标签关联
-- ============================================================================

CREATE TABLE note_tags (
    note_id         UUID REFERENCES notes(id) ON DELETE CASCADE,
    tag_id          INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (note_id, tag_id)
);

-- ============================================================================
-- 7. Wikilink 关系表
-- ============================================================================

CREATE TABLE note_links (
    id              SERIAL PRIMARY KEY,
    source_note_id  UUID NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    target_note_slug VARCHAR(512),                    -- 目标笔记 slug（可能不存在）
    target_note_id  UUID REFERENCES notes(id) ON DELETE SET NULL,
    link_text       VARCHAR(512),                     -- wikilink 显示文本（别名）
    link_type       VARCHAR(32) DEFAULT 'wikilink',   -- wikilink / embed / tag_link
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_links_source ON note_links(source_note_id);
CREATE INDEX idx_links_target ON note_links(target_note_id);
CREATE INDEX idx_links_slug ON note_links(target_note_slug);

-- ============================================================================
-- 8. 素材卡片
-- ============================================================================

CREATE TABLE material_cards (
    id              VARCHAR(32) PRIMARY KEY,          -- "卡01", "卡02" ...
    title           VARCHAR(256) NOT NULL,
    core_data       TEXT NOT NULL,                    -- 核心数据
    full_content    TEXT NOT NULL,                    -- 完整 Markdown
    category        VARCHAR(64),                      -- 经济数据 / 旅游亮点 / ...
    applicable_scenarios JSONB DEFAULT '[]',          -- ["农产品带货","健康科普"]
    source_note_id  UUID REFERENCES notes(id),       -- 引用来源笔记
    view_count      INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_material_category ON material_cards(category);

-- ============================================================================
-- 9. Prompt 模板
-- ============================================================================

CREATE TABLE prompt_templates (
    id              SERIAL PRIMARY KEY,
    scenario        VARCHAR(64) NOT NULL,             -- 政务宣传 / 文旅推广 / ...
    sub_scenario    VARCHAR(256),                     -- 三七带货脚本 / 普者黑种草文案
    title           VARCHAR(256) NOT NULL,
    template_content TEXT NOT NULL,                   -- Prompt 模板正文
    negative_prompts TEXT[],                          -- 负面提示词列表
    suggested_cards VARCHAR(32)[],                    -- 推荐素材卡片 ID 列表
    related_style   VARCHAR(32),                      -- 关联风格
    usage_count     INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_prompt_scenario ON prompt_templates(scenario);

-- ============================================================================
-- 10. 合规规则
-- ============================================================================

CREATE TABLE compliance_rules (
    id              SERIAL PRIMARY KEY,
    category        VARCHAR(32) NOT NULL,             -- border / ethnic / military / advertising / data_accuracy / copyright
    severity        VARCHAR(16) NOT NULL DEFAULT 'medium', -- high / medium / low
    pattern         TEXT NOT NULL,                    -- 正则或关键词匹配模式
    description     TEXT NOT NULL,                    -- 说明
    suggestion      TEXT NOT NULL,                    -- 修改建议
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_compliance_category ON compliance_rules(category);

-- 预设基础规则
INSERT INTO compliance_rules (category, severity, pattern, description, suggestion) VALUES
    ('advertising', 'high', '治疗|治愈|药到病除|包治', '不得使用医疗治疗效果表述', '改为"辅助调理""传统用于"等表述'),
    ('advertising', 'high', '最好|第一|唯一|最.*的', '不得使用绝对化用语', '移除或替换为"知名""优质"等'),
    ('advertising', 'medium', '原价\d+.*现价\d+', '价格对比需有真实交易记录支撑', '核实交易记录或移除原价'),
    ('border', 'high', '争议领土|未定国界|争议地区', '不得质疑已划定边界', '使用"中越边境"官方表述'),
    ('ethnic', 'high', '落后.*(壮族|苗族|彝族|瑶族|民族)|原始.*民族', '不得使用歧视性描述', '改为"传统文化""独特习俗"'),
    ('ethnic', 'medium', '迷信', '宗教仪式≠迷信', '改为"民间信仰""传统习俗"'),
    ('military', 'high', '部队番号|军事部署|兵力|驻军', '不得泄露军事信息', '删除相关信息'),
    ('military', 'medium', '战争.*游戏|好玩.*战场', '不得娱乐化战争', '保持严肃叙事'),
    ('data_accuracy', 'medium', 'GDP.*突破\d{4,}亿', '经济数据需核实年份和来源', '标注具体年份和数据来源'),
    ('copyright', 'medium', '来源于网络|图片来自网络', '网络素材版权存疑', '使用自有或已授权素材');

-- ============================================================================
-- 11. 反馈与进化
-- ============================================================================

CREATE TYPE feedback_type AS ENUM (
    'content_suggestion',  -- 内容建议
    'error_correction',    -- 纠错
    'knowledge_gap',       -- 知识缺口
    'quality_feedback'     -- 质量反馈
);

CREATE TYPE feedback_status AS ENUM ('pending', 'accepted', 'rejected', 'implemented');

CREATE TABLE feedback (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type            feedback_type NOT NULL,
    related_note_id UUID REFERENCES notes(id),
    content         TEXT NOT NULL,
    source          VARCHAR(64) DEFAULT 'web',        -- web / agent / crawler
    source_conversation_id VARCHAR(128),              -- Agent 对话 ID
    status          feedback_status NOT NULL DEFAULT 'pending',
    submitter_id    UUID REFERENCES users(id),
    resolved_by     UUID REFERENCES users(id),
    resolved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_feedback_type ON feedback(type);
CREATE INDEX idx_feedback_status ON feedback(status);
CREATE INDEX idx_feedback_note ON feedback(related_note_id);

-- ============================================================================
-- 12. 知识缺口
-- ============================================================================

CREATE TYPE gap_priority AS ENUM ('critical', 'high', 'medium', 'low');

CREATE TABLE knowledge_gaps (
    id              SERIAL PRIMARY KEY,
    query           TEXT NOT NULL,                    -- 用户搜索查询
    frequency       INTEGER NOT NULL DEFAULT 1,      -- 查询频率
    priority        gap_priority NOT NULL DEFAULT 'medium',
    suggested_category INTEGER REFERENCES categories(id),
    research_plan   TEXT,                             -- AI 生成的研究计划
    status          VARCHAR(32) NOT NULL DEFAULT 'open',  -- open / researching / filled
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_gap_priority ON knowledge_gaps(priority);
CREATE INDEX idx_gap_freq ON knowledge_gaps(frequency DESC);

-- ============================================================================
-- 13. 审核记录
-- ============================================================================

CREATE TABLE audit_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    note_id         UUID REFERENCES notes(id) ON DELETE CASCADE,
    action          VARCHAR(32) NOT NULL,             -- submit / approve / reject / request_changes
    from_status     note_status,
    to_status       note_status,
    operator_id     UUID REFERENCES users(id),
    comment         TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_note ON audit_logs(note_id);
CREATE INDEX idx_audit_time ON audit_logs(created_at DESC);

-- ============================================================================
-- 14. API Key 管理（Agent 使用）
-- ============================================================================

CREATE TABLE api_keys (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key_hash        VARCHAR(256) NOT NULL UNIQUE,
    key_prefix      VARCHAR(16) NOT NULL,             -- 前 8 位明文（如 wskb-a1b2）
    name            VARCHAR(128) NOT NULL,            -- 用途标识
    owner_id        UUID REFERENCES users(id),
    permissions     JSONB NOT NULL DEFAULT '["read"]', -- ["read","write","agent"]
    rate_limit      INTEGER NOT NULL DEFAULT 1000,   -- 次/分钟
    is_active       BOOLEAN NOT NULL DEFAULT true,
    last_used_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_apikey_hash ON api_keys(key_hash);
CREATE INDEX idx_apikey_owner ON api_keys(owner_id);

-- ============================================================================
-- 15. 访问统计
-- ============================================================================

CREATE TABLE access_logs (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID REFERENCES users(id),
    api_key_id      UUID REFERENCES api_keys(id),
    endpoint        VARCHAR(256) NOT NULL,
    method          VARCHAR(10) NOT NULL,
    status_code     INTEGER NOT NULL,
    response_time_ms INTEGER,
    ip_address      INET,
    user_agent      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_access_time ON access_logs(created_at DESC);
CREATE INDEX idx_access_endpoint ON access_logs(endpoint);
CREATE INDEX idx_access_user ON access_logs(user_id);

-- 按天分区（生产环境可选）
-- SELECT create_hypertable('access_logs', 'created_at', chunk_time_interval => INTERVAL '1 day');

-- ============================================================================
-- 16. 笔记版本历史
-- ============================================================================

CREATE TABLE note_versions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    note_id         UUID NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    version_num     INTEGER NOT NULL,
    content         TEXT NOT NULL,
    frontmatter     JSONB NOT NULL DEFAULT '{}',
    change_summary  VARCHAR(512),
    editor_id       UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (note_id, version_num)
);

CREATE INDEX idx_version_note ON note_versions(note_id);

-- ============================================================================
-- 辅助函数
-- ============================================================================

-- 更新 updated_at 触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 自动更新 tags 使用计数
CREATE OR REPLACE FUNCTION update_tag_usage_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE tags SET usage_count = usage_count + 1 WHERE id = NEW.tag_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE tags SET usage_count = GREATEST(usage_count - 1, 0) WHERE id = OLD.tag_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_tag_usage_insert
    AFTER INSERT ON note_tags
    FOR EACH ROW EXECUTE FUNCTION update_tag_usage_count();

CREATE TRIGGER trg_tag_usage_delete
    AFTER DELETE ON note_tags
    FOR EACH ROW EXECUTE FUNCTION update_tag_usage_count();

-- ============================================================================
-- 视图：笔记统计概览
-- ============================================================================

CREATE VIEW v_note_stats AS
SELECT
    n.id,
    n.title,
    n.slug,
    c.display_name AS category,
    n.status,
    n.freshness,
    n.freshness_score,
    n.view_count,
    n.like_count,
    n.bookmark_count,
    n.quality_score,
    n.created_at,
    n.updated_at,
    COALESCE(link_count.incoming, 0) AS incoming_links,
    COALESCE(link_count.outgoing, 0) AS outgoing_links
FROM notes n
LEFT JOIN categories c ON n.category_id = c.id
LEFT JOIN LATERAL (
    SELECT
        COUNT(*) FILTER (WHERE target_note_id = n.id) AS incoming,
        COUNT(*) FILTER (WHERE source_note_id = n.id) AS outgoing
    FROM note_links
) link_count ON true;

-- ============================================================================
-- 视图：用户贡献统计
-- ============================================================================

CREATE VIEW v_user_contribution AS
SELECT
    u.id,
    u.username,
    u.display_name,
    u.role,
    u.level,
    COUNT(n.id) FILTER (WHERE n.status = 'published') AS published_notes,
    COUNT(n.id) FILTER (WHERE n.status = 'pending_review') AS pending_notes,
    COALESCE(SUM(n.view_count), 0) AS total_views,
    COALESCE(SUM(n.like_count), 0) AS total_likes,
    u.created_at
FROM users u
LEFT JOIN notes n ON n.author_id = u.id
GROUP BY u.id;

-- EOF

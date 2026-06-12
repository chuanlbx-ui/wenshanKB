# WenShanKB MVP

> 文山州 AI 创作公共知识库系统 — 最小可运行版本

## 文件清单

| 文件 | 说明 | 行数 |
|------|------|------|
| `db_schema.sql` | PostgreSQL DDL 脚本（含 pgvector 扩展、16 张表、4 个视图、预设数据） | ~550 |
| `migrate.py` | Obsidian → PostgreSQL 数据迁移工具（frontmatter 解析、wikilink 提取、向量嵌入） | ~380 |
| `api_spec.yaml` | OpenAPI 3.0 规范（7 个端点、安全认证、完整 Schema） | ~380 |
| `app.py` | FastAPI 应用骨架（可独立运行，含模拟数据回退） | ~600 |

## 快速启动

```bash
# 1. 初始化数据库
psql -U postgres -c "CREATE DATABASE wenshan_kb"
psql -U postgres -d wenshan_kb -f db_schema.sql

# 2. 迁移数据
export DATABASE_URL=postgresql://kb_user:kb_pass@localhost:5432/wenshan_kb
export OPENAI_API_KEY=sk-xxxx  # 可选，用于向量嵌入
python migrate.py --full

# 3. 启动 API
pip install fastapi uvicorn psycopg2-binary asyncpg pgvector openai pyyaml
python app.py
```

## 数据库 Schema

```
users ────────── 用户与角色（5 级角色体系）
  ├─ notes ──────── 核心笔记（全文搜索 + pgvector 向量嵌入 1536 维）
  │   ├─ note_tags ── 标签关联
  │   ├─ note_links ── wikilink 关系图
  │   └─ note_versions 版本历史
  ├─ material_cards ── 素材卡片（30 张）
  ├─ prompt_templates ─ Prompt 模板（25+）
  ├─ compliance_rules ── 合规规则（10 条预设）
  ├─ feedback ─────── 用户反馈
  ├─ knowledge_gaps ── 知识缺口追踪
  ├─ audit_logs ───── 审核记录
  ├─ api_keys ─────── Agent API 密钥管理
  └─ access_logs ──── 访问统计
```

## API 端点

| 端点 | 方法 | 认证 | 说明 |
|------|------|------|------|
| `/api/v1/health` | GET | - | 健康检查 |
| `/api/v1/search` | POST | API Key/JWT | 混合搜索（语义+全文） |
| `/api/v1/notes` | GET | - | 笔记列表 |
| `/api/v1/notes/{slug}` | GET | - | 笔记详情 |
| `/api/v1/notes/{slug}/related` | GET | - | 相关笔记推荐 |
| `/api/v1/materials` | GET | API Key/JWT | 素材卡片查询 |
| `/api/v1/prompts` | GET | API Key/JWT | Prompt 模板 |
| `/api/v1/compliance/check` | POST | API Key/JWT | 合规检查 |
| `/api/v1/feedback` | POST | API Key/JWT | 提交反馈 |

## 下一步迭代

- [ ] 接入 Elasticsearch 增强全文搜索
- [ ] Milvus 大规模向量检索
- [ ] 自进化回路（Celery Beat 定时任务）
- [ ] 管理后台 Dashboard
- [ ] Hermes Agent Tools 集成

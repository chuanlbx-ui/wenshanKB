---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 4263874b1ccbbfa992fe963c5a172284_c8b708205c8411f19299525400d9a7a1
    ReservedCode1: epEJQQBdB4BIHRoEwAy3u7KqutrSuG/NOzGmdbM1S+YKinP7UfOKkPpZEIFhqAzjCqRjRKb5kYGSnoLMTE2UEiJRMW3plO0+64AQC1VdOW+I00yPfTffwB467m+iQ2NOPQS/ENwTXmTxPOKikYVl/XrXTFFcEHWp0DE+ezQqnR/rRgtQrf+tgSD14uY=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 4263874b1ccbbfa992fe963c5a172284_c8b708205c8411f19299525400d9a7a1
    ReservedCode2: epEJQQBdB4BIHRoEwAy3u7KqutrSuG/NOzGmdbM1S+YKinP7UfOKkPpZEIFhqAzjCqRjRKb5kYGSnoLMTE2UEiJRMW3plO0+64AQC1VdOW+I00yPfTffwB467m+iQ2NOPQS/ENwTXmTxPOKikYVl/XrXTFFcEHWp0DE+ezQqnR/rRgtQrf+tgSD14uY=
---



# Hermes Agent 集成方案

> 让 Hermes Agent 成为文山 AI 创作公共知识库的"智能前端"，通过 Tool Schema 实现检索、创作辅助、合规检查的深度集成。

---

## 一、集成总览

```
用户提问（自然语言）
        │
        ▼
┌───────────────────────────────────────────────────┐
│              Hermes Agent (Orchestrator)            │
│                                                    │
│  意图识别 → 工具选择 → 调用 WenShanKB API → 综合   │
│                                                    │
│  ┌─────────────────────────────────────────────┐  │
│  │            可调用 Tools (7 个)               │  │
│  ├─────────────────────────────────────────────┤  │
│  │ search_kb         知识库语义检索              │  │
│  │ get_material_card  获取素材卡片               │  │
│  │ get_prompt_template 获取创作 Prompt            │  │
│  │ check_compliance   合规检查                   │  │
│  │ get_style_guide    获取风格指南               │  │
│  │ get_ip_story       获取 IP 故事素材            │  │
│  │ submit_feedback    提交反馈回流               │  │
│  └─────────────────────────────────────────────┘  │
└──────────────────┬────────────────────────────────┘
                   │ HTTPS + Bearer Token
                   ▼
┌───────────────────────────────────────────────────┐
│           WenShanKB API Gateway                     │
│           /api/v1/agent/tools/                      │
│                                                    │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │
│  │ 认证鉴权  │ │ 限流控制 │ │ 日志记录 │ │ 降级策略 │ │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ │
└───────────────────────────────────────────────────┘
```

---

## 二、Tool 定义

### 2.1 search_kb — 知识库语义检索

```json
{
  "name": "search_kb",
  "description": "在文山州知识库中执行语义检索。返回匹配的笔记标题、摘要和完整内容。适用于用户询问文山相关的事实、数据、背景知识。",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "搜索查询，使用自然语言描述。例如：'普者黑 2025 年游客数据'、'三七种植面积'"
      },
      "category": {
        "type": "string",
        "enum": ["geography", "history", "admin", "population", "economy", "tourism", "specialty", "transport", "policy", "society", "ai-hub"],
        "description": "可选，限定搜索的笔记分类"
      },
      "max_results": {
        "type": "integer",
        "default": 5,
        "minimum": 1,
        "maximum": 10,
        "description": "返回的最大结果数"
      },
      "include_full_content": {
        "type": "boolean",
        "default": false,
        "description": "是否返回笔记完整内容。默认仅返回标题+摘要以节省 token"
      }
    },
    "required": ["query"]
  }
}
```

**返回示例**：

```json
{
  "results": [
    {
      "title": "普者黑旅游攻略",
      "category": "tourism",
      "score": 0.92,
      "summary": "普者黑国家 5A 级景区，312 座孤峰、54 个湖泊...",
      "content_snippet": "2025 年普者黑景区接待游客超 600 万人次...",
      "source_note": "[[06-文化旅游/普者黑旅游攻略]]",
      "last_updated": "2026-05-15",
      "material_cards": ["卡07", "卡10"]
    }
  ],
  "total_found": 3,
  "search_time_ms": 120
}
```

### 2.2 get_material_card — 获取素材卡片

```json
{
  "name": "get_material_card",
  "description": "获取文山州知识库中的高价值素材卡片。每张卡片包含核心数据、引用来源和适用场景。适用于创作时需要引用准确数据。",
  "parameters": {
    "type": "object",
    "properties": {
      "card_ids": {
        "type": "array",
        "items": {"type": "string"},
        "description": "素材卡片 ID 列表，如 ['卡01', '卡07']。不传则返回与 query 语义匹配的卡片"
      },
      "query": {
        "type": "string",
        "description": "当不指定 card_ids 时，通过语义匹配找到相关卡片。例如：'三七产业数据'"
      },
      "category": {
        "type": "string",
        "enum": ["经济数据", "旅游亮点", "特产卖点", "民族文化", "历史事件", "人物故事", "特色数据"],
        "description": "可选，限定卡片类别"
      },
      "max_cards": {
        "type": "integer",
        "default": 3,
        "minimum": 1,
        "maximum": 5
      }
    },
    "required": []
  }
}
```

**返回示例**：

```json
{
  "cards": [
    {
      "card_id": "卡03",
      "title": ""金不换"——文山三七占全国 90% 产量",
      "core_data": "文山三七产量占全国 90% 以上，种植面积超 60 万亩...",
      "source": "[[../07-特产与资源/三七]]",
      "applicable_scenarios": ["农产品带货", "健康科普", "产业报道"],
      "full_content": "完整的卡片 Markdown 内容..."
    }
  ]
}
```

### 2.3 get_prompt_template — 获取创作 Prompt

```json
{
  "name": "get_prompt_template",
  "description": "从文山 AI 创作提示词库中获取即用型 Prompt 模板。每个模板已预填文山真实数据，可直接用于 AI 内容生成。",
  "parameters": {
    "type": "object",
    "properties": {
      "scenario": {
        "type": "string",
        "enum": ["政务宣传", "文旅推广", "农产品带货", "民族文化", "新闻通讯", "乡土故事"],
        "description": "创作场景类型"
      },
      "sub_scenario": {
        "type": "string",
        "description": "子场景名称，如 '三七带货脚本'、'普者黑种草文案'。不传则返回该场景下所有模板供选择"
      },
      "custom_context": {
        "type": "string",
        "description": "用户提供的额外上下文，将填充到 Prompt 模板的 [填写] 字段中"
      }
    },
    "required": ["scenario"]
  }
}
```

**返回示例**：

```json
{
  "scenario": "农产品带货",
  "sub_scenario": "三七带货脚本",
  "prompt_template": "你是文山三七带货主播...（完整 Prompt）",
  "negative_prompts": [
    "严禁宣称三七'治疗'疾病",
    "不使用'最''第一'等绝对化用语"
  ],
  "suggested_material_cards": ["卡03", "卡11"],
  "related_style_guide": "带货风格"
}
```

### 2.4 check_compliance — 合规检查

```json
{
  "name": "check_compliance",
  "description": "检查文本内容是否符合文山州知识库的合规要求，包括边境话题、民族话题、军事历史、广告法、数据引用等方面。",
  "parameters": {
    "type": "object",
    "properties": {
      "content": {
        "type": "string",
        "description": "待检查的完整文本内容"
      },
      "content_type": {
        "type": "string",
        "enum": ["政务宣传", "文旅推广", "农产品带货", "民族文化", "新闻通讯", "乡土故事", "通用"],
        "description": "内容类型，用于针对性检查"
      },
      "check_categories": {
        "type": "array",
        "items": {
          "type": "string",
          "enum": ["border", "ethnic", "military", "advertising", "data_accuracy", "copyright", "all"]
        },
        "default": ["all"],
        "description": "指定检查维度，默认全部检查"
      }
    },
    "required": ["content"]
  }
}
```

**返回示例**：

```json
{
  "passed": false,
  "overall_score": 72,
  "issues": [
    {
      "category": "advertising",
      "severity": "high",
      "location": "第 3 段：'三七能有效治疗心脑血管疾病'",
      "issue": "使用了'治疗'一词，违反《广告法》第十七条",
      "suggestion": "修改为：'三七传统用于活血化瘀，有助于改善血液循环'",
      "rule_ref": "[[合规指南]] 第六节"
    }
  ],
  "warnings": [
    {
      "category": "data_accuracy",
      "severity": "medium",
      "location": "第 1 段：'文山 GDP 突破 2000 亿'",
      "issue": "数据与最新记录不符（2024 年约 1600 亿元），请核实",
      "suggestion": "确认数据来源或修改为准确数字"
    }
  ],
  "passed_checks": ["border", "ethnic", "military", "copyright"]
}
```

### 2.5 get_style_guide — 获取风格指南

```json
{
  "name": "get_style_guide",
  "description": "获取文山 AI 创作的风格指南，包含语调设定、常用词汇、避讳词汇和参考范例。",
  "parameters": {
    "type": "object",
    "properties": {
      "style": {
        "type": "string",
        "enum": ["政务", "文旅", "带货", "新闻"],
        "description": "目标风格类型"
      },
      "format": {
        "type": "string",
        "enum": ["full", "cheatsheet"],
        "default": "cheatsheet",
        "description": "full=完整指南, cheatsheet=精简速查表（推荐，节省 token）"
      }
    },
    "required": ["style"]
  }
}
```

### 2.6 get_ip_story — 获取 IP 故事素材

```json
{
  "name": "get_ip_story",
  "description": "获取文山本地 IP 故事素材，包含文化来源、可改编方向、适用媒介和参考叙事框架。",
  "parameters": {
    "type": "object",
    "properties": {
      "ip_name": {
        "type": "string",
        "description": "IP 名称，如 '三七精灵'、'句町女王'、'普者黑水精灵'"
      },
      "query": {
        "type": "string",
        "description": "不指定 ip_name 时，通过语义匹配找到相关 IP。例如：'适合做动画的 IP'"
      },
      "format": {
        "type": "string",
        "enum": ["card", "narrative"],
        "default": "card",
        "description": "card=卡片格式（精简）, narrative=含叙事框架的完整版"
      }
    },
    "required": []
  }
}
```

### 2.7 submit_feedback — 提交反馈回流

```json
{
  "name": "submit_feedback",
  "description": "将 Agent 创作过程中发现的优质内容、用户纠错、知识缺口等反馈回流到知识库。Agent 应主动在合适的时机调用此工具。",
  "parameters": {
    "type": "object",
    "properties": {
      "feedback_type": {
        "type": "string",
        "enum": ["content_suggestion", "error_correction", "knowledge_gap", "quality_feedback"],
        "description": "反馈类型"
      },
      "related_note": {
        "type": "string",
        "description": "关联的笔记标题或 wikilink"
      },
      "content": {
        "type": "string",
        "description": "反馈详细内容"
      },
      "source_conversation_id": {
        "type": "string",
        "description": "来源对话 ID，用于追溯"
      }
    },
    "required": ["feedback_type", "content"]
  }
}
```

---

## 三、上下文注入策略

### 3.1 注入时机决策

Agent 在处理用户消息时，根据以下规则决定是否调用知识库工具：

```
用户消息进入
      │
      ▼
┌─────────────────┐
│ 意图分类器       │
│ (LLM few-shot)  │
└────────┬────────┘
         │
    ┌────┼────────────────────────────┐
    ▼    ▼                            ▼
 文山相关  创作请求                  无关
    │    (写文案/做视频等)             │
    │      │                          │
    ▼      ▼                          ▼
 search_kb  get_prompt_template    直接回答
    │      + get_material_card     (不调KB)
    │      + get_style_guide
    ▼
 返回结果
    │
    ▼
 综合生成回复
```

### 3.2 注入量控制

| 场景 | max_results | include_full_content | 说明 |
|------|:-----------:|:--------------------:|------|
| 简单事实查询 | 1-2 | false | "文山 GDP 多少？" |
| 深度调研 | 3-5 | true | "文山三七产业链分析" |
| 创作辅助 | 素材 2-3 张 + Prompt 1 个 | - | 组合调用 |
| 合规检查 | - | - | 仅调 check_compliance |

### 3.3 上下文格式化

Agent 在收到知识库返回后，将其格式化为系统消息注入：

```
System Message:
[已从文山州知识库检索到以下相关信息]

## 普者黑旅游攻略
来源: [[06-文化旅游/普者黑旅游攻略]] | 更新: 2026-05-15

普者黑国家 5A 级景区，312 座孤峰、54 个湖泊...
2025 年接待游客超 600 万人次，最佳季节 6-8 月。
...

[在回答中引用上述信息时，请标注来源]
```

---

## 四、Agent 反哺机制

### 4.1 反哺场景

| 场景 | 触发条件 | 反哺动作 |
|------|----------|----------|
| 优质创作 | 用户对 Agent 回复点赞/保存 | `submit_feedback(type="content_suggestion")` → 编辑审核后可入库 |
| 错误发现 | Agent 发现知识库数据与用户提供的最新数据矛盾 | `submit_feedback(type="error_correction")` → 触发纠错工单 |
| 知识缺口 | Agent 无法从知识库找到答案，依赖自身知识回答 | `submit_feedback(type="knowledge_gap")` → 加入缺口发现队列 |
| 质量反馈 | 用户表达不满或指出问题 | `submit_feedback(type="quality_feedback")` → 分析改进 |

### 4.2 反哺数据流

```
Agent 对话结束
      │
      ▼
┌─────────────────┐
│ 异步分析线程     │  ← 不阻塞用户，后台进行
├─────────────────┤
│ 1. 提取关键信息  │
│ 2. 判断反哺场景  │
│ 3. 调用 submit_  │
│    feedback     │
└────────┬────────┘
         ▼
┌─────────────────┐
│ 知识库反哺队列   │
│ (Celery Queue)  │
└────────┬────────┘
         ▼
┌─────────────────┐
│ 自动分类 + 优先级│
│ → 编辑审核       │
│ → 知识缺口聚合   │
│ → 质量改进工单   │
└─────────────────┘
```

---

## 五、会话分析驱动进化

### 5.1 分析维度

每天凌晨从 Agent 对话日志中提取：

```python
# 伪代码：会话分析任务
class ConversationAnalyzer:
    def analyze(self, conversations):
        insights = {
            # 热门查询但知识库覆盖不足
            "uncovered_queries": self.find_uncovered(),
            
            # 用户频繁追问的话题（知识库深度不够）
            "deepening_needed": self.find_shallow_coverage(),
            
            # 高满意度对话中引用了哪些笔记
            "high_value_notes": self.find_high_satisfaction_notes(),
            
            # 合规检查中高频触发的问题类型
            "compliance_hotspots": self.find_compliance_hotspots(),
            
            # 用户实际需求与知识库分类的匹配度
            "category_mismatch": self.find_category_gaps(),
        }
        return insights
```

### 5.2 反馈到自进化引擎

```
会话分析结果
    │
    ├── uncovered_queries → 知识缺口发现（回路 4）
    │
    ├── deepening_needed → 标记笔记"需要深化"
    │                         → 纳入编辑任务
    │
    ├── high_value_notes → 提升搜索权重
    │                       → 推荐加入"精选"列表
    │
    ├── compliance_hotspots → 优化合规规则引擎
    │                         → 更新敏感词库
    │
    └── category_mismatch → 建议调整分类结构
                            → 更新标签体系
```

---

## 六、API 接口规范

### 6.1 认证

```
Authorization: Bearer <agent_api_key>
```

Agent 使用独立的 API Key，该 Key 在管理后台生成，拥有更高的速率限制和 Tools 专用端点权限。

### 6.2 端点汇总

| 端点 | 方法 | 对应 Tool |
|------|------|-----------|
| `/api/v1/agent/tools/search_kb` | POST | search_kb |
| `/api/v1/agent/tools/material_card` | POST | get_material_card |
| `/api/v1/agent/tools/prompt_template` | POST | get_prompt_template |
| `/api/v1/agent/tools/compliance` | POST | check_compliance |
| `/api/v1/agent/tools/style_guide` | POST | get_style_guide |
| `/api/v1/agent/tools/ip_story` | POST | get_ip_story |
| `/api/v1/agent/tools/feedback` | POST | submit_feedback |
| `/api/v1/agent/health` | GET | 健康检查 |

### 6.3 错误处理

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Agent API 调用频率超限，当前限制：1000 次/分钟",
    "retry_after": 30
  }
}
```

通用错误码：

| 错误码 | HTTP 状态 | 说明 |
|--------|-----------|------|
| RATE_LIMIT_EXCEEDED | 429 | 频率超限 |
| INVALID_API_KEY | 401 | API Key 无效 |
| QUERY_TOO_SHORT | 400 | 查询长度不足 |
| KB_UNAVAILABLE | 503 | 知识库服务不可用 |
| TIMEOUT | 504 | 搜索超时 |

### 6.4 降级策略

```
search_kb 调用超时
    │
    ├── 1st: 重试（指数退避，最多 2 次）
    │
    ├── 2nd: 降级到关键词搜索（Elasticsearch）
    │
    └── 3rd: 返回缓存热门结果 + 告知用户"部分服务暂时不可用"
```

---

## 七、集成路线图

| 阶段 | 内容 | 时间 |
|------|------|:----:|
| Phase 1 | search_kb + get_material_card 两个基础 Tool | MVP |
| Phase 2 | get_prompt_template + check_compliance + get_style_guide | 内测 |
| Phase 3 | get_ip_story + submit_feedback 反馈回路 | 公测 |
| Phase 4 | 会话分析引擎 + 知识图谱推荐 | 正式版 |
| Phase 5 | Agent 自主调用链：检测到多步骤需求时自动编排 Tool 组合 | 持续优化 |

## 相关链接

- [[架构总览]] — 集成架构在四层模型中的位置
- [[管理后台]] — API Key 管理、Agent 调用统计
- [[自进化机制]] — 会话分析驱动知识库自进化
- [[../ai-hub/提示词库]] — Tool 返回的 Prompt 模板来源
- [[../ai-hub/合规指南]] — check_compliance 的规则来源
*（内容由AI生成，仅供参考）*

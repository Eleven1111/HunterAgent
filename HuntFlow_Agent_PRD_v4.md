# HuntFlow Agent · 猎头顾问工作台

## 产品需求文档 + 执行计划（融合版）

**版本**：v4.0
**日期**：2026-04-20
**定位**：猎头顾问 AI 工作台，薄内核 + Skills + WebUI + Agent 入口
**开发方式**：Codex 实现 + Claude Code 审查 + CI 兜底
**首发目标**：单机可跑、单租户起步、可扩展到多团队

---

## 一、产品定位与边界

### 1.1 这是什么

猎头顾问工作台——不是全自动猎头机器人，不是完整 ATS/CRM/ERP。它是一个让猎头顾问更高效地完成日常核心工作的 AI 辅助系统。

### 1.2 首发六大核心能力

| # | 能力 | 说明 | AI 角色 |
|---|------|------|---------|
| 1 | 职位画像 | 创建职位、锁定画像、生成寻访计划 | 生成 JD、目标公司列表、搜索关键词 |
| 2 | 候选人导入 | 简历上传、解析、结构化入库 | 自动解析简历提取结构化信息 |
| 3 | 去重归并 | 身份哈希 + 人工确认队列 | 辅助识别疑似重复 |
| 4 | 短名单评分 | 规则版 Ranker + LLM 解释层 | 生成 score / reason_codes / gap_items |
| 5 | 推荐草稿 | 仅生成 draft，不改正式状态 | 生成候选人推荐报告草稿 |
| 6 | 审批回放 | 所有正式动作可追溯、可回放 | 记录 run / tool / diff / artifact |

### 1.3 明确的非目标（首发不做）

- ❌ RPA 自动爬取猎聘/脉脉/BOSS（合规风险过高）
- ❌ 复杂佣金计算引擎（首发只做 placement/invoice 状态记录）
- ❌ 多渠道 IM 网关（首发只做企业微信通知）
- ❌ 公共内容发布（小红书/公众号等自媒体）
- ❌ 跨企业流程协同
- ❌ 批量导出未脱敏数据

### 1.4 首发之后的扩展路线

| 优先级 | 模块 | 触发条件 |
|--------|------|----------|
| P1 | 电话面试录音转写 + 评估报告 | 首发闭环稳定后 |
| P1 | 面试协调与排程 | 有真实客户需要时 |
| P1 | 财务 lite（placement/invoice 状态） | 有真实成单时 |
| P2 | 背景调查报告 | 有客户要求时 |
| P2 | 试用期管理 | 有候选人入职时 |
| P2 | 二次开发 BD | 有保证期完成时 |
| P3 | 浏览器扩展（用户触发导入） | 产品稳定后 |

---

## 二、架构设计

### 2.1 三层架构

```
┌─────────────────────────────────────────────────┐
│                    入口层                         │
│  WebUI 工作台 ← → Agent 对话入口 ← → 企微通知     │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────┐
│                  Agent Runtime                    │
│  Conversation Manager → Agent Core → Skill Registry │
│  Policy Engine → Skill Sandbox → Model Orchestrator │
│  Approval Token → Audit Replay                    │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────┐
│                 业务内核 (Core Backend)            │
│  REST API (业务真相) + Events (异步联动) + MCP (模型可见面) │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────┐
│                   数据层                          │
│  PostgreSQL (业务真相) + Redis (会话缓存)           │
│  对象存储 (简历/报告) + pgvector (语义搜索)         │
└─────────────────────────────────────────────────┘
```

### 2.2 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| 后端 | Python 3.12 + FastAPI | AI 生态最佳，Codex 效率最高 |
| 数据库 | PostgreSQL 16 + pgvector | 本地 Docker 或 Supabase 云端 |
| 缓存 | Redis 7 | 会话状态、事件队列 |
| 前端 | Next.js 14 + Tailwind + shadcn/ui | 工作台 UI |
| 对象存储 | 本地文件系统（首发）/ S3 兼容（扩展） | 简历、报告 PDF |
| AI 文本 | 通义千问 Qwen-Max（主力）+ DeepSeek（备选） | 国内合规 |
| Embedding | text-embedding-v3（512 维） | 降维节省资源 |
| 语音转写 | 阿里云智能语音（P1 阶段） | 中文准确率最高 |
| 推送通知 | 企业微信应用消息 API | 猎头首选 IM |
| PDF 生成 | WeasyPrint | Python 直接用 |
| 定时任务 | APScheduler（本地）/ Vercel Cron（云端） | 单机优先 |
| 部署 | Docker Compose（首发） | 单机一键拉起 |

### 2.3 LLM 路由层设计

```python
# utils/llm_router.py — 所有 AI 调用统一走这里
# 不硬编码任何具体模型，支持切换

PROVIDER_CONFIG = {
    "primary": {
        "provider": "dashscope",      # 通义千问
        "model": "qwen-max",
        "for": ["report_generation", "evaluation", "plan_generation"]
    },
    "fast": {
        "provider": "dashscope",
        "model": "qwen-turbo",
        "for": ["resume_parsing", "intent_classification", "tagging"]
    },
    "embedding": {
        "provider": "dashscope",
        "model": "text-embedding-v3",
        "dimensions": 512
    },
    "fallback": {
        "provider": "deepseek",
        "model": "deepseek-chat",
        "for": ["all"]  # 主力不可用时降级
    }
}
```

### 2.4 Skill 分类与权限

| Skill | 类型 | 默认开放 | 说明 |
|-------|------|---------|------|
| `job_brief_fetch` | read | 是 | 拉取职位画像 |
| `candidate_search` | read | 是 | 搜索候选人 |
| `candidate_score` | read | 是 | 生成 score 与 reasons |
| `submission_draft_create` | draft-write | 是 | 只写草稿 |
| `search_plan_generate` | draft-write | 是 | 生成寻访计划草稿 |
| `jd_generate` | draft-write | 是 | 生成 JD 草稿 |
| `outreach_message_generate` | draft-write | 是 | 生成外联话术草稿 |
| `submission_submit` | write | 否 | 需 approval token |
| `export_candidates_csv` | export | 否 | 需 approval token |
| `interview_schedule` | write | 否（P1） | 需 approval token |

---

## 三、数据模型

### 3.1 核心表（共 14 张）

```sql
-- ============================================
-- PHASE 0: 基础设施表
-- ============================================

-- 启用扩展
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- tenants（租户）
CREATE TABLE public.tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    status TEXT DEFAULT 'ACTIVE',  -- ACTIVE / SUSPENDED
    data_region TEXT DEFAULT 'CN',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- teams（团队）
CREATE TABLE public.teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES public.tenants(id) NOT NULL,
    name TEXT NOT NULL,
    owner_user_id UUID,  -- 后面 ALTER 补外键
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON public.teams(tenant_id);

-- users（用户）
CREATE TABLE public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES public.tenants(id) NOT NULL,
    team_id UUID REFERENCES public.teams(id),
    email TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'consultant',
    -- 角色: owner / team_admin / consultant / researcher / reviewer / finance_lite
    wecom_userid TEXT,
    status TEXT DEFAULT 'ACTIVE',
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE UNIQUE INDEX ON public.users(tenant_id, email);
ALTER TABLE public.teams ADD FOREIGN KEY (owner_user_id) REFERENCES public.users(id);

-- ============================================
-- 业务核心表
-- ============================================

-- clients（客户/公司）
CREATE TABLE public.clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES public.tenants(id) NOT NULL,
    team_id UUID REFERENCES public.teams(id),
    owner_id UUID REFERENCES public.users(id) NOT NULL,
    name TEXT NOT NULL,
    industry TEXT,
    size TEXT,
    stage TEXT DEFAULT 'LEAD',
    -- 阶段: LEAD → CONTACTED → NEGOTIATING → SIGNED → ACTIVE
    contacts JSONB DEFAULT '[]',
    -- [{name, title, wechat, email, phone}]
    next_follow_up TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON public.clients(tenant_id, owner_id, stage);

-- job_orders（岗位/职位）
CREATE TABLE public.job_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES public.tenants(id) NOT NULL,
    team_id UUID REFERENCES public.teams(id),
    client_id UUID REFERENCES public.clients(id) NOT NULL,
    owner_id UUID REFERENCES public.users(id) NOT NULL,
    title TEXT NOT NULL,
    level TEXT,
    status TEXT DEFAULT 'OPEN',
    -- 状态: OPEN / PAUSED / FILLED / CANCELLED
    jd TEXT,
    must_have JSONB DEFAULT '[]',
    nice_to_have JSONB DEFAULT '[]',
    search_plan JSONB,
    -- {candidate_profile, target_companies[], search_keywords[],
    --  salary_market_insight, timeline{}}
    salary_min INT,
    salary_max INT,
    deadline TIMESTAMPTZ,
    embedding VECTOR(512),
    version INT DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON public.job_orders(tenant_id, owner_id, status);
CREATE INDEX ON public.job_orders USING ivfflat (embedding vector_cosine_ops) WITH (lists = 20);

-- candidates（候选人）
CREATE TABLE public.candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES public.tenants(id) NOT NULL,
    owner_id UUID REFERENCES public.users(id) NOT NULL,
    full_name TEXT NOT NULL,
    phone_encrypted TEXT,
    -- 加密存储，UI 默认脱敏
    email_encrypted TEXT,
    city TEXT,
    current_company TEXT,
    current_title TEXT,
    current_salary INT,
    expected_salary INT,
    open_to_move TEXT DEFAULT 'PASSIVE',
    -- ACTIVE / PASSIVE / NOT_LOOKING
    resume_summary TEXT,
    resume_parsed JSONB,
    -- {education, skills[], work_history[], industries[], years_experience}
    tags JSONB DEFAULT '[]',
    -- [{key, value}] 如 {key:"industry", value:"互联网"}
    normalized_identity_hash TEXT,
    -- 用于去重：hash(normalized_name + phone_last4 + email_domain)
    source_type TEXT NOT NULL DEFAULT 'MANUAL_UPLOAD',
    -- MANUAL_UPLOAD / CSV_IMPORT / EMAIL_IMPORT / REFERRAL / EXTENSION
    source_detail TEXT,
    consent_basis TEXT DEFAULT 'LEGITIMATE_INTEREST',
    last_contacted_at TIMESTAMPTZ,
    next_follow_up TIMESTAMPTZ,
    embedding VECTOR(512),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON public.candidates(tenant_id, owner_id);
CREATE INDEX ON public.candidates(normalized_identity_hash);
CREATE INDEX ON public.candidates(next_follow_up);
CREATE INDEX ON public.candidates USING ivfflat (embedding vector_cosine_ops) WITH (lists = 20);

-- resume_assets（简历原始文件）
CREATE TABLE public.resume_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES public.tenants(id) NOT NULL,
    candidate_id UUID REFERENCES public.candidates(id) NOT NULL,
    object_key TEXT NOT NULL,
    -- 对象存储路径
    file_name TEXT NOT NULL,
    file_type TEXT,
    -- application/pdf, application/msword, text/plain
    parse_status TEXT DEFAULT 'PENDING',
    -- PENDING / PARSING / DONE / FAILED
    parse_confidence FLOAT,
    parse_error TEXT,
    uploaded_by UUID REFERENCES public.users(id),
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON public.resume_assets(tenant_id, candidate_id);

-- pipelines（流程核心表 — 候选人×岗位关联）
CREATE TABLE public.pipelines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES public.tenants(id) NOT NULL,
    job_order_id UUID REFERENCES public.job_orders(id) NOT NULL,
    candidate_id UUID REFERENCES public.candidates(id) NOT NULL,
    owner_id UUID REFERENCES public.users(id) NOT NULL,
    stage TEXT DEFAULT 'SOURCED',
    -- SOURCED → SHORTLISTED → PHONE_INTERVIEW → SUBMITTED →
    -- CLIENT_INTERVIEW → OFFER → PLACED → REJECTED
    list_type TEXT DEFAULT 'LONGLIST',
    -- LONGLIST / SHORTLIST
    metadata JSONB DEFAULT '{}',
    -- {stage_history: [{stage, at, by, reason}]}
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(job_order_id, candidate_id)
);
CREATE INDEX ON public.pipelines(tenant_id, job_order_id, stage);

-- match_scores（匹配评分 — 可审计）
CREATE TABLE public.match_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES public.tenants(id) NOT NULL,
    job_order_id UUID REFERENCES public.job_orders(id) NOT NULL,
    candidate_id UUID REFERENCES public.candidates(id) NOT NULL,
    pipeline_id UUID REFERENCES public.pipelines(id),
    score INT,
    -- 0-100
    confidence FLOAT,
    reason_codes JSONB DEFAULT '[]',
    -- ["5年以上CFO经验", "互联网行业背景匹配"]
    gap_items JSONB DEFAULT '[]',
    -- ["缺少上市公司经验", "薪资期望偏高"]
    priority TEXT,
    -- HIGH / MEDIUM / LOW
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    prompt_version TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON public.match_scores(tenant_id, job_order_id);

-- submissions（推荐报告 — 草稿与正式分离）
CREATE TABLE public.submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES public.tenants(id) NOT NULL,
    job_order_id UUID REFERENCES public.job_orders(id) NOT NULL,
    candidate_id UUID REFERENCES public.candidates(id) NOT NULL,
    pipeline_id UUID REFERENCES public.pipelines(id),
    draft_markdown TEXT,
    draft_content JSONB,
    -- {candidate_snapshot, match_analysis, strengths[], concerns[], endorsement}
    status TEXT DEFAULT 'DRAFT',
    -- DRAFT / PENDING_APPROVAL / APPROVED / SUBMITTED / REJECTED
    file_url TEXT,
    share_token TEXT UNIQUE DEFAULT encode(gen_random_bytes(16), 'hex'),
    share_expires_at TIMESTAMPTZ DEFAULT now() + INTERVAL '7 days',
    approved_by UUID REFERENCES public.users(id),
    approval_id UUID,
    submitted_at TIMESTAMPTZ,
    version INT DEFAULT 1,
    model_name TEXT,
    model_version TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON public.submissions(tenant_id, status);

-- ============================================
-- Agent 运行时表
-- ============================================

-- agent_runs（Agent 运行记录）
CREATE TABLE public.agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES public.tenants(id) NOT NULL,
    session_id TEXT,
    actor_user_id UUID REFERENCES public.users(id) NOT NULL,
    goal TEXT,
    -- 用户原始输入
    status TEXT DEFAULT 'RUNNING',
    -- RUNNING / COMPLETED / FAILED / CANCELLED
    selected_skills JSONB DEFAULT '[]',
    steps JSONB DEFAULT '[]',
    -- [{step_id, skill_name, input_summary, output_summary, tool_calls[], duration_ms, status}]
    artifacts JSONB DEFAULT '[]',
    -- [{type, url, description}]
    model_name TEXT,
    model_version TEXT,
    error TEXT,
    started_at TIMESTAMPTZ DEFAULT now(),
    ended_at TIMESTAMPTZ
);
CREATE INDEX ON public.agent_runs(tenant_id, actor_user_id);

-- approvals（审批）
CREATE TABLE public.approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES public.tenants(id) NOT NULL,
    run_id UUID REFERENCES public.agent_runs(id),
    action TEXT NOT NULL,
    -- SUBMIT_RECOMMENDATION / EXPORT_CSV / SCHEDULE_INTERVIEW
    resource_type TEXT NOT NULL,
    resource_id UUID NOT NULL,
    state_diff JSONB,
    -- {before: {}, after: {}}
    token TEXT UNIQUE DEFAULT encode(gen_random_bytes(32), 'hex'),
    token_expires_at TIMESTAMPTZ DEFAULT now() + INTERVAL '1 hour',
    status TEXT DEFAULT 'PENDING',
    -- PENDING / APPROVED / REJECTED / EXPIRED
    requested_by UUID REFERENCES public.users(id) NOT NULL,
    reviewed_by UUID REFERENCES public.users(id),
    reviewed_at TIMESTAMPTZ,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON public.approvals(tenant_id, status);

-- audit_logs（审计日志）
CREATE TABLE public.audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES public.tenants(id) NOT NULL,
    run_id UUID REFERENCES public.agent_runs(id),
    event_type TEXT NOT NULL,
    -- SKILL_EXECUTED / STATE_CHANGED / APPROVAL_REQUESTED / APPROVAL_DECIDED
    -- DATA_EXPORTED / USER_LOGIN / CANDIDATE_CREATED / SUBMISSION_SUBMITTED
    resource_type TEXT,
    resource_id UUID,
    approval_id UUID REFERENCES public.approvals(id),
    actor_user_id UUID REFERENCES public.users(id),
    tool_args_hash TEXT,
    state_diff JSONB,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON public.audit_logs(tenant_id, created_at);
CREATE INDEX ON public.audit_logs(run_id);

-- ============================================
-- 事件队列（替代 Vercel Cron 的本地方案）
-- ============================================

-- automation_events（异步事件队列）
CREATE TABLE public.automation_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES public.tenants(id) NOT NULL,
    type TEXT NOT NULL,
    -- PARSE_RESUME / VECTORIZE_CANDIDATE / VECTORIZE_JOB /
    -- DEDUPE_CHECK / FOLLOWUP_REMINDER / CONTRACT_REMINDER
    entity_id UUID,
    payload JSONB DEFAULT '{}',
    status TEXT DEFAULT 'PENDING',
    -- PENDING / PROCESSING / DONE / FAILED
    scheduled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ,
    error TEXT,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON public.automation_events(status, scheduled_at);
```

### 3.2 字段安全分级

| 级别 | 字段示例 | UI 策略 | 导出策略 |
|------|---------|---------|---------|
| public | company name, job title, city | 直接显示 | 可导出 |
| business | salary range, match score, stage | 按角色显示 | 可导出 |
| pii | full name, email, phone | consultant 脱敏显示 | 需审批 |
| sensitive_pii | 证件号、银行账号 | 仅 owner 可见 | 禁止导出 |

---

## 四、RBAC 权限矩阵

| 角色 | 读权限 | 写权限 | 限制 |
|------|--------|--------|------|
| owner | 本租户全部 | 本租户全部 | 敏感导出仍需审批 |
| team_admin | 本团队全部 | 职位、候选人、草稿、排期 | 不能越团队访问 |
| consultant | 本团队职位、候选人、草稿、run | 创建草稿、发起审批、写跟进 | 不能正式提交/导出 |
| researcher | 候选人基础档案、职位画像 | 导入简历、标注、发起去重 | 不能看财务和完整 PII |
| reviewer | 与审批相关对象 | 批准/拒绝 command | 不可自批高风险动作 |
| finance_lite | Placement/Invoice lite | 更新回款与开票状态 | 看不到无关原始简历 |

---

## 五、分阶段执行计划

### 总览

| 阶段 | 名称 | 核心产出 | 估时 | 累计 |
|------|------|---------|------|------|
| P0 | 蓝图与规范 | PRD / AGENTS.md / OpenAPI / ER 草图 | 1 周 | 1 周 |
| P1 | 工程底座 | 项目骨架 / DB / Auth / 文件上传 | 2 周 | 3 周 |
| P2 | 业务内核 | 客户 / 职位 / 候选人 / Pipeline CRUD | 2 周 | 5 周 |
| P3 | Skill MVP | 解析 / 去重 / 评分 / 草稿 / Registry | 2.5 周 | 7.5 周 |
| P4 | Agent + Chat | Agent Runtime / 意图理解 / Chat UI | 1.5 周 | 9 周 |
| P5 | WebUI 工作台 | 列表页 / 详情页 / 看板 / 审批中心 | 2 周 | 11 周 |
| P6 | 审计与稳定化 | 审计回放 / Docker / CI / 备份 | 1.5 周 | 12.5 周 |
| P7 | 试点与打磨 | 真实用户测试 / Bug 修复 / 文档 | 1 周 | 13.5 周 |

---

## P0 · 蓝图与规范（Week 1）

**目标**：冻结首发范围，建立开发规范，让 Codex 有上下文可用

---

### P0-T1 · 初始化 Monorepo

**Codex Prompt**：
```
创建 huntflow 项目 monorepo 结构：

目录布局：
huntflow/
├── apps/
│   ├── api/            # FastAPI 后端
│   │   ├── main.py
│   │   ├── routes/
│   │   ├── services/
│   │   ├── middleware/
│   │   └── tests/
│   └── web/            # Next.js 前端
├── skills/             # Agent Skills（每个 skill 一个目录）
│   └── README.md
├── agent/              # Agent Runtime
│   ├── core.py
│   ├── registry.py
│   ├── executor.py
│   └── conversation.py
├── utils/              # 共享工具
│   ├── llm_router.py
│   ├── embedding.py
│   ├── pdf_generator.py
│   ├── wecom_notifier.py
│   ├── storage.py
│   └── crypto.py
├── workers/            # 异步 Worker
├── migrations/         # DB 迁移脚本
├── scripts/            # 脚本（seed / backup）
├── docs/               # 文档
│   ├── prd.md
│   ├── adr-001.md
│   └── events.md
├── AGENTS.md           # Codex 上下文规则
├── CLAUDE.md           # Claude Code 上下文规则
├── docker-compose.yml
├── .env.example
├── requirements.txt
└── README.md

requirements.txt 包含：
fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg alembic
pydantic pydantic-settings python-dotenv
httpx aiofiles python-multipart
dashscope
weasyprint jinja2
redis
pgvector
passlib[bcrypt] python-jose[cryptography]
pytest pytest-asyncio
apscheduler

.env.example 包含：
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/huntflow
REDIS_URL=redis://localhost:6379/0
DASHSCOPE_API_KEY=
DEEPSEEK_API_KEY=
WECOM_CORP_ID=
WECOM_APP_SECRET=
WECOM_AGENT_ID=
JWT_SECRET=
STORAGE_PATH=./storage
ALIYUN_ASR_APPKEY=
ALIYUN_ACCESS_KEY_ID=
ALIYUN_ACCESS_KEY_SECRET=

apps/api/main.py 实现：
- FastAPI app
- GET /health 返回 {"status": "ok", "version": "0.1.0"}
- CORS 中间件
- 异步启动/关闭事件（DB 连接池）

只输出文件内容，不要解释。
```

**检查点 P0-T1**：
```bash
cd huntflow && pip install -r requirements.txt
uvicorn apps.api.main:app --reload
curl http://localhost:8000/health
# 期望：{"status":"ok","version":"0.1.0"}
```
验收：`☐` HTTP 200 返回正确 JSON `☐` 目录结构完整

---

### P0-T2 · 写 AGENTS.md

**Codex Prompt**：
```
创建 AGENTS.md，内容为 Codex 代理的操作约束：

# AGENTS.md — HuntFlow 开发规则

## 项目概述
猎头顾问 AI 工作台。薄内核 + Skills + WebUI + Agent 入口。

## 核心约束
1. 每次任务只做一个行为变更，必须带测试和回滚方案
2. 所有 API 端点必须带 tenant_id scope，跨租户查询为 0
3. 所有 AI 生成内容只写 draft 表，不改正式状态
4. 正式写操作必须经过 approval token
5. 所有 AI 调用必须记录 model_name / model_version / prompt_version

## 技术规则
- Python 3.12 + FastAPI + SQLAlchemy async
- 所有路由函数使用 async def
- Pydantic v2 做请求/响应模型
- 数据库操作使用 SQLAlchemy ORM，不写裸 SQL
- 测试使用 pytest + pytest-asyncio
- 环境变量通过 pydantic-settings 管理

## 禁止项
- 不允许在 Skill 中直接修改 pipeline/submission 正式状态
- 不允许在 API 中硬编码 LLM 模型名称，必须走 llm_router
- 不允许存储未加密的手机号/邮箱
- 不允许批量导出未脱敏数据
- 不允许引入 RPA/爬虫相关依赖

## 文件命名
- routes: apps/api/routes/{resource}.py
- services: apps/api/services/{resource}_service.py
- skills: skills/{skill_name}/skill.py + SKILL.md
- tests: apps/api/tests/test_{resource}.py

## 提交前检查
- [ ] pytest 全部通过
- [ ] 新端点已加入 OpenAPI
- [ ] 涉及 PII 的字段已标注安全级别
- [ ] 新增 skill 有 SKILL.md
```

**检查点 P0-T2**：
验收：`☐` AGENTS.md 存在且内容完整 `☐` CLAUDE.md 同步创建（内容与 AGENTS.md 一致）

---

### P0-T3 · 写 ADR-001 架构决策

**Codex Prompt**：
```
创建 docs/adr-001.md：

# ADR-001: 薄内核 + Skills + WebUI 架构

## 状态：已采纳

## 上下文
我们需要为独立猎头顾问构建一个 AI 辅助工作台。

## 决策
采用"薄内核 + Skills + WebUI"三层架构，而不是传统的全功能 ATS/CRM。

### 业务真相走 REST
- 候选人、职位、Pipeline 等核心数据通过 REST API 管理
- 这些是"真相源"（source of truth），不依赖任何 AI 框架

### 异步联动走 Events
- 简历上传后触发解析、解析完成后触发去重、去重后触发评分
- 使用 PostgreSQL 表 + Worker 模式，不引入消息队列

### 模型可见面走 MCP/Skills
- Agent 通过 Skill Registry 发现可用能力
- 只读 Skill 默认开放，写操作 Skill 需要 approval token

## 为什么不做全功能 ATS
- 独立开发者精力有限
- 猎头核心工作集中在6个动作
- 合同/财务/试用期可以后补

## 为什么不做 RPA 爬取
- PIPL 和平台 ToS 风险
- 维护成本远超收益
- 合规替代方案足够

## 后果
- 首发功能较少，但每个都可用
- 需要猎头手动导入候选人（CSV/简历上传）
- 未来可扩展但内核不需要重构
```

**检查点 P0-T3**：
验收：`☐` ADR 文档存在 `☐` 明确说明了为什么不做全功能 ATS 和 RPA

---

### P0-T4 · 写 OpenAPI Skeleton + 事件命名表

**Codex Prompt**：
```
1. 创建 docs/openapi.yaml，至少包含以下端点的 stub：

GET    /health
POST   /api/v1/auth/login
POST   /api/v1/auth/register

GET    /api/v1/clients
POST   /api/v1/clients
GET    /api/v1/clients/{id}
PATCH  /api/v1/clients/{id}

GET    /api/v1/job-orders
POST   /api/v1/job-orders
GET    /api/v1/job-orders/{id}
PATCH  /api/v1/job-orders/{id}

GET    /api/v1/candidates
POST   /api/v1/candidates
GET    /api/v1/candidates/{id}
PATCH  /api/v1/candidates/{id}
POST   /api/v1/candidates/import
POST   /api/v1/candidates/dedupe/review
GET    /api/v1/candidates/search

GET    /api/v1/pipelines
POST   /api/v1/pipelines
PATCH  /api/v1/pipelines/{id}/stage
GET    /api/v1/job-orders/{id}/longlist
GET    /api/v1/job-orders/{id}/shortlist

POST   /api/v1/match-scores/run
POST   /api/v1/submissions/draft
GET    /api/v1/submissions/{id}
POST   /api/v1/submissions/{id}/submit

POST   /api/v1/approvals
GET    /api/v1/approvals
PATCH  /api/v1/approvals/{id}

POST   /api/v1/agent/chat
GET    /api/v1/runs/{id}
GET    /api/v1/runs/{id}/replay

每个端点只需要 summary + 最小 requestBody/response schema

2. 创建 docs/events.md 事件命名表：

| Topic | 触发时机 | 消费者 |
|-------|---------|--------|
| resume.uploaded | 简历文件上传完成 | parse_worker |
| resume.parsed | 简历解析完成 | dedupe_worker, vectorize_worker |
| candidate.created | 候选人记录创建 | vectorize_worker |
| candidate.deduped | 去重确认完成 | 无（日志） |
| job_order.created | 职位创建 | vectorize_worker |
| match.scored | 短名单评分完成 | 无（WebUI 刷新） |
| submission.drafted | 推荐草稿生成 | approval_center |
| approval.requested | 待审批 | wecom_notifier |
| approval.decided | 审批已决定 | command_executor |
| pipeline.stage_changed | Pipeline 阶段变更 | audit_logger |
```

**检查点 P0-T4**：
验收：`☐` openapi.yaml 可通过 lint `☐` 至少 20 个端点有 stub `☐` events.md 包含 10+ 事件定义

---

### P0-T5 · 写 Seed 数据脚本

**Codex Prompt**：
```
创建 scripts/seed.py：

用 SQLAlchemy 向数据库插入演示数据：

1. 创建 1 个 tenant "演示猎头公司"
2. 创建 1 个 team "技术猎头组"
3. 创建 2 个 user：
   - owner@demo.com (role=owner, name="张三")
   - consultant@demo.com (role=consultant, name="李四")
4. 创建 3 个 client：
   - "腾讯" (stage=ACTIVE, industry="互联网")
   - "字节跳动" (stage=SIGNED, industry="互联网")
   - "宁德时代" (stage=LEAD, industry="新能源")
5. 创建 3 个 job_order：
   - "CFO" for 腾讯 (salary 80-120w)
   - "VP Engineering" for 字节跳动 (salary 100-150w)
   - "财务总监" for 宁德时代 (salary 60-90w)
6. 创建 5 个 candidate（含不同背景）：
   - 各有不同的 current_company / title / tags / source_type
7. 创建 5 个 pipeline（把候选人关联到岗位）

所有 PII 字段使用虚构数据。
脚本可通过 `python scripts/seed.py` 一条命令执行。
执行前检查是否已有数据，避免重复插入。
```

**检查点 P0-T5**：
```bash
python scripts/seed.py
# 期望：终端打印 "Seeded: 1 tenant, 1 team, 2 users, 3 clients, 3 jobs, 5 candidates, 5 pipelines"
```
验收：`☐` 一条命令灌库成功 `☐` 重复执行不报错

---

### P0 阶段 Gate

| Gate | 通过条件 |
|------|---------|
| 业务 Gate | P0/P1/非目标写清 |
| 代码 Gate | monorepo 可启动，health 端点正常 |
| 数据 Gate | seed 脚本可执行 |
| 合规 Gate | AGENTS.md 包含 PII 处理规则 |
| 运营 Gate | 有演示数据 |

---

## P1 · 工程底座（Week 2-3）

**目标**：数据库可连、认证可用、文件可上传、权限可控

---

### P1-T1 · 数据库迁移

**Codex Prompt**：
```
使用 Alembic 初始化数据库迁移：

1. alembic init migrations
2. 配置 alembic.ini 和 env.py，使用 DATABASE_URL 环境变量
3. 创建第一个 migration，包含"三、数据模型"中的全部 14 张表
4. 确保 migration 可以 upgrade 和 downgrade

同时创建 apps/api/database.py：
- 异步引擎（create_async_engine）
- 异步 Session 工厂
- Base = declarative_base()

创建 apps/api/models/ 目录，每张表一个文件：
- tenant.py, team.py, user.py, client.py, job_order.py
- candidate.py, resume_asset.py, pipeline.py
- match_score.py, submission.py
- agent_run.py, approval.py, audit_log.py
- automation_event.py

每个 model 类继承 Base，字段与 SQL schema 完全一致。
```

**检查点 P1-T1**：
```bash
alembic upgrade head
# 在 psql 验证：
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' ORDER BY table_name;
# 期望：14 张表全部存在

alembic downgrade -1
alembic upgrade head
# 期望：downgrade 和 re-upgrade 均无报错
```
验收：`☐` 14 张表全部存在 `☐` pgvector 扩展已启用 `☐` migration 可回退

---

### P1-T2 · JWT 认证 + RBAC 中间件

**Codex Prompt**：
```
1. apps/api/routes/auth.py：
POST /api/v1/auth/register  注册用户
  body: {email, password, name, tenant_name}
  首次注册自动创建 tenant + team + user(role=owner)
POST /api/v1/auth/login  登录
  body: {email, password}
  返回: {access_token, user: {id, name, email, role, tenant_id, team_id}}

使用 passlib 做密码哈希，python-jose 做 JWT。
JWT payload 包含：user_id, tenant_id, team_id, role

2. apps/api/middleware/auth.py：
- get_current_user 依赖注入函数
- 从 Authorization: Bearer {token} 提取 JWT
- 解析后返回 CurrentUser(id, tenant_id, team_id, role)
- 未登录返回 401

3. apps/api/middleware/rbac.py：
- require_role(*roles) 装饰器
- require_same_tenant 检查（所有查询自动加 tenant_id 条件）
- require_same_team 检查（team 级别的资源隔离）

示例用法：
@router.get("/clients")
async def list_clients(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 自动只返回 user.tenant_id 下的客户
    ...
```

**检查点 P1-T2**：
```bash
# 注册
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@demo.com","password":"test123","name":"测试","tenant_name":"测试公司"}'
# 期望：返回 access_token

# 登录
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@demo.com","password":"test123"}'
# 期望：返回 access_token + user 信息

# 无 token 访问
curl http://localhost:8000/api/v1/clients
# 期望：401

# 用 token 访问
curl http://localhost:8000/api/v1/clients \
  -H "Authorization: Bearer {token}"
# 期望：200，空列表 []
```
验收：`☐` 注册/登录正常 `☐` 无 token 返回 401 `☐` 跨租户查询返回空

---

### P1-T3 · LLM 路由层 + 工具类

**Codex Prompt**：
```
创建以下工具文件：

1. utils/llm_router.py
实现 LLMRouter 类：
- async def chat(prompt, use_case="general", system=None) -> str
  根据 use_case 选择模型（参考 2.3 节的 PROVIDER_CONFIG）
- async def chat_json(prompt, use_case="general", system=None) -> dict
  强制返回 JSON，自动处理 markdown 代码块包裹
- async def get_embedding(text) -> list[float]
  返回 512 维向量
- 所有调用记录 model_name, model_version 到返回元数据中
- 主力不可用时自动降级到 fallback

2. utils/wecom_notifier.py
- async def push_text(wecom_userid: str, message: str) -> bool
- 自动获取并缓存 access_token（2小时过期）
- 环境变量不存在时 graceful skip（不报错，只记日志）

3. utils/storage.py
- class StorageAdapter:
  - async def upload(file_bytes, key, content_type) -> str  # 返回可访问 URL
  - async def download(key) -> bytes
  - async def delete(key) -> bool
- 首发实现 LocalStorageAdapter（存到 STORAGE_PATH 目录）
- 预留 S3StorageAdapter 接口

4. utils/crypto.py
- def encrypt_pii(plaintext: str) -> str  # AES-256-GCM 加密
- def decrypt_pii(ciphertext: str) -> str
- def mask_phone(phone: str) -> str  # 138****1234
- def mask_email(email: str) -> str  # t***@demo.com
- def compute_identity_hash(name, phone_last4, email_domain) -> str

每个文件不超过 100 行，所有异常记录日志后抛出。
```

**检查点 P1-T3**：
```python
# tests/test_utils.py
import asyncio, pytest

async def test_llm_chat():
    from utils.llm_router import LLMRouter
    router = LLMRouter()
    result = await router.chat("用一句话介绍猎头行业")
    assert len(result) > 10
    meta = await router.chat_json('返回JSON：{"name":"test","score":9}')
    assert meta["name"] == "test"

async def test_crypto():
    from utils.crypto import encrypt_pii, decrypt_pii, mask_phone, compute_identity_hash
    encrypted = encrypt_pii("13800138000")
    assert decrypt_pii(encrypted) == "13800138000"
    assert mask_phone("13800138000") == "138****8000"
    h1 = compute_identity_hash("张三", "8000", "demo.com")
    h2 = compute_identity_hash("张三", "8000", "demo.com")
    assert h1 == h2  # 相同输入相同 hash
```
验收：`☐` LLM 调用成功 `☐` JSON 解析正确 `☐` 加密/解密可逆 `☐` 脱敏格式正确

---

### P1-T4 · 前端初始化

**Codex Prompt**：
```
在 apps/web/ 初始化 Next.js 14 项目：

1. npx create-next-app@14 . --typescript --tailwind --app --src-dir
2. 安装：shadcn/ui + SWR + axios
3. 配置：
   - lib/api.ts: axios 封装，自动在 header 带 JWT，401 跳登录
   - lib/auth.ts: 登录/注册/获取当前用户
   - middleware.ts: 未登录访问任何页面跳转 /login

4. 页面：
   - app/(auth)/login/page.tsx: 邮箱+密码登录表单
   - app/(auth)/register/page.tsx: 注册表单
   - app/(dashboard)/layout.tsx: 主布局
     左侧导航栏（图标+文字，使用 lucide-react）：
     - 📊 工作台  /
     - 👥 客户    /clients
     - 📋 岗位    /job-orders
     - 👤 候选人  /candidates
     - 📁 报告    /submissions
     - 💬 对话    /chat
     - ✅ 审批    /approvals
     - 📜 审计    /audit
   - app/(dashboard)/page.tsx: 工作台首页（先放占位内容）

5. 颜色方案：专业蓝色调，参考 Moka HR 的视觉风格
```

**检查点 P1-T4**：
```bash
cd apps/web && npm run dev
# 访问 localhost:3000
```
验收：`☐` 访问 / 跳转到 /login `☐` 登录成功后显示侧边导航 `☐` 8 个导航链接点击后 URL 变化

---

### P1 阶段 Gate

| Gate | 通过条件 |
|------|---------|
| 业务 Gate | 可注册、登录、看到空的工作台 |
| 代码 Gate | migration 可 up/down，测试通过 |
| 数据 Gate | seed 脚本在新 schema 上可执行 |
| 合规 Gate | PII 加密存储已实现 |

---

## P2 · 业务内核（Week 4-5）

**目标**：客户、职位、候选人、Pipeline 的 CRUD 全部可用

---

### P2-T1 · 客户 CRUD + 前端

**Codex Prompt**：
```
1. apps/api/routes/clients.py 实现：
GET    /api/v1/clients              列表，支持 ?stage= ?search= 筛选
POST   /api/v1/clients              创建客户
GET    /api/v1/clients/{id}         详情
PATCH  /api/v1/clients/{id}         更新
PATCH  /api/v1/clients/{id}/stage   阶段流转

所有查询自动加 tenant_id 过滤。
阶段流转只允许正向：LEAD → CONTACTED → NEGOTIATING → SIGNED → ACTIVE
每次阶段变更记录 {stage, at, by} 到 metadata。

2. apps/api/services/client_service.py：
- list_clients(tenant_id, stage, search, skip, limit)
- create_client(tenant_id, owner_id, data)
- update_client(tenant_id, client_id, data)
- advance_stage(tenant_id, client_id, new_stage, user_id)

3. apps/api/tests/test_clients.py：
- test_create_client
- test_list_clients_filtered_by_tenant（跨租户隔离）
- test_advance_stage_forward（正向成功）
- test_advance_stage_backward（逆向失败 400）

4. 前端 app/(dashboard)/clients/page.tsx：
- 表格：公司名 / 行业 / 阶段(彩色 badge) / 负责人 / 下次跟进 / 操作
- 阶段颜色：LEAD=灰 CONTACTED=蓝 NEGOTIATING=黄 SIGNED=绿 ACTIVE=紫
- 顶部：搜索框 + 阶段筛选 + 「新建客户」按钮

5. 前端 app/(dashboard)/clients/[id]/page.tsx：
- 基本信息卡片 + 阶段流转按钮（只显示下一个合法阶段）
- 联系人列表（contacts JSONB）+ 添加联系人表单
```

**检查点 P2-T1**：
```
☐ GET /clients 返回当前租户的客户列表（不含其他租户）
☐ POST /clients 创建成功
☐ PATCH /stage LEAD→CONTACTED 成功
☐ PATCH /stage SIGNED→LEAD 返回 400
☐ 前端列表渲染正确，阶段筛选生效
☐ 客户详情页阶段流转按钮只显示合法下一步
```

---

### P2-T2 · 职位 CRUD + AI 能力 + 前端

**Codex Prompt**：
```
1. apps/api/routes/job_orders.py 实现：
GET    /api/v1/job-orders            列表，?status= ?client_id= 筛选
POST   /api/v1/job-orders            创建
GET    /api/v1/job-orders/{id}       详情
PATCH  /api/v1/job-orders/{id}       更新（version 自增）
PATCH  /api/v1/job-orders/{id}/status 状态变更

每次更新 version 自增，保留变更历史。

2. skills/jd_generate/ 目录：
SKILL.md：
  name: jd_generate
  type: draft-write
  description: 根据职位名称和关键要求生成规范 JD
  input: {job_order_id, key_requirements}
  output: {jd_text}

skill.py：
  async def execute(input, ctx) -> SkillResult:
    1. 读取 job_order 基本信息
    2. 调用 llm_router.chat(prompt, use_case="report_generation")
       prompt: "你是资深猎头顾问，为以下职位生成规范 JD，
               包含：职责、任职要求、加分项三部分。
               职位：{title}，关键要求：{key_requirements}"
    3. 更新 job_orders.jd
    4. 返回 SkillResult(success=True, data={jd_text}, model_meta={...})

3. skills/search_plan_generate/ 目录：
SKILL.md + skill.py：
  input: {job_order_id}
  output: {search_plan JSON, pdf_url}
  步骤：
    1. 读取 job_order 信息
    2. 调用 llm_router.chat_json 生成寻访计划：
       {candidate_profile, target_companies[{name,reason}],
        search_keywords[], must_haves[], nice_to_haves[],
        salary_market_insight, timeline{longlist_by, shortlist_by}}
    3. 更新 job_orders.search_plan
    4. 生成 PDF（utils/pdf_generator.py）
    5. 返回结果 + model_meta

4. 前端 app/(dashboard)/job-orders/page.tsx：
- 卡片网格：职位名 / 客户名 / 状态 badge / 薪资范围 / 截止日
- 顶部：状态筛选 + 「新建职位」按钮

5. 前端 app/(dashboard)/job-orders/[id]/page.tsx：
- Tabs：基本信息 | JD | 寻访计划 | Pipeline 看板
- JD Tab：显示 JD + 「AI 生成 JD」按钮 + 编辑保存
- 寻访计划 Tab：结构化展示 + 下载 PDF + 「生成寻访计划」按钮
```

**检查点 P2-T2**：
```
☐ 职位 CRUD 全部端点正常
☐ JD 生成包含 职责/要求/加分项
☐ 寻访计划包含 ≥10 家目标公司，每家有推荐理由
☐ version 字段在每次更新后自增
☐ PDF 正常生成可下载
☐ 前端卡片展示正确，Tabs 切换正常
```

---

### P2-T3 · 候选人 CRUD + 简历解析 + 去重

**Codex Prompt**：
```
1. apps/api/routes/candidates.py 实现：
GET    /api/v1/candidates            列表，?search= ?tags= 筛选
POST   /api/v1/candidates            手动创建
GET    /api/v1/candidates/{id}       详情（PII 脱敏展示）
PATCH  /api/v1/candidates/{id}       更新
POST   /api/v1/candidates/import     上传简历文件（PDF/Word/文本）
POST   /api/v1/candidates/dedupe/review  处理疑似重复

候选人列表中 phone 和 email 默认脱敏（mask_phone / mask_email）。
只有 owner/team_admin 角色可以看到完整 PII。

2. apps/api/services/candidate_service.py：
- import_resume(tenant_id, user_id, file) -> {candidate_id, parse_status}
  a. 保存文件到 storage
  b. 创建 resume_asset 记录 (parse_status=PENDING)
  c. 创建 candidate 记录（基础信息待解析填充）
  d. 写 automation_event(PARSE_RESUME)
  e. 返回候选人 ID

- dedupe_check(tenant_id, candidate_id) -> {duplicates[]}
  a. 计算 normalized_identity_hash
  b. 查找相同 hash 的已有候选人
  c. 返回疑似重复列表

- dedupe_review(tenant_id, case_id, decision) -> {merged_id}
  decision: MERGE（合并到已有）/ KEEP_BOTH（保留两条）/ REJECT（删除新的）

3. skills/resume_parse/ 目录：
SKILL.md + skill.py：
  input: {candidate_id}
  步骤：
    1. 读取 resume_asset，下载文件
    2. 用 pdfplumber（PDF）或 python-docx（Word）提取文本
    3. 调用 llm_router.chat_json(use_case="resume_parsing")：
       {name, current_company, current_title, years_experience,
        education, skills[], work_history[], industries[]}
    4. 更新 candidates.resume_parsed / resume_summary
    5. 自动打标签（industry_tags / function_tags / level_tag）
    6. 计算 identity_hash 并写入
    7. 更新 resume_asset.parse_status = DONE
    8. 写 automation_event(DEDUPE_CHECK)
    9. 写 automation_event(VECTORIZE_CANDIDATE)

4. workers/parse_worker.py：
  轮询 automation_events 中 type=PARSE_RESUME 且 status=PENDING 的记录
  调用 resume_parse skill 执行

5. 前端 app/(dashboard)/candidates/page.tsx：
- 表格：姓名 / 当前公司 / 当前职位 / 城市 / 来源 / 标签 / 操作
- PII 默认脱敏显示
- 顶部：搜索 + 标签筛选 + 「上传简历」按钮 + 「批量导入」按钮

6. 「上传简历」Dialog：
- 拖拽上传区（支持 PDF/Word/TXT）
- 上传后显示解析状态（PENDING → PARSING → DONE / FAILED）
- 解析完成后显示提取的结构化信息，可手动修正

7. 「去重审核」Dialog（当检测到重复时弹出）：
- 左右对比展示两条候选人信息
- 三个按钮：合并 / 保留两条 / 删除新的
```

**检查点 P2-T3**：
```
☐ 上传 PDF 简历 → resume_asset 创建 → parse_status 最终变为 DONE
☐ resume_parsed 包含 name / current_company / work_history
☐ Word 格式简历也能解析
☐ 解析失败时 parse_status=FAILED，parse_error 有错误信息
☐ identity_hash 相同的候选人触发去重检查
☐ 去重审核三种决策都能正常执行
☐ 前端候选人列表 PII 默认脱敏
☐ owner 角色可以看到完整 PII
```

---

### P2-T4 · Pipeline + 匹配评分 + 看板

**Codex Prompt**：
```
1. apps/api/routes/pipelines.py 实现：
GET    /api/v1/pipelines                  列表，?job_order_id= ?stage= 筛选
POST   /api/v1/pipelines                  创建（候选人关联到岗位）
PATCH  /api/v1/pipelines/{id}/stage       阶段流转
GET    /api/v1/job-orders/{id}/longlist   该岗位 Longlist（按 score 降序）
GET    /api/v1/job-orders/{id}/shortlist  该岗位 Shortlist

阶段流转记录到 metadata.stage_history：
[{stage, at, by, reason}]

2. skills/candidate_score/ 目录：
SKILL.md + skill.py：
  input: {job_order_id, candidate_ids[]}
  output: {scores: [{candidate_id, score, reason_codes, gap_items, priority}]}
  步骤：
    1. 读取 job_order（must_have / nice_to_have / search_plan）
    2. 批量读取 candidates
    3. 对每个候选人调用 llm_router.chat_json(use_case="report_generation")：
       "对照岗位要求评估候选人匹配度，输出：
        {score:0-100, reason_codes:[], gap_items:[], priority:'HIGH/MEDIUM/LOW'}"
    4. 批量写入 match_scores 表（含 model_name / model_version）
    5. 更新 pipeline 记录（如果已有关联）
    6. 返回评分结果 + model_meta

3. POST /api/v1/match-scores/run 端点：
  body: {job_order_id, candidate_ids: []}
  调用 candidate_score skill
  返回: {run_id, scores: [...]}

4. 前端：职位详情页的 Pipeline 看板 Tab
- 8 列 Kanban（使用 @dnd-kit/core 拖拽）：
  SOURCED | SHORTLISTED | PHONE_INTERVIEW | SUBMITTED |
  CLIENT_INTERVIEW | OFFER | PLACED | REJECTED
- 候选人卡片：姓名 / 公司 / 匹配分 badge / 操作菜单
- 操作菜单：晋升 / 淘汰(需填原因) / 生成外联消息 / 查看详情
- 看板上方：「批量评分」按钮（选中候选人后一键评分）
```

**检查点 P2-T4**：
```
☐ 创建 Pipeline 后在 Longlist 可见
☐ 匹配评分返回 score + reason_codes + gap_items
☐ reason_codes 有具体内容（不是空数组或通用话术）
☐ match_scores 表记录了 model_name 和 model_version
☐ 看板 8 列渲染正确
☐ 拖拽候选人卡片，stage 更新（API 调用成功）
☐ 淘汰操作需填写原因
```

---

### P2 阶段 Gate

| Gate | 通过条件 |
|------|---------|
| 业务 Gate | 可创建客户→创建职位→上传候选人→评分→看板展示 |
| 代码 Gate | 所有 API 测试通过，跨租户测试为 0 |
| 数据 Gate | seed 数据可在新端点中正常查询 |
| 合规 Gate | PII 加密存储，UI 脱敏展示 |

---

## P3 · Skill MVP（Week 6-7.5）

**目标**：推荐草稿、外联话术、向量搜索全部跑通

---

### P3-T1 · Skill Registry + 执行器

**Codex Prompt**：
```
1. agent/registry.py — Skill 注册中心
class SkillRegistry:
    def __init__(self, skills_dir="skills/"):
        self.skills = {}

    def discover(self):
        """扫描 skills/ 目录，自动发现所有 SKILL.md 并注册"""
        遍历 skills/*/SKILL.md，解析 name, type, description, input, output
        加载对应的 skill.py 模块

    def get(self, skill_name) -> SkillMeta:
        """返回 skill 元数据 + execute 函数引用"""

    def list_by_type(self, skill_type) -> list:
        """按类型筛选 skills：read / draft-write / write"""

    def get_allowed_tools(self, user_role) -> list:
        """根据用户角色返回允许的 skill 列表
        read 和 draft-write 对所有角色开放
        write 只对 owner/team_admin 开放"""

2. agent/executor.py — Skill 执行器
class SkillExecutor:
    async def execute_query(self, skill_name, input_data, ctx) -> SkillResult:
        """执行只读 skill，记录 agent_run"""
        1. 创建 agent_run 记录
        2. 调用 skill.execute(input_data, ctx)
        3. 记录步骤到 agent_run.steps
        4. 写 audit_log
        5. 返回 SkillResult

    async def execute_draft(self, skill_name, input_data, ctx) -> SkillResult:
        """执行草稿 skill，只写 draft 表"""
        同上，但标注 step.type = "draft-write"

    async def execute_command(self, skill_name, input_data, ctx, approval_token) -> SkillResult:
        """执行写操作 skill，需要 approval token"""
        1. 验证 approval token（未过期、状态为 APPROVED）
        2. 执行 skill
        3. 记录 state_diff
        4. 写 audit_log
        5. 返回结果

3. agent/models.py：
@dataclass
class SkillContext:
    user_id: str
    tenant_id: str
    team_id: str
    role: str
    db: AsyncSession

@dataclass
class SkillResult:
    success: bool
    data: dict = None
    error: str = None
    model_meta: dict = None  # {model_name, model_version, prompt_version}
    need_approval: bool = False
    approval_preview: dict = None  # 需要审批时展示的预览

4. 每个 skill 目录下的 SKILL.md 格式：
---
name: skill_name
type: read | draft-write | write
description: 一句话描述
input_schema: {field: type}
output_schema: {field: type}
---
# Skill Name
详细说明...
```

**检查点 P3-T1**：
```
☐ SkillRegistry.discover() 能发现已有的所有 skill
☐ 新增 skill 后无需改 runtime 代码，重新 discover 即可加载
☐ execute_command 无 approval token 时拒绝执行
☐ agent_run 记录包含完整的 steps 信息
☐ audit_log 写入成功
```

---

### P3-T2 · 推荐草稿 Skill

**Codex Prompt**：
```
skills/submission_draft_create/ 目录：

SKILL.md：
---
name: submission_draft_create
type: draft-write
description: 为指定岗位和候选人生成推荐报告草稿
input_schema:
  job_order_id: string
  candidate_id: string
  include_gap_analysis: boolean (default true)
output_schema:
  submission_id: string
  draft_markdown: string
  status: "draft"
---

skill.py：
async def execute(input_data, ctx) -> SkillResult:
    1. 读取 job_order（title / jd / must_have / search_plan）
    2. 读取 candidate（full_name / current_company / current_title / resume_parsed）
    3. 读取 match_score（如果已有）
    4. 构建 prompt，调用 llm_router.chat_json(use_case="report_generation")：
       "你是资深猎头顾问，为客户生成一份候选人推荐报告，包含：
        1. 候选人快照（一段话摘要）
        2. 与岗位匹配度分析（针对 must_have 逐条对应）
        3. 核心优势（2-3条，引用简历原文）
        4. 顾虑点及应对建议（1-2条）
        5. 猎头推荐意见（1段）
        如果 include_gap_analysis=true，额外输出 gap 分析"
    5. 创建 submissions 记录（status=DRAFT）
    6. 生成 PDF 并保存到 storage
    7. 返回 SkillResult(
         success=True,
         data={submission_id, draft_markdown, draft_content},
         model_meta={model_name, model_version, prompt_version}
       )

POST /api/v1/submissions/draft 端点：
  调用 executor.execute_draft("submission_draft_create", ...)
  返回 submission_id + draft_markdown

GET /api/v1/submissions/{id} 端点：
  返回 submission 详情

PATCH /api/v1/submissions/{id} 端点：
  手动编辑草稿内容（draft_markdown / draft_content）
  version 自增

前端 submissions 页面：
- 列表：候选人 / 岗位 / 状态 badge / 创建时间 / 操作
- 点击进入编辑页：
  左侧 Markdown 编辑器（可编辑草稿）
  右侧实时预览（渲染为推荐报告样式）
  底部按钮：保存 | 提交审批 | 下载 PDF
```

**检查点 P3-T2**：
```
☐ 推荐草稿生成成功，draft_markdown 非空
☐ 草稿内容包含：候选人快照 / 匹配分析 / 优势 / 顾虑 / 推荐意见
☐ submissions 表 status=DRAFT，不是 SUBMITTED
☐ PDF 生成可下载，中文无乱码
☐ 手动编辑后 version 自增
☐ 前端编辑器 + 预览正常工作
☐ model_meta 记录了模型版本信息
```

---

### P3-T3 · 外联话术 Skill

**Codex Prompt**：
```
skills/outreach_message_generate/ 目录：

SKILL.md：
---
name: outreach_message_generate
type: draft-write
description: 为候选人生成个性化外联话术（微信/邮件/电话）
input_schema:
  pipeline_id: string
  channel: wechat | email | phone
output_schema:
  messages: {wechat: string, email: {subject, body}, phone_script: string}
---

skill.py：
async def execute(input_data, ctx) -> SkillResult:
    1. 通过 pipeline_id 读取 candidate + job_order
    2. 构建 prompt：
       "根据候选人（{name}，{current_title}@{current_company}）和
        岗位（{title}，{client_name}）信息，生成三种个性化外联话术：
        - 微信消息（简短，150字以内）
        - 邮件（含主题行，正文300字以内）
        - 电话话术（开场白+核心话术+异议处理）
        话术必须包含候选人当前背景和岗位核心吸引点，
        不是通用模板。"
    3. 返回 SkillResult(
         success=True,
         data={messages},
         need_approval=False  # 只生成文本，不自动发送
       )

前端集成：
  Pipeline 看板中候选人卡片的「生成外联消息」菜单
  弹出 Dialog：三个 Tab（微信/邮件/电话）
  每个 Tab 显示生成的话术 + 「复制」按钮
  不自动发送，必须人工确认后复制使用
```

**检查点 P3-T3**：
```
☐ 三种格式全部生成
☐ 话术包含候选人姓名和当前公司
☐ 话术包含岗位核心吸引点（不是通用内容）
☐ 不同候选人+岗位组合的话术有明显差异
☐ 前端 Dialog 三个 Tab 切换正常，复制按钮可用
```

---

### P3-T4 · 向量语义搜索

**Codex Prompt**：
```
1. utils/embedding.py：
async def vectorize_text(text: str) -> list[float]:
    调用 llm_router.get_embedding(text)
    返回 512 维向量

2. apps/api/services/vector_service.py：
async def vectorize_candidate(candidate_id, db):
    读取 candidate → 构建摘要文本 → 向量化 → 更新 embedding

async def vectorize_job(job_order_id, db):
    读取 job_order → 构建 JD 摘要 → 向量化 → 更新 embedding

async def search_candidates(query: str, tenant_id, db, limit=20):
    1. query 文本向量化
    2. SQL: SELECT *, 1 - (embedding <=> query_vec) AS similarity
            FROM candidates WHERE tenant_id = ? AND embedding IS NOT NULL
            ORDER BY embedding <=> query_vec LIMIT ?
    3. 返回 [{candidate, similarity_score}]

async def match_job_to_talent_pool(job_order_id, tenant_id, db, limit=10):
    """新岗位创建时，自动从人才库匹配 Top10"""

3. GET /api/v1/candidates/search?q=互联网CFO 端点

4. workers/vectorize_worker.py：
   处理 VECTORIZE_CANDIDATE 和 VECTORIZE_JOB 事件

5. 前端候选人搜索：
   搜索框支持自然语言输入：「做过CFO的候选人」「互联网背景的财务总监」
   搜索结果按相似度排序，显示相似度分数百分比
```

**检查点 P3-T4**：
```
☐ 新建候选人后，embedding 字段有值（512 维向量）
☐ 搜索「互联网CFO」返回语义相关的候选人
☐ 搜索结果包含 similarity_score
☐ 搜索响应时间 < 2 秒
☐ 新岗位创建后自动匹配 Top10 候选人
```

---

### P3-T5 · 审批中心

**Codex Prompt**：
```
1. apps/api/routes/approvals.py：
POST   /api/v1/approvals              发起审批
GET    /api/v1/approvals              审批列表（按角色过滤可见范围）
GET    /api/v1/approvals/{id}         审批详情（含 state_diff）
PATCH  /api/v1/approvals/{id}         审批决定

审批创建时：
- 生成 approval token（32 字节随机，1 小时过期）
- 记录 state_diff（before / after 快照）
- 写 automation_event(APPROVAL_NOTIFICATION) → 企微通知 reviewer
- 写 audit_log(APPROVAL_REQUESTED)

审批决定时：
- APPROVED: 使用 approval token 执行正式写操作
- REJECTED: 记录拒绝原因
- token 过期自动标为 EXPIRED
- 写 audit_log(APPROVAL_DECIDED)

2. 需要审批的操作：
- 正式提交推荐报告（submission.status → SUBMITTED）
- 批量导出候选人 CSV
- 排程面试（P1 阶段）

3. 前端 app/(dashboard)/approvals/page.tsx：
- 待审批列表：类型 / 资源 / 申请人 / 时间 / 状态
- 点击查看 state_diff 对比（before/after）
- 批准/拒绝按钮
- reviewer 不能自批自己发起的高风险动作
```

**检查点 P3-T5**：
```
☐ 发起审批后 reviewer 企微收到通知
☐ 审批详情显示 state_diff
☐ 批准后 approval token 生效，正式写操作成功
☐ 拒绝后操作无法执行
☐ token 1 小时后过期，状态自动变为 EXPIRED
☐ 自批自己的高风险动作被拒绝
```

---

### P3 阶段 Gate

| Gate | 通过条件 |
|------|---------|
| 业务 Gate | 可从上传简历到生成推荐草稿完整走通 |
| 代码 Gate | Skill Registry 自动发现所有 skill |
| 数据 Gate | match_scores 记录含 model_version |
| 合规 Gate | 审批链生效，无 token 不能正式写入 |

---

## P4 · Agent + Chat（Week 8-9）

**目标**：猎头用自然语言触发任何功能

---

### P4-T1 · Agent Core + 意图理解

**Codex Prompt**：
```
1. agent/intent.py — 意图分类器

SKILL_INTENT_MAP = {
    "query_todo": "查询今日待办",
    "search_candidates": "搜索候选人",
    "score_candidates": "评分候选人",
    "generate_jd": "生成JD",
    "generate_search_plan": "生成寻访计划",
    "generate_outreach": "生成外联话术",
    "generate_submission_draft": "生成推荐报告草稿",
    "submit_recommendation": "提交推荐报告",
    "view_pipeline": "查看Pipeline",
    "view_approvals": "查看审批",
}

async def classify_intent(message: str, conversation_history: list, ctx) -> dict:
    prompt = f"""你是猎头工作台的意图分类器。
    根据用户消息判断意图和提取实体。

    可用意图：{json.dumps(SKILL_INTENT_MAP, ensure_ascii=False)}

    用户消息：{message}
    对话历史：{conversation_history[-5:]}

    输出 JSON：
    {{
      "intent": "意图名称",
      "entities": {{
        "job_order_id": "如果提到了具体岗位",
        "candidate_id": "如果提到了具体候选人",
        "client_name": "如果提到了具体客户"
      }},
      "confidence": 0.0-1.0,
      "clarification_needed": "如果需要用户补充信息"
    }}"""

    return await llm_router.chat_json(prompt, use_case="intent_classification")

2. agent/core.py — Agent 核心

class AgentCore:
    def __init__(self, registry, executor, conversation_manager):
        ...

    async def process(self, message: str, session_id: str, ctx) -> AsyncGenerator:
        """处理用户消息，流式返回结果"""
        # 1. 意图理解
        intent_result = await classify_intent(message, history, ctx)

        # 2. 如果需要澄清，直接返回
        if intent_result.get("clarification_needed"):
            yield {"type": "text", "content": intent_result["clarification_needed"]}
            return

        # 3. 选择 skill
        skill_name = self._map_intent_to_skill(intent_result["intent"])

        # 4. 检查权限
        allowed = registry.get_allowed_tools(ctx.role)
        if skill_name not in [s.name for s in allowed]:
            yield {"type": "text", "content": "您没有权限执行此操作"}
            return

        # 5. 执行 skill
        yield {"type": "thinking", "content": f"正在执行 {skill_name}..."}
        result = await executor.execute_appropriate(skill_name, input_data, ctx)

        # 6. 生成回复 + 渲染指令
        reply = await self._generate_reply(message, result, ctx)
        yield {"type": "text", "content": reply}

        # 7. 如果有可视化数据，发送渲染指令
        if result.data:
            render_type = self._determine_render_type(intent_result["intent"])
            yield {"type": "render", "render_type": render_type, "data": result.data}

        # 8. 如果需要审批
        if result.need_approval:
            yield {"type": "approval", "preview": result.approval_preview}

3. agent/conversation.py — 对话管理器

class ConversationManager:
    def __init__(self, redis_client):
        ...

    async def get_history(self, session_id) -> list:
        """从 Redis 获取对话历史"""

    async def add_message(self, session_id, role, content):
        """添加消息到历史（保留最近 20 条）"""

    async def get_context(self, session_id, tenant_id) -> dict:
        """获取会话上下文（当前关注的岗位/候选人等）"""
```

**检查点 P4-T1**：
```
☐ 输入「今天有什么待办」→ 返回结构化待办
☐ 输入「帮我给CFO岗位找候选人」→ 触发 search_candidates
☐ 输入「给张三生成推荐报告」→ 触发 submission_draft_create
☐ 输入模糊请求「找个人」→ 返回澄清问题
☐ 20 条测试指令，意图识别准确率 > 80%
```

---

### P4-T2 · Chat API + 前端

**Codex Prompt**：
```
1. apps/api/routes/agent.py：
POST /api/v1/agent/chat
  body: {message, session_id}
  返回 SSE 流：
  data: {"type":"text","content":"..."}          文字回复
  data: {"type":"thinking","content":"..."}      思考过程
  data: {"type":"render","render_type":"...","data":{}} 渲染指令
  data: {"type":"approval","preview":{}}         审批预览
  data: {"type":"done"}                          结束

GET /api/v1/runs/{id}
  返回 agent_run 详情（含 steps）

GET /api/v1/runs/{id}/replay
  返回完整回放数据（steps + tool_calls + artifacts + state_diff）

2. 前端 app/(dashboard)/chat/page.tsx：

布局：左侧 1/3 消息区 + 右侧 2/3 动态面板（移动端叠放）

消息区：
- 消息列表（用户右对齐蓝色，AI 左对齐灰色）
- AI 消息支持 Markdown 渲染（react-markdown）
- 流式输出打字动画
- 底部输入框 + 发送按钮
- 输入 / 弹出命令菜单

斜杠命令：
/today       今日待办
/find [关键词]  搜候选人
/score [岗位]  批量评分
/draft [候选人] 生成推荐草稿
/outreach [候选人] 生成外联话术

动态面板（根据 render_type 切换）：
- "candidate_list" → 候选人卡片列表
- "pipeline"       → Pipeline 看板
- "submission"     → 推荐报告预览
- "todo_list"      → 待办卡片列表
- "approval"       → 审批确认卡片
- "score_result"   → 评分结果表格
- null             → 使用提示

页面加载时自动发送「今天有什么待办」
```

**检查点 P4-T2**：
```
☐ 消息流渲染正确，用户/AI 样式区分
☐ 流式输出有打字动画
☐ 斜杠命令弹出菜单
☐ 右侧面板根据 render_type 正确切换
☐ 审批确认卡片可操作
☐ 移动端布局自适应
```

---

### P4-T3 · 今日待办聚合

**Codex Prompt**：
```
skills/query_todo/ 目录：

SKILL.md + skill.py：
  input: {} （无需参数，自动按 user_id 查询）
  output: {todos: [{type, title, priority, link, due}]}

  步骤：
    1. 查询待确认的推荐草稿（submissions.status=DRAFT，超过24h未处理）
    2. 查询待审批的请求（approvals.status=PENDING）
    3. 查询今天需跟进的客户（clients.next_follow_up <= tomorrow）
    4. 查询今天需跟进的候选人（candidates.next_follow_up <= tomorrow）
    5. 查询解析失败的简历（resume_assets.parse_status=FAILED）
    6. 查询新建岗位的人才库匹配结果（24h内）
    7. 按优先级排序：审批 > 跟进 > 草稿确认 > 解析失败
    8. 返回待办列表

前端 工作台首页 app/(dashboard)/page.tsx：
  - 今日待办卡片列表（从 query_todo 获取）
  - 每项有图标、标题、优先级标签、跳转链接
  - 底部统计：本周推荐数 / 在进行岗位数 / 候选人总数
```

**检查点 P4-T3**：
```
☐ 工作台首页加载时自动展示待办
☐ 有待审批时优先展示
☐ 每项待办可点击跳转到对应页面
☐ 统计数字准确
```

---

### P4 阶段 Gate

| Gate | 通过条件 |
|------|---------|
| 业务 Gate | Chat 可触发所有 P0 Skill |
| 代码 Gate | SSE 流式输出正常 |
| 合规 Gate | Agent run 有完整审计记录 |

---

## P5 · WebUI 工作台打磨（Week 9.5-11）

**目标**：工作台是猎头的主力界面，Chat 是辅助入口

---

### P5-T1 · 工作台首页 Dashboard

**Codex Prompt**：
```
app/(dashboard)/page.tsx 工作台首页：

顶部：欢迎语（"早上好，{name}"） + 日期

第一行：4 个统计卡片
- 进行中岗位数（job_orders.status=OPEN）
- 本月推荐数（submissions 本月创建数）
- 候选人总数（candidates 总数）
- 待审批数（approvals.status=PENDING）

第二行：今日待办列表（调用 query_todo skill）
- 每项有操作按钮（跳转 / 标记完成）

第三行：最近活动时间线
- 最近 10 条 audit_log 的可读化展示
- 格式："李四 生成了 CFO 岗位的推荐草稿 · 2 小时前"

使用 shadcn/ui 的 Card, Badge, Avatar 组件。
响应式：移动端单列，桌面端双列。
```

---

### P5-T2 · 审计回放页

**Codex Prompt**：
```
app/(dashboard)/audit/page.tsx 审计日志页：

列表视图：
- 时间 / 事件类型(badge) / 操作人 / 资源 / 描述
- 支持按事件类型、操作人、日期范围筛选

点击某条记录 → 展开回放面板：
- 时间线展示 agent_run 的每个 step
- 每个 step 显示：
  - skill 名称
  - 输入摘要（脱敏）
  - 输出摘要
  - 耗时
  - model_name / model_version
- 如果有 state_diff，用 diff 视图展示（左侧 before / 右侧 after）
- 如果有 approval，显示审批链

GET /api/v1/audit-logs 端点：
  支持 ?event_type= ?actor_user_id= ?start_date= ?end_date= 筛选
  分页返回
```

**检查点 P5-T2**：
```
☐ 审计日志列表正常展示
☐ 筛选功能生效
☐ 回放面板显示完整的 step 时间线
☐ state_diff 对比视图正确
☐ 模型版本信息可见
```

---

### P5-T3 · 全局搜索 + 详情页打磨

**Codex Prompt**：
```
1. 全局搜索组件（顶部导航栏）：
- 输入框支持搜索：客户名 / 候选人名 / 职位名
- 下拉展示分类结果：
  客户：[结果列表]
  职位：[结果列表]
  候选人：[结果列表]
- 点击跳转到对应详情页

2. 候选人详情页 app/(dashboard)/candidates/[id]/page.tsx：
Tabs：基本信息 | 简历 | 标签 | 关联岗位 | 活动时间线

- 基本信息：卡片布局，PII 脱敏（owner 可点击"显示完整"）
- 简历：原始简历预览 + AI 解析结构化展示（教育/工作经历/技能）
- 标签：AI 自动标签 + 手动添加/删除
- 关联岗位：该候选人在哪些 pipeline 中，当前阶段
- 活动时间线：所有与该候选人相关的操作记录

3. 职位详情页增强：
- Pipeline 看板 Tab 增加筛选（按 score 范围、按 priority）
- 寻访计划 Tab 增加"重新生成"按钮
```

---

### P5 阶段 Gate

| Gate | 通过条件 |
|------|---------|
| 业务 Gate | 工作台首页信息密度足够猎头日常使用 |
| 代码 Gate | 移动端布局正常 |
| 合规 Gate | 审计回放所有正式动作可追溯 |

---

## P6 · 审计与稳定化（Week 11.5-13）

---

### P6-T1 · Docker Compose 部署

**Codex Prompt**：
```
创建 docker-compose.yml：

services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: huntflow
      POSTGRES_USER: huntflow
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  api:
    build: .
    depends_on: [db, redis]
    environment:
      DATABASE_URL: postgresql+asyncpg://huntflow:${DB_PASSWORD}@db:5432/huntflow
      REDIS_URL: redis://redis:6379/0
    env_file: .env
    ports:
      - "8000:8000"
    command: >
      sh -c "alembic upgrade head && uvicorn apps.api.main:app --host 0.0.0.0 --port 8000"

  worker:
    build: .
    depends_on: [db, redis]
    env_file: .env
    command: python workers/main.py

  web:
    build: ./apps/web
    depends_on: [api]
    ports:
      - "3000:3000"

volumes:
  pgdata:

Dockerfile（后端）：
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0"]

同时创建：
- scripts/backup.sh（pg_dump + 文件备份到 backup/ 目录）
- scripts/restore.sh（从 backup/ 恢复）
- scripts/deploy.sh（docker compose up -d --build）
```

**检查点 P6-T1**：
```bash
docker compose up -d
curl http://localhost:8000/health
# 期望：{"status":"ok","version":"0.1.0"}
# 30 分钟内完成新机器首次部署
```
验收：`☐` 一键部署成功 `☐` 备份脚本可执行 `☐` 恢复脚本可执行

---

### P6-T2 · CI 门禁 + 安全测试

**Codex Prompt**：
```
1. .github/workflows/ci.yml：
name: CI
on: [pull_request]
jobs:
  verify:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_DB: huntflow_test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.12"}
      - run: pip install -r requirements.txt
      - run: python -m pytest apps/api/tests/ -v
      - run: python -m pytest tests/test_tenant_isolation.py -v
      - run: alembic upgrade head && alembic downgrade -1 && alembic upgrade head

2. tests/test_tenant_isolation.py：
- 创建两个 tenant，各自创建候选人
- 用 tenant_A 的 token 查询 → 只看到 tenant_A 的数据
- 用 tenant_A 的 token 访问 tenant_B 的资源 → 403 或空
- 用 consultant 角色访问 owner 专属功能 → 403

3. tests/test_approval_flow.py：
- 发起审批 → 无 token 提交 → 失败
- 发起审批 → 审批通过 → 用 token 提交 → 成功
- 发起审批 → token 过期 → 提交 → 失败
- 自批自己的审批 → 失败
```

**检查点 P6-T2**：
```
☐ CI 流水线通过
☐ 租户隔离测试全部通过
☐ 审批流程测试全部通过
☐ migration 可回退并重新升级
```

---

### P6-T3 · Worker 统一调度

**Codex Prompt**：
```
workers/main.py — 统一 Worker 入口：

使用 APScheduler 调度以下任务：

1. 每 30 秒：处理 automation_events 队列
   扫描 status=PENDING 且 scheduled_at <= now 的事件
   按 type 路由到对应处理函数：
   - PARSE_RESUME → 调用 resume_parse skill
   - VECTORIZE_CANDIDATE → 调用 vectorize_candidate
   - VECTORIZE_JOB → 调用 vectorize_job
   - DEDUPE_CHECK → 调用 dedupe_check
   - APPROVAL_NOTIFICATION → 发企微通知
   处理完成更新 status=DONE / FAILED
   失败时 retry_count += 1，小于 max_retries 重置为 PENDING

2. 每天 09:00（Asia/Shanghai）：跟进提醒
   查询 clients.next_follow_up <= tomorrow 的客户
   查询 candidates.next_follow_up <= tomorrow 的候选人
   向对应 owner 发企微提醒

3. 每天 09:30：审批超时检查
   将超过 1 小时未处理的 approval 标为 EXPIRED

4. 每周一 09:00：沉睡候选人提醒
   查询 last_contacted_at < 30 天前的候选人
   向 owner 发送汇总提醒

启动时打印所有注册的定时任务列表。
所有任务异常不阻塞其他任务。
```

**检查点 P6-T3**：
```
☐ Worker 启动无报错，打印任务列表
☐ 上传简历后 30 秒内触发解析
☐ 设置一个明天需跟进的客户，第二天 09:00 收到企微提醒
☐ 事件处理失败后自动重试
☐ 超过 max_retries 的事件标为 FAILED 不再重试
```

---

### P6 阶段 Gate

| Gate | 通过条件 |
|------|---------|
| 业务 Gate | 端到端流程可在 Docker 环境中完整跑通 |
| 代码 Gate | CI 全部通过，租户隔离测试为 0 |
| 合规 Gate | 审计日志完整，导出需审批 |
| 运营 Gate | 有备份/恢复脚本，有部署文档 |

---

## P7 · 试点与打磨（Week 13-13.5）

---

### P7-T1 · 端到端流程验收

```
手动走一遍完整流程（用真实模拟数据）：

☐ 注册账号 → 登录 → 看到空工作台
☐ 创建客户「测试科技公司」→ 设置行业/联系人
☐ 阶段流转 LEAD → CONTACTED → SIGNED
☐ 创建职位「CTO」→ AI 生成 JD → AI 生成寻访计划
☐ 上传 3 份简历 → 自动解析 → 去重检查
☐ 把 3 个候选人关联到 CTO 岗位 → 批量评分
☐ 看板中拖拽晋升到 Shortlist
☐ 为 Shortlist 候选人生成推荐草稿
☐ 编辑草稿 → 提交审批 → 审批通过
☐ 下载推荐报告 PDF
☐ Chat 界面：用自然语言触发搜索候选人、生成外联话术
☐ 工作台首页：待办列表显示正确
☐ 审计页面：所有操作可回放
```

---

### P7-T2 · 用户手册

**Codex Prompt**：
```
创建 docs/user-manual.md：

# HuntFlow 用户手册

## 快速开始（5 分钟上手）
1. 注册与登录
2. 创建第一个客户
3. 创建第一个职位
4. 上传第一份简历
5. 生成第一份推荐报告

## 功能指南
### 工作台首页
### 客户管理
### 职位管理
### 候选人管理
### Pipeline 看板
### 推荐报告
### 对话助手
### 审批中心
### 审计日志

## 常见问题
- 简历解析失败怎么办？
- 如何批量导入候选人？
- 推荐报告的评分依据是什么？
- 数据安全如何保障？

## 快捷键
- / : 打开命令菜单
- Ctrl+K : 全局搜索

每个功能配截图占位符（TODO: 替换为真实截图）
```

---

## 六、合规控制清单

### 6.1 最小合规措施

| 控制项 | 最小措施 | 验收条件 |
|--------|---------|---------|
| 字段分级 | public / business / pii / sensitive_pii 四级 | 所有表字段都有等级 |
| 脱敏 | UI 默认脱敏手机号、邮箱 | consultant 看不到完整 PII |
| 加密 | phone / email 使用 AES-256-GCM 加密存储 | 数据库直接查看为密文 |
| 来源台账 | 记录 source_type / source_detail / consent_basis | 任一候选人可追溯来源 |
| 审批链 | submit / export 一律审批 | 无 approval token 不能执行 |
| 审计回放 | run / tool / approval / state_diff | 正式动作可 replay |
| 模型治理 | 记录 model_name / model_version / prompt_version | 结果可追溯到模型版本 |
| 保留与删除 | 支持候选人数据删除 | 删除后 PII 不可恢复 |

### 6.2 数据来源优先级

| 优先级 | 来源 | 做法 | 风险 |
|--------|------|------|------|
| A | 用户手工上传简历 | 必做 | 低 |
| A | 历史 ATS/CRM 导出 | CSV 导入器 | 中 |
| B | 候选人自填表单 | 表单 + 同意说明 | 低 |
| B | 内推表单 | 记录推荐关系 | 中 |
| C | 合作猎头批量 CSV | 标注来源与合同 | 中 |
| D | 登录后自动批量抓取 | **不做** | 高 |

### 6.3 不提供的能力

| 类别 | 说明 |
|------|------|
| 代理池/IP 轮换 | 不提供 |
| 反指纹/stealth automation | 不提供 |
| 验证码绕过 | 不提供 |
| 账号池/代登录 | 不提供 |
| 绕过平台技术措施 | 不提供 |

---

## 七、风险清单与缓解

| 风险 | 表现 | 缓解 |
|------|------|------|
| 技术风险 | schema 变更多、代理输出失控 | 任务缩小、先契约后实现、CI 门禁 |
| 合规风险 | 数据来源不清、用途漂移 | 来源台账、同意记录、导出审批 |
| 运营风险 | 产品像 chat demo 不像工具 | 先做列表/详情/看板，不只做 chat |
| 数据质量 | 解析错读、误合并 | 置信度字段、人工 review queue |
| 模型偏见 | 排序偏向特定背景 | 规则优先、解释字段、人工 override |
| 跨境风险 | 原始简历流向境外模型 | 境内模型、摘要出境 |
| 工具滥权 | skill 直接改正式状态 | allowed_tools + approval token |
| 运维风险 | 单机故障、备份缺失 | 自动备份、恢复演练 |

---

## 八、开发工作流

### 8.1 每个任务的标准流程

```
1. 任务立项（人工）
   - 压缩到 ≤4 小时
   - 写 task brief（目标/输入/输出/约束/检查点）

2. 实现（Codex）
   - 使用本文档中对应的 Codex Prompt
   - 只做一个行为变化 + 测试
   - 输出 code diff

3. 审查（Claude Code）
   - 检查边界、测试、风险、回滚
   - 检查是否有 tenant scope
   - 检查是否记录了 model_version

4. 门禁（CI）
   - pytest 通过
   - 租户隔离测试通过
   - migration 可回退

5. 合并（人工）
   - 看 diff、风险、回放影响
   - merge

6. 复盘（人工 + Claude Code）
   - 写问题单和修复建议
```

### 8.2 Git 提交规范

```bash
# 格式：[阶段][模块] 描述
git commit -m "[P1][auth] 实现 JWT 认证，通过检查点"
git commit -m "[P2][candidates] 实现简历解析 skill，支持 PDF/Word"
git commit -m "[P3][submissions] 实现推荐草稿生成，通过检查点"
git commit -m "[FIX][P2] 修复候选人搜索跨租户泄漏"

# 每完成一个检查点就 commit
```

### 8.3 每日更新 AGENTS.md 进度

```markdown
## 当前进度
- ✅ P0 蓝图与规范
- ✅ P1 工程底座
- 🔄 P2 业务内核（完成 T1-T2，T3 进行中）
- ☐ P3 Skill MVP
...

## 今天的任务
P2-T3 · 候选人 CRUD + 简历解析

## 已知的坑
- Qwen chat_json 返回有时带 markdown 代码块，llm_router 已处理
- pgvector 在小数据集(<100)时 ivfflat 索引比暴力搜索慢，暂时禁用索引
```

---

## 九、30/60/90 天行动计划

| 时间 | 优先级 | 行动 |
|------|--------|------|
| 30 天 | P0 | 冻结 PRD/AGENTS.md/OpenAPI/ER；完成 tenants/users/clients/job_orders/candidates/resume_assets CRUD；做出导入、去重后端 |
| 60 天 | P0 | 完成 skill registry、query/draft executor、match_scores、submission_draft、WebUI 职位/候选人/Pipeline 看板/Chat；接上审批中心 |
| 90 天 | P1 | 完成审计回放、Docker Compose、CI、备份恢复、用户手册；开始单客户试点 |

---

## 附：审查型 Prompt 模板（Claude Code 使用）

```text
请审查这次改动是否存在以下问题：
1. 没有 tenant_id scope（跨租户泄漏）
2. 没有写入 model_version（AI 结果不可追溯）
3. 直接修改了 submission/pipeline 正式状态（应走审批）
4. PII 字段未加密存储
5. API 错误码不一致
6. 测试缺少空列表、重复 candidate、无 must-have 三类边界

只输出：
- 问题列表
- 最小修复计划
- 必补测试清单
先不要直接改代码，除非我回复"开始修复"。
```

---

*文档结束。每完成一个阶段的 Gate 检查，在进度中打 ✅。*
*首发目标：13 周内拿到一个可演示、可测试、可试点的猎头工作台。*


# HuntFlow · 产品需求文档 + 开发计划（完整合并版）

**版本**：v3.0  
**日期**：2026-04-20  
**开发者**：独立开发者（使用 Codex / Claude Code）  
**定位**：猎头工作 AI Agent，带 WebUI，13 个工作环节 Skill 化  

---

## 📌 如何使用这份文档

```
每开始一个任务前：
  → 查对应模块的「功能需求」，明确你要做什么

每完成一个任务后：
  → 执行「检查点」，逐条对照「验收标准」

每完成一个模块后：
  → 执行「模块复盘」，确认所有需求都实现了

不知道下一步做什么：
  → 看「进度追踪表」，找第一个 ☐ 的任务
```

---

## 进度追踪总表

> 每完成一项，把 `☐` 改为 `✅`，日期填上

| 模块 | 状态 | 完成日期 | 备注 |
|------|------|---------|------|
| **PHASE 0** 工程底座 | ☐ | | |
| **M01** 客户 BD | ☐ | | |
| **M02** 合同管理 | ☐ | | |
| **M03** 需求对齐 | ☐ | | |
| **M04** 人选寻访（手动） | ☐ | | |
| **M05** 电话面试 | ☐ | | |
| **M06** 人选推荐 | ☐ | | |
| **M07** Chat 界面 + Agent | ☐ | | |
| **M08** 内部人才库 | ☐ | | |
| **M09** RPA 采集层 | ☐ | | |
| **M10** 面试协调 | ☐ | | |
| **M11** 背景调查 | ☐ | | |
| **M12** 入离职管理 | ☐ | | |
| **M13** 试用期管理 | ☐ | | |
| **M14** 开票催款 | ☐ | | |
| **M15** 二次开发 + BD完善 | ☐ | | |

---

## PHASE 0 · 工程底座

**目标**：项目能跑起来，数据库能连，登录能用  
**对应周次**：Week 1 前半段（Day 1-3）

---

### PRD-P0 · 基础设施需求

**P0-F1 · 技术栈**

| 组件 | 选型 | 说明 |
|------|------|------|
| 数据库 | Supabase（PostgreSQL + pgvector + Auth） | 一站式，免运维 |
| 后端 | Python 3.12 + FastAPI | AI 生态最佳 |
| 前端 | Next.js 14 + Tailwind + shadcn/ui | Vercel 一键部署 |
| AI 文本 | 通义千问 Qwen-Max（dashscope） | 国内合规 |
| 语音转写 | 阿里云智能语音 | 中文准确率最高 |
| 推送通知 | 企业微信应用消息 API | 猎头首选 IM |
| PDF 生成 | WeasyPrint | Python 直接用 |
| 定时任务 | Vercel Cron Jobs | 无需自建 Worker |
| RPA | DrissionPage + 芝麻代理 | Week 9 才用到 |

**P0-F2 · 数据库表**（共 11 张，MVP 必须全部建好）

```
profiles        用户信息（关联 Supabase Auth）
clients         客户/公司
contracts       合同
positions       岗位
candidates      候选人（含向量字段）
pipelines       流程记录（核心）
phone_interviews 电话面试记录
reports         所有类型报告（统一存）
onboardings     入离职管理
probations      试用期回访
invoices        开票催款
automation_events 自动化事件队列
```

**P0-F3 · 用户认证**
- 使用 Supabase Auth，支持邮箱+密码登录
- 所有 API 端点需要 JWT 认证，未登录返回 401
- 数据隔离：每个用户只能看自己负责的数据（Supabase RLS）

---

### 开发任务 P0

#### P0-T1 · Supabase 项目初始化

**Codex Prompt**：
```
创建 huntflow Python 项目：
1. 目录结构：skills/ api/ utils/ workers/ tests/ frontend/
2. requirements.txt：fastapi uvicorn supabase dashscope python-dotenv weasyprint aiofiles httpx pydantic pytest pytest-asyncio
3. .env.example 包含：SUPABASE_URL SUPABASE_SERVICE_ROLE_KEY DASHSCOPE_API_KEY ALIYUN_ASR_APPKEY ALIYUN_ACCESS_KEY_ID ALIYUN_ACCESS_KEY_SECRET WECOM_CORP_ID WECOM_APP_SECRET WECOM_AGENT_ID
4. api/main.py：FastAPI app，GET /health 返回 {"status":"ok","version":"0.1.0"}
5. skills/base.py：SkillContext(user_id, db) 和 SkillResult(success, data, error, need_approval) 两个类

只输出文件内容，不要解释。
```

**检查点 P0-T1**：
```bash
uvicorn api.main:app --reload
curl http://localhost:8000/health
# 期望：{"status":"ok","version":"0.1.0"}
```
验收：`☐` HTTP 200，返回正确 JSON

---

#### P0-T2 · 数据库建表

在 Supabase Dashboard → SQL Editor 执行以下 SQL：

```sql
-- 启用扩展
create extension if not exists vector;

-- profiles（用户信息）
create table public.profiles (
  id uuid references auth.users on delete cascade primary key,
  name text not null,
  role text default 'consultant',
  wecom_userid text,
  created_at timestamptz default now()
);
create policy "users see own profile" on public.profiles
  for all using (id = auth.uid());
alter table public.profiles enable row level security;

-- clients（客户）
create table public.clients (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid references public.profiles(id) not null,
  name text not null,
  industry text,
  size text,
  stage text default 'LEAD',
  next_follow_up timestamptz,
  notes text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create policy "owner access" on public.clients for all using (owner_id = auth.uid());
alter table public.clients enable row level security;
create index on public.clients(owner_id, stage);

-- contracts（合同）
create table public.contracts (
  id uuid primary key default gen_random_uuid(),
  client_id uuid references public.clients(id) not null,
  fee_rate float not null,
  guarantee_days int default 90,
  payment_terms text,
  status text default 'DRAFT',
  file_url text,
  signed_at timestamptz,
  expires_at timestamptz,
  created_at timestamptz default now()
);

-- positions（岗位）
create table public.positions (
  id uuid primary key default gen_random_uuid(),
  client_id uuid references public.clients(id) not null,
  contract_id uuid references public.contracts(id),
  owner_id uuid references public.profiles(id) not null,
  title text not null,
  level text,
  status text default 'OPEN',
  jd text,
  search_plan jsonb,
  salary_min int,
  salary_max int,
  deadline timestamptz,
  embedding vector(1536),
  created_at timestamptz default now()
);
create policy "owner access" on public.positions for all using (owner_id = auth.uid());
alter table public.positions enable row level security;
create index on public.positions using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- candidates（候选人）
create table public.candidates (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid references public.profiles(id) not null,
  name text not null,
  current_company text,
  current_title text,
  current_salary int,
  expected_salary int,
  open_to_move text default 'PASSIVE',
  location text,
  resume_url text,
  resume_parsed jsonb,
  tags jsonb default '[]',
  source text,
  last_contacted_at timestamptz,
  next_follow_up timestamptz,
  embedding vector(1536),
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create policy "owner access" on public.candidates for all using (owner_id = auth.uid());
alter table public.candidates enable row level security;
create index on public.candidates(owner_id);
create index on public.candidates(next_follow_up);
create index on public.candidates using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- pipelines（流程核心表）
create table public.pipelines (
  id uuid primary key default gen_random_uuid(),
  position_id uuid references public.positions(id) not null,
  candidate_id uuid references public.candidates(id) not null,
  owner_id uuid references public.profiles(id) not null,
  stage text default 'SOURCED',
  list_type text default 'LONGLIST',
  match_score int,
  metadata jsonb default '{}',
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique(position_id, candidate_id)
);
create policy "owner access" on public.pipelines for all using (owner_id = auth.uid());
alter table public.pipelines enable row level security;
create index on public.pipelines(position_id, stage);
create index on public.pipelines(candidate_id);

-- phone_interviews（电话面试）
create table public.phone_interviews (
  id uuid primary key default gen_random_uuid(),
  pipeline_id uuid references public.pipelines(id) unique not null,
  audio_url text,
  transcript text,
  ai_insights jsonb,
  conducted_at timestamptz,
  created_at timestamptz default now()
);

-- reports（所有报告统一存）
create table public.reports (
  id uuid primary key default gen_random_uuid(),
  pipeline_id uuid references public.pipelines(id) not null,
  type text not null,
  content jsonb not null,
  file_url text,
  share_token text unique default encode(gen_random_bytes(16), 'hex'),
  share_expires_at timestamptz default now() + interval '7 days',
  confirmed_by uuid references public.profiles(id),
  confirmed_at timestamptz,
  ai_generated boolean default true,
  created_at timestamptz default now()
);

-- onboardings（入离职）
create table public.onboardings (
  id uuid primary key default gen_random_uuid(),
  pipeline_id uuid references public.pipelines(id) unique not null,
  offer_salary int,
  expected_join_date date,
  actual_join_date date,
  resign_date date,
  status text default 'OFFER_ACCEPTED',
  counter_offer_risk text default 'LOW',
  notes text,
  created_at timestamptz default now()
);

-- probations（试用期）
create table public.probations (
  id uuid primary key default gen_random_uuid(),
  onboarding_id uuid references public.onboardings(id) not null,
  day_checkpoint int not null,
  scheduled_at timestamptz not null,
  completed_at timestamptz,
  candidate_feedback text,
  client_feedback text,
  risk_level text default 'LOW',
  report_id uuid references public.reports(id),
  status text default 'PENDING',
  unique(onboarding_id, day_checkpoint)
);
create index on public.probations(scheduled_at, status);

-- invoices（开票）
create table public.invoices (
  id uuid primary key default gen_random_uuid(),
  pipeline_id uuid references public.pipelines(id) not null,
  amount float,
  status text default 'DRAFT',
  due_date date,
  paid_at timestamptz,
  file_url text,
  created_at timestamptz default now()
);
create index on public.invoices(status, due_date);

-- automation_events（事件队列）
create table public.automation_events (
  id uuid primary key default gen_random_uuid(),
  type text not null,
  entity_id uuid,
  payload jsonb default '{}',
  status text default 'PENDING',
  scheduled_at timestamptz not null,
  processed_at timestamptz,
  error text,
  created_at timestamptz default now()
);
create index on public.automation_events(status, scheduled_at);
```

**检查点 P0-T2**：
```sql
-- 在 Supabase SQL Editor 验证
select table_name from information_schema.tables
where table_schema = 'public'
order by table_name;
-- 期望：11张表全部出现
```
验收：`☐` 11张表全部存在  `☐` pgvector 扩展已启用

---

#### P0-T3 · 基础工具类

**Codex Prompt**：
```
创建以下三个工具文件：

1. utils/qwen_client.py
   - async def chat(prompt, model="qwen-max", system="你是专业猎头助手") -> str
   - async def chat_json(prompt, model="qwen-max") -> dict  # 强制返回JSON，带清理逻辑
   - async def get_embedding(text) -> list[float]  # 用 text-embedding-v3
   - 从 os.environ["DASHSCOPE_API_KEY"] 读取密钥
   - chat_json 要处理 markdown 代码块包裹的情况

2. utils/asr_client.py
   - async def transcribe(audio_url: str) -> str
   - 调用阿里云语音识别「录音文件识别」REST API
   - 轮询等待结果（最多等60秒，每3秒查一次）
   - 从环境变量读取 ALIYUN_ASR_APPKEY ALIYUN_ACCESS_KEY_ID ALIYUN_ACCESS_KEY_SECRET

3. utils/wecom_notifier.py
   - async def push_text(wecom_userid: str, message: str) -> bool
   - 调用企业微信「发送应用消息」接口
   - 自动获取并缓存 access_token（2小时过期）
   - 从环境变量读取 WECOM_CORP_ID WECOM_APP_SECRET WECOM_AGENT_ID

每个文件不超过 80 行，所有异常记录日志后抛出。
```

**检查点 P0-T3**：
```python
# tests/test_utils.py 中验证
import asyncio
from utils.qwen_client import chat, chat_json
from utils.wecom_notifier import push_text

async def test():
    # 测试1：LLM 调用
    result = await chat("用一句话介绍猎头行业")
    assert len(result) > 10, "LLM返回内容太短"

    # 测试2：JSON 返回
    data = await chat_json('返回JSON：{"name":"test","score":9}')
    assert data["name"] == "test"

    # 测试3：企业微信推送（需要真实配置）
    # ok = await push_text("YOUR_WECOM_ID", "测试消息")
    # assert ok

asyncio.run(test())
print("✅ utils 测试通过")
```
验收：`☐` Qwen-Max 调用成功  `☐` chat_json 正确解析  `☐` 企业微信推送成功

---

#### P0-T4 · 前端初始化

**Claude Code Prompt**：
```
初始化 Next.js 14 前端项目（在 frontend/ 目录）：

1. 安装：shadcn/ui + tailwind + SWR + @supabase/supabase-js
2. 配置 Supabase Auth（lib/supabase.ts）
3. 登录页面 app/(auth)/login/page.tsx：邮箱+密码登录表单，登录成功跳转 /
4. 受保护路由中间件：未登录访问任何页面跳转 /login
5. 主 Layout app/(dashboard)/layout.tsx：
   左侧导航（图标+文字）：
   - 📊 仪表板  /
   - 👥 客户    /clients
   - 📋 岗位    /positions
   - 👤 候选人  /candidates
   - 📁 报告    /reports
   - 💬 对话    /chat
   - 💰 财务    /finance
6. lib/api.ts：axios 封装，自动在 header 带 Supabase JWT，401 跳登录

输出所有文件的完整代码。
```

**检查点 P0-T4**：
```
☐ npm run dev 启动无报错
☐ 访问 / 跳转到 /login
☐ 登录成功后跳转回 /，显示侧边导航
☐ 7个导航链接点击后 URL 正确变化
```

---

### PHASE 0 模块复盘

```
完成标准（全部打勾才能进入 M01）：
☐ P0-T1：后端 /health 返回正常
☐ P0-T2：11张数据库表全部存在
☐ P0-T3：三个工具类测试通过
☐ P0-T4：前端登录流程完整

复盘结论：
☐ 通过 → 进入 M01
☐ 未通过，问题：_______________
```

---

---

## M01 · 客户 BD 管理

**对应工作环节**：猎头工作环节 #1 客户 BD  
**交付物**：线索 List、客户管理 List  
**对应周次**：Week 1 后半段 + Week 2 前半段

---

### PRD-M01 · 功能需求

**M01-F1 · 客户基础管理**
- 创建客户：公司名（必填）、行业（必填）、规模、备注
- 客户阶段流转：LEAD → CONTACTED → NEGOTIATING → SIGNED → ACTIVE（单向，不可逆回）
- 每个阶段必须记录操作时间和操作人
- 支持设置「下次跟进时间」，到期前 1 天企业微信提醒
- 支持添加多个联系人（姓名/职位/微信/邮件/电话）

**M01-F2 · AI 线索生成**
- 输入：行业关键词 + 公司规模偏好
- 输出：10-20 条目标公司线索，每条包含：公司名、行业、估计规模、BD 推荐理由、BD 价值评分（1-10）
- 线索可一键「加入客户库」（创建为 stage=LEAD 的 Client 记录）
- 生成时间 < 15 秒

**M01-F3 · BD 话术生成**
- 输入：选择已有客户
- 输出：三种格式的个性化外联话术（微信消息 / 邮件 / 电话话术）
- 话术必须包含客户公司名、行业特点等个性化内容
- 不是通用模板

**M01-F4 · 客户管理 List 视图**
- 表格展示：公司名 / 行业 / 阶段 / 负责人 / 下次跟进时间 / 操作
- 支持按「阶段」筛选
- 支持搜索公司名

---

### 开发任务 M01

#### M01-T1 · 客户 CRUD API

**Codex Prompt**：
```
在 api/routes/clients.py 实现以下端点（所有端点需要 JWT 认证）：

GET  /clients              返回当前用户的客户列表，支持 ?stage= 筛选
POST /clients              创建客户，body: {name, industry, size, notes}
GET  /clients/{id}         获取单个客户详情（含联系人列表）
PUT  /clients/{id}         更新客户信息
PATCH /clients/{id}/stage  流转阶段，body: {stage, note}，自动记录时间
POST /clients/{id}/contacts 添加联系人，body: {name, title, wechat, email, phone}

使用 Supabase Python client（从 utils/supabase_client.py 获取）
PATCH /stage 要验证流转合法性：LEAD→CONTACTED→NEGOTIATING→SIGNED→ACTIVE（不能跳级，不能回退）
所有操作的 owner_id 设为当前登录用户 ID

Pydantic models 定义在同文件中。
文件不超过 180 行。
```

**检查点 M01-T1**：
```
☐ GET /clients 返回当前用户的客户列表（不含其他用户的）
☐ POST /clients 创建成功，在列表可见
☐ PATCH /stage LEAD→CONTACTED 成功
☐ PATCH /stage SIGNED→LEAD 返回 400（不能回退）
☐ 另一个用户无法访问（返回 403 或空列表）
```

---

#### M01-T2 · AI 线索生成

**Codex Prompt**：
```
在 skills/skill_bd_lead.py 实现 BD 线索生成 Skill：

class BDLeadInput(BaseModel):
    industry: str        # 如"互联网/新能源"
    size_preference: str # 如"B轮以上/500人以上"
    count: int = 15

async def execute(input: BDLeadInput, ctx: SkillContext) -> SkillResult

步骤：
1. 构建 prompt，调用 utils/qwen_client.py 的 chat_json
   prompt 要求 Qwen-Max 作为猎头BD专家，列出目标客户公司
   要求输出格式：
   {"leads": [{"company_name":"","industry":"","estimated_size":"","funding_stage":"","bd_score":8,"bd_reason":"近期C轮融资扩张中"}]}

2. 返回 SkillResult(success=True, data={"leads": [...]})

同时在 api/routes/skills.py 添加：
POST /skills/bd-lead/execute
body: BDLeadInput
返回 SkillResult

文件不超过 80 行。
```

**检查点 M01-T2**：
```
☐ 调用接口返回 ≥ 10 条线索
☐ 每条线索包含 company_name / bd_score / bd_reason
☐ bd_reason 是针对输入行业的具体分析（不是通用话术）
☐ 响应时间 < 15 秒
```

---

#### M01-T3 · BD 话术生成

**Codex Prompt**：
```
在 skills/skill_outreach_bd.py 实现 BD 话术生成 Skill：

class BDOutreachInput(BaseModel):
    client_id: str
    contact_title: str  # 联系人职位，如"CHO"

async def execute(input: BDOutreachInput, ctx: SkillContext) -> SkillResult

步骤：
1. 从数据库读取 Client 信息（公司名/行业/规模）
2. 调用 chat_json 生成三种话术
   输出格式：
   {"wechat":"","email":{"subject":"","body":""},"phone_script":"开场白：...\n核心话术：..."}
3. 话术必须包含公司名和行业特点，不能是通用模板

POST /skills/bd-outreach/execute
```

**检查点 M01-T3**：
```
☐ 三种格式（微信/邮件/电话）全部生成
☐ 话术中包含客户公司名
☐ 话术中包含行业相关的价值主张（不是通用内容）
☐ 不同客户生成的话术有明显差异
```

---

#### M01-T4 · 前端客户管理页面

**Claude Code Prompt**：
```
创建前端客户管理页面：

1. app/(dashboard)/clients/page.tsx
   - 表格：公司名 / 行业 / 阶段（彩色badge） / 下次跟进 / 操作按钮
   - 顶部：搜索框 + 阶段筛选下拉 + 「新建客户」按钮
   - 阶段颜色：LEAD=灰 CONTACTED=蓝 NEGOTIATING=黄 SIGNED=绿 ACTIVE=紫

2. app/(dashboard)/clients/new/page.tsx
   - 表单：公司名（必填）/ 行业 / 规模 / 备注
   - 提交后跳转到客户详情页

3. app/(dashboard)/clients/[id]/page.tsx
   - 基本信息卡片 + 阶段流转按钮（只显示下一个合法阶段）
   - 联系人列表 + 添加联系人按钮
   - AI 功能区：「生成BD话术」按钮（点击弹出 Dialog，展示三种话术+复制按钮）

使用 SWR 做数据请求，shadcn/ui 组件。
```

**检查点 M01-T4**：
```
☐ 客户列表正常渲染，阶段筛选生效
☐ 创建客户后，列表刷新
☐ 阶段流转按钮只显示合法的下一步
☐ 「生成BD话术」Dialog 正常弹出，三种话术可复制
☐ 联系人添加后列表刷新
```

---

#### M01-T5 · 跟进提醒自动化

**Codex Prompt**：
```
在 workers/followup_reminder.py 实现每日跟进提醒：

async def check_client_followups():
    """
    查询所有 next_follow_up <= 明天 的客户
    向对应 owner 的企业微信发送提醒消息
    消息格式：「明日跟进提醒：XXX公司（阶段：谈判中），请准备好话术」
    """

在 Vercel Cron 配置（vercel.json）：
每天早上 9:00（北京时间，即 UTC+8 01:00）触发 POST /cron/followup-reminder

vercel.json 内容：
{
  "crons": [{"path": "/api/cron/followup-reminder", "schedule": "0 1 * * *"}]
}

在 api/routes/cron.py 添加 POST /cron/followup-reminder 端点（需要 CRON_SECRET 验证）
```

**检查点 M01-T5**：
```
☐ 手动调用 POST /cron/followup-reminder，企业微信收到提醒
☐ 只推送 next_follow_up 在明天之前的客户
☐ 不推送其他用户的客户
```

---

### M01 模块复盘

```
对照 PRD-M01 功能需求验收：

M01-F1 客户基础管理：
  ☐ 创建客户功能正常
  ☐ 阶段流转只允许正向，不能回退
  ☐ 下次跟进时间到期提醒正常
  ☐ 联系人增删正常

M01-F2 AI 线索生成：
  ☐ 生成 ≥ 10 条线索
  ☐ 线索质量：人工评估 5 条，bd_reason 有实质内容
  ☐ 生成时间 < 15 秒
  ☐ 一键加入客户库功能正常

M01-F3 BD 话术生成：
  ☐ 三种格式均生成
  ☐ 话术有个性化内容
  ☐ 复制功能正常

M01-F4 客户管理 List：
  ☐ 表格字段完整
  ☐ 阶段筛选有效
  ☐ 搜索功能有效

复盘结论：
☐ 通过 → 进入 M02
☐ 未通过，问题：_______________
```

---

---

## M02 · 合同管理

**对应工作环节**：猎头工作环节 #2 合同签署  
**交付物**：合同文档、合同管理 List  
**对应周次**：Week 2 中段

---

### PRD-M02 · 功能需求

**M02-F1 · 合同生命周期管理**
- 合同与客户关联（一个客户可以有多份合同）
- 合同状态：DRAFT → ACTIVE → EXPIRED / TERMINATED
- 核心字段：服务费率（%）/ 保证期天数 / 付款条款 / 签署日期 / 到期日期
- 合同文件（PDF）可上传到 Supabase Storage 并预览

**M02-F2 · AI 合同草稿生成**
- 输入：客户 ID + 费率 + 保证期 + 付款条款
- 输出：Markdown 格式合同草稿，包含完整条款
- 可导出 PDF（人工修改后上传签署版）
- 生成时间 < 20 秒

**M02-F3 · 到期自动提醒**
- 合同到期前 30 天、7 天、1 天各提醒一次
- 提醒方式：企业微信推送
- 提醒内容：客户名 / 到期日期 / 服务费率

**M02-F4 · 合同管理 List**
- 表格：合同编号 / 客户 / 费率 / 保证期 / 状态 / 到期日
- 点击查看合同详情和关联的岗位列表

---

### 开发任务 M02

#### M02-T1 · 合同 CRUD API + AI草稿

**Codex Prompt**：
```
在 api/routes/contracts.py 实现：

GET  /contracts              合同列表，支持 ?client_id= 筛选
POST /contracts              创建合同，body: {client_id, fee_rate, guarantee_days, payment_terms}
GET  /contracts/{id}         合同详情
PATCH /contracts/{id}/status 状态流转，DRAFT→ACTIVE→EXPIRED

在 skills/skill_contract_draft.py 实现：

class ContractDraftInput(BaseModel):
    client_id: str
    fee_rate: float  # 0.25 = 25%
    guarantee_days: int
    payment_terms: str

async def execute(input, ctx) -> SkillResult
步骤：
1. 查询客户信息
2. 调用 chat_json，prompt 让 Qwen-Max 基于标准猎头服务协议模板生成合同 Markdown
   合同需包含：服务范围/费率计算方式/保证期条款/付款节点/争议解决
3. 用 WeasyPrint 将 Markdown 转 PDF（utils/pdf_generator.py）
4. 上传 PDF 到 Supabase Storage
5. 返回 {draft_md, pdf_url}

POST /skills/contract-draft/execute
```

**检查点 M02-T1**：
```
☐ 合同 CRUD 端点全部通过 curl 测试
☐ AI 生成的合同包含：服务范围/费率条款/保证期/付款条款
☐ PDF 文件可通过 URL 下载（不需要登录）
☐ 合同编号格式：CTR-2026-0001（年份+4位序号）
```

---

#### M02-T2 · 到期提醒 + 前端页面

**Codex Prompt**：
```
1. 在 workers/contract_reminder.py 实现到期提醒：
   查询 expires_at 在 30/7/1 天内的 ACTIVE 合同
   向 client 的负责人发企业微信提醒
   写入 automation_events 防重复触发（同一合同同一天只提醒一次）

2. 在 vercel.json 的 crons 中添加每天 9:10 触发 /api/cron/contract-reminder

3. 前端 app/(dashboard)/contracts/page.tsx：
   合同列表表格 + 顶部「新建合同」按钮
   每行有「生成草稿」按钮（弹出 Dialog 填参数，生成后展示 Markdown 预览+PDF下载）

4. 前端 app/(dashboard)/contracts/[id]/page.tsx：
   合同详情 + 状态操作按钮 + 关联岗位列表
```

**检查点 M02-T2**：
```
☐ 手动触发合同提醒 Worker，企业微信收到正确消息
☐ 同一合同同一天不会重复提醒
☐ 前端合同列表正常展示
☐ 「生成草稿」流程：填参数→等待→展示预览→PDF下载 完整走通
```

---

### M02 模块复盘

```
对照 PRD-M02 验收：
☐ M02-F1：合同 CRUD 完整，状态流转正确
☐ M02-F2：AI草稿包含完整条款，PDF可下载
☐ M02-F3：30/7/1天提醒均能触发
☐ M02-F4：合同列表字段完整

复盘结论：
☐ 通过 → 进入 M03
☐ 未通过，问题：_______________
```

---

---

## M03 · 需求对齐

**对应工作环节**：猎头工作环节 #3 需求对齐  
**交付物**：岗位寻访计划（PDF）  
**对应周次**：Week 2 后半段

---

### PRD-M03 · 功能需求

**M03-F1 · 岗位基础管理**
- 岗位必须关联客户和合同
- 核心字段：职位名称 / 职级 / 状态（OPEN/PAUSED/FILLED/CANCELLED） / JD / 薪资范围 / 截止日期
- 状态变更有记录

**M03-F2 · AI 寻访计划生成**
- 输入：岗位 JD + 可选的访谈录音转写
- 输出 JSON 结构（同时导出 PDF）：
  - 候选人理想画像（文字描述）
  - 目标公司列表（≥ 10 家，含推荐理由）
  - 搜索关键词（中英文）
  - 必备条件 / 加分项
  - 薪资市场参考
  - 时间节点（Longlist 交付日 / Shortlist 交付日 / 首次推荐日）
- 生成 PDF 可发给客户确认
- 生成时间 < 20 秒

**M03-F3 · AI JD 生成**
- 输入：职位名称 + 关键要求（口语描述即可）
- 输出：规范的 JD 文本（中文，含职责/要求/加分项）
- 可手动编辑后保存

---

### 开发任务 M03

#### M03-T1 · 岗位 CRUD + 寻访计划 Skill

**Codex Prompt**：
```
1. api/routes/positions.py 实现岗位 CRUD（5个端点，同客户CRUD模式）

2. skills/skill_search_plan.py 实现寻访计划生成：

class SearchPlanInput(BaseModel):
    position_id: str
    interview_transcript: str = ""  # 可选，需求访谈录音的转写文本

async def execute(input, ctx) -> SkillResult
步骤：
1. 读取岗位信息（title/jd/salary_min/salary_max）
2. chat_json 生成寻访计划，prompt：
   「你是资深猎头顾问，根据以下岗位需求生成完整的寻访计划
    要求输出：{candidate_profile, target_companies[{name,reason}], 
    search_keywords[],  must_haves[], nice_to_haves[], 
    salary_market_insight, timeline:{longlist_by,shortlist_by,first_submission_by}}」
3. 将 search_plan JSON 更新到 positions 表
4. 生成 PDF 并上传，返回 {search_plan, pdf_url}

3. skills/skill_jd_generator.py：
   input: {position_id, key_requirements: str}
   用 Qwen-Max 生成规范 JD，更新 positions.jd，返回 jd_text

POST /skills/search-plan/execute
POST /skills/jd-generator/execute
```

**检查点 M03-T1**：
```
☐ 岗位 CRUD 全部端点正常
☐ 寻访计划包含 target_companies（≥ 10 家）
☐ 每家公司有推荐理由，不是泛泛而谈
☐ timeline 日期合理（Longlist < Shortlist < 首推）
☐ PDF 正常生成并可下载
☐ JD 生成：结构规范，包含职责/要求/加分项三部分
```

---

#### M03-T2 · 前端岗位页面

**Claude Code Prompt**：
```
创建岗位管理前端页面：

1. app/(dashboard)/positions/page.tsx
   卡片网格展示岗位：职位名/客户名/状态badge/截止日/候选人数量
   顶部：按状态筛选 + 「新建岗位」按钮

2. app/(dashboard)/positions/new/page.tsx
   分步表单：Step1 基本信息（职位/客户/合同/薪资）→ Step2 生成JD（AI生成+编辑） → Step3 生成寻访计划

3. app/(dashboard)/positions/[id]/page.tsx
   Tabs：「基本信息」「JD」「寻访计划（PDF预览）」「Pipeline看板」
   寻访计划 Tab：展示结构化 JSON 内容 + 下载PDF按钮
```

**检查点 M03-T2**：
```
☐ 岗位卡片展示正确
☐ 新建岗位分步流程完整走通
☐ 寻访计划 Tab 展示结构化内容
☐ PDF 下载正常
```

---

### M03 模块复盘

```
对照 PRD-M03 验收：
☐ M03-F1：岗位 CRUD 完整，状态变更有记录
☐ M03-F2：寻访计划包含所有字段，≥10家目标公司，PDF正常
☐ M03-F3：JD 生成结构规范，可编辑保存

复盘结论：
☐ 通过 → 进入 M04
☐ 未通过，问题：_______________
```

---

---

## M04 · 人选寻访（手动录入阶段）

**对应工作环节**：猎头工作环节 #4 人选寻访  
**交付物**：Longlist、Shortlist  
**对应周次**：Week 2 末 - Week 3  
**说明**：RPA 自动采集在 M09，本模块只做手动录入 + AI 匹配评分

---

### PRD-M04 · 功能需求

**M04-F1 · 候选人手动录入**
- 录入字段：姓名 / 当前公司 / 当前职位 / 当前薪资 / 期望薪资 / 所在城市 / 求职意向 / 简历上传
- 支持批量导入（Excel 模板）
- 简历上传后 AI 自动解析提取结构化信息

**M04-F2 · AI 匹配评分**
- 候选人入库后，可对指定岗位进行 AI 匹配评分（0-100）
- 评分依据：技能匹配 / 经验年限 / 行业背景 / 职级匹配
- 每条评分附带 match_reasons（2-3条）和 concerns（1-2条）

**M04-F3 · Longlist 管理**
- 候选人关联到岗位后进入 Longlist（Pipeline stage=SOURCED）
- Longlist 可按匹配分排序
- 支持从 Longlist 手动「晋升到 Shortlist」（stage=SHORTLISTED）
- 支持「淘汰」操作（stage=REJECTED + 填写原因）

**M04-F4 · AI 外联消息生成（候选人版）**
- 输入：Pipeline ID（已有候选人+岗位信息）+ 渠道类型
- 输出：个性化外联话术（微信/邮件/电话）
- 话术中包含：候选人当前职位、岗位核心吸引点
- 不自动发送，必须人工确认后复制使用

---

### 开发任务 M04

#### M04-T1 · 候选人 CRUD + AI 解析

**Codex Prompt**：
```
1. api/routes/candidates.py 候选人 CRUD：
GET  /candidates                 列表，支持 ?open_to_move= 筛选
POST /candidates                 创建
GET  /candidates/{id}            详情
PUT  /candidates/{id}            更新
POST /candidates/{id}/resume     上传简历（Supabase Storage），返回 resume_url

2. skills/skill_resume_parser.py：
class ResumeParserInput(BaseModel):
    candidate_id: str

async def execute(input, ctx) -> SkillResult
步骤：
1. 读取 candidate.resume_url
2. 下载文件（httpx），提取文本（pdfplumber 处理PDF，python-docx 处理Word）
3. chat_json 结构化提取：{name, current_company, current_title, 
   years_experience, education, skills[], work_history[], industries[]}
4. 更新 candidates.resume_parsed
5. 自动更新 name/current_company/current_title（如果这些字段为空）

POST /skills/resume-parser/execute（上传简历后自动触发）
```

**检查点 M04-T1**：
```
☐ 上传 PDF 简历，resume_parsed 自动填充
☐ 解析结果包含 name/current_company/work_history
☐ Word 格式简历也能解析
☐ 解析失败时返回 SkillResult(success=False, error=...)，不崩溃
```

---

#### M04-T2 · Pipeline + 匹配评分

**Codex Prompt**：
```
1. api/routes/pipelines.py：
GET  /pipelines                  列表，支持 ?position_id= ?stage= 筛选
POST /pipelines                  创建（候选人关联到岗位，stage=SOURCED）
PATCH /pipelines/{id}/stage      阶段流转（记录日志到 metadata.stage_history）
GET  /positions/{id}/longlist    该岗位的 Longlist（按 match_score 降序）
GET  /positions/{id}/shortlist   该岗位的 Shortlist

2. skills/skill_match_score.py：
class MatchScoreInput(BaseModel):
    pipeline_id: str

async def execute(input, ctx) -> SkillResult
步骤：
1. 读取 Pipeline → Candidate + Position 信息
2. chat_json 评分 prompt：
   「对照岗位要求，评估候选人匹配度，输出：
    {score:0-100, match_reasons:[], concerns:[], priority:'HIGH/MEDIUM/LOW'}」
3. 更新 pipelines.match_score 和 metadata.match_detail

POST /skills/match-score/execute
```

**检查点 M04-T2**：
```
☐ 创建 Pipeline 后，在 Longlist 可见
☐ 触发匹配评分，pipeline.match_score 更新
☐ match_reasons 有具体内容（不是空数组）
☐ 晋升 Shortlist 操作正常，stage 更新为 SHORTLISTED
☐ 淘汰操作需填写原因，记录到 metadata
```

---

#### M04-T3 · 外联消息 Skill + Pipeline 看板前端

**Codex Prompt**：
```
1. skills/skill_outreach_message.py：
class OutreachInput(BaseModel):
    pipeline_id: str
    channel: str  # wechat / email / phone

async def execute(input, ctx) -> SkillResult
读取候选人（name/current_title/current_company）+ 岗位（title/search_plan）
chat_json 生成个性化话术
返回 SkillResult(need_approval=True, approval_preview={messages:{}})

2. 前端 app/(dashboard)/positions/[id]/page.tsx 中的 Pipeline 看板 Tab：
用 shadcn/ui 实现8列 Kanban（使用 @dnd-kit/core 拖拽）
列标题和对应stage：待选/进Shortlist/电话面试/已推荐/客户面试/背调/Offer/已入职
候选人卡片：姓名/公司/匹配分badge/操作菜单（晋升/淘汰/生成外联消息）
「生成外联消息」点击后打开 Dialog，展示三种话术+复制按钮

3. 前端候选人库页面 app/(dashboard)/candidates/page.tsx：
卡片列表：姓名/当前公司/职位/求职意向badge/最后联系时间
支持搜索（按名字/公司）
```

**检查点 M04-T3**：
```
☐ Pipeline 看板 8 列渲染正确
☐ 拖拽候选人，stage 更新（API 调用成功）
☐ 「生成外联消息」Dialog 展示三种话术
☐ 话术包含候选人姓名和当前公司
☐ 候选人库搜索有效
```

---

### M04 模块复盘

```
对照 PRD-M04 验收：
☐ M04-F1：候选人手动录入完整，简历上传AI解析
☐ M04-F2：AI匹配评分有实质内容，不是随机数字
☐ M04-F3：Longlist/Shortlist/淘汰 操作完整
☐ M04-F4：外联消息有个性化内容，不自动发送

复盘结论：
☐ 通过 → 进入 M05
☐ 未通过，问题：_______________
```

---

---

## M05 · 电话面试

**对应工作环节**：猎头工作环节 #5 电话面试  
**交付物**：猎头评估报告（PDF）  
**对应周次**：Week 3 - Week 4 前半段

---

### PRD-M05 · 功能需求

**M05-F1 · 录音上传与转写**
- 支持上传 MP3/WAV/M4A 格式录音（最大 100MB）
- 上传后自动触发阿里云语音识别，异步转写
- 转写完成后企业微信通知猎头
- 转写准确率标准：普通话识别准确率 > 90%（人工抽样验证）

**M05-F2 · AI 评估报告生成**
- 基于转写文本 + 岗位要求，自动生成结构化评估报告
- 报告必须包含的字段：
  - 执行摘要（一句话推荐/不推荐）
  - 胜任力评估（领导力/执行力/沟通力，各 1-5 分 + 依据）
  - 求职动机分析
  - 稳定性风险（LOW/MEDIUM/HIGH + 原因）
  - 薪资期望分析（期望 vs 预算的差距）
  - 候选人优势（2-4条）
  - 顾虑点（1-3条）
  - 推荐结论（RECOMMEND/HOLD/REJECT）
  - 推荐理由
- 报告导出为品牌化 PDF（有公司 Logo 占位、结构化排版）
- 生成时间 < 30 秒

**M05-F3 · 报告审核机制**
- AI 生成的评估报告需要猎头「确认」后才能用于推荐
- 猎头可以在界面上修改报告内容后确认
- 确认操作记录：操作人 + 时间

---

### 开发任务 M05

#### M05-T1 · 录音上传 + 转写 Skill

**Codex Prompt**：
```
1. api/routes/phone_interviews.py：
POST /pipelines/{pipeline_id}/phone-interview  创建面试记录
POST /phone-interviews/{id}/upload-audio        上传录音到 Supabase Storage，
                                                 上传完成后自动触发转写（写 automation_event）
GET  /phone-interviews/{id}                     获取面试记录（含转写状态）

2. skills/skill_phone_interview.py：
class PhoneInterviewInput(BaseModel):
    phone_interview_id: str

async def execute(input, ctx) -> SkillResult
步骤：
1. 读取 phone_interview，获取 audio_url
2. 调用 utils/asr_client.py 的 transcribe(audio_url)
3. 更新 phone_interviews.transcript
4. 再调用 chat_json 提炼 ai_insights：
   {current_situation, motivation, stability_signals, 
    salary_expectation, availability, red_flags[]}
5. 更新 phone_interviews.ai_insights
6. 调用 wecom_notifier 通知猎头「转写完成，可以生成评估报告了」

3. workers/process_automation_events.py：
   定时（每分钟）扫描 automation_events 表 status=PENDING 且 scheduled_at<=now
   根据 type 路由：PHONE_INTERVIEW_TRANSCRIBE → 调用 skill_phone_interview

在 vercel.json 添加：每分钟 * * * * * 触发 /api/cron/process-events
（Vercel Cron 最小粒度是每分钟，免费版每天一次，付费版可以每分钟）
如果不想升级 Vercel，改用阿里云函数计算定时触发器（每分钟免费）
```

**检查点 M05-T1**：
```
☐ 上传 MP3 录音，audio_url 保存到数据库
☐ automation_event 写入，type=PHONE_INTERVIEW_TRANSCRIBE
☐ 触发转写后，transcript 字段非空
☐ ai_insights 包含 motivation/salary_expectation 等字段
☐ 企业微信收到转写完成通知
```

---

#### M05-T2 · 评估报告 Skill + PDF

**Codex Prompt**：
```
1. skills/skill_eval_report.py：
class EvalReportInput(BaseModel):
    phone_interview_id: str

async def execute(input, ctx) -> SkillResult
步骤：
1. 读取 phone_interview（transcript + ai_insights）
2. 通过 pipeline_id → position_id 读取岗位 search_plan
3. 构建详细 prompt，chat_json 生成评估报告 JSON：
   {executive_summary, competency:{leadership,execution,communication},
    motivation, stability_risk, stability_reason, salary_analysis,
    strengths[], concerns[], recommendation, recommendation_reason}
4. 调用 utils/pdf_generator.py 的 generate_report_pdf(report_data, template="eval") -> url
5. 创建 reports 表记录（type=EVAL, ai_generated=true, confirmed=false）
6. 返回 {report_id, report_content, pdf_url}

2. utils/pdf_generator.py：
def generate_report_pdf(data: dict, template: str) -> str（返回OSS URL）
使用 WeasyPrint，HTML 模板用 Jinja2
eval 模板需包含：标题/候选人姓名/岗位/各维度评分可视化/推荐结论醒目标注
将 PDF 上传到 Supabase Storage，返回公开 URL

POST /skills/eval-report/execute
PATCH /reports/{id}/confirm   猎头确认报告（记录 confirmed_by, confirmed_at）
```

**检查点 M05-T2**：
```
☐ 评估报告 JSON 所有字段非空
☐ recommendation 是 RECOMMEND/HOLD/REJECT 之一
☐ PDF 生成且可下载，排版正常，无中文乱码
☐ 胜任力评分有具体依据（evidence 字段有内容）
☐ 确认报告接口正常，confirmed_at 更新
☐ 人工评审 3 份报告：质量通过（有实质内容，不是废话）
```

---

#### M05-T3 · 前端录音+报告界面

**Claude Code Prompt**：
```
在 Pipeline 详情页（点击看板中的候选人卡片弹出的抽屉）添加「电话面试」区块：

1. 区块状态机：
   - 未开始：显示「新建电话面试」按钮
   - 已创建/转写中：显示录音上传区（拖拽上传）+ 转写状态进度
   - 转写完成：显示转写文本折叠展示 + 「生成评估报告」按钮
   - 报告生成中：loading 状态
   - 报告已生成（未确认）：报告预览 + 「编辑并确认」按钮（黄色警告）
   - 报告已确认：报告预览 + 「下载PDF」按钮（绿色）

2. 报告预览：
   用卡片展示各维度评分（星级图标）
   推荐结论用大字体彩色显示（RECOMMEND=绿/HOLD=黄/REJECT=红）

3. 编辑功能：
   点击「编辑并确认」弹出 Dialog
   JSON 内容渲染为表单（各字段可编辑）
   保存后调用确认接口

使用 shadcn/ui 的 Progress, Badge, Dialog 组件。
```

**检查点 M05-T3**：
```
☐ 上传录音后显示转写进度状态
☐ 转写完成后「生成评估报告」按钮出现
☐ 报告生成后各维度评分正确展示
☐ 推荐结论颜色正确（RECOMMEND=绿）
☐ 编辑报告后确认，confirmed_at 更新
☐ 未确认的报告有明显的「待确认」提示
```

---

### M05 模块复盘

```
对照 PRD-M05 验收：
☐ M05-F1：录音上传正常，转写准确率人工评估 > 90%
☐ M05-F2：报告包含所有必填字段，PDF排版正确
☐ M05-F3：确认机制有效，未确认的报告有明显标识

人工质量验收（必做）：
☐ 用一段真实猎头电话录音测试，转写结果可用
☐ 基于该录音生成评估报告，内容有实质意义

复盘结论：
☐ 通过 → 进入 M06
☐ 未通过，问题：_______________
```

---

---

## M06 · 人选推荐

**对应工作环节**：猎头工作环节 #6 人选推荐  
**交付物**：推荐报告（PDF）  
**对应周次**：Week 4

---

### PRD-M06 · 功能需求

**M06-F1 · 推荐报告生成**
- 前置条件：评估报告已生成且已确认
- 基于评估报告 + 候选人基本信息 + 岗位信息自动生成
- 报告内容：
  - 候选人快照（一页纸摘要）
  - 与岗位匹配度分析（需有具体对应关系）
  - 候选人核心优势（2-3条，引用面试原话）
  - 顾虑点及应对建议
  - 猎头推荐意见（1段）
- 附带候选人简历
- 生成时间 < 30 秒

**M06-F2 · 报告发送给客户**
- 发送方式：邮件（附件 PDF + 正文摘要）
- 生成无需登录的分享链接（7天有效期）
- 发送前需猎头确认
- 发送记录（时间 + 收件人）

**M06-F3 · 客户反馈收集**
- 客户通过分享链接查看报告后可以提交反馈
- 反馈选项：感兴趣（安排面试）/ 有顾虑（填写原因）/ 不合适（填写原因）
- 反馈提交后：Pipeline 阶段自动更新，猎头企业微信收到通知

---

### 开发任务 M06

#### M06-T1 · 推荐报告 Skill + 发送

**Codex Prompt**：
```
1. skills/skill_recommend_report.py：
class RecommendReportInput(BaseModel):
    pipeline_id: str
    custom_note: str = ""

async def execute(input, ctx) -> SkillResult
步骤：
1. 验证：pipeline 对应的 eval_report 必须已 confirmed
2. 读取：候选人信息 + 岗位信息 + eval_report.content
3. chat_json 生成推荐报告：
   {candidate_snapshot, match_analysis, core_strengths[], 
    concerns_and_mitigation[], headhunter_endorsement}
4. 生成 PDF（template="recommend"）
5. 创建 reports 记录（type=RECOMMEND），返回 share_token

2. api/routes/reports.py：
POST /reports/{id}/send-to-client  发送报告给客户（邮件，需 need_approval=True 确认）
GET  /r/{share_token}              公开报告查看页（不需要登录）
POST /r/{share_token}/feedback     客户提交反馈
  body: {result:"INTERESTED/CONCERNS/NOT_FIT", reason:""}
  side_effect: 更新 pipeline.stage，写 automation_event 通知猎头

3. 邮件发送：utils/email_client.py
   async def send_report_email(to_email, candidate_name, position_title, pdf_url, share_url)
   使用阿里云邮件推送（或 Resend）
```

**检查点 M06-T1**：
```
☐ 推荐报告生成（前置：eval_report 已确认）
☐ 推荐报告内容与评估报告一致（优势/顾虑对应）
☐ 分享链接无需登录可访问，7天后过期
☐ 发送邮件成功（收件人收到）
☐ 客户提交「感兴趣」反馈后，pipeline.stage 更新为 CLIENT_INTERVIEW
☐ 猎头企业微信收到「客户感兴趣」通知
```

---

#### M06-T2 · 报告中心前端

**Claude Code Prompt**：
```
1. app/(dashboard)/reports/page.tsx 报告中心：
   列表：类型badge(EVAL/RECOMMEND/BGCHECK) / 候选人名 / 岗位 / 生成时间 / 确认状态 / 操作
   顶部筛选：按类型 / 按岗位 / 按日期范围

2. 报告预览 Dialog（所有报告类型通用）：
   根据 report.type 渲染不同内容：
   - EVAL：展示胜任力雷达图（用 recharts）+ 推荐结论大字
   - RECOMMEND：展示候选人快照 + 匹配分析
   按钮：下载PDF / 发送给客户（如果是RECOMMEND且已confirmed）

3. app/(public)/r/[token]/page.tsx 公开报告页（不需要登录）：
   展示推荐报告内容（美观，有公司 Logo）
   底部反馈区：三个按钮 + 原因输入框
   提交反馈后显示「感谢您的反馈，我们的顾问会尽快联系您」
```

**检查点 M06-T2**：
```
☐ 报告中心列表所有类型展示正确
☐ 推荐报告发送流程：预览→确认→发送 完整走通
☐ 公开页面在手机上渲染正常
☐ 客户提交反馈后显示成功提示
```

---

### M06 模块复盘

```
对照 PRD-M06 验收：
☐ M06-F1：推荐报告内容有实质意义（人工评审）
☐ M06-F2：邮件发送成功，分享链接有效期正确
☐ M06-F3：客户反馈触发 Pipeline 更新和微信通知

端到端流程验收：
☐ 完整走一遍：录音上传→转写→评估报告→确认→推荐报告→发送→客户反馈

复盘结论：
☐ 通过 → 进入 M07
☐ 未通过，问题：_______________
```

---

---

## M07 · Chat 界面 + 基础 Agent

**对应周次**：Week 5-6  
**目标**：猎头用自然语言触发任何功能，不用找菜单

---

### PRD-M07 · 功能需求

**M07-F1 · 对话界面**
- 左侧消息流（区分用户/AI 样式）
- 底部输入框，支持 `/` 斜杠命令自动补全
- AI 回复支持流式输出（打字机效果）
- 右侧动态面板：根据 Agent 返回的内容类型切换（Longlist / Pipeline看板 / 报告 / 待办列表）

**M07-F2 · 意图理解**
- 支持的意图类型（全部13个 Skill + 查询类）：
  - 查询今日待办
  - 生成寻访计划
  - 搜寻候选人
  - 生成外联消息
  - 生成评估报告
  - 生成推荐报告
  - 面试协调
  - 生成背调报告
  - 跟踪入离职
  - 试用期回访
  - 开票催款
  - BD 线索生成
  - 合同草稿

**M07-F3 · 今日待办聚合**
- 输入「今天有什么要做的」或直接打开 /chat 页面
- 自动汇总：待回复外联 / 今天有面试 / 试用期节点到期 / 逾期账单 / 待确认报告
- 按优先级排序，每项可点击跳转

**M07-F4 · 斜杠命令**
```
/today             今日待办
/find [岗位名]     搜寻候选人
/report [候选人]   生成评估报告
/outreach [候选人] 生成外联消息
/plan [岗位名]     生成寻访计划
/invoice           查看开票状态
```

---

### 开发任务 M07

#### M07-T1 · LangGraph Agent 核心

**Claude Code Prompt**：
```
创建 agent/ 目录，实现基础 LangGraph Agent：

1. agent/intent.py
   INTENT_MAP = {
     "query_todo": ["今天", "待办", "什么要做", "今日"],
     "source_candidates": ["找候选人", "搜寻", "longlist", "找人"],
     "eval_report": ["评估报告", "写报告", "面试报告"],
     "recommend_report": ["推荐报告", "推荐给客户"],
     "outreach": ["外联", "发消息", "联系候选人"],
     "search_plan": ["寻访计划", "开单"],
     "bd_lead": ["BD线索", "找客户", "目标客户"],
     # ...其他意图
   }
   async def classify_intent(message: str, ctx) -> dict:
       # 用 Qwen-Max few-shot 分类
       # 返回 {intent, entities:{position_id?,candidate_id?,client_id?}, confidence}

2. agent/graph.py
   用 LangGraph 定义状态机：
   State: {messages[], intent, entities, skill_result, pending_approval}
   
   节点：
   - understand: 调用 classify_intent
   - plan: 根据 intent 决定调用哪个 Skill
   - execute: 调用对应 Skill
   - check_approval: 如果 need_approval=True，暂停等待
   - respond: 生成自然语言回复 + render_type 指示前端渲染什么

   图结构：understand → plan → execute → check_approval → respond

3. api/routes/agent.py
   POST /agent/chat  body:{message, session_id}
   调用 AgentRunner，返回 SSE 流：
   data: {"type":"text","content":"..."}    AI 回复文字（逐字）
   data: {"type":"render","render_type":"longlist","data":{...}}  右侧面板数据
   data: {"type":"approval","token":"...","preview":{...}}  需要确认时
   data: {"type":"done"}  结束
   
   POST /agent/confirm/{token}  用户确认后继续执行
```

**检查点 M07-T1**：
```
☐ 输入「今天有什么待办」→ 返回结构化待办列表
☐ 输入「帮我给腾讯CFO岗找候选人」→ 触发 skill_source_candidates（或提示需要更多信息）
☐ SSE 流式输出正常（postman/curl 可观察到逐步返回）
☐ 20条测试指令，意图识别准确率 > 80%（手动测试并记录结果）
```

---

#### M07-T2 · Chat 前端

**Claude Code Prompt**：
```
创建 app/(dashboard)/chat/page.tsx：

布局：左1/3消息区 + 右2/3动态面板区（或者移动端叠放）

消息区：
- 消息列表（用户消息右对齐蓝色，AI消息左对齐灰色）
- AI消息支持 Markdown 渲染（用 react-markdown）
- 流式输出时显示打字动画
- 底部输入框 + 发送按钮
- 输入 / 时弹出命令菜单（展示所有斜杠命令）

动态面板区（根据 render_type 切换）：
- "longlist"     → 渲染 CandidateCard 列表（复用M04的组件）
- "pipeline"     → 渲染 PipelineKanban（复用M04的组件）
- "report"       → 渲染 ReportPreview（复用M06的组件）
- "todo_list"    → 渲染待办卡片列表（每项有跳转链接）
- "approval"     → 渲染确认卡片（预览内容 + 确认/取消按钮）
- null           → 显示使用提示

页面加载时自动发送「今天有什么待办」并展示结果。
```

**检查点 M07-T2**：
```
☐ 消息流渲染正确（用户/AI 样式区分）
☐ 流式输出有打字动画效果
☐ 斜杠命令弹出菜单
☐ 右侧面板根据 render_type 正确切换
☐ 页面加载自动展示今日待办
☐ 确认卡片点击「确认」后继续执行
```

---

### M07 模块复盘

```
对照 PRD-M07 验收：
☐ M07-F1：Chat 界面布局正确，流式输出正常
☐ M07-F2：所有意图类型可被识别（测试 20 条）
☐ M07-F3：今日待办汇总数据准确
☐ M07-F4：6个斜杠命令可用

复盘结论：
☐ 通过 → 进入 M08
☐ 未通过，问题：_______________
```

---

---

## M08 · 内部人才库

**对应工作环节**：猎头工作环节 #13 人才库维护  
**交付物**：人选标签体系、跟进管理表  
**对应周次**：Week 6-7

---

### PRD-M08 · 功能需求

**M08-F1 · 向量语义搜索**
- 候选人入库时自动生成简历摘要向量（Supabase pgvector）
- 岗位创建时自动生成 JD 向量
- 支持自然语言搜索：「找过CFO的候选人」「有互联网背景的财务总监」
- 搜索结果按相似度排序，显示相似度分数

**M08-F2 · 标签体系**
- AI 自动打标签（行业 / 职能 / 职级 / 求职状态 / 风险标签）
- 猎头可手动添加/删除标签
- 支持按标签筛选候选人

**M08-F3 · 沉睡唤醒**
- 30天未联系的候选人标记为「沉睡」
- 定时扫描，每周一推送「沉睡候选人」列表给猎头
- 新岗位创建时，从人才库自动匹配 Top10 历史候选人并提醒

---

### 开发任务 M08

#### M08-T1 · 向量化 + 语义搜索

**Codex Prompt**：
```
1. utils/vector_search.py：

async def vectorize_candidate(candidate_id: str, db) -> bool:
    """读取候选人信息，生成摘要，向量化存到 candidates.embedding"""
    candidate = db.table("candidates").select("*").eq("id", candidate_id).single().execute()
    summary = f"{candidate.name} {candidate.current_title} {candidate.current_company} {' '.join(candidate.resume_parsed.get('skills', []) if candidate.resume_parsed else [])}"
    embedding = await get_embedding(summary)
    db.table("candidates").update({"embedding": embedding}).eq("id", candidate_id).execute()
    return True

async def vectorize_position(position_id: str, db) -> bool:
    """读取岗位JD，向量化存到 positions.embedding"""

async def search_candidates(query: str, db, limit: int = 20) -> list:
    """
    语义搜索候选人
    1. query 文本向量化
    2. 调用 Supabase RPC 做向量相似度搜索
    返回 [{candidate_id, name, current_title, similarity_score}]
    """

2. 在 Supabase SQL Editor 创建 RPC 函数：
CREATE OR REPLACE FUNCTION search_candidates(query_embedding vector(1536), match_count int)
RETURNS TABLE(id uuid, name text, current_title text, current_company text, similarity float)
LANGUAGE SQL AS $$
  SELECT id, name, current_title, current_company,
         1 - (embedding <=> query_embedding) AS similarity
  FROM candidates
  WHERE embedding IS NOT NULL
  ORDER BY embedding <=> query_embedding
  LIMIT match_count;
$$;

3. 触发点：
   - 候选人创建/更新简历时，写 automation_event(VECTORIZE_CANDIDATE)
   - 岗位创建/JD更新时，写 automation_event(VECTORIZE_POSITION)

4. GET /candidates/search?q=CFO互联网背景 端点，调用 search_candidates
```

**检查点 M08-T1**：
```
☐ 新建候选人后，embedding 字段有值（1536维向量）
☐ 搜索「互联网CFO」，返回与关键词语义相关的候选人
☐ 搜索结果包含 similarity_score（0-1之间）
☐ 搜索响应时间 < 2 秒（100条候选人数据测试）
```

---

#### M08-T2 · 标签 + 沉睡机制

**Codex Prompt**：
```
1. AI 自动打标签（在 skill_resume_parser.py 中增加）：
   解析完简历后，额外调用 chat_json 生成标签：
   {"industry_tags":["互联网","SaaS"], "function_tags":["财务","CFO"], 
    "level_tag":"C_LEVEL", "intent_tag":"PASSIVE"}
   更新到 candidates.tags

2. 手动标签 API：
   POST /candidates/{id}/tags  添加标签 body:{key,value}
   DELETE /candidates/{id}/tags/{tag_id}  删除标签

3. workers/dormant_checker.py：
   async def check_dormant_candidates():
     查询 last_contacted_at < 30天前 的候选人
     更新标签 {key:"status", value:"dormant"}
     每周一给 owner 发微信：「您有X位沉睡候选人，上次联系时间超过30天」+列表

4. 新岗位创建时的人才库匹配（在 skill_search_plan.py 末尾增加）：
   新岗位创建后，search_candidates(jd_text) 取 Top10
   写 automation_event(NEW_POSITION_TALENT_MATCH)
   处理：向 owner 推送微信「已为XX岗找到10位历史候选人，点击查看」
```

**检查点 M08-T2**：
```
☐ 候选人简历解析后自动获得标签（industry/function/level）
☐ 按标签筛选候选人功能正常
☐ 手动触发 dormant_checker，30天未联系的候选人收到「dormant」标签
☐ 创建新岗位后，微信收到「历史人才匹配」通知
```

---

### M08 模块复盘

```
对照 PRD-M08 验收：
☐ M08-F1：语义搜索有实质意义（搜「互联网CFO」能找到相关候选人）
☐ M08-F2：AI标签自动生成，手动标签可增删
☐ M08-F3：沉睡机制触发，每周提醒正常

复盘结论：
☐ 通过 → 进入 M09
☐ 未通过，问题：_______________
```

---

---

## M09 · RPA 采集层

**对应工作环节**：猎头工作环节 #4 人选寻访（自动化部分）  
**对应周次**：Week 8-9

---

### PRD-M09 · 功能需求

**M09-F1 · 多平台自动搜寻**
- 支持平台：猎聘（主力）/ 脉脉（补充）
- 输入：搜索关键词 + 目标公司列表
- 输出：候选人列表（自动去重 + AI 评分 + 入库）
- 稳定性要求：连续运行 72 小时无崩溃

**M09-F2 · 反检测措施**
- 拟人化鼠标轨迹和点击延迟
- 账号池管理（≥ 3 个账号轮换）
- 住宅 IP 代理轮换
- 滑块验证码自动处理
- 封号自动切换备用账号

**M09-F3 · 三级降级策略**
- Level 1：RPA 正常执行
- Level 2：触发频繁验证码 → 降频 + 扩大账号池
- Level 3：账号全部被封 → 企业微信通知猎头手动处理

**M09-F4 · 求职信号检测（脉脉专项）**
- 分析候选人职场动态，识别求职信号
- 标记「近期离职」「主动扩展人脉」等高意向特征

---

### 开发任务 M09

#### M09-T1 · 浏览器池 + 反检测

**Claude Code Prompt**：
```
创建 rpa/ 目录，实现以下文件：

1. rpa/base_scraper.py
   from DrissionPage import ChromiumPage, ChromiumOptions
   
   def create_stealth_page(proxy=None) -> ChromiumPage:
     - 随机 UA（提供5个真实Chrome UA的列表）
     - 代理配置
     - 禁用 AutomationControlled
     - 随机窗口大小 [1366x768, 1440x900, 1920x1080]
     - 注入 JS 隐藏 navigator.webdriver
     - 返回 page 实例
   
   def human_delay(min_sec=0.8, max_sec=2.5): time.sleep(random.uniform(...))
   
   def scroll_humanly(page, total_distance=500):
     分3-8步滚动，每步随机间隔

2. rpa/browser_pool.py
   class BrowserPool:
     sessions: dict  # session_id -> {account, proxy, status, request_count, last_used}
     
     def load_accounts_from_env():
       从环境变量 LIEPIN_ACCOUNTS 读取（JSON格式：[{username,password,phone}]）
     
     async def acquire(platform) -> Optional[dict]:  # 返回可用的 session 配置
     async def release(session_id, success, got_captcha=False, got_banned=False)
     def get_health() -> dict  # 返回各平台账号状态

3. rpa/captcha_handler.py
   async def handle_slider(page) -> bool:
     - 用 ddddocr 识别缺口位置
     - 模拟人类拖动轨迹（先快后慢，有微抖动）
     - 返回是否成功

   async def notify_human(session_id, platform, notifier) -> Optional[str]:
     - 遇到短信验证码时通知猎头
     - 等待最多5分钟，轮询 Redis 里的人工输入结果
```

**检查点 M09-T1**：
```
☐ create_stealth_page 启动 Chrome 无报错
☐ 访问 https://bot.sannysoft.com 检测页面，无明显机器人特征
☐ BrowserPool.acquire 返回可用账号（需先在环境变量配置测试账号）
☐ 触发滑块验证码，handle_slider 处理成功率 > 60%（10次测试）
```

---

#### M09-T2 · 猎聘采集器

**Claude Code Prompt**：
```
创建 rpa/scrapers/liepin.py：

class LiepinScraper:
    def __init__(self, pool: BrowserPool, captcha: CaptchaHandler): ...
    
    def search_candidates(
        self, session: dict, keywords: list[str], limit: int = 30
    ) -> dict:  # {"candidates":[], "got_captcha": bool, "need_relogin": bool}
    
    步骤：
    1. create_stealth_page(proxy=session["proxy"])
    2. 从 Redis 读取 Cookie（key="liepin_cookie_{account_id}"），注入并刷新
    3. 检查登录状态（看有无用户头像元素）
    4. 如果未登录：填写账号密码，处理可能出现的滑块验证码，登录
    5. 访问招聘方人才搜索页（https://cs.liepin.com/headhunter/search）
    6. 输入关键词（human_type 方式）
    7. 等待结果，scroll_humanly，提取候选人卡片：
       {name, current_title, current_company, experience, education, location, profile_url}
    8. 每页等待 2-4 秒，翻页（最多3页）
    9. 保存 Cookie 到 Redis
    10. 返回结果

    def _extract_candidates_from_page(page) -> list[dict]: 提取当前页候选人
    def _is_logged_in(page) -> bool: 判断登录状态

注意：
- 每个操作之间 human_delay
- 检测到验证码（判断方式：页面出现 .captcha-wrapper 元素）立即处理
- 检测到封号（判断方式：页面出现「您的账号已被禁用」）设置 got_banned=True
- 不使用 async/await（DrissionPage 是同步库），用普通函数
```

**检查点 M09-T2**：
```
☐ 用测试账号登录猎聘成功
☐ 搜索「互联网 CFO」返回 ≥ 15 条候选人
☐ 候选人数据包含 name/current_title/current_company
☐ Cookie 保存到 Redis，下次调用不需要重新登录
☐ 运行 30 分钟不触发封号（控制 human_delay）
```

---

#### M09-T3 · 数据管道 + Skill 集成

**Claude Code Prompt**：
```
1. rpa/data_pipeline.py：

async def process_raw_candidates(raw_list: list[dict], position_id: str, db) -> list[dict]:
    步骤：
    a. 去重：按 f"{name}_{current_company}" 去重，多平台数据合并
    b. AI 结构化：批量调用 chat_json（每批10条），标准化字段
    c. 内部人才库查重：按姓名+公司查 candidates 表，已有的不重复创建
    d. AI 匹配评分：调用 Qwen-Max，对比 position.search_plan 打分
    e. 入库：创建/更新 candidate 记录，创建 pipeline 记录（stage=SOURCED）
    f. 异步向量化：写 automation_event(VECTORIZE_CANDIDATE)
    返回 scored_longlist

2. 更新 skills/skill_source_candidates.py，集成 RPA：

async def execute(input, ctx) -> SkillResult:
    # Level 1: RPA 自动搜索
    session = browser_pool.acquire(Platform.LIEPIN)
    if session:
        raw = liepin_scraper.search_candidates(session, keywords)
        candidates = await data_pipeline.process(raw, position_id, ctx.db)
        return SkillResult(success=True, data={"longlist": candidates})
    
    # Level 2: 内部人才库向量搜索（保底）
    internal = await vector_search.search_candidates(query, ctx.db, limit=20)
    if internal:
        return SkillResult(success=True, data={"longlist": internal, "source": "internal_only"})
    
    # Level 3: 通知人工处理
    await wecom_notifier.push(ctx.user_id, "⚠️ 自动搜索失败，请手动搜索后上传简历")
    return SkillResult(success=False, error="RPA不可用，已通知人工处理")
```

**检查点 M09-T3**：
```
☐ 完整流程：触发 skill_source_candidates → RPA 搜猎聘 → 数据清洗 → 入库
☐ 去重逻辑：同名同公司的候选人只创建一条记录
☐ AI 评分非随机（不同候选人有明显分差）
☐ Level 2 降级：关闭猎聘账号后，自动用内部人才库返回结果
☐ Level 3 降级：内部库也没有时，微信收到通知
```

---

### M09 模块复盘

```
对照 PRD-M09 验收：
☐ M09-F1：猎聘搜索返回有效候选人，数据入库
☐ M09-F2：账号池切换正常，验证码自动处理率 > 50%
☐ M09-F3：三级降级策略均可触发
☐ 稳定性：连续运行 24 小时无崩溃（Week 9 期间持续观测）

人工验收：
☐ 搜一个真实岗位关键词，检查返回的候选人是否符合要求

复盘结论：
☐ 通过 → 进入 M10
☐ 未通过，问题：_______________
```

---

---

## M10 · 面试协调

**对应工作环节**：猎头工作环节 #7 面试协调  
**交付物**：面试日程安排、面试辅导材料  
**对应周次**：Week 10 前半段

---

### PRD-M10 · 功能需求

**M10-F1 · 面试安排**
- 创建面试：关联 Pipeline / 面试轮次 / 时间 / 面试官信息
- 一个 Pipeline 可以有多轮面试
- 发送邮件邀约（候选人 + 客户联系人）
- 面试前 24 小时自动提醒

**M10-F2 · 面试辅导材料**
- 基于公司信息 + 岗位信息 + 面试官信息 AI 生成候选人辅导材料
- 内容：公司简介 / 业务重点 / 岗位核心挑战 / 面试官风格（如果已知）/ 常见问题预测 / 着装建议
- 生成 PDF，面试前发送给候选人

**M10-F3 · 面后反馈收集**
- 面试结束后自动触发（面试时间+2小时）给双方发反馈收集
- 收集：客户意见（通过/下一轮/不合适）+ 候选人感受
- 反馈更新 Pipeline 状态

---

### 开发任务 M10

#### M10-T1 · 面试 CRUD + AI辅导

**Codex Prompt**：
```
1. api/routes/interviews.py：
POST /pipelines/{id}/interviews   创建面试
GET  /pipelines/{id}/interviews   面试列表
PATCH /interviews/{id}            更新（记录结果/反馈）

2. skills/skill_interview_schedule.py：
class InterviewInput(BaseModel):
    pipeline_id: str
    round: str  # HR/HIRING_MANAGER/FINAL
    scheduled_at: str  # ISO 时间
    interviewer_name: str
    interviewer_title: str

async def execute(input, ctx) -> SkillResult:
1. 创建 interview 记录
2. 发邮件给候选人 + 客户联系人（utils/email_client.py）
3. 生成辅导材料 PDF（chat_json 生成内容，pdf_generator 渲染）
4. 写 automation_event(INTERVIEW_REMINDER, scheduled_at=面试时间-24h)
5. 写 automation_event(INTERVIEW_FEEDBACK_REQUEST, scheduled_at=面试时间+2h)
6. 返回 {interview_id, prep_material_url}

3. 处理 INTERVIEW_REMINDER 事件：向候选人企业微信/邮件发提醒
4. 处理 INTERVIEW_FEEDBACK_REQUEST 事件：向双方发反馈收集链接
```

**检查点 M10-T1**：
```
☐ 创建面试后，候选人和客户各收到邀约邮件
☐ 辅导材料 PDF 包含：公司介绍/岗位挑战/面试官/常见问题
☐ 24小时前提醒事件正确触发
☐ 面试后2小时反馈请求发出
```

---

### M10 模块复盘

```
对照 PRD-M10 验收：
☐ M10-F1：面试安排完整，邮件邀约成功
☐ M10-F2：辅导材料内容有实质意义
☐ M10-F3：面后反馈自动触发，更新Pipeline

复盘结论：
☐ 通过 → 进入 M11
☐ 未通过，问题：_______________
```

---

---

## M11 · 背景调查

**对应工作环节**：猎头工作环节 #8 背景调查  
**交付物**：背调报告  
**对应周次**：Week 10 后半段

---

### PRD-M11 · 功能需求

**M11-F1 · 背调信息管理**
- 关联 Pipeline，记录参考人信息（姓名/职位/与候选人关系/联系方式）
- 每个候选人支持 2-5 个参考人
- 每个参考人可上传对应的通话录音

**M11-F2 · AI 背调报告**
- 对每段录音进行转写（复用 skill_phone_interview 的转写逻辑）
- 综合所有参考人评价，生成背调报告：
  - 每位参考人评价摘要
  - 共同主题（多人提到的内容）
  - 差异点（意见不一致的地方）
  - 风险点（红旗事项）
  - 综合结论（PASS/RISK/FAIL）
- 报告发送客户前需猎头确认

---

### 开发任务 M11

**Codex Prompt**：
```
1. api/routes/bg_checks.py：
POST /pipelines/{id}/bg-check            启动背调
POST /bg-checks/{id}/referees            添加参考人 body:{name,title,relationship,phone}
POST /bg-checks/{id}/referees/{ref_id}/audio  上传参考人录音
GET  /bg-checks/{id}                     背调详情

2. skills/skill_bgcheck_report.py：
class BGCheckInput(BaseModel):
    pipeline_id: str  # 背调必须关联 pipeline

async def execute(input, ctx) -> SkillResult:
1. 读取所有参考人的 audio_url
2. 批量调用 asr_client.transcribe（对每段录音）
3. 汇总所有转写文本
4. chat_json 综合分析：
   {referee_summaries:[{name,summary,key_quotes[]}],
    common_themes[], discrepancies[], risk_points[],
    overall_conclusion:"PASS/RISK/FAIL", recommendation}
5. 生成 PDF（risk_points 红色高亮），创建 reports 记录（type=BGCHECK）
```

**检查点 M11**：
```
☐ 多参考人录音均完成转写
☐ 背调报告综合了所有参考人意见
☐ 风险点在报告中有明显标注（红色）
☐ 整体结论 PASS/RISK/FAIL 有判断依据
```

---

---

## M12 · 入离职管理

**对应工作环节**：猎头工作环节 #9 入离职  
**交付物**：离职入职时间 check 表、入职跟进管理表  
**对应周次**：Week 11 前半段

---

### PRD-M12 · 功能需求

**M12-F1 · Offer 信息录入**
- 录入：Offer 薪资 / 计划离职日 / 预计入职日
- 自动计算关键节点时间
- Counter Offer 风险评估（AI 分析）

**M12-F2 · 入离职 Check 表**
- AI 生成包含以下节点的 check 表：
  - 确认提离职日期
  - 确认离职手续进行中
  - 确认入职前未被 Counter
  - 入职当天确认（最重要）
- 每个节点到期前企业微信提醒猎头
- 实际入职日确认后，自动触发试用期管理（M13）和开票（M14）

**M12-F3 · Counter Offer 监控**
- 高风险阶段（提离职后到入职前）每 3 天推送提醒
- 如发生 Counter Offer，记录应对结果

---

### 开发任务 M12

**Codex Prompt**：
```
1. api/routes/onboardings.py：
POST /pipelines/{id}/onboarding  创建 onboarding，录入 Offer 信息
PATCH /onboardings/{id}          更新（实际入职日确认）

2. skills/skill_onboarding_track.py：
async def execute(input, ctx) -> SkillResult:
1. 创建 onboarding 记录
2. AI 评估 Counter Offer 风险（基于在职年限/薪资涨幅/离职原因）
3. 生成 check 表 JSON（节点列表 + 每个节点的预计时间）
4. 批量写 automation_events：
   - 各 check 节点提醒（到期前1天）
   - Counter Offer 高频提醒（高风险时3天一次）
5. 返回 {onboarding_id, check_table, counter_offer_risk}

3. 实际入职确认处理（PATCH /onboardings/{id} actual_join_date 更新时）：
   - 写 automation_event(CREATE_PROBATION_SCHEDULE) → 触发M13
   - 写 automation_event(GENERATE_INVOICE) → 触发M14
```

**检查点 M12**：
```
☐ Offer 录入后 check 表生成，节点时间计算正确
☐ 各节点到期前企业微信提醒触发
☐ 实际入职确认后：probation events 和 invoice event 自动写入
☐ Counter Offer 风险评估有依据
```

---

---

## M13 · 试用期管理

**对应工作环节**：猎头工作环节 #10 试用期管理  
**交付物**：1天/7天/30天/60天/90天 分阶段回访报告  
**对应周次**：Week 11 后半段

---

### PRD-M13 · 功能需求

**M13-F1 · 自动调度（核心）**
- 入职日确认后，自动创建 5 条 probation 记录（1/7/30/60/90天）
- 每条记录的 scheduled_at = actual_join_date + N 天
- 到期当天 9:00 企业微信提醒猎头完成回访
- 100% 准时，零遗漏

**M13-F2 · 回访记录**
- 猎头录入候选人反馈 + 客户反馈（文字）
- AI 生成阶段回访报告（含融入状况/风险信号/下阶段建议）
- 高风险信号（候选人提到「不太适合」「在考虑其他机会」）立即推送紧急提醒

**M13-F3 · 90天通过**
- 90天回访完成后，自动标记「保证期完成」
- 触发开票（如果约定90天付款）
- 触发二次开发提醒（M15）

---

### 开发任务 M13

**Codex Prompt**：
```
1. 处理 CREATE_PROBATION_SCHEDULE 事件：
   当 onboarding.actual_join_date 确认时触发
   批量插入 probations 表（5条，day=1/7/30/60/90）
   scheduled_at = actual_join_date + N days（注意时区：Asia/Shanghai）
   同时批量写 automation_events(PROBATION_REMINDER_X, scheduled_at=probation.scheduled_at-0天早9点)

2. workers/probation_reminder.py（每天9点触发）：
   查询 scheduled_at <= today 且 status=PENDING 的 probations
   向 owner 发企业微信：「今天是[候选人]入职第X天，请完成双向回访并录入系统」

3. skills/skill_probation_followup.py：
class ProbationInput(BaseModel):
    probation_id: str
    candidate_feedback: str
    client_feedback: str

async def execute(input, ctx) -> SkillResult:
1. 更新 probation.completed_at
2. chat_json 分析风险信号：
   {integration_status, risk_signals[], risk_level:"LOW/MEDIUM/HIGH", next_advice}
3. 如果 risk_level=HIGH：立即写 automation_event(PROBATION_RISK_ALERT, scheduled_at=now)
   处理：立即企业微信推送「⚠️紧急：候选人风险信号-需立即跟进」
4. 生成阶段报告 PDF
5. 如果是 day=90 且 risk_level != HIGH：
   更新 pipeline.stage = PLACED
   写 automation_event(TRIGGER_SECONDARY_BD)
```

**检查点 M13**：
```
☐ 入职确认后，probations 表有 5 条记录，时间正确
☐ 手动模拟到期，企业微信准时收到提醒（不超过5分钟误差）
☐ 录入包含「不太适合」的反馈，触发高风险即时告警
☐ 90天完成后 pipeline.stage 更新为 PLACED
```

---

---

## M14 · 开票管理

**对应工作环节**：猎头工作环节 #11 开票管理  
**交付物**：账单、催款函  
**对应周次**：Week 12 前半段

---

### PRD-M14 · 功能需求

**M14-F1 · 自动触发开票**
- 入职确认时（或90天后，取决于合同约定）自动触发
- 金额计算：Offer 薪资 × 合同费率（精确到分）
- 生成账单 PDF（含：金额/计算依据/付款截止日/收款账户）

**M14-F2 · 三级催款**
- 到期前 3 天：提醒邮件（友好措辞）
- 逾期 7 天：催款函（正式措辞）
- 逾期 15 天：最终催款函（严肃措辞，提及合同条款）
- 每次催款通知猎头已发送

**M14-F3 · 付款管理**
- 手动确认付款（PATCH /invoices/{id}/paid）
- 付款确认后触发二次开发提醒

---

### 开发任务 M14

**Codex Prompt**：
```
1. api/routes/invoices.py：
GET  /invoices              列表，支持 ?status= 筛选
GET  /invoices/{id}         详情
PATCH /invoices/{id}/paid   确认付款

2. skills/skill_invoice_manage.py：
class InvoiceInput(BaseModel):
    pipeline_id: str
    trigger: str  # "JOIN_CONFIRMED" 或 "OVERDUE_CHECK"

async def execute(input, ctx) -> SkillResult:

JOIN_CONFIRMED 处理：
1. 读取 onboarding.offer_salary + contract.fee_rate
2. 计算 amount = offer_salary * fee_rate（向下取整到分）
3. due_date = today + 30 天（根据合同付款条款）
4. 生成账单 PDF（utils/pdf_generator.py template="invoice"）
5. 创建 invoices 记录
6. 发邮件账单给客户联系人
7. 写 automation_events（逾期检查：due_date+1, due_date+7, due_date+15）

OVERDUE_CHECK 处理（由 automation_event 触发）：
1. 读取 invoice，计算逾期天数
2. 根据逾期天数生成不同级别催款函：
   1-6天：chat_json 生成「友好提醒」措辞
   7-14天：生成「正式催款」措辞
   ≥15天：生成「最终催款」措辞（引用合同违约条款）
3. 生成催款函 PDF，发邮件，通知猎头

3. 前端 /finance 页面：
   应收款列表（Invoice 列表，含状态badge）
   统计卡片：本月应收/已收/逾期
   逾期账单红色高亮
```

**检查点 M14**：
```
☐ 入职确认后，Invoice 自动创建，金额计算正确（100%准确）
☐ 手动触发逾期检查，三级催款函措辞明显递进
☐ 付款确认后 status=PAID，不再发催款
☐ 财务页面数据准确
```

---

---

## M15 · 二次开发 + BD 完善

**对应工作环节**：猎头工作环节 #12 二次需求开发  
**交付物**：新招聘需求  
**对应周次**：Week 12 后半段

---

### PRD-M15 · 功能需求

**M15-F1 · 自动触发二次开发**
- 保证期完成（90天通过）或首笔回款后自动触发
- 企业微信提醒猎头：「XXX公司保证期通过，建议跟进新需求」

**M15-F2 · AI 二次开发话术**
- 基于该客户的合作历史（成功入职的岗位/候选人特征）
- 生成个性化的二次开发话术
- 提示可以问的问题：「上次入职的人最近表现如何？是否有新的扩招计划？」

---

### 开发任务 M15

**Codex Prompt**：
```
处理 automation_event TRIGGER_SECONDARY_BD：
1. 读取 pipeline → client 信息
2. 读取该客户的历史成功 pipeline（stage=PLACED）
3. chat_json 生成个性化二次开发话术（引用历史合作）
4. 企业微信推送给 owner：
   「🎉 [客户名]保证期通过！
    成功入职：[候选人]担任[职位]
    建议话术：[AI生成的话术]
    点击跟进：[链接]」

同时在 client 上设置 next_follow_up = today + 7天
让 M01 的跟进提醒机制继续接管
```

**检查点 M15**：
```
☐ 90天通过后企业微信收到二次开发提醒
☐ 提醒中包含历史合作信息（候选人名/职位）
☐ 话术有针对性（不是通用话术）
☐ client.next_follow_up 更新
```

---

---

## 全项目终审检查单

**在找到第一个真实用户之前，完成以下所有检查：**

### 功能完整性

```
端到端流程（必须手动跑一遍）：
☐ BD线索生成 → 创建客户 → 签合同 → 创建岗位 → 生成寻访计划
☐ 上传简历入库 → AI解析 → 关联岗位 → 匹配评分 → 生成外联消息
☐ 上传录音 → 转写 → 生成评估报告 → 确认 → 生成推荐报告 → 发送客户 → 客户反馈
☐ 安排面试 → 发辅导材料 → 面后反馈 → 触发背调 → 生成背调报告
☐ Offer录入 → Check表 → 入职确认 → 试用期5个节点 → 90天通过
☐ 入职确认 → 自动生成Invoice → 逾期催款 → 付款确认 → 二次开发提醒
☐ Chat界面：用自然语言触发上述任意功能
```

### 安全检查

```
☐ .env 文件在 .gitignore，未提交到 git（git log 检查）
☐ Supabase RLS 验证：用用户A的Token无法查询用户B的数据
☐ 报告分享链接 7 天后无法访问（设置一个过去的 expires_at 测试）
☐ 所有 API 端点无认证时返回 401
```

### 数据准确性

```
☐ Invoice 金额计算：手动验算 3 个案例（费率×薪资）
☐ Probation 日期计算：入职日+1/7/30/60/90天，时区为 Asia/Shanghai
☐ 合同到期提醒：30/7/1天，各只提醒一次
```

### 性能

```
☐ Dashboard 首屏加载 < 3 秒
☐ AI 生成报告时有 loading 状态，用户不会以为卡死
☐ 向量搜索 < 2 秒（50条候选人数据）
```

### 部署

```
☐ 后端部署到阿里云函数计算，环境变量已配置
☐ 前端部署到 Vercel
☐ Vercel Cron Jobs 配置（或阿里云定时触发器）
☐ 错误日志接入（Sentry 或阿里云日志）
☐ 手动测试生产环境完整流程一遍
```

---

## 附：Git 提交规范

```bash
# 格式：[模块][任务] 描述
git commit -m "[M05][T2] 实现 skill_eval_report，通过检查点"
git commit -m "[M09][T2] 猎聘 RPA 搜索稳定，账号切换正常"
git commit -m "[FIX][M06] 修复推荐报告 PDF 中文乱码"

# 每完成一个检查点就 commit，不要攒很多再 commit
```

---

## 附：每日更新 CLAUDE.md

每天开工前，更新 CLAUDE.md 中的「当前进度」：

```markdown
## 当前进度
- ✅ PHASE 0 工程底座
- ✅ M01 客户 BD
- ✅ M02 合同管理
- 🔄 M03 需求对齐（进行中，完成 T1，T2 待做）
- ☐ M04 人选寻访
...

## 今天的任务
M03-T2 · 前端岗位页面

## 已知的坑
- Supabase Storage 免费版上传 >50MB 文件会超时，已改为先传到临时URL再存储
- 通义千问 chat_json 返回有时带 markdown 代码块，qwen_client.py 已处理
```

---

*文档结束。每完成一个模块的复盘，在「进度追踪总表」中打 ✅。*

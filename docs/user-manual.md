# HuntFlow 用户手册

## 1. 产品范围

HuntFlow 是双轨工作台：

- 主线：`Client -> Job -> Candidate Import -> Match Score -> Submission Draft -> Approval -> Replay`
- 实验轨：结构化导入 -> 审核 -> 晋升（不直接写入主业务真值）
- Phase 6：电话初筛、评估报告、面试计划、发票轻量管理

## 2. 角色与权限

| 角色 | 核心能力 | 关键限制 |
|---|---|---|
| `consultant` | 客户/职位/候选人日常操作、生成草稿、发起审批 | 不能执行 owner/admin 才能访问的审批与审计管理能力 |
| `team_admin` | 可访问审批中心、审计回放、实验轨、Phase 6 管理接口 | 不能自批自己提交的审批 |
| `owner` | 全量运营与治理操作 | 仍受审批有效期、审计追踪约束 |

## 3. 快速开始

1. 登录系统。
2. 创建客户（Client）。
3. 创建职位（Job Order）。
4. 导入候选人（Candidate Import，可带 `job_order_id` 自动挂 Pipeline）。
5. 执行批量评分（Match Score）。
6. 生成推荐草稿（Submission Draft）。
7. 发起审批并由 reviewer 决策。
8. 在回放页确认 run 与审计日志。

## 4. 主线闭环操作

### 4.1 客户与职位

- 新建客户：`POST /api/v1/clients`
- 更新客户阶段：`PATCH /api/v1/clients/{id}`
- 新建职位：`POST /api/v1/job-orders`

建议先完成客户阶段标准化，再开职位，避免 pipeline 归属混乱。

### 4.2 候选人导入与去重

- 导入候选人：`POST /api/v1/candidates/import`
- 系统基于 `normalized_identity_hash` 去重。
- 命中去重返回 `deduped=true`，不会重复创建候选人。

### 4.3 匹配评分

- 批量评分：`POST /api/v1/match-scores/run`
- 评分结果包含 `score/confidence/reason_codes/gap_items`。

### 4.4 推荐草稿

- 生成草稿：`POST /api/v1/submissions/draft`
- 草稿状态默认 `DRAFT`，正式提交必须走审批。

## 5. 审批中心

### 5.1 发起审批

- 接口：`POST /api/v1/approvals`
- 必填：`action/resource_type/resource_id`
- 系统生成 `token` 与 `token_expires_at`。

### 5.2 审批决策

- 接口：`PATCH /api/v1/approvals/{id}`
- `decision=APPROVED|REJECTED`
- 安全规则：
  - 不允许自批（`requested_by == reviewed_by` 直接拒绝）
  - token 过期会转为 `EXPIRED`

### 5.3 审批后的状态

- 提交通过时，目标资源（如 `submission`）会更新正式状态。
- 审批行为一定落审计：`APPROVAL_REQUESTED` / `APPROVAL_DECIDED`。

## 6. 审计与回放

### 6.1 审计日志

- 接口：`GET /api/v1/audit-logs`
- 关键字段：`event_type/resource_type/resource_id/actor_user_id/state_diff/metadata`

### 6.2 Run 回放

- 接口：`GET /api/v1/runs/{id}/replay`
- 返回：`run` + 关联 `audit_events`
- 用途：问题复盘、合规追溯、跨角色交接。

## 7. 实验轨（Experimental Sourcing）

### 7.1 开关

- 实验轨受 `ENABLE_EXPERIMENTAL_SOURCING` 控制。
- 关闭时相关接口返回 `403`。

### 7.2 标准流程

1. 创建采集批次：`POST /api/v1/source-runs`
2. 审核条目：`POST /api/v1/source-items/{id}/review`
3. 晋升主线：`POST /api/v1/source-items/{id}/promote`

### 7.3 关键约束

- 未 `APPROVED` 的条目不能晋升。
- 已晋升条目不可再修改。
- 稀疏身份冲突会拒绝晋升，需补齐身份信息。

## 8. Phase 6 功能

### 8.1 电话初筛

- 新建：`POST /api/v1/phone-screens`
- 更新：`PATCH /api/v1/phone-screens/{id}`
- 常用字段：`scheduled_at`, `status`, `call_summary`, `recommendation`

### 8.2 评估报告

- 新建：`POST /api/v1/assessment-reports`
- 可关联 `phone_screen_id`，并引用最新评分与电话初筛信息。

### 8.3 面试计划

- 新建：`POST /api/v1/interview-plans`
- 更新：`PATCH /api/v1/interview-plans/{id}`
- 常用字段：`interviewer_name`, `scheduled_at`, `stage`, `status`

### 8.4 发票轻量管理

- 新建：`POST /api/v1/invoices`
- 更新：`PATCH /api/v1/invoices/{id}`
- 常用字段：`amount`, `due_date`, `status`, `memo`

## 9. Chat 命令入口

`POST /api/v1/agent/chat` 支持：

- `/today`
- `/score <job_id> <candidate_id>`
- `/draft <job_id> <candidate_id>`
- `/screen <job_id> <candidate_id> <scheduled_at>`
- `/assess <job_id> <candidate_id> [phone_screen_id]`
- `/interview <job_id> <candidate_id> <interviewer_name> <scheduled_at>`
- `/invoice <client_id> <amount> [job_id]`

## 10. 常见问题

### 10.1 审批失败

- 检查是否 reviewer 自批。
- 检查 token 是否过期。
- 检查 `resource_id` 是否属于当前租户。

### 10.2 实验轨无法晋升

- 检查 `review_status` 是否为 `APPROVED`。
- 检查是否已存在 `promoted_candidate_id`。
- 检查身份信息是否过于稀疏导致冲突。

### 10.3 回放数据不完整

- 检查对应动作是否落 `audit_logs`。
- 检查 run 是否由同一 `tenant_id` 触发。

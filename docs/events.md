# HuntFlow Event Catalog

## Scope

本表用于统一主线、实验轨、审批、审计、Phase 6 的事件口径。事件分两类：

- `topic`：业务语义事件（模板口径，供文档/设计讨论）
- `audit_event_type`：当前实现写入 `audit_logs.event_type` 的审计事件（系统事实）

## Event Matrix

| Track | topic | audit_event_type | Trigger | Producer | Primary Consumer |
|---|---|---|---|---|---|
| Mainline | client.created | CLIENT_CREATED | 新建客户成功 | `POST /api/v1/clients` | dashboard, audit viewer |
| Mainline | client.stage_changed | CLIENT_STAGE_CHANGED | 客户阶段更新成功 | `PATCH /api/v1/clients/{id}` | dashboard, audit viewer |
| Mainline | job_order.created | JOB_CREATED | 新建职位成功 | `POST /api/v1/job-orders` | dashboard, scoring flow |
| Mainline | candidate.imported | CANDIDATE_IMPORTED | 导入候选人成功（含去重后新建） | `POST /api/v1/candidates/import` | pipeline, audit viewer |
| Mainline | match.scored | MATCH_SCORED | 批量评分完成 | `POST /api/v1/match-scores/run` 或 chat `/score` | submission drafting, dashboard |
| Mainline | submission.drafted | SUBMISSION_DRAFTED | 推荐草稿生成成功 | `POST /api/v1/submissions/draft` 或 chat `/draft` | approval center |
| Approval | approval.requested | APPROVAL_REQUESTED | 发起审批成功 | `POST /api/v1/approvals` | reviewer queue, runtime approval queue |
| Approval | approval.decided | APPROVAL_DECIDED | 审批通过/拒绝 | `PATCH /api/v1/approvals/{id}` | command execution result, runtime approval queue |
| Audit | run.skill_executed | SKILL_EXECUTED | chat 执行命令型技能 | `POST /api/v1/agent/chat` | replay, observability |
| Audit | run.replay.requested | n/a | 请求 run 回放 | `GET /api/v1/runs/{id}/replay` | operator, compliance review |
| Experimental | source.run.captured | SOURCE_RUN_CAPTURED | 实验源采集批次创建完成 | `POST /api/v1/source-runs` | review queue |
| Experimental | source.item.reviewed | SOURCE_ITEM_REVIEWED | 原始条目人工审核完成 | `POST /api/v1/source-items/{id}/review` | promotion gate |
| Experimental | source.item.promoted | SOURCE_ITEM_PROMOTED | 审核通过条目晋升为正式候选人 | `POST /api/v1/source-items/{id}/promote` | candidate/pipeline mainline |
| Phase 6 | phone_screen.created | PHONE_SCREEN_CREATED | 新建电话初筛 | `POST /api/v1/phone-screens` 或 chat `/screen` | assessment prep, dashboard |
| Phase 6 | phone_screen.updated | PHONE_SCREEN_UPDATED | 更新电话初筛状态/纪要/建议 | `PATCH /api/v1/phone-screens/{id}` | assessment writer |
| Phase 6 | assessment.reported | ASSESSMENT_REPORTED | 生成评估报告 | `POST /api/v1/assessment-reports` 或 chat `/assess` | interview planning |
| Phase 6 | interview_plan.created | INTERVIEW_PLAN_CREATED | 新建面试计划 | `POST /api/v1/interview-plans` 或 chat `/interview` | ops dashboard |
| Phase 6 | interview_plan.updated | INTERVIEW_PLAN_UPDATED | 更新面试计划状态/备注 | `PATCH /api/v1/interview-plans/{id}` | ops dashboard |
| Phase 6 | invoice.created | INVOICE_CREATED | 新建发票记录 | `POST /api/v1/invoices` 或 chat `/invoice` | finance-lite tracking |
| Phase 6 | invoice.updated | INVOICE_UPDATED | 更新发票状态/备注 | `PATCH /api/v1/invoices/{id}` | finance-lite tracking |

## Runtime Queue and Async Event Types

以下类型属于 runtime/异步处理口径，不等价于 `audit_logs.event_type`，但属于运营必备事件：

| Channel | Event Type | Description |
|---|---|---|
| approval queue | APPROVAL_REQUESTED | 审批请求入队，供通知/看板消费 |
| approval queue | APPROVAL_DECIDED | 审批结果入队，供后续执行链消费 |
| automation queue | PARSE_RESUME | 简历解析任务 |
| automation queue | VECTORIZE_CANDIDATE | 候选人向量化任务 |
| automation queue | VECTORIZE_JOB | 职位向量化任务 |
| automation queue | DEDUPE_CHECK | 去重检查任务 |
| automation queue | FOLLOWUP_REMINDER | 跟进提醒任务 |
| automation queue | CONTRACT_REMINDER | 合同提醒任务 |

## Gate Usage

- Phase 0 Gate：`docs/events.md` 作为事件命名与消费关系基线。
- Phase 6 Gate：审批与审计类事件必须在回放与审计列表中可追溯。

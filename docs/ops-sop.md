# HuntFlow Ops SOP

## 1. 目标与适用范围

本 SOP 覆盖以下运行与发布场景：

- 单机模式（本地开发/演示）
- 生产模式（Docker Compose：Postgres + Redis + API + Web）
- 备份与恢复
- 发布前检查
- 回滚

## 2. 单机模式（Local Single Machine）

### 2.1 首次初始化

```bash
npm run local:setup
```

该命令会：

- 创建 `.venv` 并安装 `requirements.txt`
- 安装前端依赖
- 生成 `.env.local-mac`（若不存在）

### 2.2 启动与停止

```bash
npm run local:start      # API + Web
npm run local:start:api  # 仅 API
npm run local:stop       # 停止后台本地进程
```

### 2.3 健康检查

```bash
curl -sf http://127.0.0.1:8000/health
curl -sf http://127.0.0.1:8000/health/ready
curl -sf http://127.0.0.1:3000/login
```

### 2.4 单机模式常见配置

默认由 `scripts/local_env.sh` 注入：

- `STORE_BACKEND=file`
- `STORE_FILE_PATH=storage/local-store.json`
- `RUNTIME_BACKEND=memory`
- `ENABLE_EXPERIMENTAL_SOURCING=false`

## 3. 生产模式（Docker Compose）

### 3.1 启动

```bash
docker compose up -d
```

### 3.2 关键运行参数

- API：`STORE_BACKEND=postgres`
- API：`RUNTIME_BACKEND=redis`
- Postgres：`postgres_data` 持久卷
- Redis：`redis_data` 持久卷

### 3.3 生产健康检查

```bash
curl -sf http://127.0.0.1:${API_PORT:-8000}/health
curl -sf http://127.0.0.1:${API_PORT:-8000}/health/ready
curl -sf http://127.0.0.1:${WEB_PORT:-3000}/login
```

### 3.4 生产日志排查

```bash
docker compose logs api --tail=200
docker compose logs web --tail=200
docker compose logs postgres --tail=200
docker compose logs redis --tail=200
```

## 4. 备份与恢复

## 4.1 Postgres 备份

前置：必须设置 `DATABASE_URL`（可选 `DATABASE_SCHEMA`）。

```bash
scripts/backup.sh
# 或指定路径
scripts/backup.sh storage/backups/huntflow-YYYYMMDD-HHMMSS.json
```

备份内容包含：

- 全量业务集合（`MODEL_COLLECTIONS`）
- 会话历史（`conversation_sessions`）
- migration 版本列表

## 4.2 Postgres 恢复

```bash
scripts/restore.sh path/to/backup.json
```

恢复行为：

- 自动执行 migration
- 清空后重灌所有集合与会话
- 输出 `restored` 代表脚本完成

## 4.3 文件存储模式补充备份

单机 `file` 模式应额外备份：

- `storage/local-store.json`
- `.env.local-mac`

## 5. 发布前检查（Release Gate Checklist）

发布前至少完成以下检查：

1. 依赖与环境

```bash
python3 -m pip show fastapi uvicorn pydantic psycopg
npm -v
node -v
```

2. API 测试

```bash
npm run test:api
```

3. 最小链路冒烟

```bash
curl -sf http://127.0.0.1:8000/health
python3 scripts/local_login.py --token-only >/dev/null
```

4. 主线 Gate 核验

- 可完成主线闭环：导入 -> 评分 -> 草稿 -> 审批 -> 回放
- 无审批 token 不得执行正式写入
- 审计日志可看到关键事件（含审批事件）

5. 实验轨与 Phase 6（启用时）

- 实验轨可执行：采集 -> 审核 -> 晋升
- Phase 6 端点可用：phone screen / assessment / interview / invoice

## 6. 回滚 SOP

## 6.1 应用级快速回滚

适用：最新发布后 API/Web 异常，但数据无需回滚。

```bash
docker compose down
git checkout <last-known-good-tag-or-commit>
docker compose up -d
```

## 6.2 数据级回滚

适用：错误写入或迁移后数据异常。

1. 停写入流量（暂停 API 写操作入口）。
2. 执行恢复：

```bash
scripts/restore.sh path/to/backup.json
```

3. 验证恢复后核心读写与审计链路。

## 6.3 单机模式回滚

```bash
npm run local:stop
git checkout <last-known-good-tag-or-commit>
npm run local:start
```

如使用 `file` 存储并发生污染，恢复 `storage/local-store.json` 备份副本。

## 7. 日常值守建议

- 每次发布前执行一次备份并记录路径。
- 每周至少做一次恢复演练（非生产库）。
- 审批与审计事件缺失时，禁止继续放量发布。

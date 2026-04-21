CREATE TABLE IF NOT EXISTS "{schema}"."tenants" (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NULL,
    created_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ NULL,
    payload JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "{schema}"."teams" (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NULL,
    created_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ NULL,
    payload JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "{schema}"."users" (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NULL,
    created_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ NULL,
    payload JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "{schema}"."auth_sessions" (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NULL,
    created_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ NULL,
    payload JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "{schema}"."clients" (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NULL,
    created_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ NULL,
    payload JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "{schema}"."job_orders" (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NULL,
    created_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ NULL,
    payload JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "{schema}"."candidates" (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NULL,
    created_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ NULL,
    payload JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "{schema}"."resume_assets" (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NULL,
    created_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ NULL,
    payload JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "{schema}"."pipelines" (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NULL,
    created_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ NULL,
    payload JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "{schema}"."match_scores" (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NULL,
    created_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ NULL,
    payload JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "{schema}"."submissions" (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NULL,
    created_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ NULL,
    payload JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "{schema}"."approvals" (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NULL,
    created_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ NULL,
    payload JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "{schema}"."agent_runs" (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NULL,
    created_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ NULL,
    payload JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "{schema}"."audit_logs" (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NULL,
    created_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ NULL,
    payload JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "{schema}"."automation_events" (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NULL,
    created_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ NULL,
    payload JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "{schema}"."phone_screens" (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NULL,
    created_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ NULL,
    payload JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "{schema}"."assessment_reports" (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NULL,
    created_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ NULL,
    payload JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "{schema}"."interview_plans" (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NULL,
    created_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ NULL,
    payload JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "{schema}"."invoices" (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NULL,
    created_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ NULL,
    payload JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "{schema}"."source_runs" (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NULL,
    created_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ NULL,
    payload JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "{schema}"."source_items" (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NULL,
    created_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ NULL,
    payload JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "{schema}"."source_reviews" (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NULL,
    created_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ NULL,
    payload JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "{schema}"."conversation_sessions" (
    session_id TEXT PRIMARY KEY,
    history JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

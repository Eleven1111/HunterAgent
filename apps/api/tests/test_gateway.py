from __future__ import annotations

from app.domain.models import Candidate, Pipeline, Team, Tenant, User
from app.repositories.gateway import StoreGateway
from app.repositories.store import InMemoryStore


def test_gateway_scopes_records_by_tenant() -> None:
    store = InMemoryStore()
    tenant_a = Tenant(name="Tenant A")
    team_a = Team(tenant_id=tenant_a.id, name="A Team")
    user_a = User(
        tenant_id=tenant_a.id,
        team_id=team_a.id,
        email="a@huntflow.local",
        password="pw",
        name="User A",
        role="consultant",
    )
    tenant_b = Tenant(name="Tenant B")
    team_b = Team(tenant_id=tenant_b.id, name="B Team")
    user_b = User(
        tenant_id=tenant_b.id,
        team_id=team_b.id,
        email="b@huntflow.local",
        password="pw",
        name="User B",
        role="consultant",
    )
    candidate_a = Candidate(
        tenant_id=tenant_a.id,
        team_id=team_a.id,
        owner_id=user_a.id,
        full_name="Alice",
        resume_summary="Finance leader",
        normalized_identity_hash="alice-hash",
    )
    candidate_b = Candidate(
        tenant_id=tenant_b.id,
        team_id=team_b.id,
        owner_id=user_b.id,
        full_name="Bob",
        resume_summary="Operations leader",
        normalized_identity_hash="bob-hash",
    )

    gateway = StoreGateway(store)
    gateway.save("tenants", tenant_a)
    gateway.save("teams", team_a)
    gateway.save("users", user_a)
    gateway.save("tenants", tenant_b)
    gateway.save("teams", team_b)
    gateway.save("users", user_b)
    gateway.save("candidates", candidate_a)
    gateway.save("candidates", candidate_b)

    tenant_a_candidates = gateway.list_for_tenant("candidates", tenant_a.id)

    assert [candidate.id for candidate in tenant_a_candidates] == [candidate_a.id]
    assert gateway.get_for_tenant("candidates", candidate_b.id, tenant_a.id) is None
    assert gateway.exists_for_tenant("candidates", candidate_a.id, tenant_a.id)


def test_gateway_finds_pipeline_by_source_item() -> None:
    store = InMemoryStore()
    tenant = Tenant(name="Pilot Tenant")
    team = Team(tenant_id=tenant.id, name="Core Search")
    user = User(
        tenant_id=tenant.id,
        team_id=team.id,
        email="consultant@huntflow.local",
        password="pw",
        name="Consultant",
        role="consultant",
    )
    candidate = Candidate(
        tenant_id=tenant.id,
        team_id=team.id,
        owner_id=user.id,
        full_name="Lina Chen",
        resume_summary="Fintech CFO",
        normalized_identity_hash="lina-hash",
    )
    pipeline = Pipeline(
        tenant_id=tenant.id,
        job_order_id="job_123",
        candidate_id=candidate.id,
        owner_id=user.id,
        metadata={"source_item_id": "source_item_123"},
    )

    gateway = StoreGateway(store)
    gateway.save("pipelines", pipeline)

    assert gateway.find_pipeline_by_source_item(tenant.id, candidate.id, "source_item_123") == pipeline
    assert gateway.find_pipeline_by_source_item(tenant.id, candidate.id, "missing") is None

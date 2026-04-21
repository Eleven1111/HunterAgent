from __future__ import annotations

from app.domain.models import Submission
from app.repositories.gateway import StoreGateway
from app.repositories.store import InMemoryStore


def create_submission_draft(
    store: InMemoryStore,
    *,
    tenant_id: str,
    job_order_id: str,
    candidate_id: str,
    include_gap_analysis: bool,
    primary_model: str,
) -> Submission:
    gateway = StoreGateway(store)
    job = gateway.get("job_orders", job_order_id)
    candidate = gateway.get("candidates", candidate_id)
    latest_score = gateway.latest_match_score(tenant_id, job_order_id, candidate_id)
    match_block = latest_score.reason_codes if latest_score else ["Needs scoring"]
    gap_block = latest_score.gap_items if latest_score else []
    concern_lines = (
        [f"- {item}" for item in gap_block]
        if include_gap_analysis and gap_block
        else ["- No critical gap flagged in the current pass."]
    )
    markdown = "\n".join(
        [
            f"# {candidate.full_name} -> {job.title}",
            "",
            "## Snapshot",
            f"{candidate.full_name} is currently {candidate.current_title or 'an experienced operator'} at {candidate.current_company or 'an undisclosed company'}.",
            "",
            "## Match Analysis",
            *(f"- {item}" for item in match_block),
            "",
            "## Strengths",
            f"- Resume summary: {candidate.resume_summary}",
            f"- Target role: {job.title}",
            "",
            "## Concerns",
            *concern_lines,
            "",
            "## Recommendation",
            "Proceed to consultant review before formal submission.",
        ]
    )
    submission = Submission(
        tenant_id=tenant_id,
        job_order_id=job_order_id,
        candidate_id=candidate_id,
        draft_markdown=markdown,
        draft_content={
            "snapshot": candidate.resume_summary,
            "match_analysis": match_block,
            "gaps": gap_block if include_gap_analysis else [],
        },
        model_name=primary_model,
        model_version="draft.v1",
    )
    gateway.save("submissions", submission)
    return submission

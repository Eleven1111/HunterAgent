from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import ActorContext, get_gateway, require_roles
from app.repositories.gateway import StoreGateway
from app.schemas.contracts import InvoiceCreateRequest, InvoiceUpdateRequest
from app.services.audit import record_audit
from app.services.pilot_modules import create_invoice, update_invoice

router = APIRouter(prefix="/api/v1/invoices", tags=["invoices"])


@router.get("")
def list_invoices(
    actor: ActorContext = Depends(require_roles("owner", "team_admin")),
    gateway: StoreGateway = Depends(get_gateway),
) -> list[dict]:
    return [
        item.model_dump(mode="json")
        for item in gateway.list_for_tenant_sorted(
            "invoices",
            actor.tenant_id,
            key=lambda row: row.updated_at,
            reverse=True,
        )
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_invoice_route(
    payload: InvoiceCreateRequest,
    actor: ActorContext = Depends(require_roles("owner", "team_admin")),
    gateway: StoreGateway = Depends(get_gateway),
) -> dict:
    if not gateway.exists_for_tenant("clients", payload.client_id, actor.tenant_id):
        raise HTTPException(status_code=404, detail="Client not found")
    if payload.job_order_id and not gateway.exists_for_tenant("job_orders", payload.job_order_id, actor.tenant_id):
        raise HTTPException(status_code=404, detail="Job order not found")
    invoice = create_invoice(
        gateway.store,
        tenant_id=actor.tenant_id,
        owner_id=actor.user_id,
        client_id=payload.client_id,
        amount=payload.amount,
        due_date=payload.due_date,
        job_order_id=payload.job_order_id,
        currency=payload.currency,
        memo=payload.memo,
    )
    record_audit(
        gateway.store,
        tenant_id=actor.tenant_id,
        actor_user_id=actor.user_id,
        event_type="INVOICE_CREATED",
        resource_type="invoice",
        resource_id=invoice.id,
        metadata={"client_id": invoice.client_id, "amount": invoice.amount},
    )
    return invoice.model_dump(mode="json")


@router.patch("/{invoice_id}")
def update_invoice_route(
    invoice_id: str,
    payload: InvoiceUpdateRequest,
    actor: ActorContext = Depends(require_roles("owner", "team_admin")),
    gateway: StoreGateway = Depends(get_gateway),
) -> dict:
    invoice, state_diff = update_invoice(
        gateway.store,
        tenant_id=actor.tenant_id,
        invoice_id=invoice_id,
        status_value=payload.status,
        memo=payload.memo,
    )
    record_audit(
        gateway.store,
        tenant_id=actor.tenant_id,
        actor_user_id=actor.user_id,
        event_type="INVOICE_UPDATED",
        resource_type="invoice",
        resource_id=invoice.id,
        state_diff=state_diff,
        metadata={"client_id": invoice.client_id},
    )
    return invoice.model_dump(mode="json")

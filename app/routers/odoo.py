"""
Odoo Integration API Router

Admin endpoints for syncing data with Odoo ERP.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.client import Client
from app.services.odoo_service import OdooService

router = APIRouter(prefix="/odoo", tags=["Odoo Integration"])


class SyncResponse(BaseModel):
    success: bool
    message: str
    details: dict | None = None


@router.get("/status")
def get_odoo_status(db: Session = Depends(get_db)):
    """Check Odoo connection status."""
    service = OdooService(db)

    if not service.is_configured:
        return {
            "connected": False,
            "message": "Odoo is not configured. Set ODOO_URL, ODOO_DATABASE, ODOO_USERNAME, ODOO_API_KEY in environment.",
        }

    try:
        service._connect()
        return {
            "connected": True,
            "message": "Successfully connected to Odoo",
            "uid": service.uid,
        }
    except Exception as e:
        return {
            "connected": False,
            "message": f"Connection failed: {str(e)}",
        }


@router.post("/sync/client/{client_id}", response_model=SyncResponse)
def sync_client_to_odoo(
    client_id: int,
    db: Session = Depends(get_db),
):
    """Sync a specific client to Odoo."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    service = OdooService(db)

    try:
        partner_id = service.sync_client_to_odoo(client)
        return SyncResponse(
            success=True,
            message=f"Client synced to Odoo partner ID: {partner_id}",
            details={"odoo_partner_id": partner_id},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/all-clients", response_model=SyncResponse)
def sync_all_clients(db: Session = Depends(get_db)):
    """Sync all active clients to Odoo."""
    service = OdooService(db)

    try:
        result = service.sync_all_clients()
        return SyncResponse(
            success=True,
            message=f"Synced {result['synced']} clients, {result['errors']} errors",
            details=result,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import/clients", response_model=SyncResponse)
def import_clients_from_odoo(db: Session = Depends(get_db)):
    """Import contacts from Odoo as new clients."""
    service = OdooService(db)

    try:
        result = service.import_clients_from_odoo()
        return SyncResponse(
            success=True,
            message=f"Imported {result['imported']} clients, skipped {result['skipped']}",
            details=result,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/invoice/subscription/{client_id}")
def create_subscription_invoice(
    client_id: int,
    db: Session = Depends(get_db),
):
    """Create an invoice in Odoo for a client's subscription."""
    from app.models.billing import Subscription

    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    subscription = (
        db.query(Subscription)
        .filter(Subscription.client_id == client_id)
        .order_by(Subscription.created_at.desc())
        .first()
    )

    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found")

    service = OdooService(db)

    try:
        invoice_id = service.create_subscription_invoice(client, subscription)
        return {
            "success": True,
            "message": "Invoice created in Odoo",
            "odoo_invoice_id": invoice_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/invoice/work/{client_id}")
def create_work_invoice(
    client_id: int,
    work_log_ids: list[int],
    db: Session = Depends(get_db),
):
    """Create an invoice in Odoo for completed work."""
    from app.models.worklog import WorkLog

    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    work_logs = (
        db.query(WorkLog)
        .filter(
            WorkLog.id.in_(work_log_ids),
            WorkLog.client_id == client_id,
        )
        .all()
    )

    if not work_logs:
        raise HTTPException(status_code=404, detail="No work logs found")

    service = OdooService(db)

    try:
        invoice_id = service.create_invoice_from_work(client, work_logs)
        return {
            "success": True,
            "message": "Invoice created in Odoo",
            "odoo_invoice_id": invoice_id,
            "work_logs_invoiced": len(work_logs),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

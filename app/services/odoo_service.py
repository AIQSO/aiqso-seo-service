"""
Odoo Integration Service

Syncs client information between AIQSO SEO Service and Odoo ERP.
Supports:
- Creating/updating contacts in Odoo
- Syncing invoices and payments
- Creating projects in Odoo from SEO work
"""

import logging
import xmlrpc.client
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.billing import Subscription
from app.models.client import Client, ClientTier
from app.models.worklog import Project, WorkLog

settings = get_settings()
logger = logging.getLogger(__name__)


class OdooService:
    """Service for Odoo ERP integration."""

    def __init__(self, db: Session):
        self.db = db
        self.url = getattr(settings, "odoo_url", None)
        self.database = getattr(settings, "odoo_database", None)
        self.username = getattr(settings, "odoo_username", None)
        self.password = getattr(settings, "odoo_api_key", None)
        self.uid = None
        self._models = None

    @property
    def is_configured(self) -> bool:
        """Check if Odoo is configured."""
        return all([self.url, self.database, self.username, self.password])

    def _connect(self):
        """Establish connection to Odoo."""
        if not self.is_configured:
            raise ValueError("Odoo is not configured. Set ODOO_URL, ODOO_DATABASE, ODOO_USERNAME, ODOO_API_KEY")

        # Authenticate
        common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        self.uid = common.authenticate(self.database, self.username, self.password, {})

        if not self.uid:
            raise ValueError("Odoo authentication failed")

        # Get models interface
        self._models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

    def _execute(self, model: str, method: str, *args, **kwargs):
        """Execute an Odoo model method."""
        if not self._models:
            self._connect()

        return self._models.execute_kw(self.database, self.uid, self.password, model, method, args, kwargs)

    # -------------------------------------------------------------------------
    # Contact/Partner Sync
    # -------------------------------------------------------------------------

    def sync_client_to_odoo(self, client: Client) -> int:
        """Create or update a client in Odoo as a partner/contact."""
        # Search for existing partner by email
        existing = self._execute("res.partner", "search", [[["email", "=", client.email]]])

        partner_data = {
            "name": client.name,
            "email": client.email,
            "phone": client.phone,
            "company_name": client.company,
            "is_company": bool(client.company),
            "customer_rank": 1,  # Mark as customer
            "comment": f"AIQSO SEO Client - Tier: {client.tier.value}",
            # Custom fields (you'd create these in Odoo)
            # 'x_aiqso_client_id': client.id,
            # 'x_aiqso_tier': client.tier.value,
            # 'x_aiqso_api_key': client.api_key,
        }

        if existing:
            # Update existing partner
            partner_id = existing[0]
            self._execute("res.partner", "write", [partner_id], partner_data)
        else:
            # Create new partner
            partner_id = self._execute("res.partner", "create", [partner_data])

        # Store Odoo partner ID in client settings
        client_settings = client.settings or {}
        client_settings["odoo_partner_id"] = partner_id
        client.settings = client_settings
        self.db.commit()

        return partner_id

    def get_odoo_partner_id(self, client: Client) -> int | None:
        """Get the Odoo partner ID for a client."""
        if client.settings and "odoo_partner_id" in client.settings:
            return client.settings["odoo_partner_id"]

        # Try to find by email
        existing = self._execute("res.partner", "search", [[["email", "=", client.email]]])

        if existing:
            return existing[0]

        return None

    # -------------------------------------------------------------------------
    # Invoice Sync
    # -------------------------------------------------------------------------

    def create_invoice(
        self,
        client: Client,
        line_items: list[dict[str, Any]],
        due_days: int = 30,
    ) -> int:
        """Create an invoice in Odoo."""
        partner_id = self.get_odoo_partner_id(client)
        if not partner_id:
            partner_id = self.sync_client_to_odoo(client)

        # Create invoice
        invoice_data = {
            "partner_id": partner_id,
            "move_type": "out_invoice",  # Customer invoice
            "invoice_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "invoice_date_due": (datetime.utcnow() + timedelta(days=due_days)).strftime("%Y-%m-%d"),
            "invoice_line_ids": [
                (
                    0,
                    0,
                    {
                        "name": item["description"],
                        "quantity": item.get("quantity", 1),
                        "price_unit": item["amount"],
                    },
                )
                for item in line_items
            ],
        }

        invoice_id = self._execute("account.move", "create", [invoice_data])
        return invoice_id

    def create_invoice_from_work(
        self,
        client: Client,
        work_logs: list[WorkLog],
        description: str = "SEO Services",
    ) -> int:
        """Create an invoice from completed work logs."""
        line_items = []

        for work in work_logs:
            if work.is_billable and work.billable_amount_cents > 0:
                line_items.append(
                    {
                        "description": f"{work.title} ({work.actual_minutes or 0} min)",
                        "quantity": 1,
                        "amount": work.billable_amount_dollars,
                    }
                )

        if not line_items:
            raise ValueError("No billable work to invoice")

        return self.create_invoice(client, line_items)

    def create_subscription_invoice(
        self,
        client: Client,
        subscription: Subscription,
    ) -> int:
        """Create a subscription invoice in Odoo."""
        tier_names = {
            "starter": "SEO Starter Plan",
            "pro": "SEO Professional Plan",
            "enterprise": "SEO Enterprise Plan",
            "agency": "SEO Agency Plan",
        }

        line_items = [
            {
                "description": tier_names.get(subscription.tier_name, "SEO Subscription"),
                "quantity": 1,
                "amount": subscription.amount_dollars,
            }
        ]

        return self.create_invoice(client, line_items)

    # -------------------------------------------------------------------------
    # Project Sync
    # -------------------------------------------------------------------------

    def create_project(
        self,
        client: Client,
        project: Project,
    ) -> int:
        """Create a project in Odoo."""
        partner_id = self.get_odoo_partner_id(client)
        if not partner_id:
            partner_id = self.sync_client_to_odoo(client)

        project_data = {
            "name": project.name,
            "partner_id": partner_id,
            "description": project.description or "",
            # 'date_start': project.start_date.strftime('%Y-%m-%d') if project.start_date else None,
            # 'date': project.due_date.strftime('%Y-%m-%d') if project.due_date else None,
        }

        project_id = self._execute("project.project", "create", [project_data])

        # Store Odoo project ID
        # You'd need to add a settings column to Project model
        # For now, we'll return the ID
        return project_id

    def create_task(
        self,
        project_id: int,
        work_log: WorkLog,
    ) -> int:
        """Create a task in Odoo project from work log."""
        task_data = {
            "name": work_log.title,
            "project_id": project_id,
            "description": work_log.description or "",
            "planned_hours": (work_log.estimated_minutes or 0) / 60,
            # Map status
            # 'stage_id': self._get_stage_id(work_log.status),
        }

        task_id = self._execute("project.task", "create", [task_data])
        return task_id

    # -------------------------------------------------------------------------
    # Timesheet Sync
    # -------------------------------------------------------------------------

    def log_timesheet(
        self,
        work_log: WorkLog,
        project_id: int,
        task_id: int | None = None,
        employee_id: int | None = None,
    ) -> int:
        """Log time in Odoo timesheet."""
        timesheet_data = {
            "project_id": project_id,
            "task_id": task_id,
            "employee_id": employee_id or self._get_default_employee(),
            "name": work_log.title,
            "unit_amount": (work_log.actual_minutes or 0) / 60,  # Hours
            "date": work_log.completed_at.strftime("%Y-%m-%d")
            if work_log.completed_at
            else datetime.utcnow().strftime("%Y-%m-%d"),
        }

        timesheet_id = self._execute("account.analytic.line", "create", [timesheet_data])
        return timesheet_id

    def _get_default_employee(self) -> int:
        """Get default employee ID for timesheets."""
        # Search for employee linked to Odoo user
        employees = self._execute("hr.employee", "search", [[["user_id", "=", self.uid]]])
        return employees[0] if employees else 1

    # -------------------------------------------------------------------------
    # Bulk Sync Operations
    # -------------------------------------------------------------------------

    def sync_all_clients(self) -> dict[str, int]:
        """Sync all clients to Odoo."""
        clients = self.db.query(Client).filter(Client.is_active == True).all()

        synced = 0
        errors = 0

        for client in clients:
            try:
                self.sync_client_to_odoo(client)
                synced += 1
            except Exception as e:
                logger.error("Error syncing client %s: %s", client.id, e, exc_info=True)
                errors += 1

        return {"synced": synced, "errors": errors}

    def import_clients_from_odoo(self) -> dict[str, int]:
        """Import contacts from Odoo as clients."""
        # Get all customer partners from Odoo
        partner_ids = self._execute("res.partner", "search", [[["customer_rank", ">", 0]]])

        partners = self._execute(
            "res.partner", "read", [partner_ids], {"fields": ["name", "email", "phone", "company_name"]}
        )

        imported = 0
        skipped = 0

        for partner in partners:
            if not partner.get("email"):
                skipped += 1
                continue

            # Check if client exists
            existing = self.db.query(Client).filter(Client.email == partner["email"]).first()

            if existing:
                # Update settings with Odoo ID
                existing.settings = existing.settings or {}
                existing.settings["odoo_partner_id"] = partner["id"]
                self.db.commit()
                skipped += 1
            else:
                # Create new client
                client = Client(
                    name=partner["name"],
                    email=partner["email"],
                    phone=partner.get("phone"),
                    company=partner.get("company_name"),
                    tier=ClientTier.STARTER,
                    settings={"odoo_partner_id": partner["id"]},
                )
                self.db.add(client)
                self.db.commit()
                imported += 1

        return {"imported": imported, "skipped": skipped}

"""
Audit Logging Service

Handles security audit logging for billing operations and API access.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.client import Client


class AuditService:
    """Service for audit logging operations."""

    def __init__(self, db: Session):
        self.db = db

    def log_action(
        self,
        client: Client,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """
        Create an audit log entry for a client action.

        Args:
            client: The authenticated client performing the action
            action: Action identifier (e.g., "checkout_created", "subscription_cancelled")
            resource_type: Type of resource affected (e.g., "subscription", "payment")
            resource_id: ID of the affected resource
            ip_address: Client IP address from request
            user_agent: User agent string from request
            extra_data: Additional context data (request params, response data, etc.)

        Returns:
            The created AuditLog instance
        """
        audit_log = AuditLog(
            client_id=client.id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            extra_data=extra_data,
        )

        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)

        return audit_log

    def log_billing_action(
        self,
        client: Client,
        action: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """
        Create an audit log entry for a billing action.

        Convenience method specifically for billing operations.

        Args:
            client: The authenticated client performing the action
            action: Billing action (e.g., "checkout_created", "subscription_cancelled")
            resource_type: Billing resource type ("subscription", "payment", "checkout")
            resource_id: ID of the affected billing resource
            ip_address: Client IP address from request
            user_agent: User agent string from request
            extra_data: Additional billing context

        Returns:
            The created AuditLog instance
        """
        return self.log_action(
            client=client,
            action=f"billing_{action}",
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            extra_data=extra_data,
        )

    def log_security_event(
        self,
        client: Client,
        event: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """
        Create an audit log entry for a security event.

        Convenience method specifically for security-related events.

        Args:
            client: The authenticated client involved in the event
            event: Security event description (e.g., "api_key_used", "access_denied")
            ip_address: Client IP address from request
            user_agent: User agent string from request
            extra_data: Additional security context

        Returns:
            The created AuditLog instance
        """
        return self.log_action(
            client=client,
            action=f"security_{event}",
            resource_type="security",
            ip_address=ip_address,
            user_agent=user_agent,
            extra_data=extra_data,
        )

    def get_client_audit_logs(
        self,
        client_id: int,
        action_filter: Optional[str] = None,
        resource_type_filter: Optional[str] = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        """
        Retrieve audit logs for a specific client.

        Args:
            client_id: ID of the client
            action_filter: Optional filter by action prefix (e.g., "billing_")
            resource_type_filter: Optional filter by resource type
            limit: Maximum number of logs to return (default 100)

        Returns:
            List of AuditLog instances ordered by most recent first
        """
        query = self.db.query(AuditLog).filter(AuditLog.client_id == client_id)

        if action_filter:
            query = query.filter(AuditLog.action.like(f"{action_filter}%"))

        if resource_type_filter:
            query = query.filter(AuditLog.resource_type == resource_type_filter)

        return query.order_by(AuditLog.created_at.desc()).limit(limit).all()

    def get_recent_billing_logs(
        self,
        client_id: int,
        limit: int = 50,
    ) -> list[AuditLog]:
        """
        Get recent billing-related audit logs for a client.

        Convenience method for retrieving billing activity.

        Args:
            client_id: ID of the client
            limit: Maximum number of logs to return (default 50)

        Returns:
            List of recent billing AuditLog instances
        """
        return self.get_client_audit_logs(
            client_id=client_id,
            action_filter="billing_",
            limit=limit,
        )

"""
Audit Log Model - Security and Operations Tracking

Tracks billing operations, API access, and security events.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class AuditLog(Base, TimestampMixin):
    """Security audit log for tracking operations and events."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)

    # Action info
    action = Column(String(100), nullable=False, index=True)  # e.g., "checkout_created", "subscription_cancelled"
    resource_type = Column(String(50), nullable=True)  # e.g., "subscription", "payment"
    resource_id = Column(Integer, nullable=True)

    # Request context
    ip_address = Column(String(45), nullable=True)  # IPv6 max length is 45 chars
    user_agent = Column(String(500), nullable=True)

    # Additional data
    extra_data = Column(JSON, nullable=True)  # Additional context (request params, response data, etc.)

    # Note: created_at and updated_at provided by TimestampMixin

    # Relationships
    client = relationship("Client", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog {self.id} {self.action} client={self.client_id}>"

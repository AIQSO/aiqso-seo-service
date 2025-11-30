import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Enum, Text
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class ReportType(enum.Enum):
    """Types of SEO reports."""
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    AUDIT = "audit"
    RANKINGS = "rankings"
    CUSTOM = "custom"


class ReportStatus(enum.Enum):
    """Report generation status."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class Report(Base, TimestampMixin):
    """Generated SEO report."""

    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    website_id = Column(Integer, ForeignKey("websites.id"), nullable=True, index=True)

    # Report info
    report_type = Column(Enum(ReportType), nullable=False)
    title = Column(String(255), nullable=False)
    status = Column(Enum(ReportStatus), default=ReportStatus.PENDING, nullable=False)

    # Date range
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Content
    summary = Column(Text, nullable=True)
    highlights = Column(JSON, nullable=True)  # Key metrics/changes
    data = Column(JSON, nullable=True)  # Full report data

    # Files
    pdf_url = Column(String(500), nullable=True)
    html_content = Column(Text, nullable=True)

    # AI insights
    ai_insights = Column(Text, nullable=True)
    ai_recommendations = Column(JSON, nullable=True)

    # Delivery
    sent_at = Column(DateTime, nullable=True)
    recipient_emails = Column(JSON, nullable=True)

    # Relationships
    client = relationship("Client", back_populates="reports")

    def __repr__(self):
        return f"<Report {self.report_type.value} {self.period_start.date()} - {self.period_end.date()}>"

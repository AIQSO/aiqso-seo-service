"""
Work Log Models - Time & Task Tracking

Tracks work performed for customers, used for billing and reporting.
"""

import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class WorkStatus(enum.Enum):
    """Work item status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELED = "canceled"


class WorkCategory(enum.Enum):
    """Categories of SEO work."""

    AUDIT = "audit"  # Running audits
    TECHNICAL_SEO = "technical_seo"  # Fixing technical issues
    ON_PAGE_SEO = "on_page_seo"  # Meta tags, content optimization
    CONTENT = "content"  # Content creation/optimization
    LINK_BUILDING = "link_building"  # Backlink work
    REPORTING = "reporting"  # Creating reports
    CONSULTATION = "consultation"  # Meetings, calls, advice
    RESEARCH = "research"  # Keyword research, competitor analysis
    OTHER = "other"


class WorkLog(Base, TimestampMixin):
    """Individual work log entry."""

    __tablename__ = "work_logs"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    website_id = Column(Integer, ForeignKey("websites.id"), nullable=True)

    # Work details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(Enum(WorkCategory), default=WorkCategory.OTHER, nullable=False)
    status = Column(Enum(WorkStatus), default=WorkStatus.PENDING, nullable=False)

    # Time tracking
    estimated_minutes = Column(Integer, nullable=True)
    actual_minutes = Column(Integer, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Billing
    is_billable = Column(Boolean, default=True, nullable=False)
    hourly_rate_cents = Column(Integer, default=15000, nullable=False)  # $150/hr default
    fixed_price_cents = Column(Integer, nullable=True)  # Override for fixed-price work

    # Linked resources
    audit_id = Column(Integer, ForeignKey("audits.id"), nullable=True)

    # Notes
    internal_notes = Column(Text, nullable=True)  # Notes not shown to customer
    customer_notes = Column(Text, nullable=True)  # Notes visible to customer

    # Relationships
    client = relationship("Client", backref="work_logs")
    website = relationship("Website", backref="work_logs")

    @property
    def billable_amount_cents(self) -> int:
        """Calculate the billable amount."""
        if not self.is_billable:
            return 0
        if self.fixed_price_cents:
            return self.fixed_price_cents
        if self.actual_minutes:
            hours = self.actual_minutes / 60
            return int(hours * self.hourly_rate_cents)
        return 0

    @property
    def billable_amount_dollars(self) -> float:
        """Get billable amount in dollars."""
        return self.billable_amount_cents / 100


class Project(Base, TimestampMixin):
    """Group work items into projects."""

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)

    # Project details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(WorkStatus), default=WorkStatus.PENDING, nullable=False)

    # Scope
    scope_document = Column(Text, nullable=True)  # Markdown scope document

    # Budget
    budget_cents = Column(Integer, nullable=True)
    is_fixed_price = Column(Boolean, default=False, nullable=False)

    # Dates
    start_date = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    client = relationship("Client", backref="projects")
    work_items = relationship("ProjectWorkItem", back_populates="project", cascade="all, delete-orphan")

    @property
    def total_logged_minutes(self) -> int:
        """Sum of all work item minutes."""
        return sum(item.work_log.actual_minutes or 0 for item in self.work_items if item.work_log)

    @property
    def total_billable_cents(self) -> int:
        """Sum of all billable amounts."""
        return sum(item.work_log.billable_amount_cents for item in self.work_items if item.work_log)


class ProjectWorkItem(Base, TimestampMixin):
    """Link work logs to projects."""

    __tablename__ = "project_work_items"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    work_log_id = Column(Integer, ForeignKey("work_logs.id"), nullable=False)

    # Ordering
    sort_order = Column(Integer, default=0, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="work_items")
    work_log = relationship("WorkLog", backref="project_items")


class IssueTracker(Base, TimestampMixin):
    """Track SEO issues found and their resolution status."""

    __tablename__ = "issue_tracker"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    website_id = Column(Integer, ForeignKey("websites.id"), nullable=False)
    audit_id = Column(Integer, ForeignKey("audits.id"), nullable=True)

    # Issue details
    check_name = Column(String(100), nullable=False)  # From SEO_CHECKS
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(20), default="warning", nullable=False)  # info, warning, error, critical
    category = Column(String(50), nullable=False)  # configuration, meta, content, performance

    # Current state
    current_value = Column(Text, nullable=True)
    expected_value = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)

    # Resolution tracking
    status = Column(Enum(WorkStatus), default=WorkStatus.PENDING, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(255), nullable=True)  # Who fixed it
    resolution_notes = Column(Text, nullable=True)

    # Link to work log if work was done
    work_log_id = Column(Integer, ForeignKey("work_logs.id"), nullable=True)

    # Billing
    fix_price_cents = Column(Integer, nullable=True)  # Price to fix this issue

    # Relationships
    client = relationship("Client", backref="tracked_issues")
    website = relationship("Website", backref="tracked_issues")
    work_log = relationship("WorkLog", backref="resolved_issues")

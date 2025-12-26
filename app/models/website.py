from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class Website(Base, TimestampMixin):
    """Website/Domain model for tracking."""

    __tablename__ = "websites"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True, index=True)
    customer_id = Column(Integer, ForeignKey("subscriptions.customer_id"), nullable=True, index=True)

    # Domain info
    domain = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=True)  # Friendly name
    url = Column(String(500), nullable=True)  # Full URL with protocol

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(255), nullable=True)

    # Last audit info
    last_audit_at = Column(DateTime, nullable=True)
    last_audit_score = Column(Integer, nullable=True)  # 0-100

    # Lighthouse scores (cached)
    performance_score = Column(Integer, nullable=True)
    seo_score = Column(Integer, nullable=True)
    accessibility_score = Column(Integer, nullable=True)
    best_practices_score = Column(Integer, nullable=True)

    # Settings
    settings = Column(JSON, default=dict, nullable=False)
    # Example settings:
    # {
    #     "crawl_frequency": "weekly",
    #     "max_pages": 500,
    #     "ignore_patterns": ["/admin/*", "/api/*"],
    #     "notify_on_drop": true,
    #     "rank_drop_threshold": 5
    # }

    # Relationships
    client = relationship("Client", back_populates="websites")
    audits = relationship("Audit", back_populates="website", cascade="all, delete-orphan")
    keywords = relationship("Keyword", back_populates="website", cascade="all, delete-orphan")
    schedules = relationship("AuditSchedule", back_populates="website", cascade="all, delete-orphan")
    score_history = relationship("ScoreHistory", back_populates="website", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Website {self.domain}>"


class AuditSchedule(Base, TimestampMixin):
    """Automated audit schedule for a website."""

    __tablename__ = "audit_schedules"

    id = Column(Integer, primary_key=True, index=True)
    website_id = Column(Integer, ForeignKey("websites.id"), nullable=False, index=True)

    # Schedule configuration
    frequency = Column(String(20), nullable=False, default="weekly")  # daily, weekly, monthly
    hour = Column(Integer, nullable=False, default=6)  # Hour of day (0-23 UTC)
    day_of_week = Column(Integer, nullable=True)  # 0=Monday, 6=Sunday (for weekly)
    day_of_month = Column(Integer, nullable=True)  # 1-31 (for monthly)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)

    # Options
    include_lighthouse = Column(Boolean, default=True, nullable=False)
    include_ai_insights = Column(Boolean, default=False, nullable=False)
    notify_on_completion = Column(Boolean, default=True, nullable=False)
    notify_on_score_drop = Column(Boolean, default=True, nullable=False)
    score_drop_threshold = Column(Integer, default=10, nullable=False)  # Points

    # Relationships
    website = relationship("Website", back_populates="schedules")

    def __repr__(self):
        return f"<AuditSchedule {self.website_id} {self.frequency}>"


class ScoreHistory(Base):
    """Historical SEO scores for trend tracking."""

    __tablename__ = "score_history"

    id = Column(Integer, primary_key=True, index=True)
    website_id = Column(Integer, ForeignKey("websites.id"), nullable=False, index=True)

    # Score data
    score = Column(Integer, nullable=False)  # Overall SEO score
    performance_score = Column(Integer, nullable=True)
    seo_score = Column(Integer, nullable=True)
    accessibility_score = Column(Integer, nullable=True)
    best_practices_score = Column(Integer, nullable=True)

    # Timestamp
    captured_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Optional: link to the audit that generated this score
    audit_id = Column(Integer, ForeignKey("audits.id"), nullable=True)

    # Relationships
    website = relationship("Website", back_populates="score_history")

    def __repr__(self):
        return f"<ScoreHistory {self.website_id} {self.score} @ {self.captured_at}>"

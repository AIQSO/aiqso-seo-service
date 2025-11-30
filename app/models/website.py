from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Website(Base, TimestampMixin):
    """Website/Domain model for tracking."""

    __tablename__ = "websites"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)

    # Domain info
    domain = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=True)  # Friendly name
    url = Column(String(500), nullable=False)  # Full URL with protocol

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

    def __repr__(self):
        return f"<Website {self.domain}>"

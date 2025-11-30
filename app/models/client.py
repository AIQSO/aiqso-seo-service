import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class ClientTier(enum.Enum):
    """Service tier levels."""
    STARTER = "starter"           # $500/mo - 50 keywords, 1 site, weekly audits
    PROFESSIONAL = "professional" # $1,500/mo - 200 keywords, 3 sites, daily audits
    ENTERPRISE = "enterprise"     # $3,500/mo - 500 keywords, 10 sites, real-time
    AGENCY = "agency"             # $5,000/mo - 1000+ keywords, unlimited sites


# Tier limits configuration
TIER_LIMITS = {
    ClientTier.STARTER: {
        "max_keywords": 50,
        "max_websites": 1,
        "audit_frequency": "weekly",
        "ai_insights": False,
        "api_access": False,
        "white_label": False,
        "price": 500,
    },
    ClientTier.PROFESSIONAL: {
        "max_keywords": 200,
        "max_websites": 3,
        "audit_frequency": "daily",
        "ai_insights": True,
        "api_access": False,
        "white_label": False,
        "price": 1500,
    },
    ClientTier.ENTERPRISE: {
        "max_keywords": 500,
        "max_websites": 10,
        "audit_frequency": "realtime",
        "ai_insights": True,
        "api_access": True,
        "white_label": False,
        "price": 3500,
    },
    ClientTier.AGENCY: {
        "max_keywords": 10000,
        "max_websites": 100,
        "audit_frequency": "realtime",
        "ai_insights": True,
        "api_access": True,
        "white_label": True,
        "price": 5000,
    },
}


class Client(Base, TimestampMixin):
    """Client/Organization model."""

    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    company = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)

    # Authentication
    hashed_password = Column(String(255), nullable=True)
    api_key = Column(String(255), unique=True, nullable=True, index=True)

    # Subscription
    tier = Column(Enum(ClientTier), default=ClientTier.STARTER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    subscription_start = Column(DateTime, nullable=True)
    subscription_end = Column(DateTime, nullable=True)

    # Settings
    settings = Column(JSON, default=dict, nullable=False)

    # White-label branding (Agency tier)
    brand_name = Column(String(255), nullable=True)
    brand_logo_url = Column(String(500), nullable=True)
    brand_primary_color = Column(String(7), nullable=True)  # Hex color

    # Relationships
    websites = relationship("Website", back_populates="client", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="client", cascade="all, delete-orphan")

    def get_tier_limits(self):
        """Get the limits for this client's tier."""
        return TIER_LIMITS.get(self.tier, TIER_LIMITS[ClientTier.STARTER])

    def can_add_website(self, current_count: int) -> bool:
        """Check if client can add another website."""
        limits = self.get_tier_limits()
        return current_count < limits["max_websites"]

    def can_add_keyword(self, current_count: int) -> bool:
        """Check if client can add another keyword."""
        limits = self.get_tier_limits()
        return current_count < limits["max_keywords"]

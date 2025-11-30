from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
import enum
from app.models.base import Base, TimestampMixin


class DeviceType(enum.Enum):
    """Device type for rank tracking."""
    DESKTOP = "desktop"
    MOBILE = "mobile"


class Keyword(Base, TimestampMixin):
    """Keyword for rank tracking."""

    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, index=True)
    website_id = Column(Integer, ForeignKey("websites.id"), nullable=False, index=True)

    # Keyword info
    keyword = Column(String(255), nullable=False, index=True)
    device = Column(Enum(DeviceType), default=DeviceType.DESKTOP, nullable=False)
    country = Column(String(2), default="US", nullable=False)  # ISO country code
    language = Column(String(5), default="en", nullable=False)  # ISO language code

    # Current position
    position = Column(Integer, nullable=True)  # Current rank (null if not ranking)
    url = Column(String(500), nullable=True)  # URL ranking for this keyword
    last_updated = Column(DateTime, nullable=True)

    # Historical best/worst
    best_position = Column(Integer, nullable=True)
    worst_position = Column(Integer, nullable=True)
    best_position_date = Column(DateTime, nullable=True)

    # Search volume (from Google Ads integration)
    search_volume = Column(Integer, nullable=True)
    cpc = Column(String(20), nullable=True)  # Cost per click

    # Settings
    is_active = Column(Boolean, default=True, nullable=False)
    tags = Column(JSON, default=list, nullable=False)  # For grouping keywords

    # SerpBear integration
    serpbear_id = Column(Integer, nullable=True)  # ID in SerpBear

    # Relationships
    website = relationship("Website", back_populates="keywords")
    rankings = relationship("KeywordRanking", back_populates="keyword", cascade="all, delete-orphan")

    def get_position_change(self, days: int = 7) -> int | None:
        """Get position change over specified days."""
        if not self.rankings or len(self.rankings) < 2:
            return None

        # Get rankings sorted by date
        sorted_rankings = sorted(self.rankings, key=lambda r: r.date, reverse=True)

        # Find ranking from X days ago
        from datetime import timedelta
        target_date = datetime.utcnow() - timedelta(days=days)

        current = sorted_rankings[0].position if sorted_rankings else None
        previous = None

        for ranking in sorted_rankings:
            if ranking.date <= target_date:
                previous = ranking.position
                break

        if current is None or previous is None:
            return None

        return previous - current  # Positive = improved, Negative = dropped

    def __repr__(self):
        return f"<Keyword '{self.keyword}' @ {self.position}>"


class KeywordRanking(Base):
    """Historical keyword ranking data."""

    __tablename__ = "keyword_rankings"

    id = Column(Integer, primary_key=True, index=True)
    keyword_id = Column(Integer, ForeignKey("keywords.id"), nullable=False, index=True)

    # Ranking data
    date = Column(DateTime, nullable=False, index=True)
    position = Column(Integer, nullable=True)  # null if not ranking
    url = Column(String(500), nullable=True)

    # Additional metrics
    impressions = Column(Integer, nullable=True)  # From GSC
    clicks = Column(Integer, nullable=True)  # From GSC
    ctr = Column(String(10), nullable=True)  # Click-through rate

    # SERP features
    featured_snippet = Column(Boolean, default=False)
    local_pack = Column(Boolean, default=False)
    knowledge_panel = Column(Boolean, default=False)
    serp_features = Column(JSON, nullable=True)  # Array of features present

    # Relationships
    keyword = relationship("Keyword", back_populates="rankings")

    def __repr__(self):
        return f"<KeywordRanking {self.date.date()} @ {self.position}>"

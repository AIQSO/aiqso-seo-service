import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Enum, Text, Float
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class AuditCategory(enum.Enum):
    """SEO audit check categories."""
    CONFIGURATION = "configuration"  # robots.txt, noindex, etc.
    META = "meta"                    # Meta tags, titles, descriptions
    CONTENT = "content"              # H1, alt tags, content length
    PERFORMANCE = "performance"       # TTFB, file sizes, Core Web Vitals


class AuditStatus(enum.Enum):
    """Audit run status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Audit(Base, TimestampMixin):
    """SEO Audit run for a website."""

    __tablename__ = "audits"

    id = Column(Integer, primary_key=True, index=True)
    website_id = Column(Integer, ForeignKey("websites.id"), nullable=False, index=True)

    # Audit info
    status = Column(Enum(AuditStatus), default=AuditStatus.PENDING, nullable=False)
    url_audited = Column(String(500), nullable=False)  # Specific URL or homepage
    is_full_site = Column(Boolean, default=False)  # Full crawl vs single page

    # Results
    overall_score = Column(Integer, nullable=True)  # 0-100
    pages_crawled = Column(Integer, default=0)
    issues_found = Column(Integer, default=0)
    warnings_found = Column(Integer, default=0)

    # Scores by category
    configuration_score = Column(Integer, nullable=True)
    meta_score = Column(Integer, nullable=True)
    content_score = Column(Integer, nullable=True)
    performance_score = Column(Integer, nullable=True)

    # Lighthouse data (if included)
    lighthouse_data = Column(JSON, nullable=True)

    # AI insights
    ai_summary = Column(Text, nullable=True)
    ai_recommendations = Column(JSON, nullable=True)

    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Error info
    error_message = Column(Text, nullable=True)

    # Relationships
    website = relationship("Website", back_populates="audits")
    checks = relationship("AuditCheck", back_populates="audit", cascade="all, delete-orphan")

    def calculate_score(self):
        """Calculate overall score from individual checks."""
        if not self.checks:
            return None

        passed = sum(1 for check in self.checks if check.passed)
        total = len(self.checks)
        return int((passed / total) * 100) if total > 0 else 0


class AuditCheck(Base, TimestampMixin):
    """Individual SEO check result within an audit."""

    __tablename__ = "audit_checks"

    id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(Integer, ForeignKey("audits.id"), nullable=False, index=True)

    # Check info
    check_name = Column(String(100), nullable=False, index=True)
    category = Column(Enum(AuditCategory), nullable=False)
    url = Column(String(500), nullable=True)  # Specific URL if page-level

    # Result
    passed = Column(Boolean, nullable=False)
    score = Column(Integer, nullable=True)  # 0-100 for graded checks
    severity = Column(String(20), default="info")  # info, warning, error, critical

    # Details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    current_value = Column(Text, nullable=True)  # What was found
    expected_value = Column(Text, nullable=True)  # What was expected
    recommendation = Column(Text, nullable=True)

    # Additional data
    data = Column(JSON, nullable=True)

    # Relationships
    audit = relationship("Audit", back_populates="checks")

    def __repr__(self):
        status = "✓" if self.passed else "✗"
        return f"<AuditCheck {status} {self.check_name}>"


# Available SEO checks (ported from laravel-seo-scanner)
SEO_CHECKS = {
    # Configuration checks
    "robots_txt": {
        "category": AuditCategory.CONFIGURATION,
        "title": "Robots.txt Present",
        "description": "Check if robots.txt file exists and is accessible",
    },
    "noindex": {
        "category": AuditCategory.CONFIGURATION,
        "title": "No Noindex Tag",
        "description": "Page should not have noindex meta tag",
    },
    "nofollow": {
        "category": AuditCategory.CONFIGURATION,
        "title": "No Nofollow Tag",
        "description": "Page should not have nofollow meta tag",
    },
    "canonical": {
        "category": AuditCategory.CONFIGURATION,
        "title": "Canonical URL",
        "description": "Page should have a canonical URL specified",
    },
    "sitemap": {
        "category": AuditCategory.CONFIGURATION,
        "title": "Sitemap Present",
        "description": "XML sitemap should exist at /sitemap.xml",
    },
    "https": {
        "category": AuditCategory.CONFIGURATION,
        "title": "HTTPS Enabled",
        "description": "Site should use HTTPS",
    },

    # Meta checks
    "title": {
        "category": AuditCategory.META,
        "title": "Page Title",
        "description": "Page should have a title between 30-60 characters",
    },
    "meta_description": {
        "category": AuditCategory.META,
        "title": "Meta Description",
        "description": "Page should have meta description between 120-160 characters",
    },
    "og_tags": {
        "category": AuditCategory.META,
        "title": "Open Graph Tags",
        "description": "Page should have Open Graph meta tags",
    },
    "twitter_tags": {
        "category": AuditCategory.META,
        "title": "Twitter Card Tags",
        "description": "Page should have Twitter Card meta tags",
    },
    "lang_attribute": {
        "category": AuditCategory.META,
        "title": "Language Attribute",
        "description": "HTML tag should have lang attribute",
    },
    "viewport": {
        "category": AuditCategory.META,
        "title": "Viewport Meta Tag",
        "description": "Page should have viewport meta tag for mobile",
    },

    # Content checks
    "h1_tag": {
        "category": AuditCategory.CONTENT,
        "title": "H1 Heading",
        "description": "Page should have exactly one H1 tag",
    },
    "heading_structure": {
        "category": AuditCategory.CONTENT,
        "title": "Heading Structure",
        "description": "Headings should follow proper hierarchy (H1 > H2 > H3)",
    },
    "image_alt": {
        "category": AuditCategory.CONTENT,
        "title": "Image Alt Tags",
        "description": "All images should have alt attributes",
    },
    "broken_links": {
        "category": AuditCategory.CONTENT,
        "title": "No Broken Links",
        "description": "Page should not have broken internal links",
    },
    "content_length": {
        "category": AuditCategory.CONTENT,
        "title": "Content Length",
        "description": "Page should have at least 300 words of content",
    },
    "keyword_density": {
        "category": AuditCategory.CONTENT,
        "title": "Keyword Presence",
        "description": "Target keywords should appear in content",
    },

    # Performance checks
    "ttfb": {
        "category": AuditCategory.PERFORMANCE,
        "title": "Time to First Byte",
        "description": "TTFB should be under 600ms",
    },
    "page_size": {
        "category": AuditCategory.PERFORMANCE,
        "title": "Page Size",
        "description": "Total page size should be under 3MB",
    },
    "image_optimization": {
        "category": AuditCategory.PERFORMANCE,
        "title": "Image Optimization",
        "description": "Images should be optimized and properly sized",
    },
    "gzip_compression": {
        "category": AuditCategory.PERFORMANCE,
        "title": "GZIP Compression",
        "description": "Server should use GZIP compression",
    },
    "core_web_vitals": {
        "category": AuditCategory.PERFORMANCE,
        "title": "Core Web Vitals",
        "description": "LCP, FID, and CLS should meet thresholds",
    },
    "mobile_friendly": {
        "category": AuditCategory.PERFORMANCE,
        "title": "Mobile Friendly",
        "description": "Page should be mobile responsive",
    },
}

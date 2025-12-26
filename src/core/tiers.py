"""
Tier Management System

Loads and manages tier configurations for different access levels.
"""

import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class RateLimits:
    """Rate limit configuration."""

    audits_per_day: int | None = None
    audits_per_hour: int | None = None
    keywords_tracked: int | None = None
    websites: int | None = None


@dataclass
class Features:
    """Feature flags for a tier."""

    ai_insights: bool = False
    lighthouse_integration: bool = False
    full_site_crawl: bool = False
    api_access: bool = False
    cli_access: bool = False
    pdf_reports: bool = False
    white_label: bool = False
    priority_support: bool = False


@dataclass
class AuditSettings:
    """Audit configuration for a tier."""

    max_pages_per_crawl: int = 1
    max_depth: int = 1
    include_lighthouse: bool = False
    include_ai_insights: bool = False
    concurrent_requests: int = 1


@dataclass
class Tier:
    """Represents a service tier configuration."""

    name: str
    display_name: str
    description: str
    rate_limits: RateLimits
    features: Features
    audit_settings: AuditSettings
    allowed_domains: list[str] | None = None
    price_monthly: int | None = None
    price_annually: int | None = None
    raw_config: dict[str, Any] = field(default_factory=dict)

    def can_audit_domain(self, domain: str) -> bool:
        """Check if this tier can audit the given domain."""
        if self.allowed_domains is None:
            return True
        return any(domain == allowed or domain.endswith(f".{allowed}") for allowed in self.allowed_domains)

    def check_rate_limit(self, usage_today: int, usage_hour: int) -> bool:
        """Check if the current usage is within rate limits."""
        if self.rate_limits.audits_per_day is not None:
            if usage_today >= self.rate_limits.audits_per_day:
                return False
        if self.rate_limits.audits_per_hour is not None:
            if usage_hour >= self.rate_limits.audits_per_hour:
                return False
        return True


class TierManager:
    """Manages loading and accessing tier configurations."""

    def __init__(self, tiers_dir: str | None = None):
        """Initialize the tier manager.

        Args:
            tiers_dir: Path to the tiers configuration directory.
                       Defaults to project root/tiers/
        """
        if tiers_dir is None:
            # Default to project_root/tiers/
            project_root = Path(__file__).parent.parent.parent
            tiers_dir = project_root / "tiers"

        self.tiers_dir = Path(tiers_dir)
        self._tiers: dict[str, Tier] = {}
        self._load_tiers()

    def _load_tiers(self):
        """Load all tier configurations from YAML files."""
        # Load root-level tiers (internal, demo)
        for yaml_file in self.tiers_dir.glob("*.yaml"):
            self._load_tier_file(yaml_file)

        # Load paid tiers
        paid_dir = self.tiers_dir / "paid"
        if paid_dir.exists():
            for yaml_file in paid_dir.glob("*.yaml"):
                self._load_tier_file(yaml_file)

    def _load_tier_file(self, yaml_file: Path):
        """Load a single tier configuration file."""
        try:
            with open(yaml_file) as f:
                config = yaml.safe_load(f)

            if not config or "name" not in config:
                return

            tier = self._parse_tier_config(config)
            self._tiers[tier.name] = tier

        except Exception as e:
            logger.warning("Failed to load tier config %s: %s", yaml_file, e, exc_info=True)

    def _parse_tier_config(self, config: dict[str, Any]) -> Tier:
        """Parse a tier configuration dictionary into a Tier object."""
        rate_limits_cfg = config.get("rate_limits", {})
        rate_limits = RateLimits(
            audits_per_day=rate_limits_cfg.get("audits_per_day"),
            audits_per_hour=rate_limits_cfg.get("audits_per_hour"),
            keywords_tracked=rate_limits_cfg.get("keywords_tracked"),
            websites=rate_limits_cfg.get("websites"),
        )

        features_cfg = config.get("features", {})
        features = Features(
            ai_insights=features_cfg.get("ai_insights", False),
            lighthouse_integration=features_cfg.get("lighthouse_integration", False),
            full_site_crawl=features_cfg.get("full_site_crawl", False),
            api_access=features_cfg.get("api_access", False),
            cli_access=features_cfg.get("cli_access", False),
            pdf_reports=features_cfg.get("pdf_reports", False),
            white_label=features_cfg.get("white_label", False),
            priority_support=features_cfg.get("priority_support", False),
        )

        audit_cfg = config.get("audit_settings", {})
        audit_settings = AuditSettings(
            max_pages_per_crawl=audit_cfg.get("max_pages_per_crawl", 1),
            max_depth=audit_cfg.get("max_depth", 1),
            include_lighthouse=audit_cfg.get("include_lighthouse", False),
            include_ai_insights=audit_cfg.get("include_ai_insights", False),
            concurrent_requests=audit_cfg.get("concurrent_requests", 1),
        )

        return Tier(
            name=config["name"],
            display_name=config.get("display_name", config["name"]),
            description=config.get("description", ""),
            rate_limits=rate_limits,
            features=features,
            audit_settings=audit_settings,
            allowed_domains=config.get("allowed_domains"),
            price_monthly=config.get("price_monthly"),
            price_annually=config.get("price_annually"),
            raw_config=config,
        )

    def get_tier(self, name: str) -> Tier | None:
        """Get a tier by name."""
        return self._tiers.get(name)

    def get_all_tiers(self) -> dict[str, Tier]:
        """Get all loaded tiers."""
        return self._tiers.copy()

    def get_paid_tiers(self) -> list[Tier]:
        """Get all paid tiers sorted by price."""
        paid = [t for t in self._tiers.values() if t.price_monthly is not None]
        return sorted(paid, key=lambda t: t.price_monthly or 0)

    @property
    def internal(self) -> Tier | None:
        """Get the internal tier."""
        return self.get_tier("internal")

    @property
    def demo(self) -> Tier | None:
        """Get the demo tier."""
        return self.get_tier("demo")


@lru_cache(maxsize=1)
def get_tier_manager() -> TierManager:
    """Get the singleton tier manager instance."""
    return TierManager()

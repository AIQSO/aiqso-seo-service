"""
Core SEO Auditor

Standalone auditor that can be used without database dependencies.
Used by CLI and MCP server.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from .tiers import Tier


@dataclass
class CheckResult:
    """Result of a single SEO check."""

    name: str
    category: str
    passed: bool
    score: int
    title: str
    description: str | None = None
    current_value: str | None = None
    expected_value: str | None = None
    recommendation: str | None = None
    severity: str = "info"  # info, warning, error, critical


@dataclass
class AuditResult:
    """Complete audit result for a URL."""

    url: str
    timestamp: datetime
    duration_seconds: float
    overall_score: int
    checks: list[CheckResult] = field(default_factory=list)

    # Category scores
    configuration_score: int = 0
    meta_score: int = 0
    content_score: int = 0
    performance_score: int = 0

    # Counts
    issues_found: int = 0
    warnings_found: int = 0

    # AI insights (if enabled)
    ai_summary: str | None = None

    # Raw data
    html: str | None = None
    response_headers: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "url": self.url,
            "timestamp": self.timestamp.isoformat(),
            "duration_seconds": self.duration_seconds,
            "overall_score": self.overall_score,
            "scores": {
                "configuration": self.configuration_score,
                "meta": self.meta_score,
                "content": self.content_score,
                "performance": self.performance_score,
            },
            "issues_found": self.issues_found,
            "warnings_found": self.warnings_found,
            "ai_summary": self.ai_summary,
            "checks": [
                {
                    "name": c.name,
                    "category": c.category,
                    "passed": c.passed,
                    "score": c.score,
                    "title": c.title,
                    "description": c.description,
                    "current_value": c.current_value,
                    "expected_value": c.expected_value,
                    "recommendation": c.recommendation,
                    "severity": c.severity,
                }
                for c in self.checks
            ],
        }


# SEO check definitions
SEO_CHECKS = {
    # Configuration checks
    "https": {
        "category": "configuration",
        "title": "HTTPS Enabled",
        "description": "Site should use HTTPS for security and SEO ranking",
    },
    "robots_txt": {
        "category": "configuration",
        "title": "Robots.txt Present",
        "description": "robots.txt file guides search engine crawlers",
    },
    "sitemap": {
        "category": "configuration",
        "title": "Sitemap Present",
        "description": "XML sitemap helps search engines discover pages",
    },
    "noindex": {
        "category": "configuration",
        "title": "No Noindex Directive",
        "description": "Page should not have noindex if it should be indexed",
    },
    "canonical": {
        "category": "configuration",
        "title": "Canonical URL Set",
        "description": "Canonical tag prevents duplicate content issues",
    },
    # Meta checks
    "title": {
        "category": "meta",
        "title": "Page Title",
        "description": "Title should be 30-60 characters for optimal display",
    },
    "meta_description": {
        "category": "meta",
        "title": "Meta Description",
        "description": "Description should be 120-160 characters",
    },
    "og_tags": {
        "category": "meta",
        "title": "Open Graph Tags",
        "description": "OG tags improve social media sharing appearance",
    },
    "twitter_tags": {
        "category": "meta",
        "title": "Twitter Card Tags",
        "description": "Twitter cards improve Twitter sharing appearance",
    },
    "lang_attribute": {
        "category": "meta",
        "title": "Language Attribute",
        "description": "HTML lang attribute helps with accessibility and SEO",
    },
    "viewport": {
        "category": "meta",
        "title": "Viewport Meta Tag",
        "description": "Viewport tag enables mobile responsiveness",
    },
    # Content checks
    "h1_tag": {
        "category": "content",
        "title": "H1 Tag Present",
        "description": "Page should have exactly one H1 tag",
    },
    "heading_structure": {
        "category": "content",
        "title": "Heading Hierarchy",
        "description": "Headings should follow proper hierarchy (H1 > H2 > H3)",
    },
    "image_alt": {
        "category": "content",
        "title": "Image Alt Attributes",
        "description": "All images should have descriptive alt text",
    },
    "content_length": {
        "category": "content",
        "title": "Content Length",
        "description": "Page should have at least 300 words of content",
    },
    # Performance checks
    "ttfb": {
        "category": "performance",
        "title": "Time to First Byte",
        "description": "TTFB should be under 600ms for good performance",
    },
    "page_size": {
        "category": "performance",
        "title": "Page Size",
        "description": "Total page size should be under 3MB",
    },
    "gzip_compression": {
        "category": "performance",
        "title": "Compression Enabled",
        "description": "GZIP or Brotli compression should be enabled",
    },
}


class SEOAuditor:
    """Standalone SEO auditor for CLI and MCP usage."""

    def __init__(self, tier: Tier | None = None):
        """Initialize the auditor.

        Args:
            tier: Optional tier configuration for limits/features.
                  If None, runs with no limits (internal mode).
        """
        self.tier = tier
        self.client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def audit_url(
        self,
        url: str,
        include_lighthouse: bool = False,
        include_ai: bool = False,
    ) -> AuditResult:
        """Audit a single URL.

        Args:
            url: The URL to audit
            include_lighthouse: Whether to run Lighthouse (if available)
            include_ai: Whether to generate AI insights (if API key available)

        Returns:
            AuditResult with all check results
        """
        start_time = datetime.utcnow()
        checks: list[CheckResult] = []

        # Ensure we have a client
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

        try:
            # Fetch the page
            response = await self.client.get(url)
            html = response.text
            soup = BeautifulSoup(html, "lxml")

            # Run all checks
            checks.extend(await self._run_configuration_checks(url, response, soup))
            checks.extend(await self._run_meta_checks(soup))
            checks.extend(await self._run_content_checks(soup))
            checks.extend(await self._run_performance_checks(response))

            # Calculate scores
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            result = AuditResult(
                url=url,
                timestamp=start_time,
                duration_seconds=duration,
                overall_score=0,
                checks=checks,
                html=html,
                response_headers=dict(response.headers),
            )

            self._calculate_scores(result)

            # Generate AI insights if enabled
            if include_ai:
                result.ai_summary = await self._generate_ai_insights(result)

            return result

        except Exception as e:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            return AuditResult(
                url=url,
                timestamp=start_time,
                duration_seconds=duration,
                overall_score=0,
                checks=[
                    CheckResult(
                        name="fetch_error",
                        category="configuration",
                        passed=False,
                        score=0,
                        title="Page Fetch Failed",
                        description=str(e),
                        severity="critical",
                    )
                ],
            )

    async def _run_configuration_checks(
        self,
        url: str,
        response: httpx.Response,
        soup: BeautifulSoup,
    ) -> list[CheckResult]:
        """Run configuration-related SEO checks."""
        checks = []

        # HTTPS check
        checks.append(
            CheckResult(
                name="https",
                category="configuration",
                passed=url.startswith("https://"),
                score=100 if url.startswith("https://") else 0,
                title=SEO_CHECKS["https"]["title"],
                description=SEO_CHECKS["https"]["description"],
                current_value=url.split("://")[0],
                expected_value="https",
                severity="error" if not url.startswith("https://") else "info",
            )
        )

        # Robots.txt check
        try:
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            robots_response = await self.client.get(robots_url)
            robots_exists = robots_response.status_code == 200
        except Exception:
            robots_exists = False

        checks.append(
            CheckResult(
                name="robots_txt",
                category="configuration",
                passed=robots_exists,
                score=100 if robots_exists else 0,
                title=SEO_CHECKS["robots_txt"]["title"],
                description=SEO_CHECKS["robots_txt"]["description"],
                current_value="Found" if robots_exists else "Not found",
                severity="warning" if not robots_exists else "info",
            )
        )

        # Sitemap check
        try:
            parsed = urlparse(url)
            sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
            sitemap_response = await self.client.get(sitemap_url)
            sitemap_exists = sitemap_response.status_code == 200
        except Exception:
            sitemap_exists = False

        checks.append(
            CheckResult(
                name="sitemap",
                category="configuration",
                passed=sitemap_exists,
                score=100 if sitemap_exists else 0,
                title=SEO_CHECKS["sitemap"]["title"],
                description=SEO_CHECKS["sitemap"]["description"],
                current_value="Found" if sitemap_exists else "Not found",
                severity="warning" if not sitemap_exists else "info",
            )
        )

        # Noindex check
        noindex_meta = soup.find("meta", attrs={"name": "robots", "content": lambda x: x and "noindex" in x.lower()})
        noindex_header = "noindex" in response.headers.get("x-robots-tag", "").lower()
        has_noindex = bool(noindex_meta or noindex_header)

        checks.append(
            CheckResult(
                name="noindex",
                category="configuration",
                passed=not has_noindex,
                score=0 if has_noindex else 100,
                title=SEO_CHECKS["noindex"]["title"],
                description=SEO_CHECKS["noindex"]["description"],
                current_value="Found noindex" if has_noindex else "No noindex",
                severity="critical" if has_noindex else "info",
            )
        )

        # Canonical check
        canonical = soup.find("link", rel="canonical")
        checks.append(
            CheckResult(
                name="canonical",
                category="configuration",
                passed=canonical is not None,
                score=100 if canonical else 0,
                title=SEO_CHECKS["canonical"]["title"],
                description=SEO_CHECKS["canonical"]["description"],
                current_value=canonical.get("href") if canonical else "Not set",
                severity="warning" if not canonical else "info",
            )
        )

        return checks

    async def _run_meta_checks(self, soup: BeautifulSoup) -> list[CheckResult]:
        """Run meta tag SEO checks."""
        checks = []

        # Title check
        title = soup.find("title")
        title_text = title.get_text().strip() if title else ""
        title_len = len(title_text)
        title_ok = 30 <= title_len <= 60

        checks.append(
            CheckResult(
                name="title",
                category="meta",
                passed=title_ok and title_len > 0,
                score=min(100, int(title_len / 60 * 100)) if title_len > 0 else 0,
                title=SEO_CHECKS["title"]["title"],
                description=SEO_CHECKS["title"]["description"],
                current_value=f"{title_text[:50]}{'...' if len(title_text) > 50 else ''} ({title_len} chars)"
                if title_text
                else "Missing",
                expected_value="30-60 characters",
                severity="error" if not title_text else ("warning" if not title_ok else "info"),
            )
        )

        # Meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        desc_content = meta_desc.get("content", "").strip() if meta_desc else ""
        desc_len = len(desc_content)
        desc_ok = 120 <= desc_len <= 160

        checks.append(
            CheckResult(
                name="meta_description",
                category="meta",
                passed=desc_ok and desc_len > 0,
                score=min(100, int(desc_len / 160 * 100)) if desc_len > 0 else 0,
                title=SEO_CHECKS["meta_description"]["title"],
                description=SEO_CHECKS["meta_description"]["description"],
                current_value=f"{desc_content[:60]}{'...' if len(desc_content) > 60 else ''} ({desc_len} chars)"
                if desc_content
                else "Missing",
                expected_value="120-160 characters",
                severity="error" if not desc_content else ("warning" if not desc_ok else "info"),
            )
        )

        # Open Graph tags
        og_tags = soup.find_all("meta", property=lambda x: x and x.startswith("og:"))
        og_required = ["og:title", "og:description", "og:image", "og:url"]
        og_found = [tag.get("property") for tag in og_tags]
        og_missing = [t for t in og_required if t not in og_found]

        checks.append(
            CheckResult(
                name="og_tags",
                category="meta",
                passed=len(og_missing) == 0,
                score=int((len(og_required) - len(og_missing)) / len(og_required) * 100),
                title=SEO_CHECKS["og_tags"]["title"],
                description=SEO_CHECKS["og_tags"]["description"],
                current_value=f"Found: {', '.join(og_found)}" if og_found else "None",
                expected_value=", ".join(og_required),
                recommendation=f"Add missing: {', '.join(og_missing)}" if og_missing else None,
                severity="warning" if og_missing else "info",
            )
        )

        # Twitter cards
        twitter_tags = soup.find_all("meta", attrs={"name": lambda x: x and x.startswith("twitter:")})
        checks.append(
            CheckResult(
                name="twitter_tags",
                category="meta",
                passed=len(twitter_tags) > 0,
                score=100 if twitter_tags else 0,
                title=SEO_CHECKS["twitter_tags"]["title"],
                description=SEO_CHECKS["twitter_tags"]["description"],
                current_value=f"{len(twitter_tags)} tags found",
                severity="warning" if not twitter_tags else "info",
            )
        )

        # Lang attribute
        html_tag = soup.find("html")
        lang = html_tag.get("lang") if html_tag else None
        checks.append(
            CheckResult(
                name="lang_attribute",
                category="meta",
                passed=lang is not None,
                score=100 if lang else 0,
                title=SEO_CHECKS["lang_attribute"]["title"],
                description=SEO_CHECKS["lang_attribute"]["description"],
                current_value=lang or "Missing",
                severity="warning" if not lang else "info",
            )
        )

        # Viewport
        viewport = soup.find("meta", attrs={"name": "viewport"})
        checks.append(
            CheckResult(
                name="viewport",
                category="meta",
                passed=viewport is not None,
                score=100 if viewport else 0,
                title=SEO_CHECKS["viewport"]["title"],
                description=SEO_CHECKS["viewport"]["description"],
                current_value=viewport.get("content") if viewport else "Missing",
                severity="error" if not viewport else "info",
            )
        )

        return checks

    async def _run_content_checks(self, soup: BeautifulSoup) -> list[CheckResult]:
        """Run content-related SEO checks."""
        checks = []

        # H1 check
        h1_tags = soup.find_all("h1")
        h1_count = len(h1_tags)
        checks.append(
            CheckResult(
                name="h1_tag",
                category="content",
                passed=h1_count == 1,
                score=100 if h1_count == 1 else (50 if h1_count > 1 else 0),
                title=SEO_CHECKS["h1_tag"]["title"],
                description=SEO_CHECKS["h1_tag"]["description"],
                current_value=f"{h1_count} H1 tag(s) found",
                expected_value="Exactly 1 H1 tag",
                severity="error" if h1_count == 0 else ("warning" if h1_count > 1 else "info"),
            )
        )

        # Heading structure
        headings = []
        for level in range(1, 7):
            headings.extend([(level, h.get_text()[:50]) for h in soup.find_all(f"h{level}")])

        hierarchy_ok = True
        last_level = 0
        for level, _ in headings:
            if level > last_level + 1 and last_level > 0:
                hierarchy_ok = False
                break
            last_level = level

        checks.append(
            CheckResult(
                name="heading_structure",
                category="content",
                passed=hierarchy_ok,
                score=100 if hierarchy_ok else 50,
                title=SEO_CHECKS["heading_structure"]["title"],
                description=SEO_CHECKS["heading_structure"]["description"],
                current_value=f"H1:{len(soup.find_all('h1'))}, H2:{len(soup.find_all('h2'))}, H3:{len(soup.find_all('h3'))}",
                recommendation="Ensure headings follow proper hierarchy (H1 > H2 > H3)" if not hierarchy_ok else None,
                severity="warning" if not hierarchy_ok else "info",
            )
        )

        # Image alt tags
        images = soup.find_all("img")
        images_without_alt = [img for img in images if not img.get("alt")]
        alt_ok = len(images_without_alt) == 0

        checks.append(
            CheckResult(
                name="image_alt",
                category="content",
                passed=alt_ok,
                score=int((len(images) - len(images_without_alt)) / len(images) * 100) if images else 100,
                title=SEO_CHECKS["image_alt"]["title"],
                description=SEO_CHECKS["image_alt"]["description"],
                current_value=f"{len(images) - len(images_without_alt)}/{len(images)} images have alt"
                if images
                else "No images",
                expected_value="All images should have alt attributes",
                severity="warning" if images_without_alt else "info",
            )
        )

        # Content length (create a copy to avoid modifying original)
        content_soup = BeautifulSoup(str(soup), "lxml")
        for element in content_soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        text = content_soup.get_text(separator=" ", strip=True)
        word_count = len(text.split())
        content_ok = word_count >= 300

        checks.append(
            CheckResult(
                name="content_length",
                category="content",
                passed=content_ok,
                score=min(100, int(word_count / 300 * 100)),
                title=SEO_CHECKS["content_length"]["title"],
                description=SEO_CHECKS["content_length"]["description"],
                current_value=f"{word_count} words",
                expected_value="At least 300 words",
                severity="warning" if not content_ok else "info",
            )
        )

        return checks

    async def _run_performance_checks(self, response: httpx.Response) -> list[CheckResult]:
        """Run performance-related checks."""
        checks = []

        # TTFB
        ttfb = response.elapsed.total_seconds() * 1000
        ttfb_ok = ttfb < 600

        checks.append(
            CheckResult(
                name="ttfb",
                category="performance",
                passed=ttfb_ok,
                score=max(0, 100 - int((ttfb / 600) * 100)) if ttfb < 1200 else 0,
                title=SEO_CHECKS["ttfb"]["title"],
                description=SEO_CHECKS["ttfb"]["description"],
                current_value=f"{int(ttfb)}ms",
                expected_value="< 600ms",
                severity="warning" if not ttfb_ok else "info",
            )
        )

        # Page size
        content_length = len(response.content)
        size_mb = content_length / (1024 * 1024)
        size_ok = size_mb < 3

        checks.append(
            CheckResult(
                name="page_size",
                category="performance",
                passed=size_ok,
                score=max(0, 100 - int((size_mb / 3) * 100)) if size_mb < 6 else 0,
                title=SEO_CHECKS["page_size"]["title"],
                description=SEO_CHECKS["page_size"]["description"],
                current_value=f"{size_mb:.2f} MB",
                expected_value="< 3 MB",
                severity="warning" if not size_ok else "info",
            )
        )

        # GZIP compression
        content_encoding = response.headers.get("content-encoding", "")
        gzip_ok = "gzip" in content_encoding or "br" in content_encoding

        checks.append(
            CheckResult(
                name="gzip_compression",
                category="performance",
                passed=gzip_ok,
                score=100 if gzip_ok else 0,
                title=SEO_CHECKS["gzip_compression"]["title"],
                description=SEO_CHECKS["gzip_compression"]["description"],
                current_value=content_encoding or "None",
                expected_value="gzip or br",
                severity="warning" if not gzip_ok else "info",
            )
        )

        return checks

    def _calculate_scores(self, result: AuditResult):
        """Calculate overall and category scores."""
        checks = result.checks

        # Overall score
        if checks:
            passed = sum(1 for c in checks if c.passed)
            result.overall_score = int((passed / len(checks)) * 100)

        # Category scores
        categories = ["configuration", "meta", "content", "performance"]
        for category in categories:
            category_checks = [c for c in checks if c.category == category]
            if category_checks:
                passed = sum(1 for c in category_checks if c.passed)
                score = int((passed / len(category_checks)) * 100)

                if category == "configuration":
                    result.configuration_score = score
                elif category == "meta":
                    result.meta_score = score
                elif category == "content":
                    result.content_score = score
                elif category == "performance":
                    result.performance_score = score

        # Count issues
        result.issues_found = sum(1 for c in checks if not c.passed and c.severity in ["error", "critical"])
        result.warnings_found = sum(1 for c in checks if not c.passed and c.severity == "warning")

    async def _generate_ai_insights(self, result: AuditResult) -> str | None:
        """Generate AI-powered insights using Claude."""
        try:
            import os

            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                return None

            import anthropic

            client = anthropic.Anthropic(api_key=api_key)

            failed_checks = [c for c in result.checks if not c.passed]
            check_summary = "\n".join(
                [f"- {c.title}: {c.current_value} (expected: {c.expected_value})" for c in failed_checks[:10]]
            )

            prompt = f"""Analyze these SEO audit results for {result.url} and provide:
1. A brief summary (2-3 sentences)
2. Top 3 priority fixes
3. Quick wins that can be implemented immediately

Failed checks:
{check_summary}

Overall score: {result.overall_score}/100
"""

            message = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )

            return message.content[0].text

        except Exception as e:
            return f"AI insights unavailable: {str(e)}"

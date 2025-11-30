"""
SEO Auditor Service

Performs comprehensive SEO audits including:
- Technical SEO checks (meta tags, headers, configuration)
- Content analysis
- Performance metrics via Lighthouse
- AI-powered insights via Claude
"""

import asyncio
import httpx
from datetime import datetime
from typing import Optional
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.models.audit import Audit, AuditCheck, AuditStatus, AuditCategory, SEO_CHECKS
from app.models.website import Website
from app.config import get_settings

settings = get_settings()


class SEOAuditor:
    """Main SEO auditing service."""

    def __init__(self, db: Session):
        self.db = db
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

    async def run_audit(
        self,
        audit_id: int,
        include_lighthouse: bool = True,
        include_ai: bool = True,
    ):
        """Run a complete SEO audit."""
        audit = self.db.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            return

        try:
            # Update status
            audit.status = AuditStatus.RUNNING
            audit.started_at = datetime.utcnow()
            self.db.commit()

            # Fetch the page
            response = await self.client.get(audit.url_audited)
            html = response.text
            soup = BeautifulSoup(html, "lxml")

            # Run all checks
            await self._run_configuration_checks(audit, response, soup)
            await self._run_meta_checks(audit, soup)
            await self._run_content_checks(audit, soup)
            await self._run_performance_checks(audit, response)

            # Run Lighthouse if enabled
            if include_lighthouse:
                await self._run_lighthouse_audit(audit)

            # Generate AI insights if enabled
            if include_ai:
                await self._generate_ai_insights(audit)

            # Calculate scores
            self._calculate_scores(audit)

            # Update status
            audit.status = AuditStatus.COMPLETED
            audit.completed_at = datetime.utcnow()
            audit.duration_seconds = (audit.completed_at - audit.started_at).total_seconds()

            # Update website scores
            audit.website.last_audit_at = audit.completed_at
            audit.website.last_audit_score = audit.overall_score

            self.db.commit()

        except Exception as e:
            audit.status = AuditStatus.FAILED
            audit.error_message = str(e)
            audit.completed_at = datetime.utcnow()
            self.db.commit()
            raise

        finally:
            await self.client.aclose()

    async def _run_configuration_checks(
        self,
        audit: Audit,
        response: httpx.Response,
        soup: BeautifulSoup,
    ):
        """Run configuration-related SEO checks."""

        # Check HTTPS
        self._add_check(
            audit,
            "https",
            passed=audit.url_audited.startswith("https://"),
            current_value=audit.url_audited.split("://")[0],
            expected_value="https",
        )

        # Check robots.txt
        try:
            robots_response = await self.client.get(
                f"{audit.url_audited.rstrip('/')}/robots.txt"
            )
            robots_exists = robots_response.status_code == 200
        except:
            robots_exists = False

        self._add_check(
            audit,
            "robots_txt",
            passed=robots_exists,
            current_value="Found" if robots_exists else "Not found",
        )

        # Check sitemap
        try:
            sitemap_response = await self.client.get(
                f"{audit.url_audited.rstrip('/')}/sitemap.xml"
            )
            sitemap_exists = sitemap_response.status_code == 200
        except:
            sitemap_exists = False

        self._add_check(
            audit,
            "sitemap",
            passed=sitemap_exists,
            current_value="Found" if sitemap_exists else "Not found",
        )

        # Check noindex
        noindex_meta = soup.find("meta", attrs={"name": "robots", "content": lambda x: x and "noindex" in x.lower()})
        noindex_header = "noindex" in response.headers.get("x-robots-tag", "").lower()

        self._add_check(
            audit,
            "noindex",
            passed=not (noindex_meta or noindex_header),
            current_value="Found noindex" if (noindex_meta or noindex_header) else "No noindex",
            severity="critical" if (noindex_meta or noindex_header) else "info",
        )

        # Check canonical
        canonical = soup.find("link", rel="canonical")
        self._add_check(
            audit,
            "canonical",
            passed=canonical is not None,
            current_value=canonical.get("href") if canonical else None,
        )

    async def _run_meta_checks(self, audit: Audit, soup: BeautifulSoup):
        """Run meta tag SEO checks."""

        # Title check
        title = soup.find("title")
        title_text = title.get_text().strip() if title else ""
        title_len = len(title_text)
        title_ok = 30 <= title_len <= 60

        self._add_check(
            audit,
            "title",
            passed=title_ok,
            score=min(100, int(title_len / 60 * 100)) if title_len > 0 else 0,
            current_value=f"{title_text[:50]}... ({title_len} chars)" if title_text else "Missing",
            expected_value="30-60 characters",
            severity="error" if not title_text else ("warning" if not title_ok else "info"),
        )

        # Meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        desc_content = meta_desc.get("content", "").strip() if meta_desc else ""
        desc_len = len(desc_content)
        desc_ok = 120 <= desc_len <= 160

        self._add_check(
            audit,
            "meta_description",
            passed=desc_ok,
            score=min(100, int(desc_len / 160 * 100)) if desc_len > 0 else 0,
            current_value=f"{desc_content[:60]}... ({desc_len} chars)" if desc_content else "Missing",
            expected_value="120-160 characters",
            severity="error" if not desc_content else ("warning" if not desc_ok else "info"),
        )

        # Open Graph tags
        og_tags = soup.find_all("meta", property=lambda x: x and x.startswith("og:"))
        og_required = ["og:title", "og:description", "og:image", "og:url"]
        og_found = [tag.get("property") for tag in og_tags]
        og_missing = [t for t in og_required if t not in og_found]

        self._add_check(
            audit,
            "og_tags",
            passed=len(og_missing) == 0,
            current_value=f"Found: {', '.join(og_found)}" if og_found else "None",
            expected_value=", ".join(og_required),
            recommendation=f"Add missing: {', '.join(og_missing)}" if og_missing else None,
        )

        # Twitter cards
        twitter_tags = soup.find_all("meta", attrs={"name": lambda x: x and x.startswith("twitter:")})
        self._add_check(
            audit,
            "twitter_tags",
            passed=len(twitter_tags) > 0,
            current_value=f"{len(twitter_tags)} tags found",
        )

        # Lang attribute
        html_tag = soup.find("html")
        lang = html_tag.get("lang") if html_tag else None
        self._add_check(
            audit,
            "lang_attribute",
            passed=lang is not None,
            current_value=lang or "Missing",
        )

        # Viewport
        viewport = soup.find("meta", attrs={"name": "viewport"})
        self._add_check(
            audit,
            "viewport",
            passed=viewport is not None,
            current_value=viewport.get("content") if viewport else "Missing",
        )

    async def _run_content_checks(self, audit: Audit, soup: BeautifulSoup):
        """Run content-related SEO checks."""

        # H1 check
        h1_tags = soup.find_all("h1")
        h1_count = len(h1_tags)
        self._add_check(
            audit,
            "h1_tag",
            passed=h1_count == 1,
            current_value=f"{h1_count} H1 tag(s) found",
            expected_value="Exactly 1 H1 tag",
            severity="error" if h1_count == 0 else ("warning" if h1_count > 1 else "info"),
        )

        # Heading structure
        headings = []
        for level in range(1, 7):
            headings.extend([(level, h.get_text()[:50]) for h in soup.find_all(f"h{level}")])

        # Check hierarchy
        hierarchy_ok = True
        last_level = 0
        for level, _ in headings:
            if level > last_level + 1 and last_level > 0:
                hierarchy_ok = False
                break
            last_level = level

        self._add_check(
            audit,
            "heading_structure",
            passed=hierarchy_ok,
            current_value=f"H1:{len(soup.find_all('h1'))}, H2:{len(soup.find_all('h2'))}, H3:{len(soup.find_all('h3'))}",
            recommendation="Ensure headings follow proper hierarchy (H1 > H2 > H3)" if not hierarchy_ok else None,
        )

        # Image alt tags
        images = soup.find_all("img")
        images_without_alt = [img for img in images if not img.get("alt")]
        alt_ok = len(images_without_alt) == 0

        self._add_check(
            audit,
            "image_alt",
            passed=alt_ok,
            current_value=f"{len(images) - len(images_without_alt)}/{len(images)} images have alt",
            expected_value="All images should have alt attributes",
            severity="warning" if images_without_alt else "info",
        )

        # Content length
        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        text = soup.get_text(separator=" ", strip=True)
        word_count = len(text.split())
        content_ok = word_count >= 300

        self._add_check(
            audit,
            "content_length",
            passed=content_ok,
            score=min(100, int(word_count / 300 * 100)),
            current_value=f"{word_count} words",
            expected_value="At least 300 words",
            severity="warning" if not content_ok else "info",
        )

    async def _run_performance_checks(self, audit: Audit, response: httpx.Response):
        """Run performance-related checks."""

        # TTFB (approximated from response time)
        ttfb = response.elapsed.total_seconds() * 1000  # Convert to ms
        ttfb_ok = ttfb < 600

        self._add_check(
            audit,
            "ttfb",
            passed=ttfb_ok,
            score=max(0, 100 - int((ttfb / 600) * 100)) if ttfb < 1200 else 0,
            current_value=f"{int(ttfb)}ms",
            expected_value="< 600ms",
            severity="warning" if not ttfb_ok else "info",
        )

        # Page size
        content_length = len(response.content)
        size_mb = content_length / (1024 * 1024)
        size_ok = size_mb < 3

        self._add_check(
            audit,
            "page_size",
            passed=size_ok,
            current_value=f"{size_mb:.2f} MB",
            expected_value="< 3 MB",
            severity="warning" if not size_ok else "info",
        )

        # GZIP compression
        content_encoding = response.headers.get("content-encoding", "")
        gzip_ok = "gzip" in content_encoding or "br" in content_encoding

        self._add_check(
            audit,
            "gzip_compression",
            passed=gzip_ok,
            current_value=content_encoding or "None",
            expected_value="gzip or br",
        )

    async def _run_lighthouse_audit(self, audit: Audit):
        """Run Google Lighthouse audit."""
        # TODO: Integrate with Lighthouse CI or run locally
        # For now, skip if not configured
        if not settings.lighthouse_enabled:
            return

        # Placeholder for Lighthouse integration
        # This would call the Lighthouse CI server or run locally
        pass

    async def _generate_ai_insights(self, audit: Audit):
        """Generate AI-powered insights using Claude."""
        if not settings.anthropic_api_key:
            return

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

            # Gather check results
            failed_checks = [c for c in audit.checks if not c.passed]
            check_summary = "\n".join([
                f"- {c.title}: {c.current_value} (expected: {c.expected_value})"
                for c in failed_checks[:10]
            ])

            prompt = f"""Analyze these SEO audit results for {audit.url_audited} and provide:
1. A brief summary (2-3 sentences)
2. Top 3 priority fixes
3. Quick wins that can be implemented immediately

Failed checks:
{check_summary}

Overall score: {audit.overall_score}/100
"""

            message = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )

            audit.ai_summary = message.content[0].text

        except Exception as e:
            audit.ai_summary = f"AI insights unavailable: {str(e)}"

    def _calculate_scores(self, audit: Audit):
        """Calculate overall and category scores."""
        checks = audit.checks

        # Overall score
        if checks:
            passed = sum(1 for c in checks if c.passed)
            audit.overall_score = int((passed / len(checks)) * 100)

        # Category scores
        for category in AuditCategory:
            category_checks = [c for c in checks if c.category == category]
            if category_checks:
                passed = sum(1 for c in category_checks if c.passed)
                score = int((passed / len(category_checks)) * 100)

                if category == AuditCategory.CONFIGURATION:
                    audit.configuration_score = score
                elif category == AuditCategory.META:
                    audit.meta_score = score
                elif category == AuditCategory.CONTENT:
                    audit.content_score = score
                elif category == AuditCategory.PERFORMANCE:
                    audit.performance_score = score

        # Count issues
        audit.issues_found = sum(1 for c in checks if not c.passed and c.severity in ["error", "critical"])
        audit.warnings_found = sum(1 for c in checks if not c.passed and c.severity == "warning")
        audit.pages_crawled = 1

    def _add_check(
        self,
        audit: Audit,
        check_name: str,
        passed: bool,
        score: Optional[int] = None,
        current_value: Optional[str] = None,
        expected_value: Optional[str] = None,
        recommendation: Optional[str] = None,
        severity: str = "info",
    ):
        """Add a check result to the audit."""
        check_info = SEO_CHECKS.get(check_name, {})

        check = AuditCheck(
            audit_id=audit.id,
            check_name=check_name,
            category=check_info.get("category", AuditCategory.CONFIGURATION),
            passed=passed,
            score=score if score is not None else (100 if passed else 0),
            severity=severity if not passed else "info",
            title=check_info.get("title", check_name),
            description=check_info.get("description"),
            current_value=current_value,
            expected_value=expected_value,
            recommendation=recommendation,
        )

        self.db.add(check)
        audit.checks.append(check)

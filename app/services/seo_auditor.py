"""
SEO Auditor Service

Database-backed auditor that delegates check execution to src/core/auditor
and persists results to the database. Single source of truth for audit logic.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.audit import AuditCategory, Audit, AuditCheck, AuditStatus
from app.security import validate_audit_url
from src.core.auditor import AuditResult, CheckResult, SEOAuditor as CoreAuditor

settings = get_settings()
logger = logging.getLogger(__name__)

# Map string categories from core auditor to DB enum
_CATEGORY_MAP = {
    "configuration": AuditCategory.CONFIGURATION,
    "meta": AuditCategory.META,
    "content": AuditCategory.CONTENT,
    "performance": AuditCategory.PERFORMANCE,
}


class SEOAuditor:
    """Database-backed SEO auditing service. Delegates to core auditor for checks."""

    def __init__(self, db: Session):
        self.db = db

    async def run_audit(
        self,
        audit_id: int,
        include_lighthouse: bool = True,
        include_ai: bool = True,
    ):
        """Run a complete SEO audit and persist results."""
        audit = self.db.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            return

        try:
            audit.status = AuditStatus.RUNNING
            audit.started_at = datetime.now(UTC)
            self.db.commit()

            # SSRF protection
            validate_audit_url(audit.url_audited)

            # Delegate to core auditor for all checks
            async with CoreAuditor() as core:
                result: AuditResult = await core.audit_url(
                    audit.url_audited,
                    include_lighthouse=include_lighthouse,
                    include_ai=include_ai,
                )

            # Persist check results to database
            self._persist_checks(audit, result)

            # Generate AI insights if enabled — failures are non-fatal and
            # must not propagate to the outer exception handler.
            if include_ai and not result.ai_summary:
                try:
                    await self._generate_ai_insights(audit)
                except Exception as ai_exc:
                    logger.warning("AI insight generation failed (non-fatal): %s", ai_exc)
                    audit.ai_summary = "AI insights unavailable"
            elif result.ai_summary:
                audit.ai_summary = result.ai_summary

            # Copy scores from result
            audit.overall_score = result.overall_score
            audit.configuration_score = result.configuration_score
            audit.meta_score = result.meta_score
            audit.content_score = result.content_score
            audit.performance_score = result.performance_score
            audit.issues_found = result.issues_found
            audit.warnings_found = result.warnings_found
            audit.pages_crawled = 1

            # Mark complete
            audit.status = AuditStatus.COMPLETED
            audit.completed_at = datetime.now(UTC)
            started = audit.started_at.replace(tzinfo=UTC) if audit.started_at.tzinfo is None else audit.started_at
            audit.duration_seconds = (audit.completed_at - started).total_seconds()

            # Update website cached scores
            audit.website.last_audit_at = audit.completed_at
            audit.website.last_audit_score = audit.overall_score

            self.db.commit()

        except Exception as e:
            audit.status = AuditStatus.FAILED
            audit.error_message = str(e)
            audit.completed_at = datetime.now(UTC)
            self.db.commit()
            raise

    def _persist_checks(self, audit: Audit, result: AuditResult):
        """Convert core CheckResults to DB AuditCheck records."""
        for check in result.checks:
            db_check = AuditCheck(
                audit_id=audit.id,
                check_name=check.name,
                category=_CATEGORY_MAP.get(check.category, AuditCategory.CONFIGURATION),
                passed=check.passed,
                score=check.score,
                severity=check.severity,
                title=check.title,
                description=check.description,
                current_value=check.current_value,
                expected_value=check.expected_value,
                recommendation=check.recommendation,
            )
            self.db.add(db_check)
            audit.checks.append(db_check)

    async def _generate_ai_insights(self, audit: Audit):
        """Generate AI-powered insights using Claude, with Ollama as fallback.

        Tries Anthropic first. If the key is absent, expired, or the call
        fails for any reason, falls back to the Ollama instance configured
        via AI_SERVER_URL.  If both fail, sets ai_summary to a neutral
        unavailable message so the audit status is unaffected.
        """
        failed_checks = [c for c in audit.checks if not c.passed]
        check_summary = "\n".join(
            [f"- {c.title}: {c.current_value} (expected: {c.expected_value})" for c in failed_checks[:10]]
        )
        prompt = (
            f"Analyze these SEO audit results for {audit.url_audited} and provide:\n"
            "1. A brief summary (2-3 sentences)\n"
            "2. Top 3 priority fixes\n"
            "3. Quick wins that can be implemented immediately\n\n"
            f"Failed checks:\n{check_summary}\n\n"
            f"Overall score: {audit.overall_score}/100\n"
        )

        # --- Attempt 1: Anthropic ---
        if settings.anthropic_api_key:
            try:
                import anthropic

                client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
                message = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=500,
                    messages=[{"role": "user", "content": prompt}],
                )
                audit.ai_summary = message.content[0].text
                return
            except Exception as anthropic_exc:
                logger.warning(
                    "Anthropic AI insights failed, attempting Ollama fallback: %s", anthropic_exc
                )
        else:
            logger.debug("ANTHROPIC_API_KEY not configured; skipping Anthropic, attempting Ollama fallback.")

        # --- Attempt 2: Ollama fallback ---
        ollama_base = settings.ai_server_url.rstrip("/")
        try:
            import httpx

            payload = {
                "model": "llama3.3:70b",
                "prompt": prompt,
                "stream": False,
            }
            async with httpx.AsyncClient(timeout=60.0) as http:
                response = await http.post(f"{ollama_base}/api/generate", json=payload)
                response.raise_for_status()
                data = response.json()
                audit.ai_summary = data.get("response", "").strip() or "AI insights unavailable"
                return
        except Exception as ollama_exc:
            logger.warning("Ollama AI fallback also failed: %s", ollama_exc)

        # Both providers failed — set a neutral message and let the audit complete.
        audit.ai_summary = "AI insights unavailable"

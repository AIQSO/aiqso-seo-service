"""
Celery background tasks for SEO service.

Includes scheduled tasks for automated auditing via Celery Beat.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from app.celery_app import celery_app
from app.database import SessionLocal

logger = logging.getLogger(__name__)

# Internal domains for daily audits
INTERNAL_DOMAINS = ["aiqso.io", "www.aiqso.io"]


@celery_app.task(bind=True, max_retries=3)
def run_seo_audit(self, audit_id: int, include_lighthouse: bool = True, include_ai: bool = True):
    """Run SEO audit as background task."""
    from app.services.seo_auditor import SEOAuditor

    db = SessionLocal()
    try:
        auditor = SEOAuditor(db)
        asyncio.run(auditor.run_audit(audit_id, include_lighthouse, include_ai))
    except Exception as e:
        db.rollback()
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2)
def update_keyword_rankings(self, website_id: int):
    """Update keyword rankings for a website via SerpBear."""
    from app.services.serpbear_service import SerpBearService

    db = SessionLocal()
    try:
        service = SerpBearService(db)
        result = asyncio.run(service.sync_keyword_rankings(website_id))
        logger.info(f"Synced keyword rankings for website {website_id}: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to sync rankings for website {website_id}: {e}")
        raise self.retry(exc=e, countdown=120)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2)
def generate_pdf_report(self, report_id: int):
    """Generate PDF report."""
    from app.services.report_service import ReportService

    db = SessionLocal()
    try:
        service = ReportService(db)
        pdf_path = service.generate_report(report_id)
        if pdf_path:
            logger.info(f"Generated PDF report {report_id}: {pdf_path}")
        return {"report_id": report_id, "pdf_path": pdf_path}
    except Exception as e:
        logger.error(f"Failed to generate report {report_id}: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()


# ============ Scheduled Tasks ============


@celery_app.task
def scheduled_internal_audit():
    """
    Daily audit for internal sites (aiqso.io).
    Runs at 6 AM UTC.
    """
    from src.core.auditor import SEOAuditor as StandaloneAuditor

    logger.info("Starting scheduled internal audit")
    auditor = StandaloneAuditor()

    for domain in INTERNAL_DOMAINS:
        try:
            url = f"https://{domain}"
            logger.info(f"Running scheduled audit for {url}")
            result = asyncio.run(auditor.audit_url(url))

            # Store result in database
            _store_audit_result(domain, result, audit_type="scheduled_internal")

            logger.info(f"Completed audit for {domain}: score={result.overall_score}")
        except Exception as e:
            logger.error(f"Failed to audit {domain}: {e}")

    return {"audited": INTERNAL_DOMAINS}


@celery_app.task
def scheduled_customer_audits():
    """
    Weekly audit for all active customer websites.
    Runs on Sunday at 2 AM UTC.
    """
    from app.models.billing import Subscription, SubscriptionStatus

    db = SessionLocal()
    try:
        # Get all active subscriptions
        active_subs = db.query(Subscription).filter(Subscription.status == SubscriptionStatus.ACTIVE).all()

        client_ids = [sub.client_id for sub in active_subs]

        # Get websites for active clients
        from app.models.website import Website

        websites = db.query(Website).filter(Website.client_id.in_(client_ids), Website.is_active.is_(True)).all()

        logger.info(f"Running scheduled audits for {len(websites)} customer websites")

        for website in websites:
            # Queue individual audit (don't block)
            run_scheduled_audit.delay(website.id)

        return {"queued_audits": len(websites)}

    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2)
def run_scheduled_audit(self, website_id: int):
    """Run a scheduled audit for a specific website."""
    from app.models.website import Website
    from src.core.auditor import SEOAuditor as StandaloneAuditor

    db = SessionLocal()
    try:
        website = db.get(Website, website_id)
        if not website:
            logger.warning(f"Website {website_id} not found")
            return

        auditor = StandaloneAuditor()
        result = asyncio.run(auditor.audit_url(f"https://{website.domain}"))

        _store_audit_result(
            website.domain,
            result,
            audit_type="scheduled_customer",
            website_id=website_id,
            client_id=website.client_id,
        )

        logger.info(f"Completed scheduled audit for {website.domain}: score={result.overall_score}")

    except Exception as e:
        logger.error(f"Failed scheduled audit for website {website_id}: {e}")
        raise self.retry(exc=e, countdown=300)  # Retry in 5 minutes
    finally:
        db.close()


@celery_app.task
def process_scheduled_audits():
    """
    Process customer-configured audit schedules.
    Runs hourly to check for any due audits.
    """
    from app.models.website import AuditSchedule

    db = SessionLocal()
    try:
        now = datetime.now(UTC)
        current_hour = now.hour
        current_day = now.weekday()  # 0=Monday, 6=Sunday

        # Find websites with schedules due now
        due_schedules = (
            db.query(AuditSchedule).filter(AuditSchedule.is_active.is_(True), AuditSchedule.hour == current_hour).all()
        )

        audits_queued = 0
        for schedule in due_schedules:
            # Check frequency
            should_run = False

            if (
                schedule.frequency == "daily"
                or (schedule.frequency == "weekly" and current_day == schedule.day_of_week)
                or (schedule.frequency == "monthly" and now.day == schedule.day_of_month)
            ):
                should_run = True

            if should_run:
                run_scheduled_audit.delay(schedule.website_id)
                audits_queued += 1

                # Update last run time
                schedule.last_run_at = now
                db.commit()

        logger.info(f"Processed scheduled audits: {audits_queued} queued")
        return {"audits_queued": audits_queued}

    finally:
        db.close()


@celery_app.task
def capture_daily_scores():
    """
    Capture daily SEO scores for all active websites.
    Used for historical tracking and trend analysis.
    """
    from app.models.website import ScoreHistory, Website

    db = SessionLocal()
    try:
        websites = db.query(Website).filter(Website.is_active.is_(True)).all()

        captured = 0
        for website in websites:
            if website.last_audit_score is not None:
                score_entry = ScoreHistory(
                    website_id=website.id, score=website.last_audit_score, captured_at=datetime.now(UTC)
                )
                db.add(score_entry)
                captured += 1

        db.commit()
        logger.info(f"Captured daily scores for {captured} websites")
        return {"scores_captured": captured}

    finally:
        db.close()


@celery_app.task
def monitor_score_drops():
    """
    Monitor for significant score drops and send alerts.
    Runs every 6 hours.
    """
    from app.models.website import ScoreHistory, Website

    db = SessionLocal()
    try:
        # Look at score changes in the last 7 days
        one_week_ago = datetime.now(UTC) - timedelta(days=7)

        websites = db.query(Website).filter(Website.is_active.is_(True), Website.last_audit_score != None).all()

        alerts = []
        for website in websites:
            # Get oldest score from last week
            old_score = (
                db.query(ScoreHistory)
                .filter(ScoreHistory.website_id == website.id, ScoreHistory.captured_at >= one_week_ago)
                .order_by(ScoreHistory.captured_at.asc())
                .first()
            )

            if old_score and website.last_audit_score:
                drop = old_score.score - website.last_audit_score

                # Alert if score dropped by 10+ points
                if drop >= 10:
                    alerts.append(
                        {
                            "website_id": website.id,
                            "domain": website.domain,
                            "old_score": old_score.score,
                            "new_score": website.last_audit_score,
                            "drop": drop,
                        }
                    )

                    # TODO: Send notification (email, Slack, etc.)
                    logger.warning(
                        f"Score drop detected: {website.domain} "
                        f"dropped {drop} points ({old_score.score} -> {website.last_audit_score})"
                    )

        return {"alerts": len(alerts), "details": alerts}

    finally:
        db.close()


def _store_audit_result(
    domain: str, result, audit_type: str = "manual", website_id: int = None, client_id: int = None
):
    """Helper to store audit results in the database."""
    from app.models.audit import Audit, AuditStatus
    from app.models.website import Website

    db = SessionLocal()
    try:
        # Find or create website
        website = db.query(Website).filter(Website.domain == domain).first()
        if not website:
            website = Website(domain=domain, client_id=client_id, is_active=True)
            db.add(website)
            db.flush()

        # Create audit record
        audit = Audit(
            website_id=website.id,
            url_audited=f"https://{domain}",
            status=AuditStatus.COMPLETED,
            overall_score=result.overall_score,
            issues_found=len([c for c in result.checks if not c.passed and c.severity in ("error", "critical")]),
            warnings_found=len([c for c in result.checks if not c.passed and c.severity == "warning"]),
            configuration_score=result.configuration_score,
            meta_score=result.meta_score,
            content_score=result.content_score,
            performance_score=result.performance_score,
            pages_crawled=1,
            completed_at=datetime.now(UTC),
        )
        db.add(audit)

        # Update website score
        website.last_audit_score = result.overall_score
        website.last_audit_at = datetime.now(UTC)

        db.commit()

    finally:
        db.close()

"""
Customer Portal API Router

Public-facing endpoints for customers to view their SEO data.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit import Audit, AuditStatus
from app.models.client import Client
from app.models.keyword import Keyword
from app.models.website import Website
from app.routers.billing import get_current_client

router = APIRouter(prefix="/portal", tags=["Customer Portal"])


# Response schemas
class DashboardStats(BaseModel):
    total_websites: int
    total_keywords: int
    total_audits: int
    avg_seo_score: float | None
    issues_to_fix: int
    recent_score_change: float | None


class WebsiteSummary(BaseModel):
    id: int
    domain: str
    last_audit_score: int | None
    last_audit_at: str | None
    issues_count: int
    warnings_count: int
    status: str


class AuditSummary(BaseModel):
    id: int
    url: str
    overall_score: int
    status: str
    issues_found: int
    warnings_found: int
    completed_at: str | None
    duration_seconds: float | None


class ScoreHistory(BaseModel):
    date: str
    score: int


class IssueItem(BaseModel):
    id: int
    check_name: str
    title: str
    severity: str
    category: str
    current_value: str | None
    recommendation: str | None
    status: str


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard(
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """Get dashboard overview stats."""
    # Count websites
    total_websites = db.query(Website).filter(Website.client_id == client.id).count()

    # Count keywords
    total_keywords = db.query(Keyword).filter(Keyword.website.has(client_id=client.id)).count()

    # Count audits
    total_audits = db.query(Audit).filter(Audit.website.has(client_id=client.id)).count()

    # Average score from latest audits per website
    websites = db.query(Website).filter(Website.client_id == client.id).all()
    scores = [w.last_audit_score for w in websites if w.last_audit_score is not None]
    avg_score = sum(scores) / len(scores) if scores else None

    # Issues to fix (from tracked issues)
    from app.models.worklog import IssueTracker, WorkStatus

    issues_count = (
        db.query(IssueTracker)
        .filter(IssueTracker.client_id == client.id, IssueTracker.status != WorkStatus.COMPLETED)
        .count()
    )

    # Score change (compare to 30 days ago)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    old_audits = (
        db.query(Audit)
        .filter(
            Audit.website.has(client_id=client.id),
            Audit.completed_at <= thirty_days_ago,
            Audit.status == AuditStatus.COMPLETED,
        )
        .order_by(Audit.completed_at.desc())
        .limit(len(websites))
        .all()
    )

    old_scores = [a.overall_score for a in old_audits if a.overall_score]
    old_avg = sum(old_scores) / len(old_scores) if old_scores else None
    score_change = (avg_score - old_avg) if (avg_score and old_avg) else None

    return DashboardStats(
        total_websites=total_websites,
        total_keywords=total_keywords,
        total_audits=total_audits,
        avg_seo_score=round(avg_score, 1) if avg_score else None,
        issues_to_fix=issues_count,
        recent_score_change=round(score_change, 1) if score_change else None,
    )


@router.get("/websites", response_model=list[WebsiteSummary])
def list_websites(
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """List all websites with summary stats."""
    websites = db.query(Website).filter(Website.client_id == client.id).order_by(Website.created_at.desc()).all()

    results = []
    for site in websites:
        # Get latest audit
        latest_audit = (
            db.query(Audit)
            .filter(Audit.website_id == site.id, Audit.status == AuditStatus.COMPLETED)
            .order_by(Audit.completed_at.desc())
            .first()
        )

        results.append(
            WebsiteSummary(
                id=site.id,
                domain=site.domain,
                last_audit_score=latest_audit.overall_score if latest_audit else None,
                last_audit_at=latest_audit.completed_at.isoformat()
                if latest_audit and latest_audit.completed_at
                else None,
                issues_count=latest_audit.issues_found if latest_audit else 0,
                warnings_count=latest_audit.warnings_found if latest_audit else 0,
                status="healthy"
                if (latest_audit and latest_audit.overall_score and latest_audit.overall_score >= 80)
                else "needs_attention",
            )
        )

    return results


@router.get("/websites/{website_id}/audits", response_model=list[AuditSummary])
def list_website_audits(
    website_id: int,
    limit: int = Query(20, le=100),
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """List audits for a specific website."""
    # Verify ownership
    website = db.query(Website).filter(Website.id == website_id, Website.client_id == client.id).first()

    if not website:
        raise HTTPException(status_code=404, detail="Website not found")

    audits = db.query(Audit).filter(Audit.website_id == website_id).order_by(Audit.created_at.desc()).limit(limit).all()

    return [
        AuditSummary(
            id=a.id,
            url=a.url_audited,
            overall_score=a.overall_score or 0,
            status=a.status.value,
            issues_found=a.issues_found or 0,
            warnings_found=a.warnings_found or 0,
            completed_at=a.completed_at.isoformat() if a.completed_at else None,
            duration_seconds=a.duration_seconds,
        )
        for a in audits
    ]


@router.get("/websites/{website_id}/score-history", response_model=list[ScoreHistory])
def get_score_history(
    website_id: int,
    days: int = Query(30, le=365),
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """Get score history for a website."""
    # Verify ownership
    website = db.query(Website).filter(Website.id == website_id, Website.client_id == client.id).first()

    if not website:
        raise HTTPException(status_code=404, detail="Website not found")

    since = datetime.utcnow() - timedelta(days=days)

    audits = (
        db.query(Audit)
        .filter(Audit.website_id == website_id, Audit.status == AuditStatus.COMPLETED, Audit.completed_at >= since)
        .order_by(Audit.completed_at.asc())
        .all()
    )

    return [
        ScoreHistory(
            date=a.completed_at.strftime("%Y-%m-%d"),
            score=a.overall_score or 0,
        )
        for a in audits
    ]


@router.get("/websites/{website_id}/issues", response_model=list[IssueItem])
def list_website_issues(
    website_id: int,
    status: str | None = None,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """List SEO issues for a website."""
    from app.models.worklog import IssueTracker, WorkStatus

    # Verify ownership
    website = db.query(Website).filter(Website.id == website_id, Website.client_id == client.id).first()

    if not website:
        raise HTTPException(status_code=404, detail="Website not found")

    query = db.query(IssueTracker).filter(IssueTracker.website_id == website_id)

    if status:
        query = query.filter(IssueTracker.status == WorkStatus(status))

    issues = query.order_by(
        # Critical first, then error, warning, info
        IssueTracker.severity.desc(),
        IssueTracker.created_at.desc(),
    ).all()

    return [
        IssueItem(
            id=i.id,
            check_name=i.check_name,
            title=i.title,
            severity=i.severity,
            category=i.category,
            current_value=i.current_value,
            recommendation=i.recommendation,
            status=i.status.value,
        )
        for i in issues
    ]


@router.get("/audits/{audit_id}")
def get_audit_details(
    audit_id: int,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """Get full audit details with all checks."""
    audit = db.query(Audit).filter(Audit.id == audit_id).first()

    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    # Verify ownership through website
    if audit.website.client_id != client.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "id": audit.id,
        "url": audit.url_audited,
        "status": audit.status.value,
        "overall_score": audit.overall_score,
        "scores": {
            "configuration": audit.configuration_score,
            "meta": audit.meta_score,
            "content": audit.content_score,
            "performance": audit.performance_score,
        },
        "issues_found": audit.issues_found,
        "warnings_found": audit.warnings_found,
        "pages_crawled": audit.pages_crawled,
        "duration_seconds": audit.duration_seconds,
        "started_at": audit.started_at.isoformat() if audit.started_at else None,
        "completed_at": audit.completed_at.isoformat() if audit.completed_at else None,
        "ai_summary": audit.ai_summary,
        "checks": [
            {
                "name": c.check_name,
                "title": c.title,
                "category": c.category.value if hasattr(c.category, "value") else c.category,
                "passed": c.passed,
                "score": c.score,
                "severity": c.severity,
                "description": c.description,
                "current_value": c.current_value,
                "expected_value": c.expected_value,
                "recommendation": c.recommendation,
            }
            for c in audit.checks
        ],
    }


@router.post("/audits/request")
def request_audit(
    website_id: int,
    url: str | None = None,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """Request a new audit for a website."""
    # Verify ownership and tier limits
    website = db.query(Website).filter(Website.id == website_id, Website.client_id == client.id).first()

    if not website:
        raise HTTPException(status_code=404, detail="Website not found")

    # Check rate limits based on tier
    client.get_tier_limits()
    today = datetime.utcnow().date()

    audits_today = (
        db.query(Audit)
        .filter(
            Audit.website.has(client_id=client.id), Audit.created_at >= datetime.combine(today, datetime.min.time())
        )
        .count()
    )

    # Simple rate limit check (you'd want more sophisticated logic)
    max_per_day = {
        "starter": 10,
        "professional": 50,
        "enterprise": 200,
        "agency": 1000,
    }
    tier_name = client.tier.value.lower()
    if audits_today >= max_per_day.get(tier_name, 10):
        raise HTTPException(status_code=429, detail=f"Daily audit limit reached ({max_per_day[tier_name]}/day)")

    # Create audit
    audit_url = url or f"https://{website.domain}"
    audit = Audit(
        website_id=website.id,
        url_audited=audit_url,
        status=AuditStatus.PENDING,
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)

    # In production, you'd queue this for background processing
    # For now, return the audit ID
    return {
        "message": "Audit requested",
        "audit_id": audit.id,
        "status": "pending",
    }


@router.get("/account")
def get_account_info(
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """Get customer account information."""
    from app.models.billing import Subscription

    subscription = (
        db.query(Subscription)
        .filter(Subscription.client_id == client.id)
        .order_by(Subscription.created_at.desc())
        .first()
    )

    limits = client.get_tier_limits()

    return {
        "client": {
            "id": client.id,
            "name": client.name,
            "email": client.email,
            "company": client.company,
        },
        "subscription": {
            "tier": client.tier.value,
            "status": subscription.status.value if subscription else "none",
            "current_period_end": subscription.current_period_end.isoformat()
            if subscription and subscription.current_period_end
            else None,
        }
        if subscription
        else None,
        "limits": limits,
        "branding": {
            "brand_name": client.brand_name,
            "brand_logo_url": client.brand_logo_url,
            "brand_primary_color": client.brand_primary_color,
        }
        if limits.get("white_label")
        else None,
    }

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models.audit import Audit, AuditStatus, AuditCheck, AuditCategory
from app.models.website import Website
from app.services.seo_auditor import SEOAuditor

router = APIRouter()


# Pydantic schemas
class AuditCreate(BaseModel):
    website_id: int
    url: Optional[HttpUrl] = None  # Specific URL or homepage
    include_lighthouse: bool = True
    include_ai_insights: bool = True
    full_site: bool = False


class AuditCheckResponse(BaseModel):
    check_name: str
    category: AuditCategory
    passed: bool
    score: Optional[int]
    severity: str
    title: str
    description: Optional[str]
    current_value: Optional[str]
    recommendation: Optional[str]

    class Config:
        from_attributes = True


class AuditResponse(BaseModel):
    id: int
    website_id: int
    status: AuditStatus
    url_audited: str
    overall_score: Optional[int]
    pages_crawled: int
    issues_found: int
    warnings_found: int
    configuration_score: Optional[int]
    meta_score: Optional[int]
    content_score: Optional[int]
    performance_score: Optional[int]
    ai_summary: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    checks: list[AuditCheckResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


class AuditSummary(BaseModel):
    id: int
    website_id: int
    domain: str
    status: AuditStatus
    overall_score: Optional[int]
    issues_found: int
    created_at: datetime

    class Config:
        from_attributes = True


# Background task for running audit
async def run_audit_task(audit_id: int, include_lighthouse: bool, include_ai: bool):
    """Background task to run SEO audit."""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        auditor = SEOAuditor(db)
        await auditor.run_audit(audit_id, include_lighthouse, include_ai)
    finally:
        db.close()


# Endpoints
@router.post("/", response_model=AuditResponse, status_code=status.HTTP_201_CREATED)
async def create_audit(
    audit_request: AuditCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start a new SEO audit for a website."""
    # Get website
    website = db.query(Website).filter(Website.id == audit_request.website_id).first()
    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found"
        )

    # Determine URL to audit
    url = str(audit_request.url) if audit_request.url else website.url

    # Create audit record
    audit = Audit(
        website_id=website.id,
        url_audited=url,
        is_full_site=audit_request.full_site,
        status=AuditStatus.PENDING,
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)

    # Start audit in background
    background_tasks.add_task(
        run_audit_task,
        audit.id,
        audit_request.include_lighthouse,
        audit_request.include_ai_insights,
    )

    return AuditResponse(**audit.__dict__, checks=[])


@router.get("/", response_model=list[AuditSummary])
async def list_audits(
    website_id: Optional[int] = None,
    status: Optional[AuditStatus] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List all audits."""
    query = db.query(Audit).join(Website)

    if website_id:
        query = query.filter(Audit.website_id == website_id)
    if status:
        query = query.filter(Audit.status == status)

    audits = query.order_by(Audit.created_at.desc()).offset(skip).limit(limit).all()

    return [
        AuditSummary(
            id=a.id,
            website_id=a.website_id,
            domain=a.website.domain,
            status=a.status,
            overall_score=a.overall_score,
            issues_found=a.issues_found,
            created_at=a.created_at,
        )
        for a in audits
    ]


@router.get("/{audit_id}", response_model=AuditResponse)
async def get_audit(audit_id: int, db: Session = Depends(get_db)):
    """Get a specific audit with all checks."""
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit not found"
        )

    checks = [AuditCheckResponse(**c.__dict__) for c in audit.checks]

    return AuditResponse(**audit.__dict__, checks=checks)


@router.get("/{audit_id}/checks", response_model=list[AuditCheckResponse])
async def get_audit_checks(
    audit_id: int,
    category: Optional[AuditCategory] = None,
    passed: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Get checks for a specific audit with filtering."""
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit not found"
        )

    checks = audit.checks
    if category:
        checks = [c for c in checks if c.category == category]
    if passed is not None:
        checks = [c for c in checks if c.passed == passed]

    return [AuditCheckResponse(**c.__dict__) for c in checks]


@router.post("/{audit_id}/retry", response_model=AuditResponse)
async def retry_audit(
    audit_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Retry a failed audit."""
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit not found"
        )

    if audit.status not in [AuditStatus.FAILED, AuditStatus.COMPLETED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only retry failed or completed audits"
        )

    # Reset audit
    audit.status = AuditStatus.PENDING
    audit.error_message = None
    audit.started_at = None
    audit.completed_at = None

    # Clear old checks
    for check in audit.checks:
        db.delete(check)

    db.commit()
    db.refresh(audit)

    # Start audit in background
    background_tasks.add_task(run_audit_task, audit.id, True, True)

    return AuditResponse(**audit.__dict__, checks=[])


@router.delete("/{audit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audit(audit_id: int, db: Session = Depends(get_db)):
    """Delete an audit."""
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit not found"
        )

    db.delete(audit)
    db.commit()

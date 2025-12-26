"""
Work Log API Router

Endpoints for tracking work performed for customers.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.client import Client
from app.models.worklog import IssueTracker, Project, ProjectWorkItem, WorkCategory, WorkLog, WorkStatus
from app.routers.billing import get_current_client

router = APIRouter(prefix="/worklog", tags=["Work Log"])


# Schemas
class WorkLogCreate(BaseModel):
    title: str
    description: str | None = None
    category: str = "other"
    website_id: int | None = None
    estimated_minutes: int | None = None
    is_billable: bool = True
    hourly_rate_cents: int = 15000
    fixed_price_cents: int | None = None


class WorkLogUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    actual_minutes: int | None = None
    customer_notes: str | None = None
    internal_notes: str | None = None


class WorkLogResponse(BaseModel):
    id: int
    title: str
    description: str | None
    category: str
    status: str
    estimated_minutes: int | None
    actual_minutes: int | None
    is_billable: bool
    billable_amount: float
    started_at: str | None
    completed_at: str | None
    customer_notes: str | None


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    scope_document: str | None = None
    budget_cents: int | None = None
    is_fixed_price: bool = False
    start_date: str | None = None
    due_date: str | None = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: str | None
    status: str
    budget: float | None
    is_fixed_price: bool
    total_logged_hours: float
    total_billable: float
    start_date: str | None
    due_date: str | None


class IssueCreate(BaseModel):
    website_id: int
    check_name: str
    title: str
    description: str | None = None
    severity: str = "warning"
    category: str
    current_value: str | None = None
    expected_value: str | None = None
    recommendation: str | None = None
    fix_price_cents: int | None = None


class IssueResponse(BaseModel):
    id: int
    check_name: str
    title: str
    description: str | None
    severity: str
    category: str
    status: str
    current_value: str | None
    expected_value: str | None
    recommendation: str | None
    fix_price: float | None
    resolved_at: str | None


# Work Log endpoints
@router.post("/entries", response_model=WorkLogResponse)
def create_work_log(
    entry: WorkLogCreate,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """Create a new work log entry."""
    work_log = WorkLog(
        client_id=client.id,
        website_id=entry.website_id,
        title=entry.title,
        description=entry.description,
        category=WorkCategory(entry.category),
        status=WorkStatus.PENDING,
        estimated_minutes=entry.estimated_minutes,
        is_billable=entry.is_billable,
        hourly_rate_cents=entry.hourly_rate_cents,
        fixed_price_cents=entry.fixed_price_cents,
    )
    db.add(work_log)
    db.commit()
    db.refresh(work_log)

    return format_work_log(work_log)


@router.get("/entries", response_model=list[WorkLogResponse])
def list_work_logs(
    status: str | None = None,
    category: str | None = None,
    website_id: int | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """List work log entries."""
    query = db.query(WorkLog).filter(WorkLog.client_id == client.id)

    if status:
        query = query.filter(WorkLog.status == WorkStatus(status))
    if category:
        query = query.filter(WorkLog.category == WorkCategory(category))
    if website_id:
        query = query.filter(WorkLog.website_id == website_id)

    entries = query.order_by(WorkLog.created_at.desc()).offset(offset).limit(limit).all()
    return [format_work_log(e) for e in entries]


@router.get("/entries/{entry_id}", response_model=WorkLogResponse)
def get_work_log(
    entry_id: int,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """Get a specific work log entry."""
    entry = db.query(WorkLog).filter(WorkLog.id == entry_id, WorkLog.client_id == client.id).first()

    if not entry:
        raise HTTPException(status_code=404, detail="Work log not found")

    return format_work_log(entry)


@router.patch("/entries/{entry_id}", response_model=WorkLogResponse)
def update_work_log(
    entry_id: int,
    update: WorkLogUpdate,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """Update a work log entry."""
    entry = db.query(WorkLog).filter(WorkLog.id == entry_id, WorkLog.client_id == client.id).first()

    if not entry:
        raise HTTPException(status_code=404, detail="Work log not found")

    if update.title:
        entry.title = update.title
    if update.description:
        entry.description = update.description
    if update.status:
        entry.status = WorkStatus(update.status)
        if update.status == "in_progress" and not entry.started_at:
            entry.started_at = datetime.utcnow()
        elif update.status == "completed" and not entry.completed_at:
            entry.completed_at = datetime.utcnow()
    if update.actual_minutes is not None:
        entry.actual_minutes = update.actual_minutes
    if update.customer_notes:
        entry.customer_notes = update.customer_notes
    if update.internal_notes:
        entry.internal_notes = update.internal_notes

    db.commit()
    db.refresh(entry)

    return format_work_log(entry)


@router.post("/entries/{entry_id}/start")
def start_work(
    entry_id: int,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """Start working on an entry (sets started_at)."""
    entry = db.query(WorkLog).filter(WorkLog.id == entry_id, WorkLog.client_id == client.id).first()

    if not entry:
        raise HTTPException(status_code=404, detail="Work log not found")

    entry.status = WorkStatus.IN_PROGRESS
    entry.started_at = datetime.utcnow()
    db.commit()

    return {"message": "Work started", "started_at": entry.started_at.isoformat()}


@router.post("/entries/{entry_id}/complete")
def complete_work(
    entry_id: int,
    actual_minutes: int | None = None,
    notes: str | None = None,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """Mark work as completed."""
    entry = db.query(WorkLog).filter(WorkLog.id == entry_id, WorkLog.client_id == client.id).first()

    if not entry:
        raise HTTPException(status_code=404, detail="Work log not found")

    entry.status = WorkStatus.COMPLETED
    entry.completed_at = datetime.utcnow()

    if actual_minutes is not None:
        entry.actual_minutes = actual_minutes
    elif entry.started_at:
        # Auto-calculate from started_at
        entry.actual_minutes = int((entry.completed_at - entry.started_at).total_seconds() / 60)

    if notes:
        entry.customer_notes = notes

    db.commit()

    return {
        "message": "Work completed",
        "completed_at": entry.completed_at.isoformat(),
        "actual_minutes": entry.actual_minutes,
        "billable_amount": entry.billable_amount_dollars,
    }


# Project endpoints
@router.post("/projects", response_model=ProjectResponse)
def create_project(
    project: ProjectCreate,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """Create a new project."""
    proj = Project(
        client_id=client.id,
        name=project.name,
        description=project.description,
        scope_document=project.scope_document,
        budget_cents=project.budget_cents,
        is_fixed_price=project.is_fixed_price,
        start_date=datetime.fromisoformat(project.start_date) if project.start_date else None,
        due_date=datetime.fromisoformat(project.due_date) if project.due_date else None,
    )
    db.add(proj)
    db.commit()
    db.refresh(proj)

    return format_project(proj)


@router.get("/projects", response_model=list[ProjectResponse])
def list_projects(
    status: str | None = None,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """List projects."""
    query = db.query(Project).filter(Project.client_id == client.id)

    if status:
        query = query.filter(Project.status == WorkStatus(status))

    projects = query.order_by(Project.created_at.desc()).all()
    return [format_project(p) for p in projects]


@router.post("/projects/{project_id}/add-work/{entry_id}")
def add_work_to_project(
    project_id: int,
    entry_id: int,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """Add a work log entry to a project."""
    project = db.query(Project).filter(Project.id == project_id, Project.client_id == client.id).first()

    entry = db.query(WorkLog).filter(WorkLog.id == entry_id, WorkLog.client_id == client.id).first()

    if not project or not entry:
        raise HTTPException(status_code=404, detail="Project or entry not found")

    # Check if already added
    existing = (
        db.query(ProjectWorkItem)
        .filter(ProjectWorkItem.project_id == project_id, ProjectWorkItem.work_log_id == entry_id)
        .first()
    )

    if existing:
        raise HTTPException(status_code=400, detail="Entry already in project")

    item = ProjectWorkItem(
        project_id=project_id,
        work_log_id=entry_id,
    )
    db.add(item)
    db.commit()

    return {"message": "Work added to project"}


# Issue Tracker endpoints
@router.post("/issues", response_model=IssueResponse)
def create_issue(
    issue: IssueCreate,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """Create an issue to track."""
    tracker = IssueTracker(
        client_id=client.id,
        website_id=issue.website_id,
        check_name=issue.check_name,
        title=issue.title,
        description=issue.description,
        severity=issue.severity,
        category=issue.category,
        current_value=issue.current_value,
        expected_value=issue.expected_value,
        recommendation=issue.recommendation,
        fix_price_cents=issue.fix_price_cents,
    )
    db.add(tracker)
    db.commit()
    db.refresh(tracker)

    return format_issue(tracker)


@router.get("/issues", response_model=list[IssueResponse])
def list_issues(
    status: str | None = None,
    website_id: int | None = None,
    severity: str | None = None,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """List tracked issues."""
    query = db.query(IssueTracker).filter(IssueTracker.client_id == client.id)

    if status:
        query = query.filter(IssueTracker.status == WorkStatus(status))
    if website_id:
        query = query.filter(IssueTracker.website_id == website_id)
    if severity:
        query = query.filter(IssueTracker.severity == severity)

    issues = query.order_by(IssueTracker.created_at.desc()).all()
    return [format_issue(i) for i in issues]


@router.post("/issues/{issue_id}/resolve")
def resolve_issue(
    issue_id: int,
    notes: str | None = None,
    work_log_id: int | None = None,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """Mark an issue as resolved."""
    issue = db.query(IssueTracker).filter(IssueTracker.id == issue_id, IssueTracker.client_id == client.id).first()

    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    issue.status = WorkStatus.COMPLETED
    issue.resolved_at = datetime.utcnow()
    issue.resolution_notes = notes
    if work_log_id:
        issue.work_log_id = work_log_id

    db.commit()

    return {"message": "Issue resolved", "resolved_at": issue.resolved_at.isoformat()}


# Summary endpoints
@router.get("/summary")
def get_work_summary(
    days: int = 30,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """Get work summary for a period."""
    since = datetime.utcnow() - timedelta(days=days)

    entries = db.query(WorkLog).filter(WorkLog.client_id == client.id, WorkLog.created_at >= since).all()

    total_minutes = sum(e.actual_minutes or 0 for e in entries)
    total_billable = sum(e.billable_amount_cents for e in entries)
    completed = sum(1 for e in entries if e.status == WorkStatus.COMPLETED)

    by_category = {}
    for e in entries:
        cat = e.category.value
        if cat not in by_category:
            by_category[cat] = {"count": 0, "minutes": 0, "billable": 0}
        by_category[cat]["count"] += 1
        by_category[cat]["minutes"] += e.actual_minutes or 0
        by_category[cat]["billable"] += e.billable_amount_cents

    return {
        "period_days": days,
        "total_entries": len(entries),
        "completed_entries": completed,
        "total_hours": round(total_minutes / 60, 2),
        "total_billable": total_billable / 100,
        "by_category": by_category,
    }


# Helper functions
def format_work_log(entry: WorkLog) -> WorkLogResponse:
    return WorkLogResponse(
        id=entry.id,
        title=entry.title,
        description=entry.description,
        category=entry.category.value,
        status=entry.status.value,
        estimated_minutes=entry.estimated_minutes,
        actual_minutes=entry.actual_minutes,
        is_billable=entry.is_billable,
        billable_amount=entry.billable_amount_dollars,
        started_at=entry.started_at.isoformat() if entry.started_at else None,
        completed_at=entry.completed_at.isoformat() if entry.completed_at else None,
        customer_notes=entry.customer_notes,
    )


def format_project(proj: Project) -> ProjectResponse:
    return ProjectResponse(
        id=proj.id,
        name=proj.name,
        description=proj.description,
        status=proj.status.value,
        budget=proj.budget_cents / 100 if proj.budget_cents else None,
        is_fixed_price=proj.is_fixed_price,
        total_logged_hours=proj.total_logged_minutes / 60,
        total_billable=proj.total_billable_cents / 100,
        start_date=proj.start_date.isoformat() if proj.start_date else None,
        due_date=proj.due_date.isoformat() if proj.due_date else None,
    )


def format_issue(issue: IssueTracker) -> IssueResponse:
    return IssueResponse(
        id=issue.id,
        check_name=issue.check_name,
        title=issue.title,
        description=issue.description,
        severity=issue.severity,
        category=issue.category,
        status=issue.status.value,
        current_value=issue.current_value,
        expected_value=issue.expected_value,
        recommendation=issue.recommendation,
        fix_price=issue.fix_price_cents / 100 if issue.fix_price_cents else None,
        resolved_at=issue.resolved_at.isoformat() if issue.resolved_at else None,
    )

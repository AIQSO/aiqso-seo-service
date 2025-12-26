from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.client import Client
from app.models.report import Report, ReportStatus, ReportType

router = APIRouter()


class ReportCreate(BaseModel):
    client_id: int
    website_id: int | None = None
    report_type: ReportType
    period_start: datetime
    period_end: datetime


class ReportResponse(BaseModel):
    id: int
    client_id: int
    website_id: int | None
    report_type: ReportType
    title: str
    status: ReportStatus
    period_start: datetime
    period_end: datetime
    summary: str | None
    pdf_url: str | None
    ai_insights: str | None
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(report: ReportCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Generate a new report."""
    client = db.query(Client).filter(Client.id == report.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    title = f"{report.report_type.value.title()} Report - {report.period_start.strftime('%b %d')} to {report.period_end.strftime('%b %d, %Y')}"

    db_report = Report(
        **report.dict(),
        title=title,
        status=ReportStatus.PENDING,
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)

    # TODO: Add background task for report generation
    # background_tasks.add_task(generate_report_task, db_report.id)

    return ReportResponse(**db_report.__dict__)


@router.get("/", response_model=list[ReportResponse])
async def list_reports(
    client_id: int | None = None,
    report_type: ReportType | None = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List reports."""
    query = db.query(Report)
    if client_id:
        query = query.filter(Report.client_id == client_id)
    if report_type:
        query = query.filter(Report.report_type == report_type)

    reports = query.order_by(Report.created_at.desc()).offset(skip).limit(limit).all()
    return [ReportResponse(**r.__dict__) for r in reports]


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(report_id: int, db: Session = Depends(get_db)):
    """Get a specific report."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return ReportResponse(**report.__dict__)


@router.get("/{report_id}/download")
async def download_report(report_id: int, db: Session = Depends(get_db)):
    """Download report as PDF."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if not report.pdf_url:
        raise HTTPException(status_code=400, detail="PDF not yet generated")

    return {"pdf_url": report.pdf_url}

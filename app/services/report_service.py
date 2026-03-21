"""
Report Generation Service

Generates PDF reports using Jinja2 templates and WeasyPrint.
"""

import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.audit import Audit, AuditStatus
from app.models.client import Client
from app.models.keyword import Keyword
from app.models.report import Report, ReportStatus
from app.models.website import Website

logger = logging.getLogger(__name__)
settings = get_settings()

# Template directory
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
REPORTS_DIR = Path("/app/reports") if os.path.exists("/app") else Path("reports")


class ReportService:
    """Generates PDF reports from audit and ranking data."""

    def __init__(self, db: Session):
        self.db = db
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=True,
        )

    def generate_report(self, report_id: int) -> str | None:
        """
        Generate a PDF report and return the file path.
        Updates the report record with status and pdf_url.
        """
        report = self.db.query(Report).filter(Report.id == report_id).first()
        if not report:
            logger.error(f"Report {report_id} not found")
            return None

        try:
            report.status = ReportStatus.GENERATING
            self.db.commit()

            client = self.db.query(Client).filter(Client.id == report.client_id).first()
            if not client:
                raise ValueError(f"Client {report.client_id} not found")

            # Gather data
            context = self._build_report_context(report, client)

            # Render HTML
            html_content = self._render_html(report, context)
            report.html_content = html_content

            # Generate PDF
            pdf_path = self._render_pdf(report, html_content)
            report.pdf_url = str(pdf_path)

            # Generate summary
            report.summary = self._build_summary(context)

            report.status = ReportStatus.COMPLETED
            self.db.commit()

            logger.info(f"Generated report {report_id}: {pdf_path}")
            return str(pdf_path)

        except Exception as e:
            logger.error(f"Failed to generate report {report_id}: {e}")
            report.status = ReportStatus.FAILED
            report.summary = f"Generation failed: {str(e)}"
            self.db.commit()
            return None

    def _build_report_context(self, report: Report, client: Client) -> dict:
        """Gather all data needed for the report template."""
        websites = self.db.query(Website).filter(Website.client_id == client.id).all()

        # Get audits in the report period
        audits = (
            self.db.query(Audit)
            .filter(
                Audit.website_id.in_([w.id for w in websites]),
                Audit.status == AuditStatus.COMPLETED,
                Audit.completed_at >= report.period_start,
                Audit.completed_at <= report.period_end,
            )
            .order_by(Audit.completed_at.desc())
            .all()
        )

        # Get keywords
        keywords = (
            self.db.query(Keyword)
            .filter(Keyword.website_id.in_([w.id for w in websites]), Keyword.is_active.is_(True))
            .all()
        )

        # Calculate summary stats
        scores = [a.overall_score for a in audits if a.overall_score]
        avg_score = sum(scores) / len(scores) if scores else 0
        total_issues = sum(a.issues_found or 0 for a in audits)

        return {
            "client": client,
            "report": report,
            "websites": websites,
            "audits": audits,
            "keywords": keywords,
            "avg_score": round(avg_score, 1),
            "total_issues": total_issues,
            "total_audits": len(audits),
            "generated_at": datetime.now(UTC),
        }

    def _render_html(self, report: Report, context: dict) -> str:
        """Render the report HTML from template."""
        template_name = f"report_{report.report_type.value}.html"

        # Fall back to default template if specific one doesn't exist
        try:
            template = self.env.get_template(template_name)
        except Exception:
            template = self.env.get_template("report_default.html")

        return template.render(**context)

    def _render_pdf(self, report: Report, html_content: str) -> Path:
        """Convert HTML to PDF using WeasyPrint."""
        from weasyprint import HTML

        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"report_{report.id}_{report.report_type.value}_{datetime.now(UTC).strftime('%Y%m%d')}.pdf"
        pdf_path = REPORTS_DIR / filename

        HTML(string=html_content).write_pdf(str(pdf_path))
        return pdf_path

    def _build_summary(self, context: dict) -> str:
        """Build a text summary of the report."""
        return (
            f"Report covering {context['total_audits']} audits across "
            f"{len(context['websites'])} website(s). "
            f"Average SEO score: {context['avg_score']}/100. "
            f"Total issues found: {context['total_issues']}."
        )

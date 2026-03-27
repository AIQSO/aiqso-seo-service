"""
Notification service for SEO score alerts and daily summaries.

Supports three independent channels: Slack webhook, n8n webhook, and SMTP email.
Each channel is attempted in isolation — a failure in one does not block the others.
"""

import logging
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

# Shared timeout for outbound HTTP calls (connect + read)
_HTTP_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)


class NotificationService:
    """Send alerts via multiple channels: Slack, n8n, and SMTP email."""

    def __init__(self) -> None:
        self._settings = get_settings()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def send_score_drop_alert(
        self,
        website_domain: str,
        old_score: float,
        new_score: float,
        drop_amount: float,
        audit_url: str,
    ) -> dict[str, bool]:
        """
        Send a score-drop alert to every configured channel.

        Returns a dict mapping channel name -> success boolean so callers
        can log aggregate outcomes without raising.
        """
        subject = f"SEO Score Drop Alert: {website_domain} dropped {drop_amount:.0f} points"

        slack_message = _build_slack_score_drop(
            website_domain, old_score, new_score, drop_amount, audit_url
        )
        n8n_payload = {
            "event": "score_drop",
            "domain": website_domain,
            "old_score": old_score,
            "new_score": new_score,
            "drop_amount": drop_amount,
            "audit_url": audit_url,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        email_body = _build_email_score_drop(
            website_domain, old_score, new_score, drop_amount, audit_url
        )

        results: dict[str, bool] = {}
        results["slack"] = await self._send_slack_webhook(slack_message)
        results["n8n"] = await self._send_n8n_webhook(n8n_payload)
        results["email"] = await self._send_email(subject, email_body)

        sent = [ch for ch, ok in results.items() if ok]
        skipped = [ch for ch, ok in results.items() if ok is None]
        failed = [ch for ch, ok in results.items() if ok is False]

        if sent:
            logger.info(
                "Score drop alert sent for %s via %s", website_domain, ", ".join(sent)
            )
        if failed:
            logger.warning(
                "Score drop alert delivery failed for %s on channels: %s",
                website_domain,
                ", ".join(failed),
            )
        if not sent and not skipped:
            logger.warning(
                "No notification channels configured for score drop alert (%s).",
                website_domain,
            )

        return results

    async def send_daily_summary(
        self,
        sites_audited: int,
        average_score: float,
        score_changes: list[dict[str, Any]],
        new_issues: int,
    ) -> dict[str, bool]:
        """
        Send the daily summary to every configured channel.

        score_changes: list of dicts with keys: domain, old_score, new_score, delta
        """
        subject = f"Daily SEO Summary — {datetime.utcnow().strftime('%Y-%m-%d')}"

        slack_message = _build_slack_daily_summary(
            sites_audited, average_score, score_changes, new_issues
        )
        n8n_payload = {
            "event": "daily_summary",
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "sites_audited": sites_audited,
            "average_score": round(average_score, 1),
            "score_changes": score_changes,
            "new_issues": new_issues,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        email_body = _build_email_daily_summary(
            sites_audited, average_score, score_changes, new_issues
        )

        results: dict[str, bool] = {}
        results["slack"] = await self._send_slack_webhook(slack_message)
        results["n8n"] = await self._send_n8n_webhook(n8n_payload)
        results["email"] = await self._send_email(subject, email_body)

        sent = [ch for ch, ok in results.items() if ok]
        if sent:
            logger.info("Daily summary sent via %s", ", ".join(sent))
        elif all(v is None for v in results.values()):
            logger.debug("Daily summary skipped — no notification channels configured.")

        return results

    # ------------------------------------------------------------------
    # Private channel implementations
    # ------------------------------------------------------------------

    async def _send_slack_webhook(self, message: dict[str, Any]) -> bool | None:
        """
        POST to the Slack Incoming Webhook URL.

        Returns True on success, False on delivery failure, None if unconfigured.
        """
        url = self._settings.slack_webhook_url
        if not url:
            return None

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.post(url, json=message)
                response.raise_for_status()
            return True
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Slack webhook returned HTTP %s: %s",
                exc.response.status_code,
                exc.response.text[:200],
            )
            return False
        except httpx.RequestError as exc:
            logger.error("Slack webhook request failed: %s", exc)
            return False

    async def _send_n8n_webhook(self, payload: dict[str, Any]) -> bool | None:
        """
        POST JSON payload to the n8n webhook URL.

        Returns True on success, False on delivery failure, None if unconfigured.
        """
        url = self._settings.n8n_webhook_url
        if not url:
            return None

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
            return True
        except httpx.HTTPStatusError as exc:
            logger.error(
                "n8n webhook returned HTTP %s: %s",
                exc.response.status_code,
                exc.response.text[:200],
            )
            return False
        except httpx.RequestError as exc:
            logger.error("n8n webhook request failed: %s", exc)
            return False

    async def _send_email(self, subject: str, body: str) -> bool | None:
        """
        Send a plain-text email via SMTP (STARTTLS on port 587, or SSL on 465).

        Returns True on success, False on delivery failure, None if unconfigured.

        Required env vars: SMTP_HOST, SMTP_USER, SMTP_PASS, ALERT_EMAIL.
        Optional: SMTP_PORT (default 587), SMTP_FROM.
        """
        cfg = self._settings
        if not all([cfg.smtp_host, cfg.smtp_user, cfg.smtp_pass, cfg.alert_email]):
            return None

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = cfg.smtp_from or cfg.smtp_user
        msg["To"] = cfg.alert_email
        # Sanitize body: strip any null bytes that could corrupt the MIME stream
        safe_body = body.replace("\x00", "")
        msg.attach(MIMEText(safe_body, "plain", "utf-8"))

        try:
            if cfg.smtp_port == 465:
                # Implicit TLS
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, context=context, timeout=15) as server:
                    server.login(cfg.smtp_user, cfg.smtp_pass)
                    server.sendmail(msg["From"], [cfg.alert_email], msg.as_string())
            else:
                # STARTTLS (port 587 or custom)
                context = ssl.create_default_context()
                with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=15) as server:
                    server.ehlo()
                    server.starttls(context=context)
                    server.ehlo()
                    server.login(cfg.smtp_user, cfg.smtp_pass)
                    server.sendmail(msg["From"], [cfg.alert_email], msg.as_string())
            return True
        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP authentication failed for user %s", cfg.smtp_user)
            return False
        except (smtplib.SMTPException, OSError) as exc:
            logger.error("SMTP send failed: %s", exc)
            return False


# ------------------------------------------------------------------
# Message builders (pure functions, easy to test)
# ------------------------------------------------------------------


def _build_slack_score_drop(
    domain: str,
    old_score: float,
    new_score: float,
    drop: float,
    audit_url: str,
) -> dict[str, Any]:
    severity = ":rotating_light:" if drop >= 20 else ":warning:"
    return {
        "text": f"{severity} SEO Score Drop: *{domain}* dropped {drop:.0f} points",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{severity} SEO Score Drop Detected",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Domain:*\n{domain}"},
                    {"type": "mrkdwn", "text": f"*Drop:*\n{drop:.0f} points"},
                    {"type": "mrkdwn", "text": f"*Previous Score:*\n{old_score:.0f}"},
                    {"type": "mrkdwn", "text": f"*Current Score:*\n{new_score:.0f}"},
                ],
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Audit"},
                        "url": audit_url,
                        "style": "danger",
                    }
                ],
            },
        ],
    }


def _build_slack_daily_summary(
    sites_audited: int,
    average_score: float,
    score_changes: list[dict[str, Any]],
    new_issues: int,
) -> dict[str, Any]:
    date_str = datetime.utcnow().strftime("%B %d, %Y")
    change_lines = []
    for change in score_changes[:10]:  # cap at 10 lines
        delta = change.get("delta", 0)
        arrow = ":arrow_up:" if delta > 0 else ":arrow_down:"
        change_lines.append(
            f"{arrow} {change['domain']}: {change['old_score']:.0f} -> {change['new_score']:.0f} ({delta:+.0f})"
        )
    changes_text = "\n".join(change_lines) if change_lines else "_No score changes_"

    return {
        "text": f"Daily SEO Summary — {date_str}",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"Daily SEO Summary — {date_str}"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Sites Audited:*\n{sites_audited}"},
                    {"type": "mrkdwn", "text": f"*Average Score:*\n{average_score:.1f}"},
                    {"type": "mrkdwn", "text": f"*New Issues Found:*\n{new_issues}"},
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Score Changes:*\n{changes_text}"},
            },
        ],
    }


def _build_email_score_drop(
    domain: str,
    old_score: float,
    new_score: float,
    drop: float,
    audit_url: str,
) -> str:
    return (
        f"SEO Score Drop Alert\n"
        f"{'=' * 40}\n\n"
        f"Domain:         {domain}\n"
        f"Previous Score: {old_score:.0f}\n"
        f"Current Score:  {new_score:.0f}\n"
        f"Drop:           {drop:.0f} points\n\n"
        f"View the full audit report:\n{audit_url}\n\n"
        f"--\nAIQSO SEO Service"
    )


def _build_email_daily_summary(
    sites_audited: int,
    average_score: float,
    score_changes: list[dict[str, Any]],
    new_issues: int,
) -> str:
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    lines = [
        f"Daily SEO Summary — {date_str}",
        "=" * 40,
        "",
        f"Sites Audited:  {sites_audited}",
        f"Average Score:  {average_score:.1f}",
        f"New Issues:     {new_issues}",
        "",
        "Score Changes:",
        "-" * 20,
    ]
    if score_changes:
        for change in score_changes:
            delta = change.get("delta", 0)
            sign = "+" if delta >= 0 else ""
            lines.append(
                f"  {change['domain']}: {change['old_score']:.0f} -> {change['new_score']:.0f} ({sign}{delta:.0f})"
            )
    else:
        lines.append("  No score changes recorded.")
    lines += ["", "--", "AIQSO SEO Service"]
    return "\n".join(lines)

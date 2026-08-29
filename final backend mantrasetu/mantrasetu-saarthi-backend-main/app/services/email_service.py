"""
Email service for MantraSetu.
Behaviour:
  - SMTP_USERNAME + SMTP_PASSWORD set in .env -> real SMTP dispatch
  - Either missing -> console-fallback mode
No hardcoded credentials in this file.
"""

import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger("mantrasetu.email")


def _build_verification_email(to_email: str, verify_url: str) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Verify your MantraSetu account"
    msg["From"] = settings.SMTP_USERNAME or "noreply@mantrasetu.in"
    msg["To"] = to_email
    text_body = (
        "Namaste!\n\n"
        "Please verify your MantraSetu account:\n\n"
        + verify_url + "\n\n"
        "This link expires in 24 hours.\n\n"
        "-- MantraSetu Team"
    )
    html_body = (
        "<html><body style='font-family:Arial,sans-serif;padding:32px;'>"
        "<h2 style='color:#b05c1e;'>Namaste from MantraSetu</h2>"
        "<p>Please verify your email to activate your account.</p>"
        "<a href='" + verify_url + "' style='display:inline-block;padding:14px 28px;"
        "background:#b05c1e;color:#fff;border-radius:8px;text-decoration:none;font-weight:bold;'>"
        "Verify My Account</a>"
        "<p>Or copy: " + verify_url + "</p>"
        "<p style='color:#aaa;font-size:12px;'>Link expires in 24 hours.</p>"
        "</body></html>"
    )
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))
    return msg


async def send_verification_email(to_email: str, verify_url: str) -> bool:
    """
    Send a verification email.
    Returns True on success (including console-fallback).
    Returns False on SMTP failure.
    """
    smtp_user = settings.SMTP_USERNAME
    smtp_pass = settings.SMTP_PASSWORD

    # CONSOLE-FALLBACK: no credentials configured
    if not smtp_user or not smtp_pass:
        logger.warning(
            "[EMAIL-SERVICE] SMTP_USERNAME/SMTP_PASSWORD not set in .env -- "
            "running in CONSOLE-FALLBACK mode."
        )
        sep = "=" * 70
        print(sep)
        print("[EMAIL-CONSOLE-FALLBACK] Email would be sent to:", to_email)
        print("[EMAIL-CONSOLE-FALLBACK] Subject: Verify your MantraSetu account")
        print("[EMAIL-CONSOLE-FALLBACK] Verification link:", verify_url)
        print(sep)
        logger.info(
            "[EMAIL-SERVICE] CONSOLE-FALLBACK dispatched | to=%s | link=%s",
            to_email, verify_url,
        )
        return True

    # REAL SMTP DISPATCH
    msg = _build_verification_email(to_email, verify_url)
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())
        logger.info(
            "[EMAIL-SERVICE] SMTP dispatch SUCCESS | to=%s | server=%s:%s",
            to_email, settings.SMTP_SERVER, settings.SMTP_PORT,
        )
        print(f"[EMAIL-SERVICE] Verification email sent via SMTP to {to_email}")
        return True
    except smtplib.SMTPAuthenticationError as exc:
        logger.error("[EMAIL-SERVICE] SMTP auth FAILED | user=%s | error=%s", smtp_user, exc)
        print(f"[EMAIL-SERVICE] SMTP auth failed for user={smtp_user}: {exc}")
        return False
    except Exception as exc:
        logger.error("[EMAIL-SERVICE] SMTP dispatch FAILED | to=%s | error=%s", to_email, exc)
        print(f"[EMAIL-SERVICE] Unexpected SMTP error to {to_email}: {exc}")
        return False


# ──────────────────────────────────────────────────────────────────────────────
# HELPER: send any email (shared SMTP / fallback logic)
# ──────────────────────────────────────────────────────────────────────────────
def _smtp_send(subject: str, to_email: str, text_body: str, html_body: str) -> bool:
    """Internal helper: send via SMTP or fall back to console."""
    smtp_user = settings.SMTP_USERNAME
    smtp_pass = settings.SMTP_PASSWORD

    if not smtp_user or not smtp_pass:
        sep = "=" * 70
        print(sep)
        print("[EMAIL-CONSOLE-FALLBACK] Email would be sent to:", to_email)
        print("[EMAIL-CONSOLE-FALLBACK] Subject:", subject)
        print("[EMAIL-CONSOLE-FALLBACK] Body preview:", text_body[:300])
        print(sep)
        logger.info(
            "[EMAIL-SERVICE] CONSOLE-FALLBACK | to=%s | subject=%s",
            to_email, subject,
        )
        return True

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())
        logger.info(
            "[EMAIL-SERVICE] SMTP dispatch SUCCESS | to=%s | subject=%s",
            to_email, subject,
        )
        print(f"[EMAIL-SERVICE] Email sent via SMTP to {to_email} | subject: {subject}")
        return True
    except smtplib.SMTPAuthenticationError as exc:
        logger.error("[EMAIL-SERVICE] SMTP auth FAILED | %s", exc)
        print(f"[EMAIL-SERVICE] SMTP auth failed: {exc}")
        return False
    except Exception as exc:
        logger.error("[EMAIL-SERVICE] SMTP dispatch FAILED | to=%s | %s", to_email, exc)
        print(f"[EMAIL-SERVICE] Unexpected SMTP error to {to_email}: {exc}")
        return False


# ──────────────────────────────────────────────────────────────────────────────
# 1. DRAFT RESUME EMAIL
# ──────────────────────────────────────────────────────────────────────────────
async def send_draft_resume_email(to_email: str, draft_url: str, pandit_name: str = "") -> bool:
    """
    Send the 'resume your draft' email when a pandit clicks 'Save as Draft'.
    draft_url should be the full URL:  <BASE_URL>/signup?role=pandit&draft=<uuid>
    """
    greeter = f"Namaste {pandit_name}!" if pandit_name else "Namaste!"
    subject = "Your MantraSetu Pandit Registration — Draft Saved"

    text_body = (
        greeter + "\n\n"
        "Your Panditji registration form has been saved as a draft.\n\n"
        "Resume where you left off:\n\n"
        + draft_url + "\n\n"
        "This link is available whenever you are ready to continue.\n\n"
        "-- MantraSetu Team"
    )
    html_body = (
        "<html><body style='font-family:Arial,sans-serif;background:#fdf6f0;padding:32px;'>"
        "<div style='max-width:520px;margin:auto;background:#fff;border-radius:12px;"
        "padding:32px;box-shadow:0 2px 12px rgba(0,0,0,0.08);'>"
        "<h2 style='color:#b05c1e;margin-top:0;'>" + greeter + "</h2>"
        "<p>Your <strong>Panditji registration draft</strong> has been saved successfully.</p>"
        "<p>Click the button below to pick up right where you left off:</p>"
        "<a href='" + draft_url + "' style='display:inline-block;margin:16px 0;padding:14px 28px;"
        "background:#b05c1e;color:#fff;border-radius:8px;text-decoration:none;"
        "font-weight:bold;'>Resume My Application</a>"
        "<p style='color:#888;font-size:13px;'>Or copy this link:<br/>"
        "<a href='" + draft_url + "' style='color:#b05c1e;'>" + draft_url + "</a></p>"
        "<p style='color:#aaa;font-size:12px;'>MantraSetu — Connecting Devotees with Authentic Pandits</p>"
        "</div></body></html>"
    )

    print(f"[EMAIL-SERVICE] send_draft_resume_email | to={to_email} | draft_url={draft_url}")
    return _smtp_send(subject, to_email, text_body, html_body)


# ──────────────────────────────────────────────────────────────────────────────
# 2. STATUS UPDATE EMAIL (approve / reject)
# ──────────────────────────────────────────────────────────────────────────────
async def send_status_update_email(
    to_email: str,
    pandit_name: str,
    new_status: str,
    rejection_reason: str | None = None,
) -> bool:
    """
    Notify a pandit when their application status changes to 'approved' or 'rejected'.
    """
    greeter = f"Namaste {pandit_name}!" if pandit_name else "Namaste!"

    if new_status == "approved":
        subject = "Congratulations! Your MantraSetu Pandit Application is Approved"
        status_line = "Your application has been APPROVED."
        detail = (
            "Welcome to the MantraSetu family! Your profile is now live and devotees "
            "can discover and book your services. Log in to complete your profile."
        )
        color = "#27ae60"
        emoji = "Congratulations"
    elif new_status == "rejected":
        subject = "MantraSetu Pandit Application — Status Update"
        status_line = "We regret to inform you that your application was NOT approved at this time."
        reason_text = f"\n\nReason: {rejection_reason}" if rejection_reason else ""
        detail = (
            "Please review your application details and reapply after addressing any concerns."
            + reason_text
        )
        color = "#e74c3c"
        emoji = "Update"
    else:
        subject = f"MantraSetu Pandit Application — Status: {new_status.title()}"
        status_line = f"Your application status has been updated to: {new_status.upper()}"
        detail = "Please log in to MantraSetu to check your application status."
        color = "#b05c1e"
        emoji = "Update"

    text_body = (
        greeter + "\n\n"
        + status_line + "\n\n"
        + detail + "\n\n"
        "-- MantraSetu Team"
    )

    reason_html = (
        f"<p style='background:#fff8f0;border-left:4px solid {color};"
        f"padding:10px 14px;border-radius:4px;color:#555;font-size:13px;'>"
        f"<strong>Reason:</strong> {rejection_reason}</p>"
        if rejection_reason and new_status == "rejected" else ""
    )

    html_body = (
        "<html><body style='font-family:Arial,sans-serif;background:#fdf6f0;padding:32px;'>"
        "<div style='max-width:520px;margin:auto;background:#fff;border-radius:12px;"
        "padding:32px;box-shadow:0 2px 12px rgba(0,0,0,0.08);'>"
        "<h2 style='color:#b05c1e;margin-top:0;'>" + greeter + "</h2>"
        "<div style='border-left:4px solid " + color + ";padding:12px 16px;"
        "border-radius:4px;background:#f9f9f9;margin:16px 0;'>"
        "<strong style='color:" + color + ";font-size:1rem;'>" + emoji + "</strong>"
        "<p style='margin:6px 0 0;color:#333;'>" + status_line + "</p>"
        "</div>"
        "<p style='color:#555;'>" + detail.replace("\n", "<br/>") + "</p>"
        + reason_html +
        "<p style='color:#aaa;font-size:12px;margin-top:24px;'>"
        "MantraSetu — Connecting Devotees with Authentic Pandits</p>"
        "</div></body></html>"
    )

    print(
        f"[EMAIL-SERVICE] send_status_update_email | to={to_email}"
        f" | status={new_status} | reason={rejection_reason}"
    )
    return _smtp_send(subject, to_email, text_body, html_body)

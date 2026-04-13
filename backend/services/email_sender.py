"""
Email sender using Gmail SMTP (no SendGrid needed).

Setup — one time only:
1. Go to https://myaccount.google.com/apppasswords
2. Sign in, select "Mail" + your device, click Generate
3. Copy the 16-character app password into .env as GMAIL_APP_PASSWORD
4. Set GMAIL_ADDRESS to your Gmail address in .env
"""
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from dotenv import load_dotenv

load_dotenv()

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")


def _is_configured() -> bool:
    return bool(
        GMAIL_ADDRESS and GMAIL_APP_PASSWORD
        and GMAIL_ADDRESS != "your_gmail@gmail.com"
        and GMAIL_APP_PASSWORD != "your_16char_app_password"
    )


def _parse_recipients(to_email: str) -> list[str]:
    """Split comma-separated email string into a list of valid addresses."""
    return [e.strip() for e in to_email.split(",") if e.strip() and "@" in e.strip()]


def _build_message(to_addr: str, subject: str, html_content: str) -> MIMEMultipart:
    """
    Build a multipart/related MIME message with an inline logo.

    The HTML stored in the DB uses a base64 data URI for the logo (so browser
    iframes work).  Here we swap that src back to ``cid:newsdigest_logo`` and
    attach the image inline — the format email clients require.

    Structure:
      multipart/related
        multipart/alternative
          text/html  (references cid:newsdigest_logo)
        image/png    (Content-ID: <newsdigest_logo>)
    """
    import re

    # Replace data URI logo src with CID reference for email clients
    email_html = re.sub(
        r'src="data:image/png;base64,[^"]*"',
        'src="cid:newsdigest_logo"',
        html_content,
    )

    # Outer container — related binds HTML to inline images
    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to_addr

    # HTML part wrapped in alternative
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(email_html, "html", "utf-8"))
    msg.attach(alt)

    # Attach logo as inline CID image
    try:
        from services.summarizer import get_logo_bytes
        logo_bytes = get_logo_bytes()
        if logo_bytes:
            img = MIMEImage(logo_bytes, _subtype="png")
            img.add_header("Content-ID", "<newsdigest_logo>")
            img.add_header("Content-Disposition", "inline", filename="logo.png")
            msg.attach(img)
    except Exception as e:
        print(f"[email] Logo attachment failed: {e}")

    return msg


def send_digest(to_email: str, html_content: str, subject: str) -> bool:
    """Send digest email to one or more recipients (comma-separated). Returns True if all sent."""
    if not _is_configured():
        print("[email] Gmail not configured — skipping. Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env")
        return False

    recipients = _parse_recipients(to_email)
    if not recipients:
        print("[email] No valid recipients found.")
        return False

    success = True
    for addr in recipients:
        msg = _build_message(addr, subject, html_content)
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
                smtp.sendmail(GMAIL_ADDRESS, addr, msg.as_string())
            print(f"[email] Sent to {addr}")
        except Exception as e:
            print(f"[email] Error sending to {addr}: {e}")
            success = False
    return success


def send_test_email(to_email: str) -> bool:
    """Send a test email to all configured recipients."""
    html = """
    <div style="font-family:sans-serif;max-width:600px;margin:auto;padding:32px;
                background:#0f172a;color:#f1f5f9;border-radius:12px;">
      <h2 style="color:#60a5fa;">News Digest — Test Email</h2>
      <p>Your Gmail email configuration is working correctly.</p>
      <p style="color:#64748b;font-size:13px;">
        This is a test message from your News Digest app.
      </p>
    </div>
    """
    return send_digest(to_email, html, "News Digest — Test Email ✓")

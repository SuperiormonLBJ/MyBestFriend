"""Single path for SMTP send (contact form + system notifications)."""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_smtp_message(
    recipient: str,
    subject: str,
    body_plain: str,
    *,
    reply_to: str | None = None,
) -> None:
    from utils.config_loader import ConfigLoader

    cfg = ConfigLoader()
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = cfg.get_smtp_user()
    smtp_password = cfg.get_smtp_password()
    if not smtp_user or not smtp_password:
        raise ValueError("SMTP_USER and SMTP_PASSWORD environment variables are required.")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = recipient
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.attach(MIMEText(body_plain, "plain"))
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, recipient, msg.as_string())

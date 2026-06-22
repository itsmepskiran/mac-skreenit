# backend/services/email_service.py
import os
import smtplib
import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional
from utils_others.logger import logger


def _get_template_path(template_name: str) -> Optional[str]:
    """Find email template file across common deployment layouts."""
    base_paths = []

    env_path = os.getenv("EMAIL_TEMPLATES_PATH")
    if env_path:
        base_paths.append(Path(env_path))

    base_paths += [
        Path(__file__).parent.parent.parent / 'sql-skreenit' / 'assets' / 'templates',
        Path(__file__).parent.parent.parent / 'Skreenit_App' / 'assets' / 'templates',
        Path.home() / 'Skreenit_App' / 'assets' / 'templates',
    ]

    template_filename = f'resend_{template_name}.html'

    for base_path in base_paths:
        template_path = base_path / template_filename
        if template_path.exists():
            logger.info(f"Found template '{template_name}' at: {template_path}")
            return str(template_path)

    logger.warning(f"Template '{template_name}' not found. Tried: {[str(p) for p in base_paths]}")
    return None


class EmailService:
    def __init__(self):
        self.smtp_host     = os.getenv("GMAIL_SMTP_HOST", "smtp.gmail.com")
        self.smtp_port     = int(os.getenv("GMAIL_SMTP_PORT", "587"))
        self.smtp_user     = os.getenv("GMAIL_SMTP_USER")
        self.smtp_password = os.getenv("GMAIL_SMTP_PASSWORD")
        self.from_email    = os.getenv("FROM_EMAIL", self.smtp_user)
        self.from_name     = os.getenv("FROM_NAME", "Skreenit")

        if self.smtp_user and self.smtp_password:
            logger.info(f"Gmail SMTP configured for {self.smtp_user}")
        else:
            logger.error("GMAIL_SMTP_USER or GMAIL_SMTP_PASSWORD not set in environment")

    # ------------------------------------------------------------------
    # Internal send helper (synchronous — called via executor)
    # ------------------------------------------------------------------

    def _send(self, to_email: str, subject: str, html_content: str) -> dict:
        """Send a single HTML email over Gmail SMTP (STARTTLS on port 587)."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{self.from_name} <{self.from_email}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.from_email, to_email, msg.as_string())

        return {"status": "success", "message": f"Email sent to {to_email}"}

    async def _send_async(self, to_email: str, subject: str, html_content: str) -> dict:
        """Run _send in a thread so async FastAPI routes are not blocked."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._send, to_email, subject, html_content)

    # ------------------------------------------------------------------
    # Template loader
    # ------------------------------------------------------------------

    def _load_template(self, template_name: str, variables: dict) -> str:
        """Load branded HTML template; return inline fallback if file not found."""
        template_path = _get_template_path(template_name)
        if template_path:
            with open(template_path, 'r', encoding='utf-8') as f:
                html = f.read()
            for key, value in variables.items():
                html = html.replace(f'{{{{{key}}}}}', str(value))
            logger.info(f"Using branded HTML template: {template_name}")
            return html

        logger.warning(f"Template '{template_name}' not found — using inline fallback")
        return None  # caller builds its own fallback

    # ------------------------------------------------------------------
    # Public email methods
    # ------------------------------------------------------------------

    async def send_verification_email(self, to_email: str, full_name: str, confirmation_url: str) -> dict:
        """Send account verification email."""
        try:
            if not self.smtp_user or not self.smtp_password:
                return {"status": "error", "message": "Gmail SMTP credentials not configured"}

            logger.info(f"Sending verification email to {to_email}")

            html = self._load_template('welcome', {
                'full_name': full_name,
                'confirmation_url': confirmation_url,
            })
            if html is None:
                html = f"""
                <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px">
                    <h2 style="color:#667eea">Welcome to Skreenit, {full_name}!</h2>
                    <p>Please confirm your email address to activate your account:</p>
                    <p style="margin:24px 0">
                        <a href="{confirmation_url}"
                           style="background:#667eea;color:#fff;padding:12px 24px;border-radius:5px;text-decoration:none;font-weight:bold">
                            Confirm Your Email
                        </a>
                    </p>
                    <p style="color:#888;font-size:13px">This link expires in 24 hours.</p>
                </div>"""

            return await self._send_async(to_email, "Verify Your Skreenit Account", html)

        except Exception as e:
            logger.error(f"Verification email error: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def send_password_reset_email(self, to_email: str, full_name: str, reset_url: str) -> dict:
        """Send password reset email."""
        try:
            if not self.smtp_user or not self.smtp_password:
                return {"status": "error", "message": "Gmail SMTP credentials not configured"}

            logger.info(f"Sending password reset email to {to_email}")

            html = self._load_template('password_reset', {
                'full_name': full_name,
                'reset_url': reset_url,
            })
            if html is None:
                html = f"""
                <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px">
                    <h2 style="color:#667eea">Reset Your Skreenit Password</h2>
                    <p>Hi {full_name},</p>
                    <p>Click below to set a new password:</p>
                    <p style="margin:24px 0">
                        <a href="{reset_url}"
                           style="background:#667eea;color:#fff;padding:12px 24px;border-radius:5px;text-decoration:none;font-weight:bold">
                            Reset My Password
                        </a>
                    </p>
                    <p style="color:#888;font-size:13px">This link expires in 1 hour.</p>
                </div>"""

            return await self._send_async(to_email, "Reset Your Skreenit Password", html)

        except Exception as e:
            logger.error(f"Password reset email error: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def send_recruiter_welcome_email(self, to_email: str, full_name: str, company_id: str, login_url: str) -> dict:
        """Send recruiter account welcome email."""
        try:
            if not self.smtp_user or not self.smtp_password:
                return {"status": "error", "message": "Gmail SMTP credentials not configured"}

            logger.info(f"Sending recruiter welcome email to {to_email}")

            html = self._load_template('recruiter_welcome', {
                'full_name': full_name,
                'email': to_email,
                'company_id': company_id,
                'login_url': login_url,
            })
            if html is None:
                html = f"""
                <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px">
                    <h2 style="color:#667eea">Your Recruiter Account is Ready, {full_name}!</h2>
                    <ul style="line-height:2">
                        <li><strong>Login Email:</strong> {to_email}</li>
                        <li><strong>Company ID:</strong> {company_id}</li>
                    </ul>
                    <p style="margin:24px 0">
                        <a href="{login_url}"
                           style="background:#667eea;color:#fff;padding:12px 24px;border-radius:5px;text-decoration:none;font-weight:bold">
                            Login to Your Account
                        </a>
                    </p>
                </div>"""

            return await self._send_async(to_email, "Your Recruiter Account is Ready!", html)

        except Exception as e:
            logger.error(f"Recruiter welcome email error: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def send_support_email(self, to_email: str, subject: str, content: str) -> dict:
        """Send support/notification email."""
        try:
            if not self.smtp_user or not self.smtp_password:
                return {"status": "error", "message": "Gmail SMTP credentials not configured"}

            html = f"""
            <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px">
                <h2 style="color:#667eea">{subject}</h2>
                <div>{content}</div>
                <p style="color:#888;font-size:12px;margin-top:20px">
                    Need help? Reply to this email or contact {self.from_email}
                </p>
            </div>"""

            return await self._send_async(to_email, subject, html)

        except Exception as e:
            logger.error(f"Support email error: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def send_notification_email(self, to_email: str, subject: str, content: str) -> dict:
        """Send general notification email."""
        return await self.send_support_email(to_email, subject, content)

    def test_smtp_connectivity(self) -> bool:
        """Verify Gmail SMTP credentials are reachable."""
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
            logger.info("Gmail SMTP connectivity test passed")
            return True
        except Exception as e:
            logger.error(f"Gmail SMTP connectivity test failed: {str(e)}")
            return False

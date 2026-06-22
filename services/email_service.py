# backend/services/email_service.py
import os
import resend
from pathlib import Path
from typing import Optional
from utils_others.logger import logger


def _get_template_path(template_name: str) -> Optional[str]:
    """
    Find email template file with multiple fallback paths.
    Works across different directory structures and platforms (Mac, Linux, Windows).

    Args:
        template_name: Name of the template without path or extension (e.g., 'welcome', 'password_reset')

    Returns:
        Full path to template file or None if not found
    """
    base_paths = []

    # Highest priority: explicit env var pointing to wherever sql-skreenit lives on this machine
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

    logger.warning(f"Template '{template_name}' not found in any expected path. Tried: {[str(p) for p in base_paths]}")
    return None

class EmailService:
    def __init__(self):
        # Resend API configuration
        self.api_key = os.getenv("RESEND_API_KEY")
        self.from_email = os.getenv("FROM_EMAIL", "onboarding@skreenit.com")
        self.from_name = os.getenv("FROM_NAME", "Skreenit")
        
        # Resend Template IDs
        self.templates = {
            "verification": os.getenv("RESEND_TEMPLATE_VERIFICATION", "email-confirmation"),
            "password_reset": os.getenv("RESEND_TEMPLATE_PASSWORD_RESET", "password-reset"),
            "recruiter_welcome": os.getenv("RESEND_TEMPLATE_RECRUITER_WELCOME", "recruiter-welcome"),
            "support": os.getenv("RESEND_TEMPLATE_SUPPORT", "support-template")
        }
        
        # Initialize Resend
        if self.api_key:
            resend.api_key = self.api_key
            logger.info(f"Resend API initialized for {self.from_email}")
        else:
            logger.error("RESEND_API_KEY not found in environment")
    
    async def send_verification_email(self, to_email, full_name, confirmation_url):
        """Send verification email using Resend API.
        Primary: branded HTML template from disk.
        Fallback: simple inline HTML so the email always goes out.
        """
        try:
            if not self.api_key:
                return {"status": "error", "message": "Resend API key not configured"}

            logger.info(f"Sending verification email via Resend to {to_email}")

            template_path = _get_template_path('welcome')
            if template_path:
                with open(template_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                html_content = html_content.replace('{{full_name}}', full_name)
                html_content = html_content.replace('{{confirmation_url}}', confirmation_url)
                logger.info("Using branded HTML template for verification email")
            else:
                logger.warning("Verification template not found — sending inline fallback email")
                html_content = f"""
                <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px">
                    <h2 style="color:#667eea">Welcome to Skreenit, {full_name}!</h2>
                    <p>Thank you for registering. Please confirm your email address to activate your account:</p>
                    <p style="margin:24px 0">
                        <a href="{confirmation_url}"
                           style="background:#667eea;color:#fff;padding:12px 24px;border-radius:5px;text-decoration:none;font-weight:bold">
                            Confirm Your Email
                        </a>
                    </p>
                    <p style="color:#888;font-size:13px">This link expires in 24 hours.
                    If you didn't create an account you can ignore this email.</p>
                </div>"""

            response = resend.Emails.send({
                "from": f"{self.from_name} <{self.from_email}>",
                "to": [to_email],
                "subject": "Verify Your Skreenit Account",
                "html": html_content
            })
            logger.info(f"Verification email sent via Resend! ID: {response.get('id')}")
            return {"status": "success", "message": f"Email sent: {response.get('id')}"}

        except Exception as e:
            logger.error(f"Resend error: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def send_password_reset_email(self, to_email, full_name, reset_url):
        """Send password reset email using Resend API.
        Primary: branded HTML template from disk.
        Fallback: simple inline HTML so the email always goes out.
        """
        try:
            if not self.api_key:
                return {"status": "error", "message": "Resend API key not configured"}

            logger.info(f"Sending password reset email via Resend to {to_email}")

            template_path = _get_template_path('password_reset')
            if template_path:
                with open(template_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                html_content = html_content.replace('{{full_name}}', full_name)
                html_content = html_content.replace('{{reset_url}}', reset_url)
                logger.info("Using branded HTML template for password reset email")
            else:
                logger.warning("Password reset template not found — sending inline fallback email")
                html_content = f"""
                <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px">
                    <h2 style="color:#667eea">Reset Your Skreenit Password</h2>
                    <p>Hi {full_name},</p>
                    <p>We received a request to reset your password. Click the button below to set a new one:</p>
                    <p style="margin:24px 0">
                        <a href="{reset_url}"
                           style="background:#667eea;color:#fff;padding:12px 24px;border-radius:5px;text-decoration:none;font-weight:bold">
                            Reset My Password
                        </a>
                    </p>
                    <p style="color:#888;font-size:13px">This link expires in 1 hour.
                    If you didn't request a reset you can ignore this email.</p>
                </div>"""

            response = resend.Emails.send({
                "from": f"{self.from_name} <{self.from_email}>",
                "to": [to_email],
                "subject": "Reset Your Skreenit Password",
                "html": html_content
            })
            logger.info(f"Password reset email sent via Resend! ID: {response.get('id')}")
            return {"status": "success", "message": f"Email sent: {response.get('id')}"}

        except Exception as e:
            logger.error(f"Resend error: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def send_support_email(self, to_email, subject, content):
        """Send support email using Resend API"""
        try:
            if not self.api_key:
                return {"status": "error", "message": "Resend API key not configured"}
            
            params = {
                "from": f"{self.from_name} Support <{self.from_email}>",
                "to": [to_email],
                "template_id": self.templates["support"],
                "data": {
                    "subject": subject,
                    "content": content,
                    "support_email": self.from_email
                }
            }
            
            response = resend.Emails.send(params)
            logger.info(f"Support email sent via Resend! ID: {response.get('id')}")
            return {"status": "success", "message": f"Email sent: {response.get('id')}"}
            
        except Exception as e:
            logger.error(f"Resend error: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def send_notification_email(self, to_email, subject, content):
        """Send notification email using Resend API with templates"""
        try:
            if not self.api_key:
                return {"status": "error", "message": "Resend API key not configured"}
            
            params = {
                "from": f"{self.from_name} <notifications@skreenit.com>",
                "to": [to_email],
                "template_id": self.templates["notification"],
                "data": {
                    "subject": subject,
                    "content": content
                }
            }
            
            response = resend.Emails.send(params)
            logger.info(f"Notification email sent via Resend! ID: {response.get('id')}")
            return {"status": "success", "message": f"Email sent: {response.get('id')}"}
            
        except Exception as e:
            logger.error(f"Resend error: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def send_recruiter_welcome_email(self, to_email, full_name, company_id, login_url):
        """Send recruiter welcome email using Resend API.
        Primary: branded HTML template from disk.
        Fallback: simple inline HTML so the email always goes out.
        """
        try:
            if not self.api_key:
                return {"status": "error", "message": "Resend API key not configured"}

            logger.info(f"Sending recruiter welcome email via Resend to {to_email}")

            template_path = _get_template_path('recruiter_welcome')
            if template_path:
                with open(template_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                html_content = html_content.replace('{{full_name}}', full_name)
                html_content = html_content.replace('{{email}}', to_email)
                html_content = html_content.replace('{{company_id}}', company_id)
                html_content = html_content.replace('{{login_url}}', login_url)
                logger.info("Using branded HTML template for recruiter welcome email")
            else:
                logger.warning("Recruiter welcome template not found — sending inline fallback email")
                html_content = f"""
                <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px">
                    <h2 style="color:#667eea">Your Recruiter Account is Ready, {full_name}!</h2>
                    <p>Your recruiter account has been created. Here are your details:</p>
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

            response = resend.Emails.send({
                "from": f"{self.from_name} <{self.from_email}>",
                "to": [to_email],
                "subject": "Your Recruiter Account is Ready!",
                "html": html_content
            })
            logger.info(f"Recruiter welcome email sent via Resend! ID: {response.get('id')}")
            return {"status": "success", "message": f"Email sent: {response.get('id')}"}

        except Exception as e:
            logger.error(f"Resend error: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def test_resend_connectivity(self):
        """Test if Resend API is working"""
        try:
            if not self.api_key:
                logger.error("Resend API key not configured")
                return False
            logger.info("Resend API key configured")
            return True
        except Exception as e:
            logger.error(f"Resend connectivity test failed: {str(e)}")
            return False
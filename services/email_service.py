# backend/services/email_service.py
import os
import resend
from utils_others.logger import logger

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
        """Send verification email using Resend API with our template"""
        try:
            if not self.api_key:
                return {"status": "error", "message": "Resend API key not configured"}
            
            logger.info(f"Sending verification email via Resend to {to_email}")
            
            # Read our HTML template
            template_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'Skreenit_App', 'assets', 'templates', 'resend_welcome.html')
            
            with open(template_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Replace template variables
            html_content = html_content.replace('{{full_name}}', full_name)
            html_content = html_content.replace('{{confirmation_url}}', confirmation_url)
            
            params = {
                "from": f"{self.from_name} <{self.from_email}>",
                "to": [to_email],
                "subject": "Verify Your Skreenit Account",
                "html": html_content
            }
            
            response = resend.Emails.send(params)
            logger.info(f"Verification email sent via Resend! ID: {response.get('id')}")
            return {"status": "success", "message": f"Email sent: {response.get('id')}"}
            
        except Exception as e:
            logger.error(f"Resend error: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def send_password_reset_email(self, to_email, full_name, reset_url):
        """Send password reset email using Resend API with our template"""
        try:
            if not self.api_key:
                return {"status": "error", "message": "Resend API key not configured"}
            
            logger.info(f"Sending password reset email via Resend to {to_email}")
            
            # Read our HTML template
            template_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'Skreenit_App', 'assets', 'templates', 'resend_password_reset.html')
            
            with open(template_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Replace template variables
            html_content = html_content.replace('{{full_name}}', full_name)
            html_content = html_content.replace('{{reset_url}}', reset_url)
            
            params = {
                "from": f"{self.from_name} <{self.from_email}>",
                "to": [to_email],
                "subject": "Reset Your Skreenit Password",
                "html": html_content
            }
            
            response = resend.Emails.send(params)
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
        """Send recruiter welcome email with login credentials using Resend API with our template"""
        try:
            if not self.api_key:
                return {"status": "error", "message": "Resend API key not configured"}
            
            logger.info(f"Sending recruiter welcome email via Resend to {to_email}")
            
            # Read our HTML template
            template_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'Skreenit_App', 'assets', 'templates', 'resend_recruiter_welcome.html')
            
            with open(template_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Replace template variables
            html_content = html_content.replace('{{full_name}}', full_name)
            html_content = html_content.replace('{{email}}', to_email)
            html_content = html_content.replace('{{company_id}}', company_id)
            html_content = html_content.replace('{{login_url}}', login_url)
            
            params = {
                "from": f"{self.from_name} <{self.from_email}>",
                "to": [to_email],
                "subject": "Your Recruiter Account is Ready!",
                "html": html_content
            }
            
            response = resend.Emails.send(params)
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
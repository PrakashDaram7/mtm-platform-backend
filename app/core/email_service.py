"""Email service for sending OTP and notifications."""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_FROM_ADDRESS, EMAIL_USE_TLS

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending emails via SMTP."""
    
    @staticmethod
    def send_otp_email(recipient_email: str, otp: str) -> bool:
        """Send OTP to user's email address.
        
        Args:
            recipient_email: Email address to send OTP
            otp: 6-digit OTP code
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Validate email configuration
            if not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:
                logger.error("Email credentials not configured. Set EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in .env")
                return False
            
            # Create message
            message = MIMEMultipart()
            message['From'] = EMAIL_FROM_ADDRESS
            message['To'] = recipient_email
            message['Subject'] = 'MTM Digital Platform - Verify Your Email'
            
            # Email body
            email_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #667eea;">Verify Your Email Address</h2>
                        <p>Hello,</p>
                        <p>You requested to verify your email address on MTM Digital Platform. Use the following One-Time Password (OTP) to complete your verification:</p>
                        
                        <div style="background-color: #f5f7fa; border: 2px solid #667eea; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center;">
                            <h1 style="color: #667eea; letter-spacing: 5px; margin: 0;">{otp}</h1>
                        </div>
                        
                        <p><strong>⏱️ Validity:</strong> This OTP is valid for 2 minutes only.</p>
                        
                        <p style="color: #666; font-size: 14px;">
                            <strong>Security Note:</strong> Never share your OTP with anyone. Our team will never ask for your OTP via email or phone.
                        </p>
                        
                        <p>If you did not request this OTP, please ignore this email or contact our support team.</p>
                        
                        <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
                        
                        <p style="color: #999; font-size: 12px; margin: 0;">
                            MTM Digital Platform<br>
                            <a href="https://mtmplatform.com" style="color: #667eea; text-decoration: none;">Visit our website</a> | 
                            <a href="mailto:support@mtmplatform.com" style="color: #667eea; text-decoration: none;">Contact Support</a>
                        </p>
                    </div>
                </body>
            </html>
            """
            
            # Attach email body
            message.attach(MIMEText(email_body, 'html'))
            
            # Log connection details (for debugging)
            logger.info(f"Connecting to SMTP server: {EMAIL_HOST}:{EMAIL_PORT} (TLS={EMAIL_USE_TLS})")
            logger.info(f"Sending email from: {EMAIL_FROM_ADDRESS} to: {recipient_email}")
            
            # Connect to SMTP server and send
            with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=10) as server:
                if EMAIL_USE_TLS:
                    server.starttls()
                
                server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
                server.send_message(message)
            
            logger.info(f"✅ OTP email sent successfully to {recipient_email}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"❌ Email Authentication Failed: {str(e)}")
            logger.error(f"   Check EMAIL_HOST_USER ({EMAIL_HOST_USER}) and EMAIL_HOST_PASSWORD in .env")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"❌ SMTP Error: {str(e)}")
            return False
        except TimeoutError as e:
            logger.error(f"❌ Connection Timeout: Could not connect to {EMAIL_HOST}:{EMAIL_PORT}")
            return False
        except Exception as e:
            logger.error(f"❌ Email Error: {str(e)}")
            logger.error(f"   Email config - Host: {EMAIL_HOST}, Port: {EMAIL_PORT}, TLS: {EMAIL_USE_TLS}")
            return False
    
    @staticmethod
    def send_otp_sms(phone_number: str, otp: str) -> dict:
        """Send OTP to user's phone number (SMS).
        
        Currently not implemented. Returns error message.
        
        Args:
            phone_number: Phone number in international format
            otp: 6-digit OTP code
            
        Returns:
            Dictionary with success status and message
        """
        return {
            "success": False,
            "message": "OTP via phone/SMS is not yet implemented. Please use email to receive your OTP."
        }

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
    def send_payment_link_email(
        recipient_email: str,
        member_name: str,
        plan_name: str,
        amount: float,
        currency: str,
        payment_link: str,
        notes: str = ""
    ) -> bool:
        """Send a payment link email to a member after admin review.

        Args:
            recipient_email: Member's email address
            member_name:     Member's full name
            plan_name:       Membership plan name
            amount:          Amount due
            currency:        Currency code (e.g. MUR)
            payment_link:    The URL the member should click to pay
            notes:           Optional admin note to include

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            if not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:
                logger.error("Email credentials not configured.")
                return False

            message = MIMEMultipart()
            message['From'] = EMAIL_FROM_ADDRESS
            message['To'] = recipient_email
            message['Subject'] = 'MTM Digital Platform – Complete Your Membership Payment'

            notes_block = f"""
                        <div style="background:#FEF3C7;border-left:4px solid #F59E0B;border-radius:6px;padding:12px 16px;margin:16px 0;">
                            <p style="margin:0;color:#92400E;font-size:14px;"><strong>Note from Admin:</strong> {notes}</p>
                        </div>""" if notes else ""

            email_body = f"""
            <html>
                <body style="font-family:Arial,sans-serif;background:#f5f7fa;margin:0;padding:0;">
                    <div style="max-width:600px;margin:40px auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.10);">
                        <!-- Header -->
                        <div style="background:linear-gradient(135deg,#6C3CE1,#8B5CF6);padding:32px 32px 24px;">
                            <h1 style="color:#fff;margin:0;font-size:22px;font-weight:800;">🕉️ Mauritius Telugu Mahasabha</h1>
                            <p style="color:rgba(255,255,255,0.75);margin:6px 0 0;font-size:14px;">Membership Payment Request</p>
                        </div>

                        <!-- Body -->
                        <div style="padding:32px;">
                            <p style="font-size:16px;color:#111827;margin:0 0 8px;">Dear <strong>{member_name}</strong>,</p>
                            <p style="color:#6B7280;font-size:14px;line-height:1.6;margin:0 0 20px;">
                                Your membership application has been reviewed by our admin team.
                                Please complete your payment to activate your membership.
                            </p>

                            {notes_block}

                            <!-- Payment Summary -->
                            <div style="background:#F5F3FF;border:2px solid #DDD6FE;border-radius:12px;padding:20px 24px;margin:0 0 24px;">
                                <p style="margin:0 0 12px;color:#6C3CE1;font-weight:800;font-size:13px;text-transform:uppercase;letter-spacing:0.5px;">Payment Summary</p>
                                <table style="width:100%;border-collapse:collapse;">
                                    <tr>
                                        <td style="color:#6B7280;font-size:14px;padding:4px 0;">Plan</td>
                                        <td style="color:#111827;font-size:14px;font-weight:700;text-align:right;">{plan_name}</td>
                                    </tr>
                                    <tr>
                                        <td style="color:#6B7280;font-size:14px;padding:4px 0;">Amount Due</td>
                                        <td style="color:#6C3CE1;font-size:18px;font-weight:800;text-align:right;">{currency} {amount:,.0f}</td>
                                    </tr>
                                </table>
                            </div>

                            <!-- CTA Button -->
                            <div style="text-align:center;margin:28px 0;">
                                <a href="{payment_link}" target="_blank"
                                   style="display:inline-block;padding:14px 36px;
                                          background:linear-gradient(135deg,#6C3CE1,#8B5CF6);
                                          color:#fff;font-size:16px;font-weight:700;
                                          text-decoration:none;border-radius:10px;
                                          box-shadow:0 4px 16px rgba(108,60,225,0.35);">
                                    💳 Complete Payment Now
                                </a>
                            </div>

                            <p style="color:#9CA3AF;font-size:13px;text-align:center;margin:0 0 8px;">
                                Or copy this link in your browser:
                            </p>
                            <p style="background:#F3F4F6;border-radius:8px;padding:10px 14px;font-size:12px;
                                      color:#6C3CE1;word-break:break-all;text-align:center;margin:0 0 24px;">
                                {payment_link}
                            </p>

                            <p style="color:#6B7280;font-size:13px;line-height:1.6;">
                                After completing payment, please allow up to 24 hours for your membership
                                to be fully activated. You will receive a confirmation email with your
                                membership number.
                            </p>
                        </div>

                        <!-- Footer -->
                        <div style="background:#F9FAFB;border-top:1px solid #E5E7EB;padding:20px 32px;text-align:center;">
                            <p style="color:#9CA3AF;font-size:12px;margin:0;">
                                MTM Digital Platform &nbsp;|&nbsp;
                                <a href="mailto:info@mtm.mu" style="color:#6C3CE1;text-decoration:none;">info@mtm.mu</a>
                            </p>
                        </div>
                    </div>
                </body>
            </html>
            """

            message.attach(MIMEText(email_body, 'html'))

            with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=10) as server:
                if EMAIL_USE_TLS:
                    server.starttls()
                server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
                server.send_message(message)

            logger.info(f"✅ Payment link email sent to {recipient_email}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"❌ Email auth failed: {str(e)}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"❌ SMTP error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Payment link email error: {str(e)}")
            return False

    @staticmethod
    def send_otp_sms(phone_number: str, otp: str) -> dict:
        """Send OTP to user's phone number (SMS). Currently not implemented."""
        return {
            "success": False,
            "message": "OTP via phone/SMS is not yet implemented. Please use email to receive your OTP."
        }

"""
Email service for sending notifications and alerts.
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict, Union
import os
from datetime import datetime
from jinja2 import Template

logger = logging.getLogger(__name__)


class EmailService:
    """
    Comprehensive email service for sending notifications, alerts, and reports.
    """
    
    def __init__(self, config=None):
        """
        Initialize Email Service.
        
        Args:
            config: Configuration dictionary with email settings
        """
        self.config = config or {}
        
        # SMTP Configuration
        self.smtp_server = self.config.get('MAIL_SERVER', 'localhost')
        self.smtp_port = self.config.get('MAIL_PORT', 587)
        self.use_tls = self.config.get('MAIL_USE_TLS', True)
        self.use_ssl = self.config.get('MAIL_USE_SSL', False)
        self.username = self.config.get('MAIL_USERNAME')
        self.password = self.config.get('MAIL_PASSWORD')
        self.default_sender = self.config.get('MAIL_DEFAULT_SENDER', 'noreply@xu-news-ai-rag.com')
        
        # Email settings
        self.max_recipients = self.config.get('MAIL_MAX_RECIPIENTS', 50)
        self.timeout = self.config.get('MAIL_TIMEOUT', 30)
        
        # Check if email is properly configured
        self.is_configured = bool(
            self.smtp_server and 
            self.smtp_port and 
            (self.username or not self._requires_auth())
        )
        
        if not self.is_configured:
            logger.warning("Email service is not properly configured")
        else:
            logger.info("Email service initialized successfully")
    
    def _requires_auth(self) -> bool:
        """Check if SMTP server requires authentication."""
        # Most production SMTP servers require authentication
        return self.smtp_server not in ['localhost', '127.0.0.1']
    
    def send_email(
        self,
        to_email: Union[str, List[str]],
        subject: str,
        body: str,
        from_email: Optional[str] = None,
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None,
        html_body: Optional[str] = None,
        attachments: Optional[List[Dict]] = None
    ) -> bool:
        """
        Send an email.
        
        Args:
            to_email: Recipient email address(es)
            subject: Email subject
            body: Plain text email body
            from_email: Sender email (optional, uses default)
            cc: CC recipients (optional)
            bcc: BCC recipients (optional)
            html_body: HTML email body (optional)
            attachments: List of attachment dictionaries (optional)
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self.is_configured:
            logger.warning("Email service not configured, skipping email")
            return False
        
        try:
            # Prepare recipient lists
            to_list = self._normalize_email_list(to_email)
            cc_list = self._normalize_email_list(cc) if cc else []
            bcc_list = self._normalize_email_list(bcc) if bcc else []
            
            # Check recipient limits
            total_recipients = len(to_list) + len(cc_list) + len(bcc_list)
            if total_recipients > self.max_recipients:
                logger.error(f"Too many recipients: {total_recipients} (max: {self.max_recipients})")
                return False
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = from_email or self.default_sender
            msg['To'] = ', '.join(to_list)
            msg['Subject'] = subject
            msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
            
            if cc_list:
                msg['Cc'] = ', '.join(cc_list)
            
            # Add plain text body
            text_part = MIMEText(body, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # Add HTML body if provided
            if html_body:
                html_part = MIMEText(html_body, 'html', 'utf-8')
                msg.attach(html_part)
            
            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    self._add_attachment(msg, attachment)
            
            # Send email
            return self._send_message(msg, to_list + cc_list + bcc_list)
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def _normalize_email_list(self, emails: Union[str, List[str]]) -> List[str]:
        """Normalize email input to a list of email addresses."""
        if isinstance(emails, str):
            return [email.strip() for email in emails.split(',') if email.strip()]
        elif isinstance(emails, list):
            return [email.strip() for email in emails if isinstance(email, str) and email.strip()]
        else:
            return []
    
    def _add_attachment(self, msg: MIMEMultipart, attachment: Dict):
        """Add attachment to email message."""
        try:
            file_path = attachment.get('path')
            filename = attachment.get('filename')
            content_type = attachment.get('content_type', 'application/octet-stream')
            
            if not file_path or not os.path.exists(file_path):
                logger.warning(f"Attachment file not found: {file_path}")
                return
            
            with open(file_path, 'rb') as f:
                part = MIMEBase(*content_type.split('/'))
                part.set_payload(f.read())
                encoders.encode_base64(part)
                
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {filename or os.path.basename(file_path)}'
                )
                
                msg.attach(part)
                
        except Exception as e:
            logger.error(f"Failed to add attachment: {e}")
    
    def _send_message(self, msg: MIMEMultipart, recipients: List[str]) -> bool:
        """Send the email message via SMTP."""
        try:
            # Choose SMTP class based on SSL/TLS settings
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=self.timeout)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=self.timeout)
                if self.use_tls:
                    server.starttls()
            
            # Authenticate if credentials provided
            if self.username and self.password:
                server.login(self.username, self.password)
            
            # Send email
            text = msg.as_string()
            server.sendmail(msg['From'], recipients, text)
            server.quit()
            
            logger.info(f"Email sent successfully to {len(recipients)} recipients")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP Authentication failed: {e}")
            return False
        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"SMTP Recipients refused: {e}")
            return False
        except smtplib.SMTPServerDisconnected as e:
            logger.error(f"SMTP Server disconnected: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email via SMTP: {e}")
            return False
    
    def send_crawler_notification(
        self,
        user_email: str,
        source_name: str,
        articles_count: int,
        source_url: str,
        customizable_title: Optional[str] = None,
        customizable_content: Optional[str] = None
    ) -> bool:
        """
        Send customizable notification about successful crawling.
        
        Args:
            user_email: User email address
            source_name: Name of the crawled source
            articles_count: Number of articles collected
            source_url: URL of the source
            customizable_title: Custom email title (optional)
            customizable_content: Custom email content (optional)
            
        Returns:
            True if notification was sent successfully
        """
        # Default title and content
        default_title = f"New articles collected from {source_name}"
        default_content = f"""
        Hello,
        
        We've successfully collected {articles_count} new articles from your RSS source "{source_name}".
        
        Source URL: {source_url}
        Articles collected: {articles_count}
        Collection time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        You can view and search these articles in your knowledge base.
        
        Best regards,
        XU-News-AI-RAG System
        """
        
        # Use customizable content if provided
        subject = customizable_title or default_title
        body = customizable_content or default_content
        
        # Create HTML version
        html_body = self._create_notification_html(
            source_name=source_name,
            articles_count=articles_count,
            source_url=source_url,
            custom_content=customizable_content
        )
        
        return self.send_email(
            to_email=user_email,
            subject=subject,
            body=body,
            html_body=html_body
        )
    
    def _create_notification_html(
        self,
        source_name: str,
        articles_count: int,
        source_url: str,
        custom_content: Optional[str] = None
    ) -> str:
        """Create HTML notification email."""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: linear-gradient(135deg, #1976D2, #42A5F5); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }
                .content { background: #f9f9f9; padding: 20px; }
                .stats { background: white; padding: 15px; margin: 15px 0; border-radius: 5px; border-left: 4px solid #1976D2; }
                .footer { background: #333; color: white; padding: 15px; text-align: center; border-radius: 0 0 8px 8px; font-size: 12px; }
                .button { display: inline-block; background: #1976D2; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 10px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚀 XU-News-AI-RAG</h1>
                    <h2>New Articles Collected!</h2>
                </div>
                
                <div class="content">
                    {% if custom_content %}
                        <p>{{ custom_content }}</p>
                    {% else %}
                        <p>Great news! We've successfully collected new articles for your knowledge base.</p>
                    {% endif %}
                    
                    <div class="stats">
                        <h3>📊 Collection Summary</h3>
                        <ul>
                            <li><strong>Source:</strong> {{ source_name }}</li>
                            <li><strong>Articles Collected:</strong> {{ articles_count }}</li>
                            <li><strong>Source URL:</strong> <a href="{{ source_url }}">{{ source_url }}</a></li>
                            <li><strong>Collection Time:</strong> {{ collection_time }}</li>
                        </ul>
                    </div>
                    
                    <p>These articles are now available in your personal knowledge base and can be searched using our AI-powered semantic search.</p>
                    
                    <a href="#" class="button">🔍 Search Your Knowledge Base</a>
                </div>
                
                <div class="footer">
                    <p>This is an automated notification from XU-News-AI-RAG</p>
                    <p>You can customize these notifications in your account settings</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        template = Template(html_template)
        return template.render(
            source_name=source_name,
            articles_count=articles_count,
            source_url=source_url,
            custom_content=custom_content,
            collection_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
    
    def send_error_alert(
        self,
        admin_email: str,
        error_type: str,
        error_message: str,
        context: Optional[Dict] = None
    ) -> bool:
        """
        Send error alert to administrator.
        
        Args:
            admin_email: Administrator email address
            error_type: Type of error (e.g., 'crawler_failure', 'system_error')
            error_message: Detailed error message
            context: Additional context information
            
        Returns:
            True if alert was sent successfully
        """
        subject = f"🚨 XU-News-AI-RAG Alert: {error_type}"
        
        body = f"""
        XU-News-AI-RAG System Alert
        ===========================
        
        Error Type: {error_type}
        Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        Error Message:
        {error_message}
        """
        
        if context:
            body += "\n\nAdditional Context:\n"
            for key, value in context.items():
                body += f"- {key}: {value}\n"
        
        body += "\n\nPlease investigate and take appropriate action.\n"
        
        return self.send_email(
            to_email=admin_email,
            subject=subject,
            body=body
        )
    
    def send_weekly_report(
        self,
        recipient_email: str,
        report_data: Dict
    ) -> bool:
        """
        Send weekly activity report.
        
        Args:
            recipient_email: Report recipient email
            report_data: Dictionary with report data
            
        Returns:
            True if report was sent successfully
        """
        subject = f"📊 XU-News-AI-RAG Weekly Report - {datetime.now().strftime('%Y-%m-%d')}"
        
        body = f"""
        XU-News-AI-RAG Weekly Activity Report
        ====================================
        
        Report Period: {report_data.get('start_date')} to {report_data.get('end_date')}
        
        Content Statistics:
        - New articles collected: {report_data.get('new_articles', 0)}
        - Total documents: {report_data.get('total_documents', 0)}
        - Active sources: {report_data.get('active_sources', 0)}
        
        Search Activity:
        - Total searches performed: {report_data.get('total_searches', 0)}
        - Average search response time: {report_data.get('avg_search_time', 0):.2f}s
        - Most popular keywords: {', '.join(report_data.get('popular_keywords', []))}
        
        System Health:
        - Crawler success rate: {report_data.get('crawler_success_rate', 0):.1f}%
        - System uptime: {report_data.get('uptime', 'N/A')}
        
        Thank you for using XU-News-AI-RAG!
        """
        
        return self.send_email(
            to_email=recipient_email,
            subject=subject,
            body=body
        )
    
    def test_configuration(self) -> Dict[str, Union[bool, str]]:
        """
        Test email configuration by sending a test email to the configured sender.
        
        Returns:
            Dictionary with test results
        """
        if not self.is_configured:
            return {
                'success': False,
                'message': 'Email service not configured'
            }
        
        test_email = self.default_sender
        subject = "XU-News-AI-RAG Email Configuration Test"
        body = f"""
        This is a test email from XU-News-AI-RAG.
        
        If you receive this email, your email configuration is working correctly.
        
        Configuration details:
        - SMTP Server: {self.smtp_server}
        - Port: {self.smtp_port}
        - TLS: {self.use_tls}
        - SSL: {self.use_ssl}
        - Authenticated: {bool(self.username)}
        
        Test sent at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        try:
            success = self.send_email(
                to_email=test_email,
                subject=subject,
                body=body
            )
            
            if success:
                return {
                    'success': True,
                    'message': f'Test email sent successfully to {test_email}'
                }
            else:
                return {
                    'success': False,
                    'message': 'Failed to send test email (check logs for details)'
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Email configuration test failed: {str(e)}'
            }
    
    def get_service_status(self) -> Dict:
        """Get email service status information."""
        return {
            'configured': self.is_configured,
            'smtp_server': self.smtp_server,
            'smtp_port': self.smtp_port,
            'use_tls': self.use_tls,
            'use_ssl': self.use_ssl,
            'authenticated': bool(self.username),
            'default_sender': self.default_sender,
            'max_recipients': self.max_recipients,
        }

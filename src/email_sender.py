"""Email sender for sending reports via SMTP."""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

from .config import (
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    EMAIL_FROM,
    EMAIL_TO,
    validate_email_config,
)

logger = logging.getLogger(__name__)


class EmailSendError(Exception):
    """Exception raised when email sending fails."""
    pass


def send_email(
    subject: str,
    html_content: str,
    text_content: str | None = None,
    to_addresses: list[str] | None = None,
    from_address: str | None = None,
) -> bool:
    """Send an email via SMTP.
    
    Args:
        subject: Email subject line
        html_content: HTML body of the email
        text_content: Optional plain text alternative
        to_addresses: List of recipient addresses (defaults to EMAIL_TO config)
        from_address: Sender address (defaults to EMAIL_FROM config)
        
    Returns:
        True if email was sent successfully
        
    Raises:
        EmailSendError: If sending fails
    """
    # Use defaults from config
    to_addresses = to_addresses or EMAIL_TO
    from_address = from_address or EMAIL_FROM
    
    # Filter out empty addresses
    to_addresses = [addr.strip() for addr in to_addresses if addr.strip()]
    
    if not to_addresses:
        raise EmailSendError("No recipient addresses provided")
    
    # Validate email configuration
    config_errors = validate_email_config()
    if config_errors:
        raise EmailSendError(f"Email configuration errors: {', '.join(config_errors)}")
    
    # Create message
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = from_address
    message["To"] = ", ".join(to_addresses)
    
    # Add plain text part
    if text_content:
        text_part = MIMEText(text_content, "plain")
        message.attach(text_part)
    
    # Add HTML part
    html_part = MIMEText(html_content, "html")
    message.attach(html_part)
    
    try:
        # Create secure SSL context
        context = ssl.create_default_context()
        
        # Connect to SMTP server
        if SMTP_PORT == 465:
            # SSL connection
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(from_address, to_addresses, message.as_string())
        else:
            # STARTTLS connection
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls(context=context)
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(from_address, to_addresses, message.as_string())
        
        logger.info(f"Email sent successfully to {', '.join(to_addresses)}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        raise EmailSendError(f"SMTP authentication failed: {e}")
    except smtplib.SMTPRecipientsRefused as e:
        raise EmailSendError(f"Recipients refused: {e}")
    except smtplib.SMTPException as e:
        raise EmailSendError(f"SMTP error: {e}")
    except Exception as e:
        raise EmailSendError(f"Failed to send email: {e}")


def send_daily_report(
    html_content: str,
    text_content: str | None = None,
    report_date: str = "",
) -> bool:
    """Send the daily water tank report.
    
    Args:
        html_content: HTML email content
        text_content: Optional plain text content
        report_date: Date string for subject line
        
    Returns:
        True if sent successfully
    """
    subject = f"💧 Water Tank Report - {report_date}" if report_date else "💧 Water Tank Daily Report"
    
    return send_email(
        subject=subject,
        html_content=html_content,
        text_content=text_content,
    )


"""Email sender using Resend API."""

import logging
from typing import Optional

import resend

from .config import (
    RESEND_API_KEY,
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
    text_content: Optional[str] = None,
    to_addresses: Optional[list[str]] = None,
    from_address: Optional[str] = None,
) -> bool:
    """Send an email via Resend API.
    
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
    
    # Set Resend API key
    resend.api_key = RESEND_API_KEY
    
    try:
        # Build email payload
        email_params = {
            "from": from_address,
            "to": to_addresses,
            "subject": subject,
            "html": html_content,
        }
        
        if text_content:
            email_params["text"] = text_content
        
        # Send via Resend
        response = resend.Emails.send(email_params)
        
        email_id = response.get("id", "unknown") if isinstance(response, dict) else getattr(response, "id", "unknown")
        logger.info(f"Email sent successfully (ID: {email_id}) to {', '.join(to_addresses)}")
        return True
        
    except Exception as e:
        raise EmailSendError(f"Failed to send email: {e}")


def send_daily_report(
    html_content: str,
    text_content: Optional[str] = None,
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

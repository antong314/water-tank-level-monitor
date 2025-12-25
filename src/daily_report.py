"""Daily Report - Cron Job 2: Analyze data and send email report.

This job runs daily at 6 AM Costa Rica time to:
1. Query last 24 hours of data from Supabase
2. Analyze fill rate (from night period) and usage
3. Store summary in Supabase
4. Generate and send email report

Usage:
    python -m src.daily_report
"""

import logging
from datetime import datetime, timedelta

import pytz

from .config import TIMEZONE, validate_config, validate_email_config
from .supabase_client import SupabaseClient
from .tuya_client import TuyaClient, TuyaAPIError
from .analyzer import analyze_day, get_current_level_info
from .email_builder import build_daily_report_email, build_simple_text_report
from .email_sender import send_daily_report, EmailSendError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_daily_report(report_date: datetime | None = None) -> dict:
    """Execute the daily report generation and email.
    
    Args:
        report_date: Date to generate report for (defaults to yesterday)
        
    Returns:
        Dictionary with report results
    """
    logger.info("=" * 60)
    logger.info("WATER TANK DAILY REPORT - Starting")
    logger.info("=" * 60)
    
    # Validate configuration
    config_errors = validate_config()
    if config_errors:
        for error in config_errors:
            logger.error(f"Configuration error: {error}")
        return {"success": False, "error": "Configuration validation failed"}
    
    # Initialize clients
    supabase = SupabaseClient()
    tz = pytz.timezone(TIMEZONE)
    
    # Determine report date (default to yesterday in local timezone)
    if report_date is None:
        now_local = datetime.now(tz)
        report_date = now_local - timedelta(days=1)
    
    report_date_str = report_date.strftime("%Y-%m-%d")
    logger.info(f"Generating report for: {report_date_str}")
    
    try:
        # Fetch readings for the report date
        logger.info("Fetching readings from Supabase...")
        readings = supabase.get_readings_for_date(report_date)
        logger.info(f"Found {len(readings)} readings")
        
        if not readings:
            logger.warning(f"No readings found for {report_date_str}")
            return {
                "success": False,
                "error": f"No readings found for {report_date_str}",
            }
        
        # Analyze the day
        logger.info("Analyzing data...")
        summary = analyze_day(readings, report_date, TIMEZONE)
        
        logger.info(f"Analysis complete:")
        logger.info(f"  - Depth readings: {summary.get('liquid_depth_count', 0)}")
        logger.info(f"  - Fill rate: {summary.get('night_fill_rate_per_hour', 'N/A')} units/hr")
        logger.info(f"  - Est. usage: {summary.get('estimated_usage_liters', 'N/A')} liters")
        
        # Store summary in Supabase
        logger.info("Storing summary in Supabase...")
        supabase.upsert_daily_summary(summary)
        
        # Get current device status for email
        current_status = None
        try:
            tuya = TuyaClient()
            current_status = tuya.get_current_status()
            logger.info(f"Current device status: {'Online' if current_status.get('online') else 'Offline'}")
        except TuyaAPIError as e:
            logger.warning(f"Could not fetch current status: {e}")
        except Exception as e:
            logger.warning(f"Error fetching current status: {e}")
        
        # Check email configuration
        email_errors = validate_email_config()
        if email_errors:
            logger.warning("Email configuration incomplete, skipping email send")
            for error in email_errors:
                logger.warning(f"  - {error}")
            return {
                "success": True,
                "summary": summary,
                "email_sent": False,
                "email_error": "Email configuration incomplete",
            }
        
        # Build and send email
        logger.info("Building email report...")
        html_content = build_daily_report_email(summary, current_status)
        text_content = build_simple_text_report(summary)
        
        logger.info("Sending email...")
        try:
            send_daily_report(
                html_content=html_content,
                text_content=text_content,
                report_date=report_date_str,
            )
            logger.info("Email sent successfully!")
            email_sent = True
            email_error = None
        except EmailSendError as e:
            logger.error(f"Failed to send email: {e}")
            email_sent = False
            email_error = str(e)
        
        logger.info("=" * 60)
        logger.info("DAILY REPORT COMPLETE")
        logger.info("=" * 60)
        
        return {
            "success": True,
            "report_date": report_date_str,
            "summary": summary,
            "email_sent": email_sent,
            "email_error": email_error,
        }
        
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        logger.exception(error_msg)
        return {"success": False, "error": error_msg}


def main():
    """Entry point for daily report cron job."""
    result = run_daily_report()
    
    if not result.get("success"):
        logger.error(f"Daily report failed: {result.get('error')}")
        exit(1)
    
    if result.get("email_sent"):
        logger.info("Daily report completed and email sent successfully")
    else:
        logger.info(f"Daily report completed but email not sent: {result.get('email_error')}")


if __name__ == "__main__":
    main()


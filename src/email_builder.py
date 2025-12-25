"""Email builder for generating HTML email reports."""

from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import TIMEZONE
from .analyzer import depth_to_liters, depth_to_percent


# Default template directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def get_template_env(templates_dir: Path = TEMPLATES_DIR) -> Environment:
    """Get Jinja2 template environment.
    
    Args:
        templates_dir: Path to templates directory
        
    Returns:
        Configured Jinja2 Environment
    """
    return Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(["html", "xml"]),
    )


def build_daily_report_email(
    summary: dict[str, Any],
    current_status: dict[str, Any] | None = None,
    templates_dir: Path = TEMPLATES_DIR,
) -> str:
    """Build HTML email for daily report.
    
    Args:
        summary: Daily summary data from analyzer
        current_status: Optional current device status
        templates_dir: Path to templates directory
        
    Returns:
        Rendered HTML email content
    """
    env = get_template_env(templates_dir)
    template = env.get_template("daily_report.html")
    
    # Get current depth from status or summary
    if current_status and current_status.get("status"):
        current_depth = current_status["status"].get("liquid_depth", summary.get("end_depth", 0))
    else:
        current_depth = summary.get("end_depth", 0)
    
    try:
        current_depth = int(current_depth)
    except (ValueError, TypeError):
        current_depth = 0
    
    # Calculate display values
    current_percent = round(depth_to_percent(current_depth), 1)
    current_liters = round(depth_to_liters(current_depth), 0)
    
    # Format report date
    report_date = summary.get("report_date", datetime.now().strftime("%Y-%m-%d"))
    try:
        date_obj = datetime.strptime(report_date, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%B %d, %Y")
    except ValueError:
        formatted_date = report_date
    
    # Build template context
    context = {
        "report_date": formatted_date,
        
        # Current level
        "current_depth": current_depth,
        "current_percent": current_percent,
        "current_liters": int(current_liters),
        
        # Daily range
        "min_depth": summary.get("min_depth", 0),
        "max_depth": summary.get("max_depth", 0),
        "min_liters": int(depth_to_liters(summary.get("min_depth", 0))),
        "max_liters": int(depth_to_liters(summary.get("max_depth", 0))),
        
        # Fill rate
        "fill_rate": round(summary.get("night_fill_rate_per_hour", 0), 2),
        "fill_rate_liters": round(depth_to_liters(summary.get("night_fill_rate_per_hour", 0)), 1),
        "daily_intake_liters": int(summary.get("estimated_intake_liters", 0)),
        "r_squared": round(summary.get("night_r_squared", 0), 3),
        
        # Usage
        "usage_liters": int(summary.get("estimated_usage_liters", 0)),
        "net_change": summary.get("net_change_depth", 0),
        
        # Metadata
        "readings_count": summary.get("liquid_depth_count", summary.get("readings_count", 0)),
        "night_duration_hours": round(summary.get("night_duration_hours", 0), 1),
        
        # Device status
        "device_online": current_status.get("online", True) if current_status else True,
    }
    
    return template.render(**context)


def build_simple_text_report(summary: dict[str, Any]) -> str:
    """Build plain text version of daily report.
    
    Args:
        summary: Daily summary data
        
    Returns:
        Plain text report
    """
    report_date = summary.get("report_date", "Unknown")
    
    lines = [
        "=" * 50,
        f"WATER TANK DAILY REPORT - {report_date}",
        "=" * 50,
        "",
        "CURRENT LEVEL",
        f"  Depth: {summary.get('end_depth', 0)} units",
        f"  Volume: {int(depth_to_liters(summary.get('end_depth', 0)))} liters",
        f"  Fill: {round(depth_to_percent(summary.get('end_depth', 0)), 1)}%",
        "",
        "DAILY RANGE",
        f"  Minimum: {summary.get('min_depth', 0)} units ({int(depth_to_liters(summary.get('min_depth', 0)))}L)",
        f"  Maximum: {summary.get('max_depth', 0)} units ({int(depth_to_liters(summary.get('max_depth', 0)))}L)",
        "",
        "SPRING INTAKE",
        f"  Fill rate: {round(summary.get('night_fill_rate_per_hour', 0), 2)} units/hour",
        f"  Est. daily intake: {int(summary.get('estimated_intake_liters', 0))} liters",
        "",
        "WATER USAGE",
        f"  Estimated usage: {int(summary.get('estimated_usage_liters', 0))} liters",
        f"  Net change: {summary.get('net_change_depth', 0)} units",
        "",
        "-" * 50,
        f"Based on {summary.get('liquid_depth_count', 0)} sensor readings",
        "=" * 50,
    ]
    
    return "\n".join(lines)


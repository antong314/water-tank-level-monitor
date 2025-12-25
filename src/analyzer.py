"""Analysis logic for water tank data."""

from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pytz

from .config import (
    TIMEZONE,
    NIGHT_START_HOUR,
    NIGHT_END_HOUR,
    LITERS_PER_DEPTH_UNIT,
    SENSOR_MAX_DEPTH,
    TOTAL_CAPACITY_LITERS,
)


def analyze_night_period(
    readings: list[dict[str, Any]],
    timezone: str = TIMEZONE,
) -> dict[str, Any] | None:
    """Analyze night period (midnight to 6am) to determine fill rate.
    
    During night hours, assume no water usage - pure filling from spring.
    Uses linear regression to calculate fill rate.
    
    Args:
        readings: List of sensor readings with event_time and value
        timezone: Timezone for local time conversion
        
    Returns:
        Dictionary with fill rate metrics, or None if insufficient data
    """
    tz = pytz.timezone(timezone)
    
    # Filter readings for night period (midnight to 6am local time)
    night_readings = []
    for r in readings:
        if r.get("code") != "liquid_depth":
            continue
        
        event_time = r.get("event_time")
        if not event_time:
            continue
        
        # Convert to local time
        utc_time = datetime.fromtimestamp(event_time / 1000, tz=pytz.UTC)
        local_time = utc_time.astimezone(tz)
        
        # Night = NIGHT_START_HOUR to NIGHT_END_HOUR
        if NIGHT_START_HOUR <= local_time.hour < NIGHT_END_HOUR:
            try:
                depth = int(r.get("value", 0))
                night_readings.append({
                    "time": event_time,
                    "depth": depth,
                    "local_time": local_time,
                })
            except (ValueError, TypeError):
                continue
    
    if len(night_readings) < 2:
        return None
    
    # Sort by time
    night_readings.sort(key=lambda x: x["time"])
    
    # Remove reversals (depth should only increase during fill)
    filtered = [night_readings[0]]
    for r in night_readings[1:]:
        if r["depth"] >= filtered[-1]["depth"]:
            filtered.append(r)
    
    if len(filtered) < 2:
        return None
    
    # Linear regression
    times = np.array([
        (r["time"] - filtered[0]["time"]) / (1000 * 60 * 60)
        for r in filtered
    ])  # Hours from start
    depths = np.array([r["depth"] for r in filtered])
    
    coeffs = np.polyfit(times, depths, 1)
    rate = float(coeffs[0])  # Slope = depth units per hour
    
    # Calculate R-squared
    predicted = np.polyval(coeffs, times)
    ss_res = np.sum((depths - predicted) ** 2)
    ss_tot = np.sum((depths - np.mean(depths)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    
    return {
        "rate_per_hour": rate,
        "r_squared": float(r_squared),
        "start_depth": int(filtered[0]["depth"]),
        "end_depth": int(filtered[-1]["depth"]),
        "duration_hours": float(times[-1]),
        "reading_count": len(filtered),
        "start_time": filtered[0]["local_time"].isoformat(),
        "end_time": filtered[-1]["local_time"].isoformat(),
    }


def estimate_daily_usage(
    readings: list[dict[str, Any]],
    night_fill_rate: float,
    timezone: str = TIMEZONE,
) -> dict[str, Any] | None:
    """Estimate water usage during the day.
    
    Logic:
    - Theoretical intake = night_fill_rate × duration in hours
    - Net change = end_depth - start_depth
    - Usage = theoretical_intake - net_change
    
    Args:
        readings: List of sensor readings
        night_fill_rate: Fill rate in depth units per hour (from night analysis)
        timezone: Timezone for local time conversion
        
    Returns:
        Dictionary with usage metrics, or None if insufficient data
    """
    # Get depth readings only
    depth_readings = [
        r for r in readings
        if r.get("code") == "liquid_depth"
    ]
    
    if not depth_readings:
        return None
    
    # Sort by time
    depth_readings.sort(key=lambda x: x.get("event_time", 0))
    
    # Extract depth values
    try:
        depths = [int(r.get("value", 0)) for r in depth_readings]
    except (ValueError, TypeError):
        return None
    
    start_depth = depths[0]
    end_depth = depths[-1]
    min_depth = min(depths)
    max_depth = max(depths)
    
    # Calculate time span in hours
    start_time = depth_readings[0].get("event_time", 0)
    end_time = depth_readings[-1].get("event_time", 0)
    duration_hours = (end_time - start_time) / (1000 * 60 * 60)
    
    if duration_hours <= 0:
        return None
    
    # Theoretical intake if filling continuously at night rate
    theoretical_intake = night_fill_rate * duration_hours
    
    # Net change
    net_change = end_depth - start_depth
    
    # Estimated usage = what came in - what's left more than before
    estimated_usage = theoretical_intake - net_change
    
    return {
        "start_depth": start_depth,
        "end_depth": end_depth,
        "min_depth": min_depth,
        "max_depth": max_depth,
        "net_change": net_change,
        "theoretical_intake_depth": theoretical_intake,
        "estimated_usage_depth": max(0, estimated_usage),  # Can't be negative
        "duration_hours": duration_hours,
        "readings_count": len(depth_readings),
    }


def depth_to_liters(depth: float) -> float:
    """Convert depth units to liters.
    
    Args:
        depth: Depth in sensor units
        
    Returns:
        Volume in liters
    """
    return depth * LITERS_PER_DEPTH_UNIT


def depth_to_percent(depth: float) -> float:
    """Convert depth units to percentage of tank capacity.
    
    Args:
        depth: Depth in sensor units
        
    Returns:
        Fill percentage (0-100)
    """
    if SENSOR_MAX_DEPTH <= 0:
        return 0
    return min(100, max(0, (depth / SENSOR_MAX_DEPTH) * 100))


def analyze_day(
    readings: list[dict[str, Any]],
    date: datetime,
    timezone: str = TIMEZONE,
) -> dict[str, Any]:
    """Perform complete analysis for a single day.
    
    Args:
        readings: List of all sensor readings for the day
        date: Date being analyzed
        timezone: Timezone for local time conversion
        
    Returns:
        Complete daily summary dictionary
    """
    tz = pytz.timezone(timezone)
    
    # Analyze night period for fill rate
    night_analysis = analyze_night_period(readings, timezone)
    
    # Default fill rate if night analysis fails
    fill_rate = night_analysis["rate_per_hour"] if night_analysis else 0
    
    # Analyze usage
    usage_analysis = estimate_daily_usage(readings, fill_rate, timezone)
    
    # Build summary
    summary = {
        "report_date": date.strftime("%Y-%m-%d"),
        "readings_count": len(readings),
        "liquid_depth_count": len([r for r in readings if r.get("code") == "liquid_depth"]),
    }
    
    # Add night period metrics
    if night_analysis:
        summary.update({
            "night_start_depth": night_analysis["start_depth"],
            "night_end_depth": night_analysis["end_depth"],
            "night_duration_hours": round(night_analysis["duration_hours"], 2),
            "night_fill_rate_per_hour": round(night_analysis["rate_per_hour"], 2),
            "night_r_squared": round(night_analysis["r_squared"], 4),
        })
    
    # Add usage metrics
    if usage_analysis:
        summary.update({
            "start_depth": usage_analysis["start_depth"],
            "end_depth": usage_analysis["end_depth"],
            "min_depth": usage_analysis["min_depth"],
            "max_depth": usage_analysis["max_depth"],
            "net_change_depth": usage_analysis["net_change"],
            "estimated_intake_depth": round(usage_analysis["theoretical_intake_depth"], 2),
            "estimated_intake_liters": round(depth_to_liters(usage_analysis["theoretical_intake_depth"]), 2),
            "estimated_usage_depth": round(usage_analysis["estimated_usage_depth"], 2),
            "estimated_usage_liters": round(depth_to_liters(usage_analysis["estimated_usage_depth"]), 2),
        })
    
    return summary


def get_current_level_info(current_depth: int) -> dict[str, Any]:
    """Get current level information for display.
    
    Args:
        current_depth: Current depth reading from sensor
        
    Returns:
        Dictionary with level information
    """
    return {
        "depth": current_depth,
        "liters": round(depth_to_liters(current_depth), 1),
        "percent": round(depth_to_percent(current_depth), 1),
        "total_capacity_liters": TOTAL_CAPACITY_LITERS,
    }


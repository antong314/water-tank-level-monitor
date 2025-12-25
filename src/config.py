"""Configuration and environment variables for Water Tank Monitor."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()


# =============================================================================
# Tuya API Configuration
# =============================================================================
TUYA_CLIENT_ID = os.getenv("TUYA_CLIENT_ID", "")
TUYA_CLIENT_SECRET = os.getenv("TUYA_CLIENT_SECRET", "")
TUYA_BASE_URL = os.getenv("TUYA_BASE_URL", "https://openapi.tuyaus.com")
TUYA_DEVICE_ID = os.getenv("TUYA_DEVICE_ID", "")
TUYA_USER_ID = os.getenv("TUYA_USER_ID", "")


# =============================================================================
# Supabase Configuration
# =============================================================================
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


# =============================================================================
# Email Configuration (using Resend)
# =============================================================================
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "")
EMAIL_TO = os.getenv("EMAIL_TO", "").split(",")


# =============================================================================
# Timezone Configuration
# =============================================================================
TIMEZONE = os.getenv("TIMEZONE", "America/Costa_Rica")


# =============================================================================
# Tank Configuration
# =============================================================================
# Tank setup: 2 × 500L cylindrical tanks
TANK_COUNT = int(os.getenv("TANK_COUNT", "2"))
TANK_CAPACITY_LITERS = int(os.getenv("TANK_CAPACITY_LITERS", "500"))
TOTAL_CAPACITY_LITERS = TANK_COUNT * TANK_CAPACITY_LITERS  # 1000L total

# Placeholder dimensions (UPDATE WITH ACTUAL MEASUREMENTS)
# Typical 500L tank: ~80cm diameter, ~100cm height
TANK_DIAMETER_CM = int(os.getenv("TANK_DIAMETER_CM", "80"))
TANK_HEIGHT_CM = int(os.getenv("TANK_HEIGHT_CM", "100"))

# Sensor calibration
# Based on sample data: depth 75 ≈ 62%, suggesting max depth around 120 units
SENSOR_MIN_DEPTH = int(os.getenv("SENSOR_MIN_DEPTH", "0"))
SENSOR_MAX_DEPTH = int(os.getenv("SENSOR_MAX_DEPTH", "120"))

# Conversion factor: liters per depth unit
# 1000L total / 120 depth units = 8.33 liters per depth unit
LITERS_PER_DEPTH_UNIT = TOTAL_CAPACITY_LITERS / SENSOR_MAX_DEPTH if SENSOR_MAX_DEPTH > 0 else 0


# =============================================================================
# Night Period Configuration (for fill rate analysis)
# =============================================================================
# Night period: midnight to 6am (assumed no water usage)
NIGHT_START_HOUR = 0  # Midnight
NIGHT_END_HOUR = 6    # 6 AM


# =============================================================================
# Data Collection Configuration
# =============================================================================
# How far back to look for logs on first sync (in hours)
INITIAL_SYNC_HOURS = int(os.getenv("INITIAL_SYNC_HOURS", "168"))  # 7 days

# Rate limiting delay between API calls (in seconds)
API_RATE_LIMIT_DELAY = float(os.getenv("API_RATE_LIMIT_DELAY", "0.5"))


def validate_config() -> list[str]:
    """Validate that required configuration is present.
    
    Returns:
        List of missing/invalid configuration items
    """
    errors = []
    
    # Tuya API
    if not TUYA_CLIENT_ID:
        errors.append("TUYA_CLIENT_ID is required")
    if not TUYA_CLIENT_SECRET:
        errors.append("TUYA_CLIENT_SECRET is required")
    if not TUYA_DEVICE_ID:
        errors.append("TUYA_DEVICE_ID is required")
    
    # Supabase
    if not SUPABASE_URL:
        errors.append("SUPABASE_URL is required")
    if not SUPABASE_KEY:
        errors.append("SUPABASE_KEY is required")
    
    return errors


def validate_email_config() -> list[str]:
    """Validate email configuration.
    
    Returns:
        List of missing/invalid configuration items
    """
    errors = []
    
    if not RESEND_API_KEY:
        errors.append("RESEND_API_KEY is required for email")
    if not EMAIL_FROM:
        errors.append("EMAIL_FROM is required for email")
    if not EMAIL_TO or not EMAIL_TO[0]:
        errors.append("EMAIL_TO is required for email")
    
    return errors


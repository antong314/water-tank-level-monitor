"""Data Collector - Cron Job 1: Fetch sensor data from Tuya and store in Supabase.

This job runs hourly to:
1. Authenticate with Tuya API
2. Fetch logs since last sync
3. Deduplicate and insert into Supabase
4. Log sync status

Usage:
    python -m src.data_collector
"""

import time
import logging
from datetime import datetime

from .config import validate_config, INITIAL_SYNC_HOURS
from .tuya_client import TuyaClient, TuyaAPIError
from .supabase_client import SupabaseClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_data_collection() -> dict:
    """Execute the data collection process.
    
    Returns:
        Dictionary with collection results
    """
    logger.info("=" * 60)
    logger.info("WATER TANK DATA COLLECTOR - Starting")
    logger.info("=" * 60)
    
    # Validate configuration
    config_errors = validate_config()
    if config_errors:
        for error in config_errors:
            logger.error(f"Configuration error: {error}")
        return {"success": False, "error": "Configuration validation failed"}
    
    # Initialize clients
    tuya = TuyaClient()
    supabase = SupabaseClient()
    
    try:
        # Determine time range for fetching logs
        end_time_ms = int(time.time() * 1000)
        
        # Check for last successful sync
        last_sync = supabase.get_last_sync()
        last_event_time = supabase.get_last_event_time()
        
        if last_event_time:
            # Start from the last event time + 1ms
            start_time_ms = last_event_time + 1
            logger.info(f"Resuming from last event: {datetime.fromtimestamp(last_event_time / 1000)}")
        elif last_sync and last_sync.get("last_event_time"):
            # Fall back to last sync time
            start_time_ms = last_sync["last_event_time"] + 1
            logger.info(f"Resuming from last sync: {last_sync.get('synced_at')}")
        else:
            # First run - fetch last N hours of data
            start_time_ms = int((time.time() - INITIAL_SYNC_HOURS * 3600) * 1000)
            logger.info(f"First run - fetching last {INITIAL_SYNC_HOURS} hours of data")
        
        # Fetch logs from Tuya
        logger.info(f"Fetching logs from {datetime.fromtimestamp(start_time_ms / 1000)} "
                   f"to {datetime.fromtimestamp(end_time_ms / 1000)}")
        
        logs = tuya.fetch_logs(start_time_ms, end_time_ms)
        logger.info(f"Fetched {len(logs)} log entries from Tuya")
        
        if not logs:
            logger.info("No new logs to sync")
            supabase.log_sync(
                last_event_time=last_event_time,
                records_added=0,
                status="success",
            )
            return {"success": True, "records_added": 0}
        
        # Insert into Supabase
        records_added = supabase.insert_readings(logs)
        logger.info(f"Inserted {records_added} records into Supabase")
        
        # Get the newest event time from fetched logs
        newest_event_time = max(log.get("event_time", 0) for log in logs)
        
        # Log successful sync
        supabase.log_sync(
            last_event_time=newest_event_time,
            records_added=records_added,
            status="success",
        )
        
        # Log some statistics
        depth_logs = [log for log in logs if log.get("code") == "liquid_depth"]
        if depth_logs:
            depths = [int(log.get("value", 0)) for log in depth_logs]
            logger.info(f"Depth readings: {len(depth_logs)}, "
                       f"range: {min(depths)} - {max(depths)}")
        
        logger.info("=" * 60)
        logger.info("DATA COLLECTION COMPLETE")
        logger.info("=" * 60)
        
        return {
            "success": True,
            "records_added": records_added,
            "logs_fetched": len(logs),
            "newest_event_time": newest_event_time,
        }
        
    except TuyaAPIError as e:
        error_msg = f"Tuya API error: {e}"
        logger.error(error_msg)
        supabase.log_sync(
            last_event_time=None,
            records_added=0,
            status="error",
            error_message=error_msg,
        )
        return {"success": False, "error": error_msg}
        
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        logger.exception(error_msg)
        try:
            supabase.log_sync(
                last_event_time=None,
                records_added=0,
                status="error",
                error_message=error_msg,
            )
        except Exception:
            pass  # Don't fail if we can't log the error
        return {"success": False, "error": error_msg}


def main():
    """Entry point for data collector cron job."""
    result = run_data_collection()
    
    if not result.get("success"):
        logger.error(f"Data collection failed: {result.get('error')}")
        exit(1)
    
    logger.info(f"Data collection successful: {result.get('records_added', 0)} records added")


if __name__ == "__main__":
    main()


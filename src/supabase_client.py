"""Supabase client for storing and retrieving water tank data."""

from datetime import datetime, timedelta
from typing import Any

from supabase import create_client, Client
import pytz

from .config import SUPABASE_URL, SUPABASE_KEY, TIMEZONE


class SupabaseClient:
    """Client for interacting with Supabase database."""
    
    def __init__(
        self,
        url: str = SUPABASE_URL,
        key: str = SUPABASE_KEY,
    ):
        self.client: Client = create_client(url, key)
        self.tz = pytz.timezone(TIMEZONE)
    
    # =========================================================================
    # Sensor Readings
    # =========================================================================
    
    def insert_readings(self, readings: list[dict[str, Any]]) -> int:
        """Insert sensor readings into database, deduplicating by event_time and code.
        
        Args:
            readings: List of reading dictionaries from Tuya API
            
        Returns:
            Number of records inserted
        """
        if not readings:
            return 0
        
        # Prepare records for insertion
        records = []
        for reading in readings:
            event_time = reading.get("event_time")
            if not event_time:
                continue
            
            # Convert epoch ms to UTC datetime
            event_time_utc = datetime.fromtimestamp(event_time / 1000, tz=pytz.UTC)
            
            records.append({
                "event_time": event_time,
                "event_time_utc": event_time_utc.isoformat(),
                "code": reading.get("code", ""),
                "value": str(reading.get("value", "")),
                "status": reading.get("status"),
                "event_from": reading.get("event_from"),
                "event_id": reading.get("event_id"),
            })
        
        if not records:
            return 0
        
        # Use upsert with on_conflict to handle duplicates
        result = self.client.table("sensor_readings").upsert(
            records,
            on_conflict="event_time,code",
        ).execute()
        
        return len(result.data) if result.data else 0
    
    def get_last_event_time(self) -> int | None:
        """Get the most recent event_time from sensor_readings.
        
        Returns:
            Most recent event_time in milliseconds, or None if no records
        """
        result = (
            self.client.table("sensor_readings")
            .select("event_time")
            .order("event_time", desc=True)
            .limit(1)
            .execute()
        )
        
        if result.data and len(result.data) > 0:
            return result.data[0]["event_time"]
        return None
    
    def get_readings_for_date(
        self,
        date: datetime,
        code: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get all readings for a specific date (in local timezone).
        
        Args:
            date: Date to query (local timezone)
            code: Optional filter by sensor code (e.g., 'liquid_depth')
            
        Returns:
            List of reading records
        """
        # Get start and end of day in local timezone
        local_date = self.tz.localize(datetime(date.year, date.month, date.day))
        start_utc = local_date.astimezone(pytz.UTC)
        end_utc = (local_date + timedelta(days=1)).astimezone(pytz.UTC)
        
        query = (
            self.client.table("sensor_readings")
            .select("*")
            .gte("event_time_utc", start_utc.isoformat())
            .lt("event_time_utc", end_utc.isoformat())
            .order("event_time")
        )
        
        if code:
            query = query.eq("code", code)
        
        result = query.execute()
        return result.data or []
    
    def get_readings_range(
        self,
        start_time_utc: datetime,
        end_time_utc: datetime,
        code: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get readings within a time range.
        
        Args:
            start_time_utc: Start of range (UTC)
            end_time_utc: End of range (UTC)
            code: Optional filter by sensor code
            
        Returns:
            List of reading records
        """
        query = (
            self.client.table("sensor_readings")
            .select("*")
            .gte("event_time_utc", start_time_utc.isoformat())
            .lt("event_time_utc", end_time_utc.isoformat())
            .order("event_time")
        )
        
        if code:
            query = query.eq("code", code)
        
        result = query.execute()
        return result.data or []
    
    # =========================================================================
    # Sync Log
    # =========================================================================
    
    def log_sync(
        self,
        last_event_time: int | None,
        records_added: int,
        status: str,
        error_message: str | None = None,
    ) -> None:
        """Log a data sync operation.
        
        Args:
            last_event_time: Most recent event timestamp synced
            records_added: Number of records inserted
            status: 'success' or 'error'
            error_message: Error details if status is 'error'
        """
        self.client.table("sync_log").insert({
            "last_event_time": last_event_time,
            "records_added": records_added,
            "status": status,
            "error_message": error_message,
        }).execute()
    
    def get_last_sync(self) -> dict[str, Any] | None:
        """Get the most recent successful sync log entry.
        
        Returns:
            Sync log record or None
        """
        result = (
            self.client.table("sync_log")
            .select("*")
            .eq("status", "success")
            .order("synced_at", desc=True)
            .limit(1)
            .execute()
        )
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    
    # =========================================================================
    # Daily Summaries
    # =========================================================================
    
    def upsert_daily_summary(self, summary: dict[str, Any]) -> None:
        """Insert or update a daily summary.
        
        Args:
            summary: Daily summary data
        """
        self.client.table("daily_summaries").upsert(
            summary,
            on_conflict="report_date",
        ).execute()
    
    def get_daily_summary(self, date: datetime) -> dict[str, Any] | None:
        """Get daily summary for a specific date.
        
        Args:
            date: Date to query
            
        Returns:
            Daily summary record or None
        """
        date_str = date.strftime("%Y-%m-%d")
        
        result = (
            self.client.table("daily_summaries")
            .select("*")
            .eq("report_date", date_str)
            .limit(1)
            .execute()
        )
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    
    def get_recent_summaries(self, days: int = 7) -> list[dict[str, Any]]:
        """Get daily summaries for the last N days.
        
        Args:
            days: Number of days to retrieve
            
        Returns:
            List of daily summary records
        """
        cutoff = datetime.now(self.tz) - timedelta(days=days)
        cutoff_str = cutoff.strftime("%Y-%m-%d")
        
        result = (
            self.client.table("daily_summaries")
            .select("*")
            .gte("report_date", cutoff_str)
            .order("report_date", desc=True)
            .execute()
        )
        
        return result.data or []


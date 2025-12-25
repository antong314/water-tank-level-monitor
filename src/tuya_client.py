"""Tuya API client for fetching water tank sensor data."""

import time
import hmac
import hashlib
import requests
from urllib.parse import parse_qsl, urlencode
from typing import Any

from .config import (
    TUYA_CLIENT_ID,
    TUYA_CLIENT_SECRET,
    TUYA_BASE_URL,
    TUYA_DEVICE_ID,
    API_RATE_LIMIT_DELAY,
)


class TuyaAPIError(Exception):
    """Exception raised for Tuya API errors."""
    pass


class TuyaClient:
    """Client for interacting with Tuya IoT API."""
    
    def __init__(
        self,
        client_id: str = TUYA_CLIENT_ID,
        client_secret: str = TUYA_CLIENT_SECRET,
        base_url: str = TUYA_BASE_URL,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url
        self.token: str | None = None
        self.token_expiry: float = 0
    
    def _sort_query_params(self, path: str, for_signature: bool = False) -> str:
        """Sort query parameters alphabetically as required by Tuya API signature.
        
        Args:
            path: URL path with optional query string
            for_signature: If True, don't URL-encode values (Tuya signs raw values)
            
        Returns:
            Path with sorted query parameters
        """
        if "?" not in path:
            return path
        
        base_path, query_string = path.split("?", 1)
        params = parse_qsl(query_string, keep_blank_values=True)
        sorted_params = sorted(params, key=lambda x: x[0])
        
        if for_signature:
            sorted_query = "&".join(f"{k}={v}" for k, v in sorted_params)
        else:
            sorted_query = urlencode(sorted_params)
        
        return f"{base_path}?{sorted_query}"
    
    def _make_signature(
        self,
        t: str,
        nonce: str = "",
        method: str = "GET",
        path: str = "",
        body: str = "",
        access_token: str = "",
    ) -> str:
        """Create HMAC-SHA256 signature for Tuya API authentication.
        
        Args:
            t: Timestamp in milliseconds
            nonce: Random nonce (optional)
            method: HTTP method
            path: URL path with query parameters
            body: Request body
            access_token: Access token for authenticated requests
            
        Returns:
            Uppercase hex signature
        """
        sorted_path = self._sort_query_params(path, for_signature=True)
        content_sha256 = hashlib.sha256(body.encode("utf-8") if body else b"").hexdigest()
        headers_str = ""
        
        string_to_sign = f"{method}\n{content_sha256}\n{headers_str}\n{sorted_path}"
        
        if access_token:
            sign_str = self.client_id + access_token + t + nonce + string_to_sign
        else:
            sign_str = self.client_id + t + nonce + string_to_sign
        
        sign = hmac.new(
            self.client_secret.encode("utf-8"),
            sign_str.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest().upper()
        
        return sign
    
    def get_token(self) -> bool:
        """Obtain access token from Tuya API.
        
        Returns:
            True if successful, False otherwise
        """
        t = str(int(time.time() * 1000))
        path = "/v1.0/token?grant_type=1"
        sign = self._make_signature(t, method="GET", path=path)
        
        headers = {
            "client_id": self.client_id,
            "sign": sign,
            "t": t,
            "sign_method": "HMAC-SHA256",
        }
        
        url = f"{self.base_url}{path}"
        resp = requests.get(url, headers=headers, timeout=30)
        data = resp.json()
        
        if data.get("success"):
            self.token = data["result"]["access_token"]
            self.token_expiry = time.time() + data["result"]["expire_time"] - 60
            return True
        
        raise TuyaAPIError(f"Failed to get token: {data.get('msg', 'Unknown error')}")
    
    def _ensure_token(self) -> bool:
        """Ensure we have a valid access token."""
        if not self.token or time.time() > self.token_expiry:
            return self.get_token()
        return True
    
    def get(self, path: str) -> dict[str, Any]:
        """Make authenticated GET request to Tuya API.
        
        Args:
            path: API endpoint path with query parameters
            
        Returns:
            JSON response as dictionary
        """
        self._ensure_token()
        
        t = str(int(time.time() * 1000))
        sign = self._make_signature(t, method="GET", path=path, access_token=self.token or "")
        
        headers = {
            "client_id": self.client_id,
            "access_token": self.token or "",
            "sign": sign,
            "t": t,
            "sign_method": "HMAC-SHA256",
        }
        
        url = f"{self.base_url}{path}"
        resp = requests.get(url, headers=headers, timeout=30)
        return resp.json()
    
    def get_device_details(self, device_id: str = TUYA_DEVICE_ID) -> dict[str, Any]:
        """Get device details and current status.
        
        Args:
            device_id: Tuya device ID
            
        Returns:
            Device details including current status
        """
        return self.get(f"/v1.0/devices/{device_id}")
    
    def fetch_logs(
        self,
        start_time_ms: int,
        end_time_ms: int,
        device_id: str = TUYA_DEVICE_ID,
        page_size: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch all device logs between start and end time with pagination.
        
        Args:
            start_time_ms: Start timestamp in milliseconds
            end_time_ms: End timestamp in milliseconds
            device_id: Tuya device ID
            page_size: Number of records per page (max 100)
            
        Returns:
            List of all log entries
        """
        all_logs: list[dict[str, Any]] = []
        current_end_time = end_time_ms
        
        while True:
            params = {
                "type": "7",
                "start_time": str(start_time_ms),
                "end_time": str(current_end_time),
                "size": str(page_size),
            }
            
            sorted_params = sorted(params.items(), key=lambda x: x[0])
            query_string = urlencode(sorted_params)
            url = f"/v1.0/devices/{device_id}/logs?{query_string}"
            
            response = self.get(url)
            
            if not response.get("success") or not response.get("result"):
                break
            
            result = response["result"]
            log_list = result.get("logs", [])
            
            if not log_list:
                break
            
            all_logs.extend(log_list)
            
            has_next = result.get("has_next", False)
            if not has_next:
                break
            
            # Use oldest timestamp - 1ms as new end_time for next page
            oldest_event_time = min(log.get("event_time", 0) for log in log_list)
            current_end_time = oldest_event_time - 1
            
            if current_end_time <= start_time_ms:
                break
            
            # Rate limiting delay
            time.sleep(API_RATE_LIMIT_DELAY)
        
        return all_logs
    
    def get_current_status(self, device_id: str = TUYA_DEVICE_ID) -> dict[str, Any]:
        """Get current sensor status.
        
        Args:
            device_id: Tuya device ID
            
        Returns:
            Dictionary with current status values keyed by code
        """
        details = self.get_device_details(device_id)
        
        if not details.get("success"):
            raise TuyaAPIError(f"Failed to get device status: {details.get('msg', 'Unknown error')}")
        
        result = details["result"]
        status = {}
        
        for item in result.get("status", []):
            status[item["code"]] = item["value"]
        
        return {
            "online": result.get("online", False),
            "update_time": result.get("update_time"),
            "status": status,
        }


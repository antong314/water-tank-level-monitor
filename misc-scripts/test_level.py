#!/usr/bin/env python3
"""
Tuya Water Tank Monitor - Fixed Signature Version

Install: pip install requests
Usage: python tuya_water_tank_v4.py
"""

import time
import hmac
import hashlib
import requests
import json
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qsl, urlencode

# =============================================================================
# YOUR CREDENTIALS
# =============================================================================
CLIENT_ID = "y9gskj4ra8puc8pdu3dc"
CLIENT_SECRET = "edf2efcce8984bd5b7482aa40a0ecfc6"
BASE_URL = "https://openapi.tuyaus.com"

# Your specific device and user
DEVICE_ID = "eb3c06f2af31ffe41cyyvo"
USER_ID = "54T00B6U"

# =============================================================================
# API Helper Class - Fixed Signature
# =============================================================================

class TuyaAPI:
    def __init__(self, client_id, client_secret, base_url):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url
        self.token = None
        self.token_expiry = 0
    
    def _sort_query_params(self, path, for_signature=False):
        """
        Sort query parameters alphabetically as required by Tuya API signature.
        Returns the path with sorted query parameters.
        
        for_signature: If True, don't URL-encode the values (Tuya signs raw values)
        """
        if '?' not in path:
            return path
        
        base_path, query_string = path.split('?', 1)
        params = parse_qsl(query_string, keep_blank_values=True)
        # Sort parameters alphabetically by key
        sorted_params = sorted(params, key=lambda x: x[0])
        
        if for_signature:
            # For signature: use raw values without URL encoding
            sorted_query = "&".join(f"{k}={v}" for k, v in sorted_params)
        else:
            sorted_query = urlencode(sorted_params)
        
        return f"{base_path}?{sorted_query}"
    
    def _make_signature(self, t, nonce="", method="GET", path="", body="", access_token=""):
        """
        Correct Tuya signature algorithm.
        Query parameters in path MUST be sorted alphabetically.
        """
        # Sort query parameters alphabetically (required by Tuya)
        # Use raw values without URL encoding for signature
        sorted_path = self._sort_query_params(path, for_signature=True)
        
        # Content hash (SHA256 of body, or empty string hash)
        content_sha256 = hashlib.sha256(body.encode('utf-8') if body else b'').hexdigest()
        
        # Headers to sign (empty for basic requests)
        headers_str = ""
        
        # String to sign format:
        # HTTPMethod + "\n" + Content-SHA256 + "\n" + Headers + "\n" + URL
        string_to_sign = f"{method}\n{content_sha256}\n{headers_str}\n{sorted_path}"
        
        # Sign string = client_id + [access_token] + t + [nonce] + stringToSign
        if access_token:
            sign_str = self.client_id + access_token + t + nonce + string_to_sign
        else:
            sign_str = self.client_id + t + nonce + string_to_sign
        
        # HMAC-SHA256
        sign = hmac.new(
            self.client_secret.encode('utf-8'),
            sign_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest().upper()
        
        return sign
    
    def get_token(self):
        """Get access token"""
        t = str(int(time.time() * 1000))
        
        # For token request, sign the full path with query string
        path = "/v1.0/token?grant_type=1"
        sign = self._make_signature(t, method="GET", path=path)
        
        headers = {
            "client_id": self.client_id,
            "sign": sign,
            "t": t,
            "sign_method": "HMAC-SHA256",
        }
        
        url = f"{self.base_url}{path}"
        print(f"   Requesting: {url}")
        
        resp = requests.get(url, headers=headers)
        data = resp.json()
        
        if data.get("success"):
            self.token = data["result"]["access_token"]
            self.token_expiry = time.time() + data["result"]["expire_time"] - 60
            return True
        else:
            print(f"   Token error: {data}")
            return False
    
    def _ensure_token(self):
        if not self.token or time.time() > self.token_expiry:
            return self.get_token()
        return True
    
    def get(self, path):
        """Make authenticated GET request"""
        if not self._ensure_token():
            return {"success": False, "msg": "Failed to get token"}
        
        t = str(int(time.time() * 1000))
        sign = self._make_signature(t, method="GET", path=path, access_token=self.token)
        
        headers = {
            "client_id": self.client_id,
            "access_token": self.token,
            "sign": sign,
            "t": t,
            "sign_method": "HMAC-SHA256",
        }
        
        url = f"{self.base_url}{path}"
        resp = requests.get(url, headers=headers)
        return resp.json()


def main():
    api = TuyaAPI(CLIENT_ID, CLIENT_SECRET, BASE_URL)
    
    print("=" * 60)
    print("TUYA WATER TANK MONITOR")
    print("=" * 60)
    print(f"Device ID: {DEVICE_ID}")
    print(f"User ID: {USER_ID}")
    
    # Authenticate
    print("\n[1] Authenticating...")
    if not api.get_token():
        print("\n❌ Authentication failed!")
        print("\nTroubleshooting:")
        print("1. Verify Access ID and Secret in platform.tuya.com → Your Project → Overview")
        print("2. Make sure you selected 'Western America' as your data center")
        print("3. Check that IoT Core API is subscribed and authorized")
        return
    print("✓ Success!")
    
    # Get device details
    print("\n[2] Fetching device details...")
    details = api.get(f"/v1.0/devices/{DEVICE_ID}")
    
    if details.get("success"):
        d = details["result"]
        print(f"\n   Name: {d.get('name')}")
        print(f"   Category: {d.get('category')}")
        print(f"   Product ID: {d.get('product_id')}")
        print(f"   Online: {'🟢 Yes' if d.get('online') else '🔴 No'}")
        print(f"   IP: {d.get('ip')}")
        print(f"   Time Zone: {d.get('time_zone')}")
        
        update_time = d.get('update_time')
        if update_time:
            print(f"   Last Update: {datetime.fromtimestamp(update_time)}")
        
        if d.get('status'):
            print(f"\n   📊 CURRENT STATUS:")
            print("   " + "-" * 40)
            for s in d['status']:
                code = s['code']
                value = s['value']
                
                # Format based on expected values
                if 'liquid_level' in code.lower() or 'level_value' in code.lower():
                    if isinstance(value, (int, float)) and value > 100:
                        print(f"   💧 {code}: {value/1000:.3f}m ({value}mm)")
                    else:
                        print(f"   💧 {code}: {value}")
                elif 'percent' in code.lower() or 'ratio' in code.lower():
                    print(f"   📊 {code}: {value}%")
                elif 'state' in code.lower() or 'status' in code.lower() or 'alarm' in code.lower():
                    print(f"   🚨 {code}: {value}")
                else:
                    print(f"   • {code}: {value}")
    else:
        print(f"   Error: {details}")
        return
    
    # Get device specifications
    print("\n[3] Fetching device specifications...")
    specs = api.get(f"/v1.0/devices/{DEVICE_ID}/specifications")
    
    if specs.get("success"):
        result = specs["result"]
        print(f"   Category: {result.get('category')}")
        
        if result.get('status'):
            print(f"\n   Available Data Points:")
            for s in result['status']:
                print(f"     • {s['code']}: type={s.get('type')}")
                if s.get('values'):
                    print(f"       values: {s.get('values')}")
    else:
        print(f"   {specs.get('msg', 'Not available')}")
    
    # Get all devices for this user
    print(f"\n[4] Fetching all devices for user {USER_ID}...")
    user_devices = api.get(f"/v1.0/users/{USER_ID}/devices")
    
    if user_devices.get("success"):
        devices = user_devices["result"]
        print(f"   Found {len(devices)} device(s):")
        for dev in devices:
            online = "🟢" if dev.get('online') else "🔴"
            print(f"   {online} {dev.get('name')} ({dev.get('id')})")
    else:
        print(f"   {user_devices.get('msg', 'Could not fetch')}")
    
    # Get device logs (fetch ALL with pagination)
    print("\n[5] Fetching device logs (last 7 days)...")
    end_time = int(time.time() * 1000)
    start_time = int((time.time() - 7 * 24 * 3600) * 1000)
    
    all_logs = []
    page = 1
    current_end_time = end_time
    
    while True:
        # Build URL - use time-based pagination instead of row_key
        params = {
            "type": "7",
            "start_time": str(start_time),
            "end_time": str(current_end_time),
            "size": "100"
        }
        
        # Sort params alphabetically and encode properly
        sorted_params = sorted(params.items(), key=lambda x: x[0])
        query_string = urlencode(sorted_params)
        url = f"/v1.0/devices/{DEVICE_ID}/logs?{query_string}"
        
        logs = api.get(url)
        
        if not logs.get("success") or not logs.get("result"):
            print(f"   Error: {logs.get('msg', 'No logs')}")
            print(f"   Response: {logs}")
            break
        
        result = logs["result"]
        log_list = result.get("logs", [])
        
        if not log_list:
            break
            
        all_logs.extend(log_list)
        
        has_next = result.get("has_next", False)
        
        # Get the oldest timestamp from this page to use as end_time for next page
        oldest_event_time = min(log.get('event_time', 0) for log in log_list)
        first_ts = datetime.fromtimestamp(log_list[0].get('event_time', 0) / 1000)
        last_ts = datetime.fromtimestamp(oldest_event_time / 1000)
        
        print(f"   Page {page}: {len(log_list)} entries ({first_ts.strftime('%H:%M:%S')} - {last_ts.strftime('%H:%M:%S')})")
        
        if not has_next:
            break
        
        # Use the oldest timestamp - 1ms as the new end_time for the next page
        current_end_time = oldest_event_time - 1
        
        # Check if we've gone past our start_time
        if current_end_time <= start_time:
            print(f"   Reached start_time boundary")
            break
        
        page += 1
        
        # Small delay to avoid rate limiting
        time.sleep(0.5)
    
    if all_logs:
        print(f"\n   📈 ALL READINGS ({len(all_logs)} total):")
        print("   " + "-" * 50)
        
        for log in all_logs:
            ts = datetime.fromtimestamp(log.get('event_time', 0) / 1000)
            code = log.get('code', '')
            value = log.get('value', '')
            
            # Format value
            if isinstance(value, (int, float)) and value > 100 and 'level' in code.lower():
                value_str = f"{value/1000:.3f}m"
            else:
                value_str = str(value)
            
            print(f"   {ts.strftime('%Y-%m-%d %H:%M:%S')} | {code}: {value_str}")
        
        # Save to file
        filename = 'water_tank_logs.json'
        print(f"\n   💾 Saving to {filename}...")
        with open(filename, 'w') as f:
            json.dump(all_logs, f, indent=2)
        print(f"   ✓ Saved {len(all_logs)} entries!")
    
    # Statistics
    print("\n[6] Checking statistics endpoints...")
    stat_types = api.get(f"/v1.0/devices/{DEVICE_ID}/all-statistic-type")
    
    if stat_types.get("success") and stat_types.get("result"):
        print(f"   Available: {stat_types['result']}")
    else:
        print(f"   No statistics configured")
    
    print("\n" + "=" * 60)
    print("✓ Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
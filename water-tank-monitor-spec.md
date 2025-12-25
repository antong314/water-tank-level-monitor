# Water Tank Monitor - Complete Project Specification

## Overview

A Railway-deployed Python application that monitors water tank levels via Tuya IoT sensors, stores data in Supabase, and sends daily email reports analyzing water usage and spring intake rates.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        WATER TANK MONITOR                               │
│                      (Railway Project)                                  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────┐  ┌─────────────────────────────────┐
│  CRON JOB 1: Data Collector         │  │  CRON JOB 2: Daily Analyzer     │
│  Schedule: Every hour (0 * * * *)   │  │  Schedule: 6 AM Costa Rica      │
│                                     │  │            (0 12 * * * UTC)     │
├─────────────────────────────────────┤  ├─────────────────────────────────┤
│  1. Authenticate with Tuya API      │  │  1. Query last 24h from Supabase│
│  2. Fetch logs since last fetch     │  │  2. Segment into periods:       │
│  3. Dedupe & insert into Supabase   │  │     - Night (midnight-6am) = fill│
│  4. Log sync status                 │  │     - Day (6am-midnight) = mixed│
│                                     │  │  3. Calculate metrics:          │
│  Tables:                            │  │     - Intake rate (from night)  │
│  - sensor_readings (raw data)       │  │     - Estimated usage           │
│  - sync_log (tracking)              │  │     - Min/max levels            │
│                                     │  │  4. Store summary in Supabase   │
│                                     │  │  5. Generate & send email       │
│                                     │  │                                 │
│                                     │  │  Tables:                        │
│                                     │  │  - daily_summaries              │
└─────────────────────────────────────┘  └─────────────────────────────────┘
                    │                                      │
                    ▼                                      ▼
         ┌─────────────────────────────────────────────────────────────┐
         │                      SUPABASE                               │
         └─────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
water-tank-monitor/
├── src/
│   ├── __init__.py
│   ├── config.py              # Environment variables, constants
│   ├── tuya_client.py         # Tuya API authentication & fetching
│   ├── supabase_client.py     # Supabase connection & queries
│   ├── data_collector.py      # Cron Job 1: Fetch & store
│   ├── analyzer.py            # Analysis logic
│   ├── email_builder.py       # HTML email generation
│   ├── email_sender.py        # SMTP sending
│   └── daily_report.py        # Cron Job 2: Analyze & email
├── templates/
│   └── daily_report.html      # Email template
├── scripts/
│   └── init_db.sql            # Supabase schema
├── pyproject.toml
├── railway.json
├── README.md
└── .env.example
```

---

## Environment Variables

```bash
# Tuya API (get from platform.tuya.com)
TUYA_CLIENT_ID=your_tuya_client_id
TUYA_CLIENT_SECRET=your_tuya_client_secret
TUYA_BASE_URL=https://openapi.tuyaus.com
TUYA_DEVICE_ID=your_device_id
TUYA_USER_ID=your_user_id

# Supabase (get from supabase.com dashboard)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_service_role_key

# Email
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your_smtp_user
SMTP_PASSWORD=your_smtp_password
EMAIL_FROM=water-monitor@example.com
EMAIL_TO=recipient@example.com

# Timezone
TIMEZONE=America/Costa_Rica
```

---

## Supabase Database Schema

```sql
-- Raw sensor readings from Tuya
CREATE TABLE sensor_readings (
    id BIGSERIAL PRIMARY KEY,
    event_time BIGINT NOT NULL,           -- Tuya timestamp (ms)
    event_time_utc TIMESTAMPTZ NOT NULL,  -- Converted for queries
    code VARCHAR(50) NOT NULL,            -- liquid_depth, liquid_level_percent, etc.
    value VARCHAR(100) NOT NULL,          -- Sensor value
    status INTEGER,
    event_from INTEGER,
    event_id INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(event_time, code)              -- Prevent duplicates
);

-- Index for efficient date-range queries
CREATE INDEX idx_readings_time ON sensor_readings(event_time_utc);
CREATE INDEX idx_readings_code_time ON sensor_readings(code, event_time_utc);

-- Sync tracking
CREATE TABLE sync_log (
    id SERIAL PRIMARY KEY,
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    last_event_time BIGINT,               -- Most recent event fetched
    records_added INTEGER,
    status VARCHAR(20),                   -- success, error
    error_message TEXT
);

-- Daily analysis summaries
CREATE TABLE daily_summaries (
    id SERIAL PRIMARY KEY,
    report_date DATE NOT NULL UNIQUE,
    
    -- Levels (in depth units from sensor)
    min_depth INTEGER,
    max_depth INTEGER,
    start_depth INTEGER,                  -- At start of day (midnight)
    end_depth INTEGER,                    -- At end of day (midnight)
    
    -- Fill metrics (calculated from night period: midnight-6am)
    night_start_depth INTEGER,
    night_end_depth INTEGER,
    night_duration_hours DECIMAL(5,2),
    night_fill_rate_per_hour DECIMAL(10,2),  -- depth units/hour
    night_r_squared DECIMAL(5,4),            -- Linear regression quality
    
    -- Usage metrics
    estimated_intake_depth DECIMAL(10,2),    -- Theoretical intake all day
    estimated_intake_liters DECIMAL(10,2),
    estimated_usage_depth DECIMAL(10,2),
    estimated_usage_liters DECIMAL(10,2),
    net_change_depth INTEGER,
    
    -- Metadata
    readings_count INTEGER,
    liquid_depth_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Tank Constants (Placeholder - User Will Update)

```python
# config.py - Tank configuration

# Tank setup: 2 × 500L cylindrical tanks
TANK_COUNT = 2
TANK_CAPACITY_LITERS = 500  # Per tank
TOTAL_CAPACITY_LITERS = TANK_COUNT * TANK_CAPACITY_LITERS  # 1000L total

# Placeholder dimensions (UPDATE WITH ACTUAL MEASUREMENTS)
# Typical 500L tank: ~80cm diameter, ~100cm height
TANK_DIAMETER_CM = 80
TANK_HEIGHT_CM = 100

# Sensor calibration (UPDATE BASED ON ACTUAL SENSOR RANGE)
# Looking at the data, depth values range from ~39 to ~77
# Need to determine what 0% and 100% correspond to
SENSOR_MIN_DEPTH = 0    # Empty tank reading
SENSOR_MAX_DEPTH = 120  # Full tank reading (estimate from data showing 75 = 62%)

# Conversion factor: liters per depth unit
# Based on percentage readings: 75 depth = 62%, so max depth ≈ 121
# 1000L total / 120 depth units = 8.33 liters per depth unit
LITERS_PER_DEPTH_UNIT = TOTAL_CAPACITY_LITERS / SENSOR_MAX_DEPTH
```

---

## Tuya API Client (Port from test_level.py)

The existing `test_level.py` contains working Tuya API authentication. Key components:

### Authentication Logic

```python
import time
import hmac
import hashlib
import requests
from urllib.parse import parse_qsl, urlencode

class TuyaAPI:
    def __init__(self, client_id, client_secret, base_url):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url
        self.token = None
        self.token_expiry = 0
    
    def _sort_query_params(self, path, for_signature=False):
        """Sort query parameters alphabetically as required by Tuya API signature."""
        if '?' not in path:
            return path
        
        base_path, query_string = path.split('?', 1)
        params = parse_qsl(query_string, keep_blank_values=True)
        sorted_params = sorted(params, key=lambda x: x[0])
        
        if for_signature:
            sorted_query = "&".join(f"{k}={v}" for k, v in sorted_params)
        else:
            sorted_query = urlencode(sorted_params)
        
        return f"{base_path}?{sorted_query}"
    
    def _make_signature(self, t, nonce="", method="GET", path="", body="", access_token=""):
        """Correct Tuya signature algorithm."""
        sorted_path = self._sort_query_params(path, for_signature=True)
        content_sha256 = hashlib.sha256(body.encode('utf-8') if body else b'').hexdigest()
        headers_str = ""
        string_to_sign = f"{method}\n{content_sha256}\n{headers_str}\n{sorted_path}"
        
        if access_token:
            sign_str = self.client_id + access_token + t + nonce + string_to_sign
        else:
            sign_str = self.client_id + t + nonce + string_to_sign
        
        sign = hmac.new(
            self.client_secret.encode('utf-8'),
            sign_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest().upper()
        
        return sign
    
    def get_token(self):
        """Get access token"""
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
        resp = requests.get(url, headers=headers)
        data = resp.json()
        
        if data.get("success"):
            self.token = data["result"]["access_token"]
            self.token_expiry = time.time() + data["result"]["expire_time"] - 60
            return True
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
```

### Fetching Logs with Pagination

```python
def fetch_logs(api, device_id, start_time_ms, end_time_ms):
    """Fetch all logs between start and end time with pagination."""
    all_logs = []
    current_end_time = end_time_ms
    
    while True:
        params = {
            "type": "7",
            "start_time": str(start_time_ms),
            "end_time": str(current_end_time),
            "size": "100"
        }
        
        sorted_params = sorted(params.items(), key=lambda x: x[0])
        query_string = urlencode(sorted_params)
        url = f"/v1.0/devices/{device_id}/logs?{query_string}"
        
        logs = api.get(url)
        
        if not logs.get("success") or not logs.get("result"):
            break
        
        result = logs["result"]
        log_list = result.get("logs", [])
        
        if not log_list:
            break
            
        all_logs.extend(log_list)
        
        has_next = result.get("has_next", False)
        if not has_next:
            break
        
        # Use oldest timestamp - 1ms as new end_time for next page
        oldest_event_time = min(log.get('event_time', 0) for log in log_list)
        current_end_time = oldest_event_time - 1
        
        if current_end_time <= start_time_ms:
            break
        
        time.sleep(0.5)  # Rate limiting
    
    return all_logs
```

---

## Analysis Logic

### Night Period Analysis (Midnight - 6 AM Costa Rica)

During night hours, assume no water usage - pure filling from spring.
Use linear regression to calculate fill rate.

```python
import numpy as np
from datetime import datetime, timedelta
import pytz

def analyze_night_period(readings, timezone='America/Costa_Rica'):
    """
    Analyze night period (midnight to 6am) to determine fill rate.
    Returns fill rate in depth units per hour.
    """
    tz = pytz.timezone(timezone)
    
    # Filter readings for night period (midnight to 6am local time)
    night_readings = []
    for r in readings:
        if r['code'] != 'liquid_depth':
            continue
        
        # Convert to local time
        utc_time = datetime.fromtimestamp(r['event_time'] / 1000, tz=pytz.UTC)
        local_time = utc_time.astimezone(tz)
        
        # Night = 0:00 to 6:00
        if 0 <= local_time.hour < 6:
            night_readings.append({
                'time': r['event_time'],
                'depth': int(r['value']),
                'local_time': local_time
            })
    
    if len(night_readings) < 2:
        return None
    
    # Sort by time
    night_readings.sort(key=lambda x: x['time'])
    
    # Remove reversals (depth should only increase during fill)
    filtered = [night_readings[0]]
    for r in night_readings[1:]:
        if r['depth'] >= filtered[-1]['depth']:
            filtered.append(r)
    
    if len(filtered) < 2:
        return None
    
    # Linear regression
    times = np.array([(r['time'] - filtered[0]['time']) / (1000 * 60 * 60) for r in filtered])  # Hours
    depths = np.array([r['depth'] for r in filtered])
    
    coeffs = np.polyfit(times, depths, 1)
    rate = coeffs[0]  # Slope = depth units per hour
    
    # Calculate R-squared
    predicted = np.polyval(coeffs, times)
    ss_res = np.sum((depths - predicted) ** 2)
    ss_tot = np.sum((depths - np.mean(depths)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    
    return {
        'rate_per_hour': rate,
        'r_squared': r_squared,
        'start_depth': filtered[0]['depth'],
        'end_depth': filtered[-1]['depth'],
        'duration_hours': times[-1],
        'reading_count': len(filtered)
    }
```

### Daily Usage Estimation

```python
def estimate_daily_usage(readings, night_fill_rate, timezone='America/Costa_Rica'):
    """
    Estimate water usage during the day.
    
    Logic:
    - Theoretical intake = night_fill_rate × 24 hours
    - Net change = end_depth - start_depth
    - Usage = theoretical_intake - net_change
    """
    tz = pytz.timezone(timezone)
    
    # Get depth readings only
    depth_readings = [r for r in readings if r['code'] == 'liquid_depth']
    if not depth_readings:
        return None
    
    # Sort by time
    depth_readings.sort(key=lambda x: x['event_time'])
    
    start_depth = int(depth_readings[0]['value'])
    end_depth = int(depth_readings[-1]['value'])
    min_depth = min(int(r['value']) for r in depth_readings)
    max_depth = max(int(r['value']) for r in depth_readings)
    
    # Calculate time span in hours
    duration_hours = (depth_readings[-1]['event_time'] - depth_readings[0]['event_time']) / (1000 * 60 * 60)
    
    # Theoretical intake if filling continuously at night rate
    theoretical_intake = night_fill_rate * duration_hours
    
    # Net change
    net_change = end_depth - start_depth
    
    # Estimated usage
    estimated_usage = theoretical_intake - net_change
    
    return {
        'start_depth': start_depth,
        'end_depth': end_depth,
        'min_depth': min_depth,
        'max_depth': max_depth,
        'net_change': net_change,
        'theoretical_intake_depth': theoretical_intake,
        'estimated_usage_depth': max(0, estimated_usage),  # Can't be negative
        'duration_hours': duration_hours,
        'readings_count': len(depth_readings)
    }
```

---

## Sample Data Reference

From `water_tank_logs.csv`, the data structure is:

```csv
event_time,event_time_formatted,code,value,status,event_from,event_id
1766690709683,2025-12-25 14:25:09,liquid_depth,75,1,1,7
1766690706393,2025-12-25 14:25:06,liquid_depth,74,1,1,7
1766690705249,2025-12-25 14:25:05,liquid_level_percent,62,1,1,7
```

Key observations:
- `event_time` is milliseconds since epoch
- `code` values: `liquid_depth`, `liquid_level_percent`, `liquid_state`
- `liquid_depth` ranges from ~39 to ~77 in the sample
- `liquid_level_percent` ranges from ~32% to ~64%
- Data has sensor noise (values oscillate ±1-2 units)
- `liquid_state` can be `normal` or `lower_alarm`

---

## Email Template (HTML)

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f5f5f5;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #0ea5e9, #0284c7);
            color: white;
            padding: 24px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 24px;
        }
        .header .date {
            opacity: 0.9;
            margin-top: 8px;
        }
        .content {
            padding: 24px;
        }
        .section {
            margin-bottom: 24px;
        }
        .section-title {
            font-size: 14px;
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 12px;
        }
        .metric {
            display: flex;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid #e2e8f0;
        }
        .metric:last-child {
            border-bottom: none;
        }
        .metric-label {
            color: #475569;
        }
        .metric-value {
            font-weight: 600;
            color: #0f172a;
        }
        .metric-value.highlight {
            color: #0ea5e9;
            font-size: 18px;
        }
        .footer {
            background: #f8fafc;
            padding: 16px 24px;
            text-align: center;
            color: #64748b;
            font-size: 12px;
        }
        .level-bar {
            height: 24px;
            background: #e2e8f0;
            border-radius: 12px;
            overflow: hidden;
            margin-top: 8px;
        }
        .level-fill {
            height: 100%;
            background: linear-gradient(90deg, #0ea5e9, #06b6d4);
            border-radius: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💧 Water Tank Report</h1>
            <div class="date">{{ report_date }}</div>
        </div>
        
        <div class="content">
            <div class="section">
                <div class="section-title">Current Level</div>
                <div class="metric">
                    <span class="metric-label">Tank Level</span>
                    <span class="metric-value highlight">{{ current_percent }}% ({{ current_liters }}L)</span>
                </div>
                <div class="level-bar">
                    <div class="level-fill" style="width: {{ current_percent }}%"></div>
                </div>
            </div>
            
            <div class="section">
                <div class="section-title">Daily Range</div>
                <div class="metric">
                    <span class="metric-label">Minimum</span>
                    <span class="metric-value">{{ min_depth }} units ({{ min_liters }}L)</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Maximum</span>
                    <span class="metric-value">{{ max_depth }} units ({{ max_liters }}L)</span>
                </div>
            </div>
            
            <div class="section">
                <div class="section-title">Spring Intake</div>
                <div class="metric">
                    <span class="metric-label">Fill Rate (overnight)</span>
                    <span class="metric-value">{{ fill_rate }} units/hour</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Est. Daily Intake</span>
                    <span class="metric-value">{{ daily_intake_liters }}L</span>
                </div>
            </div>
            
            <div class="section">
                <div class="section-title">Water Usage</div>
                <div class="metric">
                    <span class="metric-label">Estimated Usage</span>
                    <span class="metric-value highlight">{{ usage_liters }}L</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Net Change</span>
                    <span class="metric-value">{{ net_change }} units</span>
                </div>
            </div>
        </div>
        
        <div class="footer">
            Based on {{ readings_count }} sensor readings
        </div>
    </div>
</body>
</html>
```

---

## Railway Configuration

### railway.json

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "numReplicas": 1,
    "sleepApplication": false,
    "restartPolicyType": "ON_FAILURE"
  }
}
```

### Cron Job Configuration (in Railway Dashboard)

1. **Service: data-collector**
   - Command: `python -m src.data_collector`
   - Schedule: `0 * * * *` (every hour at :00)

2. **Service: daily-report**
   - Command: `python -m src.daily_report`
   - Schedule: `0 12 * * *` (12:00 UTC = 6:00 AM Costa Rica)

---

## pyproject.toml

```toml
[project]
name = "water-tank-monitor"
version = "0.1.0"
description = "Water tank monitoring with Tuya IoT sensors"
requires-python = ">=3.11"

dependencies = [
    "requests>=2.31.0",
    "supabase>=2.0.0",
    "numpy>=1.26.0",
    "pytz>=2024.1",
    "jinja2>=3.1.0",
    "python-dotenv>=1.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

---

## Implementation Checklist

1. [x] Create project directory: `water-tank-monitor/`
2. [x] Initialize with `pyproject.toml`
3. [x] Create Supabase project and run SQL schema
4. [x] Create `src/config.py` with environment loading
5. [x] Create `src/tuya_client.py` (port from test_level.py)
6. [x] Create `src/supabase_client.py`
7. [x] Create `src/data_collector.py` (Cron Job 1)
8. [x] Create `src/analyzer.py`
9. [x] Create `src/email_builder.py`
10. [x] Create `src/email_sender.py`
11. [x] Create `src/daily_report.py` (Cron Job 2)
12. [x] Create `templates/daily_report.html`
13. [x] Create `.env.example`
14. [x] Create `README.md`
15. [ ] Deploy to Railway
16. [ ] Configure cron schedules in Railway

---

## Reference Files Location

- Original Tuya script: `misc-scripts/test_level.py`
- Sample data: `misc-scripts/water_tank_logs.csv`
- Analysis reference: `misc-scripts/water_tank_analysis_summary.md`

---

## Notes

1. **Sensor Calibration**: The depth-to-liters conversion needs calibration. From sample data, depth 75 ≈ 62%, suggesting max depth around 120 units.

2. **Timezone**: Costa Rica is UTC-6 (no daylight saving). 6 AM local = 12:00 UTC.

3. **Data Quality**: Sensor has noise (±1-2 unit oscillations). Analysis should use:
   - Linear regression for fill rate (smooths noise)
   - Filtering out reversals during fill periods
   - Reasonable thresholds for change detection

4. **Two Tanks**: The system monitors 2 × 500L tanks. The sensor appears to measure combined level.


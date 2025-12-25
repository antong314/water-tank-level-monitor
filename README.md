# Water Tank Monitor

A Python application that monitors water tank levels via Tuya IoT sensors, stores data in Supabase, and sends daily email reports analyzing water usage and spring intake rates.

## Features

- 📡 **Real-time Data Collection**: Fetches sensor data from Tuya IoT devices hourly
- 💾 **Persistent Storage**: Stores all readings in Supabase for historical analysis
- 📊 **Smart Analysis**: Calculates fill rates using linear regression on overnight data
- 📧 **Daily Reports**: Beautiful HTML email reports with usage statistics
- 🚂 **Railway Ready**: Configured for easy deployment on Railway.app

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        WATER TANK MONITOR                               │
│                      (Railway Project)                                  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────┐  ┌─────────────────────────────────┐
│  CRON JOB 1: Data Collector     │  │  CRON JOB 2: Daily Analyzer     │
│  Schedule: Every hour           │  │  Schedule: 6 AM Costa Rica      │
│                                 │  │            (12:00 UTC)          │
├─────────────────────────────────┤  ├─────────────────────────────────┤
│  1. Authenticate with Tuya API  │  │  1. Query last 24h from Supabase│
│  2. Fetch logs since last fetch │  │  2. Analyze night period        │
│  3. Dedupe & insert into Supabase│  │  3. Calculate fill rate & usage│
│  4. Log sync status             │  │  4. Store summary in Supabase   │
│                                 │  │  5. Generate & send email       │
└─────────────────────────────────┘  └─────────────────────────────────┘
                    │                                      │
                    ▼                                      ▼
         ┌─────────────────────────────────────────────────────────────┐
         │                      SUPABASE                               │
         │  sensor_readings | sync_log | daily_summaries               │
         └─────────────────────────────────────────────────────────────┘
```

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

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Tuya IoT Cloud account with water level sensor
- Supabase account
- SMTP email credentials (for reports)

### 2. Installation

```bash
# Clone the repository
cd water-tank-monitor

# Install dependencies
pip install -e .

# Or with uv
uv pip install -e .
```

### 3. Database Setup

1. Create a new project in [Supabase](https://supabase.com)
2. Go to SQL Editor
3. Run the contents of `scripts/init_db.sql`

### 4. Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required environment variables:

| Variable | Description |
|----------|-------------|
| `TUYA_CLIENT_ID` | Tuya IoT Cloud Access ID |
| `TUYA_CLIENT_SECRET` | Tuya IoT Cloud Access Secret |
| `TUYA_DEVICE_ID` | Your water level sensor device ID |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase anon/service key |
| `SMTP_HOST` | SMTP server hostname |
| `SMTP_PORT` | SMTP port (587 for TLS, 465 for SSL) |
| `SMTP_USER` | SMTP username |
| `SMTP_PASSWORD` | SMTP password |
| `EMAIL_FROM` | Sender email address |
| `EMAIL_TO` | Recipient email(s), comma-separated |

### 5. Running Locally

**Data Collector** (run hourly):
```bash
python -m src.data_collector
```

**Daily Report** (run daily at 6 AM):
```bash
python -m src.daily_report
```

## Deployment on Railway

### 1. Create Railway Project

1. Go to [Railway.app](https://railway.app)
2. Create new project from GitHub repo
3. Add environment variables in Railway dashboard

### 2. Configure Cron Jobs

Create two services in Railway:

**Service 1: Data Collector**
- Command: `python -m src.data_collector`
- Schedule: `0 * * * *` (every hour)

**Service 2: Daily Report**
- Command: `python -m src.daily_report`
- Schedule: `0 12 * * *` (12:00 UTC = 6:00 AM Costa Rica)

## Analysis Logic

### Night Period Analysis

During night hours (midnight to 6 AM), the system assumes no water usage and calculates the spring fill rate using linear regression:

1. Filter readings for night period
2. Remove any depth reversals (depth should only increase)
3. Fit linear regression: `depth = rate × time + intercept`
4. Extract fill rate (slope) in depth units per hour
5. Calculate R² to measure fit quality

### Usage Estimation

Daily water usage is calculated as:

```
Theoretical Intake = Fill Rate × 24 hours
Net Change = End Depth - Start Depth
Estimated Usage = Theoretical Intake - Net Change
```

## Tank Configuration

Default configuration (update in `.env` or `src/config.py`):

| Parameter | Default | Description |
|-----------|---------|-------------|
| `TANK_COUNT` | 2 | Number of tanks |
| `TANK_CAPACITY_LITERS` | 500 | Capacity per tank (liters) |
| `SENSOR_MAX_DEPTH` | 120 | Sensor reading at 100% full |

The conversion factor is: `1000L ÷ 120 units ≈ 8.33 liters per depth unit`

## Tuya IoT Setup

### Getting Credentials

1. Go to [Tuya IoT Platform](https://platform.tuya.com)
2. Create a Cloud project (select "Western America" data center for US)
3. Subscribe to "IoT Core" API
4. Link your Smart Life app and devices
5. Find your device ID in the "Devices" section

### Sensor Data

The water level sensor provides these readings:

| Code | Description | Example |
|------|-------------|---------|
| `liquid_depth` | Water depth in sensor units | 75 |
| `liquid_level_percent` | Fill percentage | 62 |
| `liquid_state` | Alarm state | normal, lower_alarm |

## Troubleshooting

### Tuya API Errors

- **Sign verification failed**: Check that query parameters are sorted alphabetically
- **Token expired**: The client automatically refreshes tokens
- **No data returned**: Verify device ID and check device is online

### Supabase Connection Issues

- Verify `SUPABASE_URL` and `SUPABASE_KEY` are correct
- Check Row Level Security policies if enabled
- Ensure tables exist (run `init_db.sql`)

### Email Not Sending

- Verify SMTP credentials
- Check firewall/network allows outbound SMTP
- Some providers require "App Passwords" (Gmail, etc.)

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions welcome! Please open an issue or submit a pull request.

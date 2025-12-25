-- Water Tank Monitor - Supabase Database Schema
-- Run this script in your Supabase SQL Editor to create the required tables

-- =============================================================================
-- Raw sensor readings from Tuya
-- =============================================================================
CREATE TABLE IF NOT EXISTS sensor_readings (
    id BIGSERIAL PRIMARY KEY,
    event_time BIGINT NOT NULL,           -- Tuya timestamp (milliseconds since epoch)
    event_time_utc TIMESTAMPTZ NOT NULL,  -- Converted for queries
    code VARCHAR(50) NOT NULL,            -- liquid_depth, liquid_level_percent, etc.
    value VARCHAR(100) NOT NULL,          -- Sensor value
    status INTEGER,                       -- Tuya status code
    event_from INTEGER,                   -- Event source
    event_id INTEGER,                     -- Event type ID
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(event_time, code)              -- Prevent duplicates
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_readings_time ON sensor_readings(event_time_utc);
CREATE INDEX IF NOT EXISTS idx_readings_code_time ON sensor_readings(code, event_time_utc);
CREATE INDEX IF NOT EXISTS idx_readings_event_time ON sensor_readings(event_time DESC);

-- Enable Row Level Security (optional but recommended)
ALTER TABLE sensor_readings ENABLE ROW LEVEL SECURITY;

-- Create policy for authenticated users (adjust as needed)
-- DROP POLICY IF EXISTS "Allow all for authenticated" ON sensor_readings;
-- CREATE POLICY "Allow all for authenticated" ON sensor_readings FOR ALL USING (true);

-- =============================================================================
-- Sync tracking
-- =============================================================================
CREATE TABLE IF NOT EXISTS sync_log (
    id SERIAL PRIMARY KEY,
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    last_event_time BIGINT,               -- Most recent event fetched
    records_added INTEGER,
    status VARCHAR(20),                   -- success, error
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_sync_log_synced_at ON sync_log(synced_at DESC);
CREATE INDEX IF NOT EXISTS idx_sync_log_status ON sync_log(status);

-- =============================================================================
-- Daily analysis summaries
-- =============================================================================
CREATE TABLE IF NOT EXISTS daily_summaries (
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

CREATE INDEX IF NOT EXISTS idx_daily_summaries_date ON daily_summaries(report_date DESC);

-- =============================================================================
-- Comments for documentation
-- =============================================================================
COMMENT ON TABLE sensor_readings IS 'Raw sensor readings from Tuya IoT water level sensor';
COMMENT ON COLUMN sensor_readings.event_time IS 'Original Tuya timestamp in milliseconds since epoch';
COMMENT ON COLUMN sensor_readings.code IS 'Sensor code: liquid_depth, liquid_level_percent, liquid_state';
COMMENT ON COLUMN sensor_readings.value IS 'Sensor reading value (stored as string for flexibility)';

COMMENT ON TABLE sync_log IS 'Log of data synchronization jobs from Tuya to Supabase';
COMMENT ON COLUMN sync_log.last_event_time IS 'Most recent event_time successfully synced (for pagination)';

COMMENT ON TABLE daily_summaries IS 'Pre-computed daily analysis of water tank data';
COMMENT ON COLUMN daily_summaries.night_fill_rate_per_hour IS 'Fill rate calculated from midnight-6am period (depth units/hour)';
COMMENT ON COLUMN daily_summaries.night_r_squared IS 'R-squared value from linear regression (1.0 = perfect fit)';

-- =============================================================================
-- Useful queries (for reference)
-- =============================================================================

-- Get latest readings
-- SELECT * FROM sensor_readings ORDER BY event_time DESC LIMIT 10;

-- Get readings for a specific date
-- SELECT * FROM sensor_readings 
-- WHERE event_time_utc >= '2025-01-01' AND event_time_utc < '2025-01-02'
-- ORDER BY event_time;

-- Get liquid_depth readings only
-- SELECT * FROM sensor_readings 
-- WHERE code = 'liquid_depth' 
-- ORDER BY event_time DESC LIMIT 100;

-- Check sync status
-- SELECT * FROM sync_log ORDER BY synced_at DESC LIMIT 5;

-- Get recent daily summaries
-- SELECT * FROM daily_summaries ORDER BY report_date DESC LIMIT 7;


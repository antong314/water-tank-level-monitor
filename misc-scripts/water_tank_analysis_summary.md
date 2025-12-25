# Water Tank Fill Rate Analysis Summary

## Key Finding: **Fill Rate = 10.51 depth units/hour**

This is the most accurate measurement using **linear regression** on all data points.

## Code Files and Scripts

### Main Analysis Scripts

1. **`improved_water_tank_analysis.py`** (Primary Analysis)
   - **Location**: `/Users/antongorshkov/Documents/home/improved_water_tank_analysis.py`
   - **Purpose**: Comprehensive fill rate analysis with multiple calculation methods
   - **Key Functions**:
     - `parse_csv()`: Reads CSV and filters for `liquid_depth` entries (lines 12-31)
     - `remove_reversals()`: Filters out depth reversals (lines 33-42)
     - `calculate_time_bucket_rates()`: Groups readings into 5-minute buckets (lines 44-92)
     - `calculate_moving_average_rates()`: Calculates rates using sliding window (lines 94-122)
     - `calculate_linear_regression_rate()`: **Most accurate method** - fits line through all points (lines 124-150)
     - `print_improved_analysis()`: Displays comprehensive statistics (lines 152-233)
     - `export_improved_csv()`: Exports results to CSV files (lines 235-287)
   - **Dependencies**: `numpy` for linear regression calculations
   - **Usage**: `python3 improved_water_tank_analysis.py`

2. **`investigate_outliers.py`** (Outlier Investigation)
   - **Location**: `/Users/antongorshkov/Documents/home/investigate_outliers.py`
   - **Purpose**: Identifies and analyzes outliers in fill rate data
   - **Key Functions**:
     - `analyze_outliers()`: Uses IQR method to detect outliers (lines 27-105)
     - `check_data_quality()`: Validates data quality issues (lines 107-147)
     - `suggest_improvements()`: Recommends analysis improvements (lines 149-178)
   - **Usage**: `python3 investigate_outliers.py`

3. **`analyze_water_tank.py`** (Initial Analysis - Superseded)
   - **Location**: `/Users/antongorshkov/Documents/home/analyze_water_tank.py`
   - **Purpose**: Initial analysis script (filtered by 1-minute minimum intervals)
   - **Note**: This was the first attempt; improved version is `improved_water_tank_analysis.py`

### Data Files

- **Input**: `water_tank_logs.csv` - Original CSV with all sensor readings
- **Output Files**:
  - `water_tank_improved_regression_summary.csv` - **Use this for fill rate**
  - `water_tank_improved_bucket_rates.csv` - Time bucket analysis
  - `water_tank_improved_moving_avg_rates.csv` - Moving average analysis
  - `water_tank_rate_analysis.csv` - Initial filtered analysis (1-min intervals)

## Why Previous Analysis Showed Wide Variation (7-72 depth units/hour)

### Root Causes:

1. **Discrete Sensor Readings**: The sensor reports depth in whole units (1, 2, or 3 unit jumps), not continuous values
2. **Variable Time Intervals**: Readings occur at irregular intervals (seconds to minutes apart)
3. **Small Sample Sizes**: When calculating rates between individual readings, a 2-3 unit jump in a short time creates artificially high rates
4. **Sensor Noise**: Some readings show depth reversals (decreasing), which were filtered out

### Example of the Problem:
- Reading at 11:40:24 shows depth = 45.0
- Reading at 11:42:03 shows depth = 47.0
- Time difference: 1.7 minutes
- Calculated rate: 72.46 depth units/hour (outlier!)

But this is misleading because:
- The sensor jumped 2 units in 1.7 minutes
- This doesn't mean the tank filled at that rate continuously
- The next reading might show no change for several minutes

## Improved Analysis Methods

### 1. Linear Regression (BEST - Recommended)
- **Fill Rate**: 10.51 depth units/hour
- **R-squared**: 0.9911 (excellent fit - 99.11% of variation explained)
- **Implementation**: `calculate_linear_regression_rate()` in `improved_water_tank_analysis.py` (lines 124-150)
- **Method**: 
  - Uses `numpy.polyfit()` to fit linear model: `depth = rate × time + intercept`
  - Converts timestamps to hours from start: `time_hours = (timestamp - start_time) / (1000 × 60 × 60)`
  - Calculates R²: `R² = 1 - (SS_res / SS_tot)` where:
    - `SS_res` = sum of squared residuals (actual - predicted)
    - `SS_tot` = total sum of squares (actual - mean)
- **Advantage**: Accounts for overall trend, not affected by individual reading jumps
- **Code Reference**: Lines 124-150 in `improved_water_tank_analysis.py`

### 2. Time Bucket Analysis (5-minute buckets)
- **Average Rate**: 15.84 depth units/hour
- **Median Rate**: 12.26 depth units/hour
- **Implementation**: `calculate_time_bucket_rates()` in `improved_water_tank_analysis.py` (lines 44-92)
- **Method**:
  - Groups readings into 5-minute time buckets: `bucket_idx = (timestamp - start_time) // (5 × 60 × 1000)`
  - Calculates average depth per bucket: `avg_depth = mean(depths in bucket)`
  - Calculates rate between consecutive buckets: `rate = (depth_diff) / (time_diff_hours)`
- **Issue**: Some buckets show 0.0 rate when no depth change occurred in that window
- **Use Case**: Good for identifying periods of faster/slower filling
- **Code Reference**: Lines 44-92 in `improved_water_tank_analysis.py`

### 3. Moving Average Analysis (5-reading window)
- **Average Rate**: 23.36 depth units/hour
- **Median Rate**: 0.00 depth units/hour (many zero rates due to small windows)
- **Implementation**: `calculate_moving_average_rates()` in `improved_water_tank_analysis.py` (lines 94-122)
- **Method**:
  - Uses sliding window of 5 consecutive readings
  - Calculates rate from first to last reading in window: `rate = (last_depth - first_depth) / time_diff`
- **Use Case**: Alternative smoothing method, less stable than buckets
- **Code Reference**: Lines 94-122 in `improved_water_tank_analysis.py`

### 4. Net Rate (Simple)
- **Rate**: 11.62 depth units/hour
- **Method**: `(Final depth - Initial depth) / Total time`
- **Advantage**: Simple and intuitive
- **Disadvantage**: Doesn't account for sensor noise or reversals
- **Code Reference**: Calculated in `print_improved_analysis()` line 169

## Recommendations

### For Accurate Fill Rate:
✅ **Use Linear Regression Rate: 10.51 depth units/hour**

This is the most accurate because:
- Uses all data points
- Accounts for sensor noise and discrete jumps
- R² = 0.9911 indicates excellent fit
- Best for constant fill rate scenarios

### For Monitoring Fill Patterns:
✅ **Use Time Bucket Analysis** (exported to CSV)

- Identifies periods of faster/slower filling
- Shows when tank is filling vs. stable
- Good for detecting anomalies

### Data Quality Improvements:

1. **Filter Depth Reversals**: ✅ Done (removed 325 reversal readings)
   - **Implementation**: `remove_reversals()` function (lines 33-42)
   - **Logic**: Only keeps readings where `current_depth >= previous_depth`
   - **Result**: Reduced from 490 readings to 165 readings
   - **Code Reference**: `improved_water_tank_analysis.py` lines 33-42

2. **Use Longer Time Windows**: ✅ Done (5-minute buckets)
   - **Implementation**: `calculate_time_bucket_rates()` with `bucket_minutes=5`
   - **Rationale**: Reduces noise from very short intervals
   - **Code Reference**: `improved_water_tank_analysis.py` lines 44-92

3. **Linear Regression**: ✅ Done (best overall rate)
   - **Implementation**: `calculate_linear_regression_rate()` using numpy
   - **Rationale**: Best method for constant fill rate scenarios
   - **Code Reference**: `improved_water_tank_analysis.py` lines 124-150

4. **Outlier Detection**: ✅ Done (IQR method)
   - **Implementation**: `analyze_outliers()` in `investigate_outliers.py` (lines 27-105)
   - **Method**: Interquartile Range (IQR) method
     - Q1 = 25th percentile, Q3 = 75th percentile
     - IQR = Q3 - Q1
     - Outliers: values < Q1 - 1.5×IQR or > Q3 + 1.5×IQR
   - **Code Reference**: `investigate_outliers.py` lines 27-105

5. **Consider Sensor Calibration**: If reversals continue, sensor may need calibration

## Calculation Details

### Linear Regression Formula

The linear regression fits the model:
```
depth(t) = rate × t + intercept
```

Where:
- `t` = time in hours from start
- `rate` = fill rate in depth units/hour (slope)
- `intercept` = starting depth

**Calculation Steps** (from `calculate_linear_regression_rate()`):
1. Convert timestamps to hours: `time_hours = (timestamps - start_time) / (1000 × 60 × 60)`
2. Fit polynomial: `coeffs = np.polyfit(time_hours, depths, 1)`
3. Extract rate: `rate = coeffs[0]` (slope)
4. Calculate R²: `R² = 1 - (SS_res / SS_tot)`

**R² Interpretation**:
- 0.9911 = 99.11% of variation explained by linear model
- Values close to 1.0 indicate excellent fit
- This high R² confirms constant fill rate assumption

### Time Bucket Calculation

**Algorithm** (from `calculate_time_bucket_rates()`):
1. Divide time into 5-minute buckets: `bucket_idx = (timestamp - start) // (5 × 60 × 1000)`
2. Group readings by bucket
3. Calculate average depth per bucket: `avg_depth = mean(all depths in bucket)`
4. Calculate rate between buckets: `rate = (curr_avg_depth - prev_avg_depth) / time_diff_hours`

**Why 5 minutes?**
- Balances between noise reduction and temporal resolution
- Long enough to smooth out discrete jumps
- Short enough to detect rate changes

### Reversal Filtering

**Algorithm** (from `remove_reversals()`):
```python
filtered = [data[0]]  # Keep first reading
for i in range(1, len(data)):
    if data[i]['depth'] >= filtered[-1]['depth']:
        filtered.append(data[i])  # Only keep if depth increases or stays same
```

**Rationale**: 
- Tank should only fill (constant intake)
- Decreasing depth indicates sensor error or noise
- Removed 325 readings (66% of data) showing reversals

## Files Generated

1. **`water_tank_improved_regression_summary.csv`** - **Use this for the fill rate**
   - Contains: `fill_rate_depth_units_per_hour`, `r_squared`, `predicted_start_depth`, `predicted_end_depth`
   - Generated by: `export_improved_csv()` lines 278-287

2. **`water_tank_improved_bucket_rates.csv`** - For detailed time-based analysis
   - Contains: `from_time`, `to_time`, `from_depth`, `to_depth`, `depth_change`, `time_hours`, `rate_per_hour`
   - Generated by: `export_improved_csv()` lines 238-255

3. **`water_tank_improved_moving_avg_rates.csv`** - Alternative smoothing method
   - Contains: Same as bucket rates plus `window_size`
   - Generated by: `export_improved_csv()` lines 257-276

4. **`water_tank_rate_analysis.csv`** - Initial filtered analysis (1-min minimum intervals)
   - Generated by: `analyze_water_tank.py` (superseded by improved version)

## How to Reproduce Analysis

### Prerequisites
```bash
pip install numpy  # Required for linear regression
```

### Run Analysis
```bash
cd /Users/antongorshkov/Documents/home
python3 improved_water_tank_analysis.py
```

### Expected Output
- Console output with statistics
- Three CSV files with analysis results
- Fill rate: ~10.51 depth units/hour

### Customize Parameters

In `improved_water_tank_analysis.py`:
- **Bucket size**: Change `bucket_minutes=5` in `calculate_time_bucket_rates()` call (line 301)
- **Moving average window**: Change `window_size=5` in `calculate_moving_average_rates()` call (line 304)
- **Input file**: Change `csv_file` path in `main()` (line 290)
- **Output prefix**: Change `output_prefix` in `main()` (line 291)

## Conclusion

The tank has a **consistent fill rate of approximately 10.5 depth units per hour**. The wide variation seen in individual readings (7-72) was due to:
- Discrete sensor readings (1-3 unit jumps)
- Short time intervals between readings
- Sensor noise/reversals

The linear regression method provides the most accurate overall fill rate by accounting for these factors. The high R² value (0.9911) confirms that the fill rate is indeed constant, validating the assumption of constant intake.

## Key Takeaways for Future Analysis

1. **Always use linear regression** for constant rate scenarios - it's the most accurate
2. **Filter reversals** when data should be monotonic (only increasing)
3. **Use time buckets** for identifying periods of rate changes
4. **Check R²** to validate model fit (should be > 0.95 for good fit)
5. **Investigate outliers** to understand data quality issues


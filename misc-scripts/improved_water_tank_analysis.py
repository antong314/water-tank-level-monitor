#!/usr/bin/env python3
"""
Improved water tank fill rate analysis with better smoothing and outlier handling.
"""

import csv
import statistics
from datetime import datetime
from collections import defaultdict
import numpy as np

def parse_csv(csv_file_path):
    """Parse CSV and filter for liquid_depth entries."""
    liquid_depth_data = []
    
    with open(csv_file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['code'] == 'liquid_depth':
                liquid_depth_data.append({
                    'timestamp': int(row['event_time']),
                    'datetime': row['event_time_formatted'],
                    'depth': float(row['value']),
                    'status': row['status'],
                    'event_id': row['event_id']
                })
    
    # Sort by timestamp (oldest first)
    liquid_depth_data.sort(key=lambda x: x['timestamp'])
    
    return liquid_depth_data

def remove_reversals(data):
    """Remove depth reversals (assumes tank only fills, never drains)."""
    filtered = [data[0]]  # Keep first reading
    
    for i in range(1, len(data)):
        if data[i]['depth'] >= filtered[-1]['depth']:
            filtered.append(data[i])
        # Skip readings that show depth decreasing
    
    return filtered

def calculate_time_bucket_rates(data, bucket_minutes=5):
    """Calculate rates using time buckets for more stable measurements."""
    bucket_ms = bucket_minutes * 60 * 1000
    buckets = defaultdict(list)
    
    # Group readings into time buckets
    start_time = data[0]['timestamp']
    for reading in data:
        bucket_idx = (reading['timestamp'] - start_time) // bucket_ms
        buckets[bucket_idx].append(reading)
    
    # Calculate average depth for each bucket
    bucket_averages = []
    for bucket_idx in sorted(buckets.keys()):
        bucket_readings = buckets[bucket_idx]
        avg_depth = statistics.mean(r['depth'] for r in bucket_readings)
        avg_time = statistics.mean(r['timestamp'] for r in bucket_readings)
        bucket_averages.append({
            'bucket': bucket_idx,
            'timestamp': avg_time,
            'datetime': bucket_readings[0]['datetime'],  # Use first reading's datetime
            'depth': avg_depth,
            'readings_count': len(bucket_readings)
        })
    
    # Calculate rates between buckets
    rates = []
    for i in range(1, len(bucket_averages)):
        prev = bucket_averages[i-1]
        curr = bucket_averages[i]
        
        time_diff_ms = curr['timestamp'] - prev['timestamp']
        time_diff_hours = time_diff_ms / (1000 * 60 * 60)
        depth_diff = curr['depth'] - prev['depth']
        
        if time_diff_hours > 0:
            rates.append({
                'from_time': prev['datetime'],
                'to_time': curr['datetime'],
                'from_depth': prev['depth'],
                'to_depth': curr['depth'],
                'depth_change': depth_diff,
                'time_hours': time_diff_hours,
                'rate_per_hour': depth_diff / time_diff_hours,
                'bucket_from': prev['bucket'],
                'bucket_to': curr['bucket']
            })
    
    return bucket_averages, rates

def calculate_moving_average_rates(data, window_size=5):
    """Calculate rates using moving average of readings."""
    rates = []
    
    for i in range(window_size, len(data)):
        # Get window of readings
        window = data[i-window_size:i+1]
        
        # Calculate rate from first to last in window
        first = window[0]
        last = window[-1]
        
        time_diff_ms = last['timestamp'] - first['timestamp']
        time_diff_hours = time_diff_ms / (1000 * 60 * 60)
        depth_diff = last['depth'] - first['depth']
        
        if time_diff_hours > 0:
            rates.append({
                'from_time': first['datetime'],
                'to_time': last['datetime'],
                'from_depth': first['depth'],
                'to_depth': last['depth'],
                'depth_change': depth_diff,
                'time_hours': time_diff_hours,
                'rate_per_hour': depth_diff / time_diff_hours,
                'window_size': window_size
            })
    
    return rates

def calculate_linear_regression_rate(data):
    """Calculate fill rate using linear regression (most accurate for constant fill)."""
    timestamps = np.array([r['timestamp'] for r in data])
    depths = np.array([r['depth'] for r in data])
    
    # Convert timestamps to hours from start
    start_time = timestamps[0]
    time_hours = (timestamps - start_time) / (1000 * 60 * 60)
    
    # Fit linear regression: depth = rate * time + intercept
    coeffs = np.polyfit(time_hours, depths, 1)
    rate = coeffs[0]  # slope = fill rate
    intercept = coeffs[1]  # starting depth
    
    # Calculate R-squared
    predicted = np.polyval(coeffs, time_hours)
    ss_res = np.sum((depths - predicted) ** 2)
    ss_tot = np.sum((depths - np.mean(depths)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    
    return {
        'rate_per_hour': rate,
        'intercept': intercept,
        'r_squared': r_squared,
        'predicted_start': intercept,
        'predicted_end': intercept + rate * time_hours[-1]
    }

def print_improved_analysis(data, bucket_rates, moving_avg_rates, regression):
    """Print improved analysis results."""
    print("=" * 80)
    print("IMPROVED WATER TANK FILL RATE ANALYSIS")
    print("=" * 80)
    print()
    
    # Basic info
    print("📊 DATA OVERVIEW")
    print("-" * 80)
    print(f"Total liquid_depth readings: {len(data)}")
    if data:
        first_reading = data[0]
        last_reading = data[-1]
        total_time_ms = last_reading['timestamp'] - first_reading['timestamp']
        total_time_hours = total_time_ms / (1000 * 60 * 60)
        net_change = last_reading['depth'] - first_reading['depth']
        net_rate = net_change / total_time_hours if total_time_hours > 0 else 0
        
        print(f"Time span: {first_reading['datetime']} to {last_reading['datetime']}")
        print(f"Total duration: {total_time_hours:.2f} hours")
        print(f"Depth range: {min(d['depth'] for d in data):.1f} to {max(d['depth'] for d in data):.1f}")
        print(f"Net change: {net_change:.1f} depth units")
        print(f"Simple net rate: {net_rate:.2f} depth units/hour")
        print()
    
    # Linear regression (most accurate for constant fill)
    print("📈 LINEAR REGRESSION ANALYSIS (Best for constant fill rate)")
    print("-" * 80)
    print(f"Fill rate: {regression['rate_per_hour']:.2f} depth units/hour")
    print(f"R-squared: {regression['r_squared']:.4f} (1.0 = perfect fit)")
    print(f"Predicted start depth: {regression['predicted_start']:.2f}")
    print(f"Predicted end depth: {regression['predicted_end']:.2f}")
    print()
    
    # Time bucket analysis
    print("📊 TIME BUCKET ANALYSIS (5-minute buckets)")
    print("-" * 80)
    if bucket_rates:
        bucket_rate_values = [r['rate_per_hour'] for r in bucket_rates]
        print(f"Number of buckets: {len(bucket_rate_values)}")
        print(f"Average rate: {statistics.mean(bucket_rate_values):.2f} depth units/hour")
        print(f"Median rate: {statistics.median(bucket_rate_values):.2f} depth units/hour")
        if len(bucket_rate_values) > 1:
            print(f"Std deviation: {statistics.stdev(bucket_rate_values):.2f} depth units/hour")
            print(f"Min rate: {min(bucket_rate_values):.2f} depth units/hour")
            print(f"Max rate: {max(bucket_rate_values):.2f} depth units/hour")
        print()
    
    # Moving average analysis
    print("📊 MOVING AVERAGE ANALYSIS (5-reading window)")
    print("-" * 80)
    if moving_avg_rates:
        ma_rate_values = [r['rate_per_hour'] for r in moving_avg_rates]
        print(f"Number of windows: {len(ma_rate_values)}")
        print(f"Average rate: {statistics.mean(ma_rate_values):.2f} depth units/hour")
        print(f"Median rate: {statistics.median(ma_rate_values):.2f} depth units/hour")
        if len(ma_rate_values) > 1:
            print(f"Std deviation: {statistics.stdev(ma_rate_values):.2f} depth units/hour")
            print(f"Min rate: {min(ma_rate_values):.2f} depth units/hour")
            print(f"Max rate: {max(ma_rate_values):.2f} depth units/hour")
        print()
    
    # Comparison
    print("📊 RATE COMPARISON")
    print("-" * 80)
    print(f"Linear regression rate: {regression['rate_per_hour']:.2f} depth units/hour")
    if bucket_rates:
        print(f"Time bucket average:   {statistics.mean([r['rate_per_hour'] for r in bucket_rates]):.2f} depth units/hour")
    if moving_avg_rates:
        print(f"Moving average:        {statistics.mean([r['rate_per_hour'] for r in moving_avg_rates]):.2f} depth units/hour")
    print()
    
    # Rate stability
    print("📊 RATE STABILITY ANALYSIS")
    print("-" * 80)
    if bucket_rates:
        bucket_rates_list = [r['rate_per_hour'] for r in bucket_rates]
        cv = statistics.stdev(bucket_rates_list) / statistics.mean(bucket_rates_list) if statistics.mean(bucket_rates_list) > 0 else 0
        print(f"Coefficient of Variation (time buckets): {cv:.3f}")
        print(f"  (< 0.1 = very stable, 0.1-0.3 = stable, > 0.3 = variable)")
    print()

def export_improved_csv(bucket_rates, moving_avg_rates, regression, output_prefix):
    """Export improved analysis to CSV files."""
    # Export bucket rates
    bucket_csv = f"{output_prefix}_bucket_rates.csv"
    with open(bucket_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'from_time', 'to_time', 'from_depth', 'to_depth',
            'depth_change', 'time_hours', 'rate_per_hour'
        ])
        for rate in bucket_rates:
            writer.writerow([
                rate['from_time'],
                rate['to_time'],
                rate['from_depth'],
                rate['to_depth'],
                rate['depth_change'],
                rate['time_hours'],
                rate['rate_per_hour']
            ])
    print(f"💾 Bucket rates exported to: {bucket_csv}")
    
    # Export moving average rates
    ma_csv = f"{output_prefix}_moving_avg_rates.csv"
    with open(ma_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'from_time', 'to_time', 'from_depth', 'to_depth',
            'depth_change', 'time_hours', 'rate_per_hour', 'window_size'
        ])
        for rate in moving_avg_rates:
            writer.writerow([
                rate['from_time'],
                rate['to_time'],
                rate['from_depth'],
                rate['to_depth'],
                rate['depth_change'],
                rate['time_hours'],
                rate['rate_per_hour'],
                rate['window_size']
            ])
    print(f"💾 Moving average rates exported to: {ma_csv}")
    
    # Export regression summary
    reg_csv = f"{output_prefix}_regression_summary.csv"
    with open(reg_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['metric', 'value'])
        writer.writerow(['fill_rate_depth_units_per_hour', f"{regression['rate_per_hour']:.4f}"])
        writer.writerow(['r_squared', f"{regression['r_squared']:.4f}"])
        writer.writerow(['predicted_start_depth', f"{regression['predicted_start']:.2f}"])
        writer.writerow(['predicted_end_depth', f"{regression['predicted_end']:.2f}"])
    print(f"💾 Regression summary exported to: {reg_csv}")

def main():
    csv_file = '/Users/antongorshkov/Documents/home/water_tank_logs.csv'
    output_prefix = '/Users/antongorshkov/Documents/home/water_tank_improved'
    
    print("Reading CSV file...")
    data = parse_csv(csv_file)
    
    print("Removing depth reversals...")
    data_no_reversals = remove_reversals(data)
    print(f"  Removed {len(data) - len(data_no_reversals)} reversal readings")
    
    print("Calculating time bucket rates (5-minute buckets)...")
    bucket_averages, bucket_rates = calculate_time_bucket_rates(data_no_reversals, bucket_minutes=5)
    
    print("Calculating moving average rates (5-reading window)...")
    moving_avg_rates = calculate_moving_average_rates(data_no_reversals, window_size=5)
    
    print("Calculating linear regression rate...")
    regression = calculate_linear_regression_rate(data_no_reversals)
    
    print_improved_analysis(data_no_reversals, bucket_rates, moving_avg_rates, regression)
    
    export_improved_csv(bucket_rates, moving_avg_rates, regression, output_prefix)

if __name__ == '__main__':
    main()



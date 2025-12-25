#!/usr/bin/env python3
"""
Analyze water tank liquid_depth data to understand fill rate and rate of change.
"""

import csv
from datetime import datetime
from collections import defaultdict
import statistics

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

def calculate_rate_of_change(data, min_interval_minutes=1):
    """Calculate rate of change between consecutive readings.
    
    Args:
        data: List of depth readings
        min_interval_minutes: Minimum time interval in minutes to consider (filters noise)
    """
    rates = []
    min_interval_ms = min_interval_minutes * 60 * 1000
    
    for i in range(1, len(data)):
        prev = data[i-1]
        curr = data[i]
        
        time_diff_ms = curr['timestamp'] - prev['timestamp']
        time_diff_hours = time_diff_ms / (1000 * 60 * 60)  # Convert to hours
        depth_diff = curr['depth'] - prev['depth']
        
        # Only include intervals that meet minimum time threshold
        if time_diff_ms >= min_interval_ms:
            rate = depth_diff / time_diff_hours  # Depth units per hour
            rates.append({
                'from_time': prev['datetime'],
                'to_time': curr['datetime'],
                'from_depth': prev['depth'],
                'to_depth': curr['depth'],
                'depth_change': depth_diff,
                'time_hours': time_diff_hours,
                'time_minutes': time_diff_ms / (1000 * 60),
                'rate_per_hour': rate,
                'timestamp_from': prev['timestamp'],
                'timestamp_to': curr['timestamp']
            })
    
    return rates

def calculate_smoothed_rates(data, window_minutes=5):
    """Calculate smoothed rates over time windows."""
    window_ms = window_minutes * 60 * 1000
    smoothed = []
    
    i = 0
    while i < len(data):
        window_start = data[i]
        window_end_idx = i
        
        # Find all points within the window
        for j in range(i + 1, len(data)):
            if data[j]['timestamp'] - window_start['timestamp'] <= window_ms:
                window_end_idx = j
            else:
                break
        
        if window_end_idx > i:
            window_end = data[window_end_idx]
            time_diff_hours = (window_end['timestamp'] - window_start['timestamp']) / (1000 * 60 * 60)
            depth_diff = window_end['depth'] - window_start['depth']
            
            if time_diff_hours > 0:
                smoothed.append({
                    'from_time': window_start['datetime'],
                    'to_time': window_end['datetime'],
                    'from_depth': window_start['depth'],
                    'to_depth': window_end['depth'],
                    'depth_change': depth_diff,
                    'time_hours': time_diff_hours,
                    'rate_per_hour': depth_diff / time_diff_hours,
                    'readings_in_window': window_end_idx - i + 1
                })
        
        # Move to next window (non-overlapping)
        i = window_end_idx + 1 if window_end_idx > i else i + 1
    
    return smoothed

def analyze_filling_periods(rates):
    """Identify periods where tank is being filled vs not filled."""
    filling_periods = []
    stable_periods = []
    draining_periods = []
    
    # Thresholds (adjust based on your data)
    FILL_THRESHOLD = 0.1  # Depth units per hour - minimum to consider "filling"
    DRAIN_THRESHOLD = -0.1  # Negative rate to consider "draining"
    
    for rate in rates:
        if rate['rate_per_hour'] > FILL_THRESHOLD:
            filling_periods.append(rate)
        elif rate['rate_per_hour'] < DRAIN_THRESHOLD:
            draining_periods.append(rate)
        else:
            stable_periods.append(rate)
    
    return filling_periods, stable_periods, draining_periods

def print_statistics(data, rates, filling_periods, stable_periods, draining_periods, smoothed_rates=None):
    """Print comprehensive statistics."""
    print("=" * 80)
    print("WATER TANK LIQUID DEPTH ANALYSIS")
    print("=" * 80)
    print()
    
    # Basic data info
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
        print(f"Total duration: {total_time_hours:.2f} hours ({total_time_hours/24:.2f} days)")
        print(f"Depth range: {min(d['depth'] for d in data):.1f} to {max(d['depth'] for d in data):.1f}")
        print(f"Average depth: {statistics.mean(d['depth'] for d in data):.2f}")
        print(f"Net change: {net_change:.1f} depth units ({net_rate:.2f} depth units/hour)")
        print()
    
    # Rate of change statistics (filtered)
    print("📈 RATE OF CHANGE STATISTICS (filtered: min 1 minute intervals)")
    print("-" * 80)
    if rates:
        all_rates = [r['rate_per_hour'] for r in rates]
        positive_rates = [r for r in all_rates if r > 0]
        negative_rates = [r for r in all_rates if r < 0]
        
        print(f"Total rate calculations (≥1 min intervals): {len(rates)}")
        print(f"Average rate: {statistics.mean(all_rates):.3f} depth units/hour")
        if len(all_rates) > 1:
            print(f"Median rate: {statistics.median(all_rates):.3f} depth units/hour")
            print(f"Std deviation: {statistics.stdev(all_rates):.3f} depth units/hour")
        
        if positive_rates:
            print(f"\nFilling rates (positive):")
            print(f"  Count: {len(positive_rates)}")
            print(f"  Average: {statistics.mean(positive_rates):.3f} depth units/hour")
            print(f"  Median: {statistics.median(positive_rates):.3f} depth units/hour")
            print(f"  Max: {max(positive_rates):.3f} depth units/hour")
            print(f"  Min: {min(positive_rates):.3f} depth units/hour")
        
        if negative_rates:
            print(f"\nDraining rates (negative):")
            print(f"  Count: {len(negative_rates)}")
            print(f"  Average: {statistics.mean(negative_rates):.3f} depth units/hour")
            print(f"  Median: {statistics.median(negative_rates):.3f} depth units/hour")
            print(f"  Max: {max(negative_rates):.3f} depth units/hour")
            print(f"  Min: {min(negative_rates):.3f} depth units/hour")
        print()
    
    # Smoothed rates (5-minute windows)
    if smoothed_rates:
        print("📊 SMOOTHED RATES (5-minute windows)")
        print("-" * 80)
        smoothed_rate_values = [r['rate_per_hour'] for r in smoothed_rates]
        positive_smoothed = [r for r in smoothed_rate_values if r > 0]
        negative_smoothed = [r for r in smoothed_rate_values if r < 0]
        
        print(f"Total smoothed windows: {len(smoothed_rates)}")
        print(f"Average smoothed rate: {statistics.mean(smoothed_rate_values):.3f} depth units/hour")
        if len(smoothed_rate_values) > 1:
            print(f"Median smoothed rate: {statistics.median(smoothed_rate_values):.3f} depth units/hour")
        
        if positive_smoothed:
            print(f"\nFilling periods (smoothed):")
            print(f"  Count: {len(positive_smoothed)}")
            print(f"  Average: {statistics.mean(positive_smoothed):.3f} depth units/hour")
            print(f"  Median: {statistics.median(positive_smoothed):.3f} depth units/hour")
        
        if negative_smoothed:
            print(f"\nDraining periods (smoothed):")
            print(f"  Count: {len(negative_smoothed)}")
            print(f"  Average: {statistics.mean(negative_smoothed):.3f} depth units/hour")
            print(f"  Median: {statistics.median(negative_smoothed):.3f} depth units/hour")
        print()
    
    # Period analysis
    print("⏱️  PERIOD ANALYSIS")
    print("-" * 80)
    print(f"Filling periods: {len(filling_periods)} ({len(filling_periods)/len(rates)*100:.1f}% of time)")
    print(f"Stable periods: {len(stable_periods)} ({len(stable_periods)/len(rates)*100:.1f}% of time)")
    print(f"Draining periods: {len(draining_periods)} ({len(draining_periods)/len(rates)*100:.1f}% of time)")
    print()
    
    if filling_periods:
        fill_rates = [p['rate_per_hour'] for p in filling_periods]
        total_fill_time = sum(p['time_hours'] for p in filling_periods)
        print(f"Filling period details:")
        print(f"  Average fill rate: {statistics.mean(fill_rates):.3f} depth units/hour")
        print(f"  Max fill rate: {max(fill_rates):.3f} depth units/hour")
        print(f"  Total filling time: {total_fill_time:.2f} hours")
        print()
    
    # Top filling periods
    print("🚀 TOP 10 FASTEST FILLING PERIODS (≥1 min intervals)")
    print("-" * 80)
    if filling_periods:
        top_filling = sorted(filling_periods, key=lambda x: x['rate_per_hour'], reverse=True)[:10]
        for i, period in enumerate(top_filling, 1):
            print(f"{i:2d}. Rate: {period['rate_per_hour']:6.2f} depth units/hour")
            print(f"    From: {period['from_time']} (depth: {period['from_depth']:.1f})")
            print(f"    To:   {period['to_time']} (depth: {period['to_depth']:.1f})")
            print(f"    Duration: {period['time_minutes']:.1f} minutes ({period['time_hours']:.3f} hours)")
            print()
    else:
        print("No filling periods detected.")
        print()
    
    # Top smoothed filling periods
    if smoothed_rates:
        print("🚀 TOP 10 FASTEST FILLING PERIODS (5-minute smoothed)")
        print("-" * 80)
        positive_smoothed = [r for r in smoothed_rates if r['rate_per_hour'] > 0]
        if positive_smoothed:
            top_smoothed = sorted(positive_smoothed, key=lambda x: x['rate_per_hour'], reverse=True)[:10]
            for i, period in enumerate(top_smoothed, 1):
                print(f"{i:2d}. Rate: {period['rate_per_hour']:6.2f} depth units/hour")
                print(f"    From: {period['from_time']} (depth: {period['from_depth']:.1f})")
                print(f"    To:   {period['to_time']} (depth: {period['to_depth']:.1f})")
                print(f"    Duration: {period['time_hours']:.3f} hours ({period['readings_in_window']} readings)")
                print()
        print()
    
    # Time-based analysis
    print("🕐 TIME-BASED PATTERNS")
    print("-" * 80)
    if data:
        # Group by hour of day
        hourly_rates = defaultdict(list)
        for rate in rates:
            dt = datetime.strptime(rate['from_time'], '%Y-%m-%d %H:%M:%S')
            hour = dt.hour
            hourly_rates[hour].append(rate['rate_per_hour'])
        
        if hourly_rates:
            print("Average fill rate by hour of day:")
            for hour in sorted(hourly_rates.keys()):
                avg_rate = statistics.mean(hourly_rates[hour])
                count = len(hourly_rates[hour])
                print(f"  {hour:02d}:00 - {avg_rate:6.3f} depth units/hour ({count} readings)")
        print()

def export_detailed_csv(rates, output_file):
    """Export detailed rate of change data to CSV."""
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'from_time', 'to_time', 'from_depth', 'to_depth', 
            'depth_change', 'time_hours', 'rate_per_hour'
        ])
        
        for rate in rates:
            writer.writerow([
                rate['from_time'],
                rate['to_time'],
                rate['from_depth'],
                rate['to_depth'],
                rate['depth_change'],
                rate['time_hours'],
                rate['rate_per_hour']
            ])
    
    print(f"💾 Detailed rate data exported to: {output_file}")

def main():
    csv_file = '/Users/antongorshkov/Documents/home/water_tank_logs.csv'
    output_csv = '/Users/antongorshkov/Documents/home/water_tank_rate_analysis.csv'
    smoothed_csv = '/Users/antongorshkov/Documents/home/water_tank_smoothed_rates.csv'
    
    print("Reading CSV file...")
    data = parse_csv(csv_file)
    
    print("Calculating rates of change (filtered: min 1 minute intervals)...")
    rates = calculate_rate_of_change(data, min_interval_minutes=1)
    
    print("Calculating smoothed rates (5-minute windows)...")
    smoothed_rates = calculate_smoothed_rates(data, window_minutes=5)
    
    print("Analyzing filling periods...")
    filling_periods, stable_periods, draining_periods = analyze_filling_periods(rates)
    
    print_statistics(data, rates, filling_periods, stable_periods, draining_periods, smoothed_rates)
    
    export_detailed_csv(rates, output_csv)
    
    # Export smoothed rates
    with open(smoothed_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'from_time', 'to_time', 'from_depth', 'to_depth', 
            'depth_change', 'time_hours', 'rate_per_hour', 'readings_in_window'
        ])
        
        for rate in smoothed_rates:
            writer.writerow([
                rate['from_time'],
                rate['to_time'],
                rate['from_depth'],
                rate['to_depth'],
                rate['depth_change'],
                rate['time_hours'],
                rate['rate_per_hour'],
                rate['readings_in_window']
            ])
    
    print(f"💾 Smoothed rate data exported to: {smoothed_csv}")

if __name__ == '__main__':
    main()


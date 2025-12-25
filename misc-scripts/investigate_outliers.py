#!/usr/bin/env python3
"""
Investigate outliers in water tank fill rate data to improve accuracy.
"""

import csv
import statistics
from datetime import datetime

def load_rate_data(csv_file):
    """Load rate analysis data."""
    rates = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rates.append({
                'from_time': row['from_time'],
                'to_time': row['to_time'],
                'from_depth': float(row['from_depth']),
                'to_depth': float(row['to_depth']),
                'depth_change': float(row['depth_change']),
                'time_hours': float(row['time_hours']),
                'rate_per_hour': float(row['rate_per_hour'])
            })
    return rates

def analyze_outliers(rates):
    """Identify and analyze outliers in fill rates."""
    fill_rates = [r for r in rates if r['rate_per_hour'] > 0]
    
    if not fill_rates:
        return
    
    rate_values = [r['rate_per_hour'] for r in fill_rates]
    
    # Calculate statistics
    mean_rate = statistics.mean(rate_values)
    median_rate = statistics.median(rate_values)
    stdev = statistics.stdev(rate_values) if len(rate_values) > 1 else 0
    
    # Identify outliers using IQR method
    sorted_rates = sorted(rate_values)
    q1_idx = len(sorted_rates) // 4
    q3_idx = 3 * len(sorted_rates) // 4
    q1 = sorted_rates[q1_idx]
    q3 = sorted_rates[q3_idx]
    iqr = q3 - q1
    
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    
    outliers = [r for r in fill_rates if r['rate_per_hour'] < lower_bound or r['rate_per_hour'] > upper_bound]
    
    print("=" * 80)
    print("OUTLIER ANALYSIS")
    print("=" * 80)
    print()
    print(f"Total fill rate measurements: {len(fill_rates)}")
    print(f"Mean rate: {mean_rate:.2f} depth units/hour")
    print(f"Median rate: {median_rate:.2f} depth units/hour")
    print(f"Std deviation: {stdev:.2f} depth units/hour")
    print()
    print(f"Q1 (25th percentile): {q1:.2f}")
    print(f"Q3 (75th percentile): {q3:.2f}")
    print(f"IQR: {iqr:.2f}")
    print(f"Lower bound (Q1 - 1.5*IQR): {lower_bound:.2f}")
    print(f"Upper bound (Q3 + 1.5*IQR): {upper_bound:.2f}")
    print()
    print(f"Outliers detected: {len(outliers)} ({len(outliers)/len(fill_rates)*100:.1f}%)")
    print()
    
    # Analyze outlier characteristics
    print("OUTLIER CHARACTERISTICS")
    print("-" * 80)
    
    # Group outliers by time duration
    short_duration_outliers = [o for o in outliers if o['time_hours'] < 0.05]  # Less than 3 minutes
    medium_duration_outliers = [o for o in outliers if 0.05 <= o['time_hours'] < 0.1]  # 3-6 minutes
    long_duration_outliers = [o for o in outliers if o['time_hours'] >= 0.1]  # 6+ minutes
    
    print(f"Short duration outliers (<3 min): {len(short_duration_outliers)}")
    print(f"Medium duration outliers (3-6 min): {len(medium_duration_outliers)}")
    print(f"Long duration outliers (≥6 min): {len(long_duration_outliers)}")
    print()
    
    # Check for depth change patterns
    print("DEPTH CHANGE PATTERNS IN OUTLIERS")
    print("-" * 80)
    depth_changes = [o['depth_change'] for o in outliers]
    print(f"Depth changes in outliers: {sorted(set(depth_changes))}")
    print()
    
    # Show top outliers
    print("TOP 10 HIGHEST OUTLIERS")
    print("-" * 80)
    top_outliers = sorted(outliers, key=lambda x: x['rate_per_hour'], reverse=True)[:10]
    for i, outlier in enumerate(top_outliers, 1):
        print(f"{i:2d}. Rate: {outlier['rate_per_hour']:6.2f} depth units/hour")
        print(f"    Duration: {outlier['time_hours']*60:.1f} minutes")
        print(f"    Depth change: {outlier['depth_change']:.1f} units")
        print(f"    From: {outlier['from_time']} ({outlier['from_depth']:.1f})")
        print(f"    To: {outlier['to_time']} ({outlier['to_depth']:.1f})")
        print()
    
    return outliers, lower_bound, upper_bound

def check_data_quality(rates):
    """Check for data quality issues."""
    print("=" * 80)
    print("DATA QUALITY CHECKS")
    print("=" * 80)
    print()
    
    # Check for very small time intervals
    very_short = [r for r in rates if r['time_hours'] < 0.01]  # Less than 36 seconds
    print(f"Very short intervals (<36 sec): {len(very_short)}")
    if very_short:
        print("  These may be too noisy for accurate rate calculation")
        print()
    
    # Check for very small depth changes
    small_changes = [r for r in rates if abs(r['depth_change']) < 0.5]
    print(f"Very small depth changes (<0.5 units): {len(small_changes)}")
    print()
    
    # Check for depth reversals (going down when should be filling)
    reversals = [r for r in rates if r['depth_change'] < 0]
    print(f"Depth reversals (negative change): {len(reversals)}")
    if reversals:
        print("  Sample reversals:")
        for rev in reversals[:5]:
            print(f"    {rev['from_time']}: {rev['from_depth']:.1f} → {rev['to_depth']:.1f} ({rev['depth_change']:.1f})")
        print()
    
    # Check time gaps
    time_gaps = []
    for i in range(1, len(rates)):
        gap_hours = (datetime.strptime(rates[i]['from_time'], '%Y-%m-%d %H:%M:%S') - 
                    datetime.strptime(rates[i-1]['to_time'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600
        time_gaps.append(gap_hours)
    
    if time_gaps:
        print(f"Time gaps between measurements:")
        print(f"  Average gap: {statistics.mean(time_gaps):.3f} hours")
        print(f"  Max gap: {max(time_gaps):.3f} hours")
        print(f"  Min gap: {min(time_gaps):.3f} hours")
        print()

def suggest_improvements(outliers, lower_bound, upper_bound):
    """Suggest improvements to the analysis."""
    print("=" * 80)
    print("SUGGESTED IMPROVEMENTS")
    print("=" * 80)
    print()
    
    print("1. FILTER OUTLIERS:")
    print(f"   Remove rates outside [{lower_bound:.2f}, {upper_bound:.2f}] depth units/hour")
    print()
    
    print("2. MINIMUM TIME THRESHOLD:")
    print("   Use minimum 5-minute intervals for more stable rates")
    print()
    
    print("3. MINIMUM DEPTH CHANGE:")
    print("   Filter out measurements with depth changes < 1 unit (sensor noise)")
    print()
    
    print("4. MOVING AVERAGE:")
    print("   Use rolling window average (e.g., 3-5 readings) to smooth data")
    print()
    
    print("5. MEDIAN FILTER:")
    print("   Use median instead of mean for more robust rate calculation")
    print()
    
    print("6. REMOVE REVERSALS:")
    print("   Filter out negative depth changes if tank should only fill")
    print()

if __name__ == '__main__':
    csv_file = '/Users/antongorshkov/Documents/home/water_tank_rate_analysis.csv'
    
    print("Loading rate data...")
    rates = load_rate_data(csv_file)
    
    print("Analyzing outliers...")
    outliers, lower_bound, upper_bound = analyze_outliers(rates)
    
    print("Checking data quality...")
    check_data_quality(rates)
    
    print("Suggesting improvements...")
    suggest_improvements(outliers, lower_bound, upper_bound)



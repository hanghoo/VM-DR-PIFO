#!/usr/bin/env python3
"""
Measure WRR bandwidth allocation from receiver logs
Analyzes packet reception rates in time windows during congestion
"""

import re
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime


def parse_receiver_log(receiver_file):
    """Parse receiver log and extract packet reception timestamps"""
    timestamps = []

    if not receiver_file.exists():
        print(f"Warning: {receiver_file} not found")
        return timestamps

    with open(receiver_file, 'r') as f:
        for line in f:
            # Format: "packet is received at time : 1234567890.123"
            match = re.search(r'received at time : ([\d.]+)', line)
            if match:
                timestamp = float(match.group(1))
                timestamps.append(timestamp)

    return timestamps


def calculate_window_rates(timestamps, window_start, window_end):
    """Calculate packet rate in a time window"""
    packets_in_window = [t for t in timestamps if window_start <= t <= window_end]
    window_duration = window_end - window_start
    if window_duration > 0:
        rate = len(packets_in_window) / window_duration
        return len(packets_in_window), rate
    return 0, 0.0


def expected_allocation_from_quantums(quantums):
    """Compute expected WRR allocation percentages from quantum values."""
    total = sum(quantums)
    if total <= 0:
        return [0.0, 0.0, 0.0]
    return [q / total * 100.0 for q in quantums]


def measure_bandwidth_allocation(outputs_dir, start_time=None, end_time=None, window_size=10, quantums=None):
    """
    Measure bandwidth allocation for each flow

    Args:
        outputs_dir: Directory containing receiver logs
        start_time: Start time for measurement (if None, use first packet time)
        end_time: End time for measurement (if None, use last packet time)
        window_size: Size of time windows in seconds
        quantums: List of 3 WRR quantum values (e.g. [20000, 10000, 2000]). If None, use default.
    """
    if quantums is None:
        quantums = [20000, 10000, 2000]
    outputs_path = Path(outputs_dir)

    # Parse receiver logs for each flow
    flow_timestamps = {}
    for flow_id in range(3):
        receiver_file = outputs_path / f"receiver_h_r{flow_id+1}.txt"
        timestamps = parse_receiver_log(receiver_file)
        flow_timestamps[flow_id] = timestamps
        print(f"Flow {flow_id}: {len(timestamps)} packets received")

    if not any(flow_timestamps.values()):
        print("Error: No packets found in receiver logs")
        return

    # Determine measurement time window
    all_timestamps = []
    for timestamps in flow_timestamps.values():
        all_timestamps.extend(timestamps)

    if not all_timestamps:
        print("Error: No timestamps found")
        return

    if start_time is None:
        start_time = min(all_timestamps) + 5  # Start 5 seconds after first packet
    if end_time is None:
        end_time = max(all_timestamps) - 5  # End 5 seconds before last packet

    print(f"\nMeasurement window: {start_time:.2f} - {end_time:.2f} seconds")
    print(f"Window size: {window_size} seconds")
    print("=" * 60)

    # Calculate rates for each time window; track steady-state end (last window with all flows active)
    current_time = start_time
    window_num = 1
    steady_state_end = start_time  # end time of last window where all 3 flows had packets

    while current_time < end_time:
        window_end = min(current_time + window_size, end_time)

        print(f"\nWindow {window_num}: {current_time:.2f} - {window_end:.2f} seconds")
        print("-" * 60)

        total_packets = 0
        total_rate = 0.0
        flow_stats = {}

        for flow_id in range(3):
            timestamps = flow_timestamps[flow_id]
            packet_count, rate = calculate_window_rates(timestamps, current_time, window_end)
            flow_stats[flow_id] = {'packets': packet_count, 'rate': rate}
            total_packets += packet_count
            total_rate += rate

            print(f"  Flow {flow_id}: {packet_count} packets, {rate:.2f} pps")

        # Steady state: all three flows have at least one packet in this window
        if all(flow_stats[f]['packets'] > 0 for f in range(3)):
            steady_state_end = window_end

        # Calculate percentages
        if total_rate > 0:
            print(f"\n  Total: {total_packets} packets, {total_rate:.2f} pps")
            print("  Bandwidth allocation:")
            for flow_id in range(3):
                percentage = (flow_stats[flow_id]['rate'] / total_rate) * 100
                print(f"    Flow {flow_id}: {percentage:.2f}%")

        current_time = window_end
        window_num += 1

    # Helper to print overall stats and expected comparison over a time range
    def print_overall_stats(stat_start, stat_end, title):
        total_packets_all = 0
        total_rate_all = 0.0
        flow_stats_all = {}
        for flow_id in range(3):
            timestamps = flow_timestamps[flow_id]
            packet_count, rate = calculate_window_rates(timestamps, stat_start, stat_end)
            flow_stats_all[flow_id] = {'packets': packet_count, 'rate': rate}
            total_packets_all += packet_count
            total_rate_all += rate
        print(f"\n{title}")
        print(f"Time range: {stat_start:.2f} - {stat_end:.2f} seconds")
        print("-" * 60)
        for flow_id in range(3):
            print(f"Flow {flow_id}: {flow_stats_all[flow_id]['packets']} packets, {flow_stats_all[flow_id]['rate']:.2f} pps")
        if total_rate_all > 0:
            print(f"\nTotal: {total_packets_all} packets, {total_rate_all:.2f} pps")
            print("Bandwidth allocation:")
            for flow_id in range(3):
                actual_pct = (flow_stats_all[flow_id]['rate'] / total_rate_all) * 100
                print(f"  Flow {flow_id}: {actual_pct:.2f}%")
            expected = expected_allocation_from_quantums(quantums)
            ratio_str = ":".join(str(q) for q in quantums)
            print(f"\nExpected allocation (quantums {ratio_str}):")
            for flow_id in range(3):
                actual_pct = (flow_stats_all[flow_id]['rate'] / total_rate_all) * 100
                diff = abs(actual_pct - expected[flow_id])
                print(f"  Flow {flow_id}: {expected[flow_id]:.2f}% (actual: {actual_pct:.2f}%, diff: {diff:.2f}%)")
        return flow_stats_all, total_rate_all

    # Overall statistics: steady state only (all flows active) — use this for WRR comparison
    print("\n" + "=" * 60)
    print("Overall Statistics (steady state only - all flows active):")
    print("=" * 60)
    print_overall_stats(start_time, steady_state_end, "")

    # Overall statistics: entire window (includes wind-down; for reference)
    if steady_state_end < end_time - 1.0:
        print("\n" + "=" * 60)
        print("Overall Statistics (entire measurement window, includes wind-down):")
        print("=" * 60)
        print_overall_stats(start_time, end_time, "")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Measure WRR bandwidth allocation")
    parser.add_argument("outputs_dir", type=str,
                       help="Directory containing receiver logs (e.g., program/qos/outputs)")
    parser.add_argument("--start-time", type=float,
                       help="Start time for measurement (seconds since epoch)")
    parser.add_argument("--end-time", type=float,
                       help="End time for measurement (seconds since epoch)")
    parser.add_argument("--window-size", type=int, default=10,
                       help="Time window size in seconds (default: 10)")
    parser.add_argument("--quantums", type=str, default="20000,10000,2000",
                       help="WRR quantums for flow 0,1,2 (comma-separated). Default: 20000,10000,2000")

    args = parser.parse_args()

    quantums = [int(x.strip()) for x in args.quantums.split(",")]
    if len(quantums) != 3:
        parser.error("--quantums must have exactly 3 values (e.g. 20000,10000,2000)")
    if any(q <= 0 for q in quantums):
        parser.error("--quantums must be positive")

    measure_bandwidth_allocation(
        args.outputs_dir,
        args.start_time,
        args.end_time,
        args.window_size,
        quantums
    )


if __name__ == "__main__":
    main()

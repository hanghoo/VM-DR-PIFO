#!/usr/bin/env python3
"""
Calculate actual sending rate from sender logs
Analyzes sender logs to determine the actual packet sending rate
"""

import re
import sys
from pathlib import Path
from collections import defaultdict


def parse_sender_log(sender_file):
    """Parse sender log and extract packet sending timestamps"""
    timestamps = []
    total_packets = 0
    total_time = 0.0
    average_rate = 0.0

    if not sender_file.exists():
        print(f"Warning: {sender_file} not found")
        return timestamps, total_packets, total_time, average_rate

    with open(sender_file, 'r') as f:
        lines = f.readlines()

        # Parse packet sending timestamps
        for line in lines:
            # Format: "This host has sent <N> packets until now : <timestamp>" (same regex as analyze_wrr_results)
            match = re.search(r'sent (\d+) packets until now : ([\d.]+)', line)
            if match:
                packet_count = int(match.group(1))
                timestamp = float(match.group(2))
                timestamps.append((packet_count, timestamp))

        # Parse summary at the end
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i]
            # Format: "  Total packets: {count}"
            match = re.search(r'Total packets: (\d+)', line)
            if match:
                total_packets = int(match.group(1))

            # Format: "  Total time: {time} seconds"
            match = re.search(r'Total time: ([\d.]+) seconds', line)
            if match:
                total_time = float(match.group(1))

            # Format: "  Average rate: {rate} packets/sec"
            match = re.search(r'Average rate: ([\d.]+) packets/sec', line)
            if match:
                average_rate = float(match.group(1))
                break  # Found summary, stop looking

    return timestamps, total_packets, total_time, average_rate


def calculate_send_rate_from_timestamps(timestamps, start_time=None, end_time=None):
    """Calculate sending rate from timestamps in a time window"""
    if not timestamps:
        return 0, 0.0

    # Filter timestamps by time window
    if start_time is not None or end_time is not None:
        filtered = []
        for packet_count, timestamp in timestamps:
            if start_time is not None and timestamp < start_time:
                continue
            if end_time is not None and timestamp > end_time:
                continue
            filtered.append((packet_count, timestamp))
        timestamps = filtered

    if len(timestamps) < 2:
        return len(timestamps), 0.0

    # Calculate rate from first and last packet
    first_packet_count, first_time = timestamps[0]
    last_packet_count, last_time = timestamps[-1]

    packet_count = last_packet_count - first_packet_count + 1
    time_duration = last_time - first_time

    if time_duration > 0:
        rate = packet_count / time_duration
    else:
        rate = 0.0

    return packet_count, rate


def calculate_send_rate(outputs_dir, flow_id=None, start_time=None, end_time=None):
    """
    Calculate actual sending rate for each flow

    Args:
        outputs_dir: Directory containing sender logs
        flow_id: Specific flow ID to analyze (0, 1, or 2), or None for all flows
        start_time: Start time for measurement (if None, use all data)
        end_time: End time for measurement (if None, use all data)
    """
    outputs_path = Path(outputs_dir)

    flows_to_analyze = [flow_id] if flow_id is not None else [0, 1, 2]

    print("=" * 60)
    print("Actual Sending Rate Analysis")
    print("=" * 60)

    total_send_rate = 0.0

    for flow_id in flows_to_analyze:
        sender_file = outputs_path / f"sender_h{flow_id+1}.txt"
        timestamps, total_packets, total_time, average_rate = parse_sender_log(sender_file)

        print(f"\nFlow {flow_id} (sender_h{flow_id+1}.txt):")
        print("-" * 60)

        if not timestamps:
            print("  No timestamps found in log")
            continue

        # Method 1: From summary (if available)
        if total_packets > 0 and total_time > 0:
            print(f"  Summary method:")
            print(f"    Total packets: {total_packets}")
            print(f"    Total time: {total_time:.2f} seconds")
            print(f"    Average rate: {average_rate:.2f} packets/sec")

        # Method 2: From timestamps (all data)
        if len(timestamps) >= 2:
            packet_count_all, rate_all = calculate_send_rate_from_timestamps(timestamps)
            first_time = timestamps[0][1]
            last_time = timestamps[-1][1]
            duration_all = last_time - first_time

            print(f"\n  Timestamp method (all data):")
            print(f"    First packet: {first_time:.2f} seconds")
            print(f"    Last packet: {last_time:.2f} seconds")
            print(f"    Duration: {duration_all:.2f} seconds")
            print(f"    Packet count: {packet_count_all}")
            print(f"    Average rate: {rate_all:.2f} packets/sec")

        # Method 3: From timestamps (time window)
        if start_time is not None or end_time is not None:
            packet_count_window, rate_window = calculate_send_rate_from_timestamps(
                timestamps, start_time, end_time
            )
            if packet_count_window > 0:
                print(f"\n  Timestamp method (time window):")
                if start_time is not None:
                    print(f"    Start time: {start_time:.2f} seconds")
                if end_time is not None:
                    print(f"    End time: {end_time:.2f} seconds")
                print(f"    Packet count: {packet_count_window}")
                print(f"    Average rate: {rate_window:.2f} packets/sec")

        # Calculate intervals between consecutive packets
        if len(timestamps) >= 2:
            intervals = []
            for i in range(1, len(timestamps)):
                prev_time = timestamps[i-1][1]
                curr_time = timestamps[i][1]
                interval = curr_time - prev_time
                intervals.append(interval)

            if intervals:
                avg_interval = sum(intervals) / len(intervals)
                min_interval = min(intervals)
                max_interval = max(intervals)
                rate_from_interval = 1.0 / avg_interval if avg_interval > 0 else 0.0

                print(f"\n  Interval analysis:")
                print(f"    Average interval: {avg_interval*1000:.2f} ms")
                print(f"    Min interval: {min_interval*1000:.2f} ms")
                print(f"    Max interval: {max_interval*1000:.2f} ms")
                print(f"    Rate from interval: {rate_from_interval:.2f} packets/sec")

        if len(timestamps) >= 2:
            # Use timestamp method as primary result
            packet_count, rate = calculate_send_rate_from_timestamps(timestamps, start_time, end_time)
            total_send_rate += rate

    print("\n" + "=" * 60)
    print("Total Sending Rate (all flows):")
    print("=" * 60)
    print(f"  Total send rate: {total_send_rate:.2f} packets/sec")

    return total_send_rate


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Calculate actual sending rate from sender logs")
    parser.add_argument("outputs_dir", type=str,
                       help="Directory containing sender logs (e.g., program/qos/outputs)")
    parser.add_argument("--flow-id", type=int, choices=[0, 1, 2],
                       help="Specific flow ID to analyze (0, 1, or 2)")
    parser.add_argument("--start-time", type=float,
                       help="Start time for measurement (seconds since epoch)")
    parser.add_argument("--end-time", type=float,
                       help="End time for measurement (seconds since epoch)")

    args = parser.parse_args()

    calculate_send_rate(
        args.outputs_dir,
        args.flow_id,
        args.start_time,
        args.end_time
    )


if __name__ == "__main__":
    main()

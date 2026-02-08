#!/usr/bin/env python3
"""
Unified analysis script for WRR bandwidth allocation and latency
This script ensures consistency between bandwidth and latency measurements
"""

import re
import sys
from pathlib import Path
from collections import defaultdict
import statistics

# Maximum valid latency (ms). Latencies above this are rejected to avoid wrong matches.
# WRR congestion can cause tens of seconds delay; 120 s gives margin without being too loose.
MAX_LATENCY_MS = 120000  # 120 seconds


def parse_receiver_log(receiver_file, payload_marker="P4 is cool"):
    """
    Parse receiver log and extract packet reception timestamps.
    Only counts packets that contain the given payload (e.g. load = 'P4 is cool'),
    so that ICMPv6 and other non-sent packets are excluded.
    """
    timestamps = []

    if not receiver_file.exists():
        print(f"Warning: {receiver_file} not found")
        return timestamps

    pending_ts = None
    with open(receiver_file, 'r') as f:
        for line in f:
            # New packet block started; discard any pending timestamp from previous block
            if 'got a packet' in line:
                pending_ts = None
                continue
            # Format: "packet is received at time : 1234567890.123"
            match = re.search(r'received at time : ([\d.]+)', line)
            if match:
                pending_ts = float(match.group(1))
                continue
            # Only count this packet if it has our payload (e.g. load = 'P4 is cool')
            if payload_marker in line and pending_ts is not None:
                timestamps.append(pending_ts)
                pending_ts = None

    return timestamps


def parse_sender_log(sender_file):
    """Parse sender log and extract packet send timestamps and sequence numbers"""
    send_times = []

    if not sender_file.exists():
        print(f"Warning: {sender_file} not found")
        return send_times

    with open(sender_file, 'r') as f:
        for line in f:
            # Format: "This host has sent 123 packets until now : 1234567890.123"
            match = re.search(r'sent (\d+) packets until now : ([\d.]+)', line)
            if match:
                seq_num = int(match.group(1))
                timestamp = float(match.group(2))
                send_times.append((seq_num, timestamp))

    return send_times


def calculate_latency(send_times, recv_times, window_start, window_end):
    """
    Calculate latency for packets received in the time window.
    Uses seq_num matching: recv_idx (0-based) corresponds to packet seq_num = recv_idx+1.
    Lookup send_time by seq_num, so works with sparse logs (log_every > 1).
    """
    latencies = []

    # Build seq_num -> send_time map (adaptive to log_every: sparse or dense)
    send_time_by_seq = {seq_num: t for seq_num, t in send_times}

    for recv_idx, recv_time in enumerate(recv_times):
        if not (window_start <= recv_time <= window_end):
            continue
        packet_seq = recv_idx + 1  # 1-based packet number
        if packet_seq not in send_time_by_seq:
            continue
        send_time = send_time_by_seq[packet_seq]
        latency_ms = (recv_time - send_time) * 1000
        if 0 <= latency_ms < MAX_LATENCY_MS:
            latencies.append(latency_ms)

    return latencies


def diagnose_latency_failures(flow_id, send_times, recv_times):
    """
    Find which received packets failed to get a latency and why (seq_num matching).
    Returns a list of dicts: {'recv_idx', 'recv_time', 'send_time' or None, 'latency_ms' or None, 'reason'}
    """
    send_time_by_seq = {seq_num: t for seq_num, t in send_times}
    failures = []
    for recv_idx, recv_time in enumerate(recv_times):
        packet_seq = recv_idx + 1
        if packet_seq not in send_time_by_seq:
            failures.append({
                'recv_idx': recv_idx,
                'recv_time': recv_time,
                'send_time': None,
                'latency_ms': None,
                'reason': f'no_send_timestamp (packet {packet_seq} not in sender log; log_every may omit it)'
            })
            continue
        send_time = send_time_by_seq[packet_seq]
        latency_ms = (recv_time - send_time) * 1000
        if latency_ms < 0:
            failures.append({
                'recv_idx': recv_idx,
                'recv_time': recv_time,
                'send_time': send_time,
                'latency_ms': latency_ms,
                'reason': 'latency_negative (recv time before send time, reorder or clock skew)'
            })
        elif latency_ms >= MAX_LATENCY_MS:
            failures.append({
                'recv_idx': recv_idx,
                'recv_time': recv_time,
                'send_time': send_time,
                'latency_ms': latency_ms,
                'reason': f'latency_exceeds_max (>= {MAX_LATENCY_MS} ms)'
            })
    return failures


def analyze_wrr_results(outputs_dir, start_time=None, end_time=None, window_size=10, start_offset=0):
    """
    Unified analysis of WRR bandwidth allocation and latency.

    Expects in outputs_dir:
      - receiver_h_r1.txt, receiver_h_r2.txt, receiver_h_r3.txt  (receiver logs)
      - sender_h1.txt, sender_h2.txt, sender_h3.txt             (sender logs)

    Receiver log: only packets with load = 'P4 is cool' are counted (ICMPv6 etc. excluded).
    Receiver block format: "packet is received at time : <timestamp>" then later "load = 'P4 is cool'"
    Sender log line format: "This host has sent <N> packets until now : <timestamp>"

    Args:
        outputs_dir: Directory containing sender and receiver logs (e.g. program/qos/outputs)
        start_time: Start time for measurement (if None, use first packet time + start_offset)
        end_time: End time for measurement (if None, use last packet time; all packets included)
        window_size: Size of time windows in seconds
        start_offset: Offset in seconds from first packet time (default: 0, start from first packet)
    """
    outputs_path = Path(outputs_dir)
    if not outputs_path.is_dir():
        print(f"Error: outputs_dir is not a directory: {outputs_path}")
        return

    # Parse logs for each flow
    flow_recv_times = {}
    flow_send_times = {}

    for flow_id in range(3):
        receiver_file = outputs_path / f"receiver_h_r{flow_id+1}.txt"
        sender_file = outputs_path / f"sender_h{flow_id+1}.txt"

        recv_times = parse_receiver_log(receiver_file)
        send_times = parse_sender_log(sender_file)

        flow_recv_times[flow_id] = recv_times
        flow_send_times[flow_id] = send_times

        print(f"Flow {flow_id}:")
        print(f"  Received: {len(recv_times)} packets")
        print(f"  Sent: {len(send_times)} packets")

    if not any(flow_recv_times.values()):
        print("Error: No packets found in receiver logs")
        return

    # Determine measurement time window
    all_recv_times = []
    for recv_times in flow_recv_times.values():
        all_recv_times.extend(recv_times)

    if not all_recv_times:
        print("Error: No timestamps found")
        return

    # Also consider send times to get the earliest packet time
    all_send_times = []
    for send_times in flow_send_times.values():
        for seq_num, send_time in send_times:
            all_send_times.append(send_time)

    # Use the earliest time (either send or receive) as the reference
    earliest_time = min(min(all_recv_times) if all_recv_times else float('inf'),
                       min(all_send_times) if all_send_times else float('inf'))
    if earliest_time == float('inf'):
        print("Error: No timestamps found in sender or receiver logs")
        return

    if start_time is None:
        start_time = earliest_time + start_offset  # Start from first packet + offset
    if end_time is None:
        # Include all packets: use last packet time (no tail exclusion by default)
        end_time = max(all_recv_times)
    if end_time <= start_time:
        print("Error: Measurement window is empty (end_time <= start_time)")
        return

    print(f"\n{'='*60}")
    print(f"Measurement window: {start_time:.2f} - {end_time:.2f} seconds")
    print(f"Window size: {window_size} seconds")
    print(f"{'='*60}\n")

    # Analyze each time window
    current_time = start_time
    window_num = 1
    all_window_stats = []

    while current_time < end_time:
        window_end = min(current_time + window_size, end_time)

        print(f"Window {window_num}: {current_time:.2f} - {window_end:.2f} seconds")
        print("-" * 60)

        window_stats = {}
        total_packets = 0
        total_rate = 0.0

        for flow_id in range(3):
            recv_times = flow_recv_times[flow_id]
            send_times = flow_send_times[flow_id]

            # Count packets in window
            packets_in_window = [t for t in recv_times if current_time <= t <= window_end]
            packet_count = len(packets_in_window)
            window_duration = window_end - current_time
            rate = packet_count / window_duration if window_duration > 0 else 0.0

            # Calculate latency
            latencies = calculate_latency(send_times, recv_times, current_time, window_end)

            window_stats[flow_id] = {
                'packets': packet_count,
                'rate': rate,
                'latencies': latencies
            }

            total_packets += packet_count
            total_rate += rate

            # Print bandwidth stats
            print(f"  Flow {flow_id}: {packet_count} packets, {rate:.2f} pps", end="")
            if latencies:
                print(f" | Latency: {len(latencies)} samples, "
                      f"median={statistics.median(latencies):.2f} ms, "
                      f"mean={statistics.mean(latencies):.2f} ms")
            else:
                print(" | Latency: No samples")

        # Calculate percentages
        if total_rate > 0:
            print(f"\n  Total: {total_packets} packets, {total_rate:.2f} pps")
            print("  Bandwidth allocation:")
            for flow_id in range(3):
                percentage = (window_stats[flow_id]['rate'] / total_rate) * 100
                print(f"    Flow {flow_id}: {percentage:.2f}%")

        # Print latency statistics
        print("\n  Latency Statistics:")
        for flow_id in range(3):
            latencies = window_stats[flow_id]['latencies']
            if latencies:
                print(f"    Flow {flow_id}:")
                print(f"      Samples: {len(latencies)}")
                print(f"      Min: {min(latencies):.2f} ms")
                if len(latencies) >= 1:
                    print(f"      Median: {statistics.median(latencies):.2f} ms")
                else:
                    print(f"      Median: N/A")
                print(f"      Max: {max(latencies):.2f} ms")
                print(f"      Mean: {statistics.mean(latencies):.2f} ms")
                if len(latencies) >= 2:
                    print(f"      Std: {statistics.stdev(latencies):.2f} ms")
                else:
                    print(f"      Std: N/A (need >= 2 samples)")
            else:
                print(f"    Flow {flow_id}: No latency samples")

        all_window_stats.append(window_stats)
        current_time = window_end
        window_num += 1
        print()

    # Overall statistics across all windows
    print("=" * 60)
    print("Overall Statistics (all windows combined):")
    print("=" * 60)

    # Combine all latencies
    overall_latencies = {0: [], 1: [], 2: []}
    total_packets_all = {0: 0, 1: 0, 2: 0}

    for window_stats in all_window_stats:
        for flow_id in range(3):
            overall_latencies[flow_id].extend(window_stats[flow_id]['latencies'])
            total_packets_all[flow_id] += window_stats[flow_id]['packets']

    print("\nBandwidth Allocation (all windows):")
    total_all = sum(total_packets_all.values())
    for flow_id in range(3):
        percentage = (total_packets_all[flow_id] / total_all * 100) if total_all > 0 else 0
        print(f"  Flow {flow_id}: {total_packets_all[flow_id]} packets ({percentage:.2f}%)")

    print("\nLatency Statistics (all windows combined):")
    for flow_id in range(3):
        latencies = overall_latencies[flow_id]
        if latencies:
            print(f"\n  Flow {flow_id}:")
            print(f"    Packets: {len(latencies)}")
            print(f"    Min: {min(latencies):.2f} ms")
            if len(latencies) >= 1:
                print(f"    Median: {statistics.median(latencies):.2f} ms")
            else:
                print(f"    Median: N/A")
            print(f"    Max: {max(latencies):.2f} ms")
            print(f"    Mean: {statistics.mean(latencies):.2f} ms")
            if len(latencies) >= 2:
                print(f"    Std: {statistics.stdev(latencies):.2f} ms")
            else:
                print(f"    Std: N/A (need >= 2 samples)")
        else:
            print(f"\n  Flow {flow_id}: No latency samples")

    # Consistency check
    print("\n" + "=" * 60)
    print("Consistency Check:")
    print("=" * 60)
    for flow_id in range(3):
        bandwidth_packets = total_packets_all[flow_id]
        latency_packets = len(overall_latencies[flow_id])
        diff = bandwidth_packets - latency_packets
        print(f"  Flow {flow_id}:")
        print(f"    Bandwidth measurement: {bandwidth_packets} packets")
        print(f"    Latency measurement: {latency_packets} packets")
        if bandwidth_packets > 0:
            print(f"    Difference: {diff} packets ({diff/bandwidth_packets*100:.2f}%)")
        else:
            print(f"    Difference: {diff} packets (N/A)")
        if diff > 0:
            print(f"    ⚠️  Warning: {diff} packets received but latency not calculated")
        elif diff < 0:
            print(f"    ⚠️  Warning: {abs(diff)} more latency samples than received packets")

    # Diagnose unmatched packets for flows where bandwidth > latency count
    flows_with_gap = [f for f in range(3) if total_packets_all[f] > len(overall_latencies[f])]
    if flows_with_gap:
        print("\n" + "=" * 60)
        print("Unmatched packet diagnosis (seq_num matching):")
        print("=" * 60)
        for flow_id in flows_with_gap:
            send_times = flow_send_times[flow_id]
            recv_times = flow_recv_times[flow_id]
            failures = diagnose_latency_failures(flow_id, send_times, recv_times)
            latency_count = len(overall_latencies[flow_id])
            # When sender log is sparse (log_every > 1), most failures are no_send_timestamp; print summary only
            no_ts_count = sum(1 for f in failures if 'no_send_timestamp' in f.get('reason', ''))
            if len(failures) > 20 and no_ts_count == len(failures):
                print(f"\n  Flow {flow_id}: {len(failures)} packets have no send timestamp (expected with log_every > 1)")
                print(f"    Latency computed for {latency_count} packets (those with send timestamps)")
            else:
                print(f"\n  Flow {flow_id}: {len(failures)} packet(s) failed to get latency")
                for i, fail in enumerate(failures[:50]):  # limit to first 50
                    print(f"    [{i+1}] recv_idx={fail['recv_idx']}, recv_time={fail['recv_time']:.6f}")
                    if fail['send_time'] is not None:
                        print(f"        send_time={fail['send_time']:.6f}, latency_ms={fail['latency_ms']:.2f}")
                    print(f"        reason: {fail['reason']}")
                if len(failures) > 50:
                    print(f"    ... and {len(failures) - 50} more")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Unified analysis of WRR bandwidth allocation and latency"
    )
    parser.add_argument("outputs_dir", type=str,
                       help="Directory containing sender and receiver logs")
    parser.add_argument("--start-time", type=float,
                       help="Start time for measurement (seconds since epoch)")
    parser.add_argument("--end-time", type=float,
                       help="End time for measurement (seconds since epoch)")
    parser.add_argument("--window-size", type=int, default=10,
                       help="Time window size in seconds (default: 10)")
    parser.add_argument("--start-offset", type=float, default=0,
                       help="Offset in seconds from first packet time (default: 0, start from first packet)")

    args = parser.parse_args()

    analyze_wrr_results(
        args.outputs_dir,
        args.start_time,
        args.end_time,
        args.window_size,
        args.start_offset
    )


if __name__ == "__main__":
    main()

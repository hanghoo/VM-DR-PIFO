#!/usr/bin/env python3
"""
Enhanced traffic sending script
Supports:
- Fixed rank value (default 2000)
- Auto-stop (based on time or packet count)
- Create congestion scenarios to test WRR weight allocation
- --fast: high-speed mode (pre-build packets + sendpfast, minimal logging; no per-packet timestamps, not for latency analysis; requires tcpreplay)
"""

import argparse
import socket
import struct
import sys
import time

from scapy.all import sendp, sendpfast, get_if_list, get_if_hwaddr, get_if_addr
from scapy.all import Ether, IP, TCP, IPOption


def get_if():
    iface = None
    for i in get_if_list():
        if "eth0" in i:
            iface = i
            break
    if not iface:
        print("Cannot find eth0 interface")
        exit(1)
    return iface


def main():
    parser = argparse.ArgumentParser(description="Enhanced traffic sending script (fixed rank)")
    parser.add_argument("--h", help="Workload file path (optional, if provided read from file)", type=str, default=None)
    parser.add_argument("--des", help="Destination IP address", type=str, required=True)
    parser.add_argument("--rate", help="Send rate: sleep time between packets (seconds), lower value = higher rate", type=float, default=None)
    parser.add_argument("--pps", help="Send rate in packets per second (overrides --rate if set). E.g. --pps=18 for 18 pps", type=float, default=None)
    parser.add_argument("--log-every", help="Log send timestamp every N packets (default 1). Use 0 for no per-packet log (max pps test); use >1 to reduce I/O; log_every>1 or 0 yields fewer timestamps for latency analysis", type=int, default=1)

    # Fixed rank options
    parser.add_argument("--num-packets", help="Number of packets (if using dynamic generation)", type=int, default=None)
    parser.add_argument("--rank-value", help="Fixed rank value", type=int, default=2000)

    # Auto-stop options
    parser.add_argument("--duration", help="Send duration (seconds), 0 means send all packets. Used to create congestion scenarios", type=float, default=0)
    parser.add_argument("--max-packets", help="Maximum packet count limit", type=int, default=None)

    # Flow mode
    parser.add_argument("--flow-id", help="Flow ID (for logging)", type=int, default=0)
    parser.add_argument("--fast", action="store_true",
                        help="High-speed mode: pre-build packets, use sendpfast, minimal logging. No per-packet timestamps (not for latency analysis). Requires tcpreplay.")

    args = parser.parse_args()

    # Determine packet count and rank value
    if args.h:
        # Read from file
        with open(args.h, 'r') as f:
            ranks = [int(line.strip()) for line in f if line.strip()]
        num_packets = len(ranks)
        rank_value = ranks[0] if ranks else args.rank_value
    elif args.num_packets:
        # Dynamic generation: all packets use fixed rank
        num_packets = args.num_packets
        rank_value = args.rank_value
        ranks = [rank_value] * num_packets
    else:
        print("Error: Must provide --h (workload file) or --num-packets (packet count)")
        sys.exit(1)

    # Rate: --pps takes precedence over --rate
    if args.pps is not None:
        if args.pps <= 0:
            print("Error: --pps must be positive")
            sys.exit(1)
        args.rate = 1.0 / args.pps
    elif args.rate is None:
        args.rate = 0.001
    if args.rate <= 0:
        print("Error: rate (or 1/pps) must be positive")
        sys.exit(1)

    # Set stop conditions
    start_time = time.time()
    max_time = start_time + args.duration if args.duration > 0 else None
    max_packets = args.max_packets if args.max_packets else num_packets

    # Initialize network
    addr = socket.gethostbyname(args.des)
    iface = get_if()
    args.m = "P4 is cool"

    # ---------- Fast mode: pre-build + sendpfast, minimal logging ----------
    if args.fast:
        target_pps = int(1.0 / args.rate)
        n_pkts = min(max_packets, int(args.duration * target_pps)) if max_time else max_packets
        if n_pkts <= 0:
            print("Fast mode: no packets to send (duration too short or max_packets=0)")
        else:
            print(f"Flow {args.flow_id}: Fast mode – pre-building {n_pkts} packets, then sendpfast at {target_pps} pps")
            print(f"  Rank value: {rank_value} (fixed)")
            if args.log_every > 0:
                print(f"  Will write theoretical timestamps (every {args.log_every} pkts) after send for latency analysis")
            else:
                print(f"  No timestamps (use --log-every=N to write theoretical timestamps after send)")
            rank_bytes = struct.pack('>i', rank_value)
            base = Ether(src=get_if_hwaddr(iface), dst="ff:ff:ff:ff:ff:ff", type=0x800) / IP(
                src=get_if_addr(iface), dst=addr, options=IPOption(rank_bytes)
            ) / TCP() / args.m
            pkts = [base.copy() for _ in range(n_pkts)]
            t0 = time.time()
            sendpfast(pkts, pps=target_pps, loop=1, iface=iface)
            elapsed = time.time() - t0
            print(f"\nFlow {args.flow_id}: Fast mode completed")
            print(f"  Total packets: {n_pkts}")
            print(f"  Total time: {elapsed:.2f} seconds")
            if elapsed > 0:
                print(f"  Average rate: {n_pkts/elapsed:.2f} packets/sec")
            # Optional: write theoretical send timestamps (post-send, zero impact on pps)
            if args.log_every > 0:
                print(f"  Theoretical timestamps (every {args.log_every} pkts) for latency analysis")
                for n in range(1, n_pkts + 1):
                    if n == 1 or n % args.log_every == 0 or n == n_pkts:
                        t = t0 + (n - 1) * (elapsed / (n_pkts - 1)) if n_pkts > 1 else t0
                        print(f"This host has sent {n} packets until now : {t}")
            sys.stdout.flush()
        return

    # ---------- Normal mode: per-packet send with rate control and optional logging ----------
    print(f"Flow {args.flow_id}: Starting to send traffic to {addr}")
    print(f"  Rank value: {rank_value} (fixed)")
    print(f"  Send rate: {args.rate} sec/packet ({1.0/args.rate:.2f} packets/sec)")
    if args.log_every == 0:
        print(f"  No per-packet log (--log-every=0, max pps test)")
    elif args.log_every > 1:
        print(f"  Log every {args.log_every} packets (to reduce I/O)")
    if max_time:
        print(f"  Duration: {args.duration} seconds (will create congestion scenario)")
    else:
        print(f"  Total packets: {num_packets}")

    sent_count = 0
    next_send_time = start_time

    try:
        for i, rank in enumerate(ranks):
            # Check stop conditions
            if sent_count >= max_packets:
                print(f"Reached maximum packet limit: {max_packets}")
                break

            if max_time and time.time() >= max_time:
                print(f"Reached time limit: {args.duration} seconds")
                break

            # Wait until next ideal send time (keeps rate accurate under variable send overhead)
            now = time.time()
            if sent_count > 0 and now < next_send_time:
                time.sleep(next_send_time - now)

            # Construct packet
            rank_bytes = struct.pack('>i', rank)
            pkt = Ether(
                src=get_if_hwaddr(iface),
                dst="ff:ff:ff:ff:ff:ff",
                type=0x800
            ) / IP(
                src=get_if_addr(iface),
                dst=addr,
                options=IPOption(rank_bytes)
            ) / TCP() / args.m

            # Send packet
            sendp(pkt, iface=iface, verbose=False)
            sent_count += 1

            # Advance next ideal send time by one interval (keeps rate accurate, no drift)
            next_send_time += args.rate

            # Record send time (every log_every packets to reduce I/O; log_every=0 = no per-packet log)
            if args.log_every > 0 and (sent_count == 1 or sent_count % args.log_every == 0):
                send_time = time.time()
                print(f"This host has sent {sent_count} packets until now : {send_time}")

    except KeyboardInterrupt:
        print(f"\nInterrupted: sent {sent_count} packets")
        raise

    elapsed = time.time() - start_time
    print(f"\nFlow {args.flow_id}: Sending completed")
    print(f"  Total packets: {sent_count}")
    print(f"  Total time: {elapsed:.2f} seconds")
    if elapsed > 0:
        print(f"  Average rate: {sent_count/elapsed:.2f} packets/sec")


if __name__ == '__main__':
    main()

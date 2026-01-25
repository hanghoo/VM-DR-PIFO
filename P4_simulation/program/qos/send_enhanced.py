#!/usr/bin/env python3
"""
Enhanced traffic sending script
Supports:
- Fixed rank value (default 2000)
- Auto-stop (based on time or packet count)
- Create congestion scenarios to test WRR weight allocation
"""

import argparse
import socket
import struct
import sys
import time

from scapy.all import sendp, send, hexdump, get_if_list, get_if_hwaddr, get_if_addr, srp
from scapy.all import Ether, IP, UDP, TCP, IPv6
from scapy.all import Packet, IPOption


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
    parser.add_argument("--rate", help="Send rate: sleep time between packets (seconds), lower value = higher rate", type=float, default=0.001)

    # Fixed rank options
    parser.add_argument("--num-packets", help="Number of packets (if using dynamic generation)", type=int, default=None)
    parser.add_argument("--rank-value", help="Fixed rank value", type=int, default=2000)

    # Auto-stop options
    parser.add_argument("--duration", help="Send duration (seconds), 0 means send all packets. Used to create congestion scenarios", type=float, default=0)
    parser.add_argument("--max-packets", help="Maximum packet count limit", type=int, default=None)

    # Flow mode
    parser.add_argument("--flow-id", help="Flow ID (for logging)", type=int, default=0)

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

    # Set stop conditions
    start_time = time.time()
    max_time = start_time + args.duration if args.duration > 0 else None
    max_packets = args.max_packets if args.max_packets else num_packets

    # Initialize network
    addr = socket.gethostbyname(args.des)
    iface = get_if()
    args.m = "P4 is cool"

    print(f"Flow {args.flow_id}: Starting to send traffic to {addr}")
    print(f"  Rank value: {rank_value} (fixed)")
    print(f"  Send rate: {args.rate} sec/packet ({1.0/args.rate:.0f} packets/sec)")
    if max_time:
        print(f"  Duration: {args.duration} seconds (will create congestion scenario)")
    else:
        print(f"  Total packets: {num_packets}")

    sent_count = 0

    try:
        for i, rank in enumerate(ranks):
            # Check stop conditions
            if sent_count >= max_packets:
                print(f"Reached maximum packet limit: {max_packets}")
                break

            if max_time and time.time() >= max_time:
                print(f"Reached time limit: {args.duration} seconds")
                break

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

            # Record send time
            send_time = time.time()
            print(f"This host has sent {sent_count} packets until now : {send_time}")

            # Fixed rate sending
            time.sleep(args.rate)

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

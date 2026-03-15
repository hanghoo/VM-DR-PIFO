#!/usr/bin/env python3
"""
Telemetry sender for h3: sends MRI probes to c1 (10.0.2.3) for Q-learning.
Uses send.py style MRI packets with start timestamp for latency computation.
"""

import argparse
import socket
import sys
import time

from scapy.all import (
    IP,
    UDP,
    Ether,
    FieldLenField,
    IntField,
    IPOption,
    Packet,
    PacketListField,
    ShortField,
    get_if_hwaddr,
    get_if_list,
    get_if_addr,
    sendp,
)
from scapy.layers.inet import _IPOption_HDR


def get_if():
    for i in get_if_list():
        if "eth0" in i:
            return i
    print("Cannot find eth0 interface", file=sys.stderr)
    sys.exit(1)
    return None


class SwitchTrace(Packet):
    fields_desc = [
        IntField("swid", 0),
        IntField("qdepth", 0),
        IntField("flow1_qdepth", 0),
        IntField("flow2_qdepth", 0),
        IntField("latency", 0),
    ]

    def extract_padding(self, p):
        return "", p


class IPOption_MRI(IPOption):
    name = "MRI"
    option = 31
    fields_desc = [
        _IPOption_HDR,
        FieldLenField(
            "length", None, fmt="B",
            length_of="swtraces",
            adjust=lambda pkt, l: l + 4
        ),
        ShortField("count", 0),
        PacketListField(
            "swtraces", [], SwitchTrace,
            count_from=lambda pkt: pkt.count
        ),
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Telemetry sender: MRI probes to c1 for Q-learning."
    )
    parser.add_argument(
        "--des",
        default="10.0.2.3",
        help="Destination IP (default: 10.0.2.3 for c1)"
    )
    parser.add_argument(
        "-r", "--rate",
        type=float,
        default=2.0,
        help="Send rate in packets per second (default: 2)"
    )
    parser.add_argument(
        "-d", "--duration",
        type=int,
        default=60,
        help="Duration in seconds (default: 60)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=4321,
        help="UDP destination port (default: 4321)"
    )
    args = parser.parse_args()

    addr = socket.gethostbyname(args.des)
    iface = get_if()
    src = get_if_addr(iface)

    interval = 1.0 / args.rate if args.rate > 0 else 1.0
    total_pkts = int(args.duration * args.rate)

    pkt = (
        Ether(src=get_if_hwaddr(iface), dst="ff:ff:ff:ff:ff:ff")
        / IP(src=src, dst=addr, options=IPOption_MRI(count=0, swtraces=[]))
        / UDP(dport=args.port, sport=1234)
        / f"0,{time.time()},telemetry"
    )

    print(f"Sending MRI probes to {addr} port {args.port}, {total_pkts} pkts @ {args.rate} pps", flush=True)
    try:
        for i in range(total_pkts):
            pkt[UDP].payload.load = f"{i},{time.time()},telemetry".encode()
            sendp(pkt, iface=iface, verbose=False)
            if (i + 1) % 20 == 0:
                print(f"  sent #{i + 1}", flush=True)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nInterrupted", flush=True)
    print("Telemetry sender done.", flush=True)


if __name__ == "__main__":
    main()

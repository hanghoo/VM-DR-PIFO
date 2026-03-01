#!/usr/bin/env python3
"""
MRI-style probe sender for P4_simulation.
Sends low-rate packets with IPOption_MRI (option 31) for in-band telemetry.
Used with receive.py for MRI_STYLE_TEST_GUIDE.md testing.
"""

import argparse
import socket
import sys
from time import sleep

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
    print("Cannot find eth0 interface")
    sys.exit(1)
    return None


class SwitchTrace(Packet):
    fields_desc = [
        IntField("swid", 0),
        IntField("qdepth", 0),
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
            adjust=lambda pkt, l: l * 2 + 4
        ),
        ShortField("count", 0),
        PacketListField(
            "swtraces", [], SwitchTrace,
            count_from=lambda pkt: pkt.count
        ),
    ]


def main():
    parser = argparse.ArgumentParser(
        description="MRI-style probe sender. Sends packets with MRI option for qdepth telemetry."
    )
    parser.add_argument(
        "des",
        nargs="?",
        default="10.0.2.1",
        help="Destination IP (default: 10.0.2.1 for h_r1)"
    )
    parser.add_argument(
        "message",
        nargs="?",
        default="P4 is cool",
        help='Payload message (default: "P4 is cool")'
    )
    parser.add_argument(
        "duration",
        nargs="?",
        type=int,
        default=30,
        help="Number of seconds to send (default: 30)"
    )
    parser.add_argument(
        "-r", "--rate",
        type=float,
        default=1.0,
        help="Send rate in packets per second (default: 1). Use higher rate (e.g. 50) to see qdepth>1 under congestion."
    )
    args = parser.parse_args()

    addr = socket.gethostbyname(args.des)
    iface = get_if()
    src = get_if_addr(iface)

    pkt = (
        Ether(src=get_if_hwaddr(iface), dst="ff:ff:ff:ff:ff:ff")
        / IP(src=src, dst=addr, options=IPOption_MRI(count=0, swtraces=[]))
        / UDP(dport=4321, sport=1234)
        / args.message
    )

    interval = 1.0 / args.rate if args.rate > 0 else 1.0
    total_pkts = int(args.duration * args.rate)
    print(f"Sending MRI probes to {addr}, {total_pkts} packets at {args.rate} pps")
    pkt.show2()

    try:
        for i in range(total_pkts):
            sendp(pkt, iface=iface, verbose=False)
            if (i + 1) % 10 == 0 or args.rate <= 5:
                print(f"sent #{i + 1}")
            sleep(interval)
    except KeyboardInterrupt:
        print("\nInterrupted")
        raise


if __name__ == "__main__":
    main()

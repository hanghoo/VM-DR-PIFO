#!/usr/bin/env python3

import argparse
import socket
import time

from scapy.all import Ether, IP, TCP, Packet, IntField, ShortField, FieldLenField, PacketListField
from scapy.all import IPOption, get_if_list, get_if_hwaddr, get_if_addr, sendp
from scapy.layers.inet import _IPOption_HDR


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
        FieldLenField("length", None, fmt="B", length_of="swtraces", adjust=lambda pkt, l: l * 2 + 4),
        ShortField("count", 0),
        PacketListField("swtraces", [], SwitchTrace, count_from=lambda pkt: pkt.count),
    ]


def get_if():
    for i in get_if_list():
        if "eth0" in i:
            return i
    raise RuntimeError("Cannot find eth0 interface")


def main():
    parser = argparse.ArgumentParser(description="Send minimal MRI telemetry packets")
    parser.add_argument("--des", type=str, default="10.0.2.2", help="Destination IPv4")
    parser.add_argument("--count", type=int, default=10, help="Number of packets to send")
    parser.add_argument("--interval", type=float, default=0.2, help="Seconds between packets")
    parser.add_argument("--dport", type=int, default=12345, help="TCP destination port")
    args = parser.parse_args()

    iface = get_if()
    dst = socket.gethostbyname(args.des)
    src = get_if_addr(iface)

    print(f"sending on {iface}, src={src}, dst={dst}, count={args.count}")
    for idx in range(args.count):
        pkt = (
            Ether(src=get_if_hwaddr(iface), dst="ff:ff:ff:ff:ff:ff")
            / IP(src=src, dst=dst, options=IPOption_MRI(count=0, swtraces=[]))
            / TCP(dport=args.dport, sport=20000 + idx)
            / b"MRI-TEST"
        )
        sendp(pkt, iface=iface, verbose=False)
        print(f"sent #{idx + 1}")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()

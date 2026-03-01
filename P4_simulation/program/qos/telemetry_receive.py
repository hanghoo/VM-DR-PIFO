#!/usr/bin/env python3

import argparse
import sys
import time

from scapy.all import IP, Packet, IntField, ShortField, FieldLenField, PacketListField
from scapy.all import IPOption, get_if_list, sniff
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


def find_mri_option(pkt):
    if IP not in pkt:
        return None
    opts = pkt[IP].options
    for opt in opts:
        if isinstance(opt, IPOption_MRI):
            return opt
        if getattr(opt, "option", None) == 31:
            return opt
    return None


def handle(pkt):
    mri = find_mri_option(pkt)
    if mri is None:
        return
    print(f"\n[{time.time():.6f}] got MRI packet")
    try:
        print(f"  count={getattr(mri, 'count', 'N/A')}")
        traces = getattr(mri, "swtraces", [])
        for i, tr in enumerate(traces):
            print(f"  trace[{i}] swid={tr.swid} qdepth={tr.qdepth}")
    except Exception as e:
        print(f"  failed to decode MRI details: {e}")
        print(f"  raw option: {mri}")
    sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser(description="Receive and print MRI telemetry packets")
    parser.add_argument("--iface", type=str, default=None, help="Interface to sniff (default: eth0)")
    parser.add_argument("--count", type=int, default=0, help="Stop after N packets (0 means continuous)")
    args = parser.parse_args()

    iface = args.iface or get_if()
    print(f"sniffing on {iface} for IP packets with MRI option (31)")
    sniff(iface=iface, filter="ip", prn=handle, store=False, count=args.count)


if __name__ == "__main__":
    main()

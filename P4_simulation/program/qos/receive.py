#!/usr/bin/env python3
"""
MRI-style receiver for P4_simulation.
Sniffs UDP port 4321 and displays full packet structure including MRI options (swid, qdepth).
Used with send.py for MRI_STYLE_TEST_GUIDE.md testing.
"""

import sys
import time

from scapy.all import (
    IP,
    FieldLenField,
    IntField,
    IPOption,
    Packet,
    PacketListField,
    ShortField,
    get_if_list,
    sniff,
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


def find_mri_option(pkt):
    """Find MRI option (option 31) in IP packet."""
    if IP not in pkt:
        return None
    opts = pkt[IP].options
    for opt in opts:
        if isinstance(opt, IPOption_MRI):
            return opt
        if getattr(opt, "option", None) == 31:
            return opt
    return None


def handle_pkt(pkt):
    print("got a packet")
    print("packet received at time:", time.time())
    # Full packet structure - shows all layers including MRI options with swid, qdepth
    pkt.show2()
    # Summary of MRI traces if present
    mri = find_mri_option(pkt)
    if mri is not None:
        try:
            print("--- MRI summary ---")
            print(f"  count={getattr(mri, 'count', 'N/A')}")
            traces = getattr(mri, "swtraces", [])
            for i, tr in enumerate(traces):
                print(f"  trace[{i}] swid={tr.swid} qdepth={tr.qdepth}")
        except Exception as e:
            print(f"  (MRI parse: {e})")
    print("---")
    sys.stdout.flush()


def main():
    iface = "eth0"
    print(f"sniffing on {iface} for UDP port 4321 (MRI probes)")
    print("the simulation started at time:", time.time())
    sys.stdout.flush()
    sniff(filter="udp and port 4321", iface=iface, prn=handle_pkt)


if __name__ == "__main__":
    main()

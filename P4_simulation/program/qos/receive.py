#!/usr/bin/env python3
"""
MRI-style receiver for P4_simulation.
Sniffs UDP port 4321 and displays full packet structure including MRI options (swid, qdepth).
Used with send.py for MRI_STYLE_TEST_GUIDE.md testing.
"""

import os
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
        IntField("flow1_qdepth", 0),
        IntField("flow2_qdepth", 0),
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
            adjust=lambda pkt, l: l + 4  # 4-byte header + swtraces (16 bytes per trace)
        ),
        ShortField("count", 0),
        PacketListField(
            "swtraces", [], SwitchTrace,
            count_from=lambda pkt: pkt.count
        ),
    ]


def find_mri_option(pkt):
    """Find MRI option (option 31) in IP packet. Returns parsed mri or None."""
    if IP not in pkt:
        return None
    opts = pkt[IP].options
    for opt in opts:
        if isinstance(opt, IPOption_MRI):
            return opt
        if getattr(opt, "option", None) == 31:
            return opt
        # Scapy may parse unknown options as (type, raw_bytes) tuple
        if isinstance(opt, tuple) and len(opt) >= 2 and opt[0] == 31:
            return ("raw", opt[1])
    return None


def parse_mri_from_raw(raw_bytes):
    """Parse MRI from raw option bytes: count(2) + traces. Supports 16 and 20 byte traces."""
    try:
        if len(raw_bytes) < 4:
            return None
        count = (raw_bytes[0] << 8) | raw_bytes[1]
        trace_bytes = len(raw_bytes) - 2
        if count == 0:
            return []
        if trace_bytes < count * 16:
            return None
        bytes_per_trace = trace_bytes // count
        if bytes_per_trace not in (16, 20):
            return None
        traces = []
        off = 2
        for _ in range(count):
            if bytes_per_trace == 16:
                t = {
                    "swid": int.from_bytes(raw_bytes[off:off+4], "big"),
                    "qdepth": int.from_bytes(raw_bytes[off+4:off+8], "big"),
                    "flow1_qdepth": int.from_bytes(raw_bytes[off+8:off+12], "big"),
                    "flow2_qdepth": int.from_bytes(raw_bytes[off+12:off+16], "big"),
                    "latency": 0,
                }
            else:
                t = {
                    "swid": int.from_bytes(raw_bytes[off:off+4], "big"),
                    "qdepth": int.from_bytes(raw_bytes[off+4:off+8], "big"),
                    "flow1_qdepth": int.from_bytes(raw_bytes[off+8:off+12], "big"),
                    "flow2_qdepth": int.from_bytes(raw_bytes[off+12:off+16], "big"),
                    "latency": int.from_bytes(raw_bytes[off+16:off+20], "big"),
                }
            traces.append(t)
            off += bytes_per_trace
        return traces
    except Exception:
        return None


def parse_mri_manual(pkt):
    """Manually parse MRI from raw bytes. Supports both 16-byte and 20-byte trace format.
    Returns list of dicts: [{"swid", "qdepth", "flow1_qdepth", "flow2_qdepth", "latency?"}, ...]
    or None if parse fails.
    """
    try:
        raw = bytes(pkt)
        # Skip Ethernet (14 bytes) to get IP header
        if len(raw) < 34:
            return None
        raw = raw[14:]
        ihl = (raw[0] & 0x0f) * 4
        if ihl < 20:
            return None
        # Find option 31 in IP options (between byte 20 and ihl)
        opt_start = 20
        while opt_start < ihl - 1:
            opt_type = raw[opt_start]
            opt_len = raw[opt_start + 1]
            if opt_len < 2:
                break
            if opt_type == 31:  # MRI
                if opt_len < 6:  # need at least 4 + 2 for count
                    return None
                count = (raw[opt_start + 2] << 8) | raw[opt_start + 3]
                trace_bytes = opt_len - 4
                if count == 0:
                    return []
                bytes_per_trace = trace_bytes // count
                if bytes_per_trace not in (16, 20):
                    return None
                traces = []
                off = opt_start + 4
                for _ in range(count):
                    if bytes_per_trace == 16:
                        t = {
                            "swid": int.from_bytes(raw[off:off+4], "big"),
                            "qdepth": int.from_bytes(raw[off+4:off+8], "big"),
                            "flow1_qdepth": int.from_bytes(raw[off+8:off+12], "big"),
                            "flow2_qdepth": int.from_bytes(raw[off+12:off+16], "big"),
                            "latency": 0,
                        }
                    else:
                        t = {
                            "swid": int.from_bytes(raw[off:off+4], "big"),
                            "qdepth": int.from_bytes(raw[off+4:off+8], "big"),
                            "flow1_qdepth": int.from_bytes(raw[off+8:off+12], "big"),
                            "flow2_qdepth": int.from_bytes(raw[off+12:off+16], "big"),
                            "latency": int.from_bytes(raw[off+16:off+20], "big"),
                        }
                    traces.append(t)
                    off += bytes_per_trace
                return traces
            opt_start += opt_len
    except Exception:
        pass
    return None


# Running stats: total qdepth and per-flow depth (from all traces per packet)
_stats = {"total_sum": 0, "total_cnt": 0, "flow1_sum": 0, "flow2_sum": 0, "flow1_cnt": 0, "flow2_cnt": 0}

# For --state-file: last (q_ef, q_af) from s1 trace
_state_file_path = None


def handle_pkt(pkt):
    print("got a packet")
    print("packet received at time:", time.time())
    pkt.show2()
    traces_data = None
    mri = find_mri_option(pkt)
    if mri is not None:
        if isinstance(mri, tuple) and mri[0] == "raw":
            raw_opt = mri[1] if isinstance(mri[1], bytes) else bytes(mri[1])
            if len(raw_opt) >= 3:
                traces_data = parse_mri_from_raw(raw_opt[1:])
        else:
            try:
                traces = getattr(mri, "swtraces", [])
                traces_data = []
                for tr in traces:
                    traces_data.append({
                        "swid": getattr(tr, "swid", 0),
                        "qdepth": getattr(tr, "qdepth", 0),
                        "flow1_qdepth": getattr(tr, "flow1_qdepth", 0),
                        "flow2_qdepth": getattr(tr, "flow2_qdepth", 0),
                    })
            except Exception as e:
                print(f"  (MRI parse: {e})")
    if traces_data is None:
        traces_data = parse_mri_manual(pkt)
    if traces_data is not None:
        try:
            # Use s1 (swid=1) trace for state file; fallback to first
            t_s1 = next((x for x in traces_data if x.get("swid") == 1), traces_data[0])
            q_ef, q_af = t_s1.get("flow1_qdepth", 0), t_s1.get("flow2_qdepth", 0)
            if _state_file_path:
                try:
                    with open(_state_file_path, "w") as f:
                        f.write("%d,%d\n" % (q_ef, q_af))
                except Exception as e:
                    print(f"  (state file write failed: {e})", file=sys.stderr)
            print("--- MRI summary ---")
            print(f"  count={len(traces_data)}")
            for i, t in enumerate(traces_data):
                qd = t["qdepth"]
                f1 = t["flow1_qdepth"]
                f2 = t["flow2_qdepth"]
                print(f"  trace[{i}] swid={t['swid']} qdepth={qd} flow1={f1} flow2={f2}")
                _stats["total_sum"] += qd
                _stats["total_cnt"] += 1
                _stats["flow1_sum"] += f1
                _stats["flow2_sum"] += f2
                _stats["flow1_cnt"] += 1
                _stats["flow2_cnt"] += 1
            if traces_data:
                n = _stats["total_cnt"]
                avg_total = _stats["total_sum"] / n
                avg_f1 = _stats["flow1_sum"] / n if n else 0
                avg_f2 = _stats["flow2_sum"] / n if n else 0
                print(f"  --- running avg (n={n}) --- total_qdepth={avg_total:.1f} flow1={avg_f1:.1f} flow2={avg_f2:.1f}")
        except Exception as e:
            print(f"  (MRI stats: {e})")
    print("---")
    sys.stdout.flush()


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Receiver: sniff UDP, parse MRI (port 4321) or data (port 4322)")
    ap.add_argument("--iface", default="eth0", help="Interface to sniff")
    ap.add_argument("--port", type=int, default=4322, help="UDP port to sniff. 4321=MRI telemetry, 4322=data (h1/h2)")
    ap.add_argument("--state-file", default=None, help="Write q_ef,q_af to file for rule_based_controller")
    args = ap.parse_args()
    global _state_file_path
    _state_file_path = args.state_file
    if _state_file_path and not os.path.isabs(_state_file_path):
        _script_dir = os.path.dirname(os.path.abspath(__file__))
        _state_file_path = os.path.join(_script_dir, _state_file_path)
        os.makedirs(os.path.dirname(_state_file_path), exist_ok=True)
    iface = args.iface
    port = args.port
    print(f"sniffing on {iface} for UDP port {port}")
    if _state_file_path:
        print(f"writing state to {_state_file_path}")
        try:
            with open(_state_file_path, "w") as f:
                f.write("0,0\n")
            print("  (created initial state file)")
        except Exception as e:
            print(f"  (failed to create state file: {e})", file=sys.stderr)
    print("the simulation started at time:", time.time())
    sys.stdout.flush()
    sniff(filter=f"udp and port {port}", iface=iface, prn=handle_pkt)


if __name__ == "__main__":
    main()

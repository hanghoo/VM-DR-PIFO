#!/usr/bin/env python3
"""
Telemetry receiver for c1: parses MRI (qdepth, flow1/flow2), computes latency,
writes state file for Q-learning controller.
- flow1 = AF (h1), flow2 = EF (h2)
- State file format: q_ef,q_af,latency_ms (EF queue depth for Q-learning state)
- Payload format from telemetry_sender: "seq,start_ts,msg"
"""

import os
import re
import sys
import time

from scapy.all import IP, UDP, get_if_list, sniff

# Import MRI parsing from receive.py
from receive import parse_mri_manual, parse_mri_from_raw, find_mri_option


def get_if():
    for i in get_if_list():
        if "eth0" in i:
            return i
    print("Cannot find eth0 interface", file=sys.stderr)
    sys.exit(1)
    return None


def parse_payload_latency(pkt):
    """Parse 'seq,start_ts,msg' from UDP payload, return (seq, latency_ms) or None."""
    if UDP not in pkt or IP not in pkt:
        return None
    try:
        payload = bytes(pkt[UDP].payload)
        s = payload.decode("utf-8", errors="ignore")
        m = re.match(r"^(\d+),([\d.]+),", s)
        if not m:
            return None
        seq = int(m.group(1))
        start_ts = float(m.group(2))
        end_ts = time.time()
        latency_ms = (end_ts - start_ts) * 1000
        return (seq, latency_ms)
    except Exception:
        return None


_state_file_path = None
# Clamp qdepth to [0, 10] per QCMP
NQ = 10


def clamp_qdepth(v):
    return min(NQ, max(0, int(v)))


def handle_pkt(pkt):
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
            except Exception:
                pass
    if traces_data is None:
        traces_data = parse_mri_manual(pkt)

    latency_info = parse_payload_latency(pkt)

    if not _state_file_path:
        return

    if traces_data is None:
        return

    t_s1 = next((x for x in traces_data if x.get("swid") == 1), traces_data[0])
    # flow1=AF (h1), flow2=EF (h2)
    q_af = clamp_qdepth(t_s1.get("flow1_qdepth", 0))
    q_ef = clamp_qdepth(t_s1.get("flow2_qdepth", 0))
    latency_ms = latency_info[1] if latency_info else 0.0

    try:
        with open(_state_file_path, "w") as f:
            f.write(f"{q_ef},{q_af},{latency_ms:.2f}\n")
    except Exception as e:
        print(f"  (state file write failed: {e})", file=sys.stderr)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Telemetry receiver for Q-learning: writes q_ef,q_af,latency_ms")
    ap.add_argument("--iface", default="eth0", help="Interface to sniff")
    _default_state = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qos_qlearning_state.txt")
    ap.add_argument("--state-file", default=_default_state,
                    help="State file for controller (default: <qos_dir>/qos_qlearning_state.txt)")
    ap.add_argument("--port", type=int, default=4321, help="UDP port (default: 4321)")
    args = ap.parse_args()

    global _state_file_path
    _state_file_path = args.state_file
    if not os.path.isabs(_state_file_path):
        _script_dir = os.path.dirname(os.path.abspath(__file__))
        _state_file_path = os.path.join(_script_dir, _state_file_path)
    os.makedirs(os.path.dirname(_state_file_path) or ".", exist_ok=True)

    with open(_state_file_path, "w") as f:
        f.write("0,0,0.0\n")

    print(f"Telemetry receiver: sniffing {args.iface} UDP port {args.port}, writing to {_state_file_path}", flush=True)
    sniff(filter=f"udp and port {args.port}", iface=args.iface, prn=handle_pkt)


if __name__ == "__main__":
    main()

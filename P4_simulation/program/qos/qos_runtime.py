#!/usr/bin/env python3
"""
Q-learning WRR runtime: reads telemetry state, runs Q-learning, pushes EF quantum via P4Runtime.
Run on host after Mininet is up. Requires: telemetry_receiver on c1, telemetry_sender on h3.
"""

import argparse
import os
import sys
import time

# Add utils for p4runtime_lib
_script_dir = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(_script_dir, "qos_qlearning_state.txt")
_utils_dir = os.path.abspath(os.path.join(_script_dir, "..", "..", "utils"))
_p4runtime_path = os.path.join(_utils_dir, "p4runtime_lib")
if _utils_dir not in sys.path:
    sys.path.insert(0, _utils_dir)
if _p4runtime_path not in sys.path:
    sys.path.insert(0, _p4runtime_path)

try:
    from p4runtime_lib import bmv2
    from p4runtime_lib import helper
    from p4.v1 import p4runtime_pb2
    from p4runtime_lib.convert import encode
except ImportError as e:
    print(f"Error: {e}. Run from P4_simulation directory.", file=sys.stderr)
    sys.exit(1)

from qlearning_controller import QLearningWRRController, AF_QUANTUM_FIXED, EF_QUANTUM_MIN, EF_QUANTUM_MAX

# Queue indices: 0=AF (fixed), 1=EF (variable)
QUEUE_AF = 0
QUEUE_EF = 1

CONTROL_INTERVAL_SEC = 0.5


def set_quantum_via_p4runtime(sw, p4info_helper, queue_idx, quantum_value, reset_quota=True):
    """Set quantum for a queue via P4Runtime set_quantum_table."""
    try:
        table = p4info_helper.get("tables", name="set_quantum_table")
        if not table.match_fields:
            raise Exception("set_quantum_table has no match fields")
        match_field = table.match_fields[0]
        match_field_id = match_field.id
        match_field_bitwidth = match_field.bitwidth

        table_entry = p4runtime_pb2.TableEntry()
        table_entry.table_id = p4info_helper.get_tables_id("set_quantum_table")
        field_match = p4runtime_pb2.FieldMatch()
        field_match.field_id = match_field_id
        field_match.exact.value = encode(queue_idx, match_field_bitwidth)
        table_entry.match.extend([field_match])

        action_info = p4info_helper.get("actions", name="set_wrr_quantum")
        action = table_entry.action.action
        action.action_id = action_info.preamble.id
        param_map = {p.name: p.id for p in action_info.params}

        p1 = action.params.add()
        p1.param_id = param_map["queue_idx"]
        p1.value = encode(queue_idx, 48)
        p2 = action.params.add()
        p2.param_id = param_map["quantum_value"]
        p2.value = encode(quantum_value, 48)
        p3 = action.params.add()
        p3.param_id = param_map["reset_quota"]
        p3.value = encode(1 if reset_quota else 0, 1)

        try:
            sw.ModifyTableEntry(table_entry)
        except Exception as e:
            if "NOT_FOUND" in str(e).upper() or "UNKNOWN" in str(e).upper():
                sw.WriteTableEntry(table_entry)
            else:
                raise
        return True
    except Exception as e:
        print(f"  set_quantum failed: {e}", file=sys.stderr)
        return False


def read_state(state_file):
    """Read q_ef, q_af, latency_ms from state file. Returns (q_ef, q_af, latency_ms) or None."""
    try:
        if not os.path.exists(state_file):
            return None
        with open(state_file, "r") as f:
            line = f.read().strip()
        parts = line.split(",")
        if len(parts) < 3:
            return None
        q_ef = float(parts[0])
        q_af = float(parts[1])
        latency_ms = float(parts[2])
        return (q_ef, q_af, latency_ms)
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Q-learning WRR controller runtime")
    parser.add_argument("--grpc-port", type=int, default=50051, help="s1 gRPC port")
    parser.add_argument("--state-file", default=STATE_FILE, help="Telemetry state file")
    parser.add_argument("--interval", type=float, default=CONTROL_INTERVAL_SEC, help="Control interval (s)")
    parser.add_argument("--p4info", default=None, help="Path to qos.p4info.txt")
    parser.add_argument("--bmv2-json", default=None, help="Path to qos.json")
    parser.add_argument("--d-ub", type=float, default=50.0, help="Delay upper bound (ms)")
    parser.add_argument("--eps-ub", type=float, default=0.05, help="Violation probability")
    parser.add_argument("--lambda", dest="lambda_tradeoff", type=float, default=1.0, help="QoS vs weight tradeoff")
    parser.add_argument("--log-file", default=None, help="Log file for decisions (CSV). Default: logs/qlearning_decisions.csv")
    args = parser.parse_args()

    project_root = os.path.abspath(os.path.join(_script_dir, "..", ".."))
    p4info_path = args.p4info or os.path.join(_script_dir, "build", "qos.p4.p4info.txt")
    if not os.path.exists(p4info_path):
        p4info_path = os.path.join(_script_dir, "qos.json", "qos.p4info.txt")
    bmv2_path = args.bmv2_json or os.path.join(_script_dir, "build", "qos.json")
    if not os.path.exists(bmv2_path):
        bmv2_path = os.path.join(_script_dir, "qos.json", "qos.json")

    if not os.path.exists(p4info_path):
        print(f"P4Info not found: {p4info_path}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(bmv2_path):
        print(f"BMv2 JSON not found: {bmv2_path}", file=sys.stderr)
        sys.exit(1)

    logs_dir = os.path.join(_script_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    proto_dump = os.path.join(logs_dir, "qlearning-p4runtime.txt")
    log_file = args.log_file or os.path.join(logs_dir, "qlearning_decisions.csv")

    print("Connecting to switch...", flush=True)
    sw = bmv2.Bmv2SwitchConnection(
        name="s1",
        address=f"127.0.0.1:{args.grpc_port}",
        device_id=0,
        proto_dump_file=proto_dump,
    )
    p4info_helper = helper.P4InfoHelper(p4info_path)

    # Ensure pipeline is set (assume run_exercise already did; we only push table entries)
    try:
        sw.MasterArbitrationUpdate()
    except Exception as e:
        print(f"Arbitration failed (switch may not be ready): {e}", file=sys.stderr)

    controller = QLearningWRRController(
        alpha=0.2,
        gamma=0.9,
        epsilon=0.4,
        d_ub_ms=args.d_ub,
        eps_ub=args.eps_ub,
        lambda_tradeoff=args.lambda_tradeoff,
    )

    # Initial EF quantum
    ef_quantum = 6000
    controller.set_ef_quantum(ef_quantum)

    # Set initial quantums: AF=6000 (fixed), EF=6000
    print("Setting initial quantums: AF=6000, EF=6000", flush=True)
    set_quantum_via_p4runtime(sw, p4info_helper, QUEUE_AF, AF_QUANTUM_FIXED, reset_quota=True)
    set_quantum_via_p4runtime(sw, p4info_helper, QUEUE_EF, ef_quantum, reset_quota=True)

    print(f"Q-learning controller started. State file: {args.state_file}, interval: {args.interval}s", flush=True)
    print(f"Log file: {log_file}", flush=True)
    print("---", flush=True)

    # Write CSV header
    with open(log_file, "w") as f:
        f.write("timestamp,step,q_ef,q_af,latency_ms,action,EF,reward\n")

    step_count = 0
    while True:
        try:
            state = read_state(args.state_file)
            if state is None:
                time.sleep(args.interval)
                continue

            q_ef, q_af, latency_ms = state
            step_count += 1

            # Q-learning step: state uses q_ef (EF queue depth)
            new_ef, reward, action_name = controller.step(q_ef, latency_ms)

            # Push EF quantum only (AF stays fixed)
            ok = set_quantum_via_p4runtime(sw, p4info_helper, QUEUE_EF, new_ef, reset_quota=True)
            if ok:
                print(f"[{step_count}] q_ef={q_ef:.0f} lat={latency_ms:.1f}ms -> {action_name} -> EF={new_ef} r={reward:.3f}", flush=True)
                # Append to log file (CSV)
                with open(log_file, "a") as f:
                    f.write(f"{time.time():.3f},{step_count},{q_ef:.2f},{q_af:.2f},{latency_ms:.2f},{action_name},{new_ef},{reward:.4f}\n")
            else:
                print(f"[{step_count}] set_quantum failed", flush=True)

            # Decay epsilon periodically
            if step_count % 20 == 0:
                controller.decay_epsilon()

        except KeyboardInterrupt:
            print("\nStopped.", flush=True)
            break
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Test script: Test set_quantum() and get_quantum() methods using P4Runtime

Features:
1. Initialize and run P4 program
2. Read initial quantum values (via packets + register read)
3. Dynamically modify quantums via P4Runtime (set_quantum_table)
4. Send packets to trigger get_quantum(), then read updated values from register

Usage:
    sudo python3 test_quantum_p4runtime.py [--grpc-port 50051] [--device-id 0]

Note: sudo is required to send raw packets for triggering get_quantum().
"""

import sys
import os
import argparse
import time
import struct
import subprocess


def get_project_paths():
    """Get project-related paths (script is in utils/tools/)."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    utils_dir = os.path.dirname(script_dir)
    project_root = os.path.dirname(utils_dir)
    p4runtime_lib_path = os.path.abspath(os.path.join(utils_dir, 'p4runtime_lib'))
    logs_dir = os.path.join(project_root, "program", "qos", "logs")
    return {
        'script_dir': script_dir, 'utils_dir': utils_dir, 'project_root': project_root,
        'p4runtime_lib_path': p4runtime_lib_path, 'logs_dir': logs_dir,
    }


_paths = get_project_paths()
utils_dir = os.path.abspath(os.path.normpath(_paths['utils_dir']))
p4runtime_lib_path = os.path.abspath(os.path.normpath(_paths['p4runtime_lib_path']))
if utils_dir not in sys.path:
    sys.path.insert(0, utils_dir)
if p4runtime_lib_path not in sys.path:
    sys.path.insert(0, p4runtime_lib_path)

try:
    from p4runtime_lib import bmv2
    from p4runtime_lib import helper
    from p4runtime_lib.switch import ShutdownAllSwitchConnections
    from p4.v1 import p4runtime_pb2
    from p4runtime_lib.convert import encode
except ImportError as e:
    print(f"Error: Failed to import P4Runtime library: {e}")
    print(f"  utils_dir: {utils_dir}, p4runtime_lib_path: {p4runtime_lib_path}")
    sys.exit(1)


def connect_to_switch(grpc_port=50051, device_id=0):
    """Connect to BMv2 switch"""
    try:
        paths = get_project_paths()
        logs_dir = paths['logs_dir']
        os.makedirs(logs_dir, exist_ok=True)
        proto_dump_file = os.path.join(logs_dir, "p4runtime-requests.txt")
        sw = bmv2.Bmv2SwitchConnection(
            name='s1',
            address=f'127.0.0.1:{grpc_port}',
            device_id=device_id,
            proto_dump_file=proto_dump_file
        )
        print(f"✓ Successfully connected to switch (grpc_port={grpc_port}, device_id={device_id})")
        return sw
    except Exception as e:
        print(f"✗ Failed to connect to switch: {e}")
        print(f"  Please ensure the switch is running and listening on port {grpc_port}")
        sys.exit(1)


def setup_p4_program(sw, p4info_helper, bmv2_json_path):
    """Initialize P4 program"""
    try:
        print("\nInitializing P4 program...")
        # First, perform master arbitration to become the primary controller
        print("  Performing master arbitration...")
        sw.MasterArbitrationUpdate()
        print("  ✓ Master arbitration successful")

        # Then set the forwarding pipeline config
        print("  Setting forwarding pipeline config...")
        sw.SetForwardingPipelineConfig(
            p4info=p4info_helper.p4info,
            bmv2_json_file_path=bmv2_json_path
        )
        print("✓ P4 program initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize P4 program: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def read_register_via_cli(thrift_port=9090, register_name="quantum_storage", index=0):
    """Read register value using simple_switch_CLI."""
    try:
        cmd = ['simple_switch_CLI', '--thrift-port', str(thrift_port)]
        inp = f"register_read {register_name} {index}\n"
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, _ = p.communicate(input=inp)
        if p.returncode != 0:
            return None
        for line in out.split('\n'):
            if f"{register_name}[{index}]=" in line:
                s = line.split('= ', 1)[1].strip()
                try:
                    return int(s)
                except ValueError:
                    return None
        return None
    except Exception:
        return None


def read_register_via_thrift(thrift_port=9090, register_name="quantum_storage", index=0):
    """Read register value using Thrift API (P4Runtime doesn't support register reads)."""
    try:
        paths = get_project_paths()
        project_root = paths['project_root']
        bm_runtime_path = os.path.join(project_root, "behavioral-model", "tools")
        bm_runtime_path = os.path.abspath(bm_runtime_path)
        for p in (bm_runtime_path, os.path.join(bm_runtime_path, "bm_runtime")):
            if p not in sys.path:
                sys.path.insert(0, p)
        from bm_runtime.standard import Standard
        from thrift.transport import TTransport, TSocket
        from thrift.protocol import TBinaryProtocol, TMultiplexedProtocol

        transport = TTransport.TBufferedTransport(TSocket.TSocket('localhost', thrift_port))
        protocol = TMultiplexedProtocol.TMultiplexedProtocol(
            TBinaryProtocol.TBinaryProtocol(transport), "Standard")
        client = Standard.Client(protocol)
        transport.open()
        try:
            return client.bm_register_read(0, register_name, index)
        finally:
            transport.close()
    except Exception:
        return None


def read_register(sw, p4info_helper, register_name, index, thrift_port=9090, method="auto"):
    """Read register value. method: 'auto' (cli then thrift), 'cli', or 'thrift'. Returns (value, method_used)."""
    if method == "auto":
        v = read_register_via_cli(thrift_port, register_name, index)
        if v is not None:
            return v, "cli"
        v = read_register_via_thrift(thrift_port, register_name, index)
        return v, "thrift"
    if method == "cli":
        return read_register_via_cli(thrift_port, register_name, index), "cli"
    return read_register_via_thrift(thrift_port, register_name, index), "thrift"


def setup_get_quantum_table(sw, p4info_helper):
    """Setup get_quantum_table entries for all queues."""
    print("  Setting up get_quantum_table entries...")
    ok = 0
    for queue_idx in range(3):
        try:
            table = p4info_helper.get("tables", name="get_quantum_table")
            if not table.match_fields:
                raise Exception("get_quantum_table has no match fields")
            mf = table.match_fields[0]
            te = p4runtime_pb2.TableEntry()
            te.table_id = p4info_helper.get_tables_id("get_quantum_table")
            fm = p4runtime_pb2.FieldMatch()
            fm.field_id = mf.id
            fm.exact.value = encode(queue_idx, mf.bitwidth)
            te.match.extend([fm])
            ai = p4info_helper.get("actions", name="get_wrr_quantum")
            te.action.action.action_id = ai.preamble.id
            pm = {p.name: p.id for p in ai.params}
            ap = te.action.action.params.add()
            ap.param_id = pm["queue_idx"]
            ap.value = encode(queue_idx, 48)
            sw.WriteTableEntry(te)
            print(f"    ✓ get_quantum table entry for queue {queue_idx}")
            ok += 1
        except Exception as e:
            print(f"    ✗ get_quantum table queue {queue_idx}: {e}")
    return ok == 3


def find_interface():
    """Find interface for sending packets (e.g. s1-eth1 in Mininet)."""
    try:
        from scapy.all import get_if_list
        ifs = get_if_list()
        for pref in ["s1-eth1", "s1-eth0", "veth0", "eth0"]:
            for i in ifs:
                if pref in i:
                    return i
        for i in ifs:
            if "lo" not in i:
                return i
        return ifs[0] if ifs else None
    except Exception:
        return None


def send_packet_to_trigger_get_quantum(queue_idx, iface=None):
    """Send packet with srcAddr[15:0]=queue_idx to trigger get_quantum()."""
    try:
        from scapy.all import sendp, Ether, IP, TCP
        if os.geteuid() != 0:
            print("  ⚠ Need sudo to send raw packets. Run: sudo python3 test_quantum_p4runtime.py")
            return False
        if iface is None:
            iface = find_interface()
        if not iface:
            return False
        pkt = Ether() / IP(src=f"0.0.0.{queue_idx}", dst="10.0.0.1") / TCP()
        sendp(pkt, iface=iface, verbose=False)
        return True
    except Exception:
        return False


def get_table_match_field_name(p4info_helper, table_name):
    """Get the match field name for a table"""
    try:
        # Get table info
        table = p4info_helper.get("tables", name=table_name)
        if table.match_fields:
            # Return the first match field name
            field_name = table.match_fields[0].name
            print(f"  Debug: Found match field '{field_name}' for table '{table_name}'")
            return field_name
        print(f"  Warning: Table '{table_name}' has no match fields")
        return None
    except Exception as e:
        print(f"  Warning: Could not get match field name for {table_name}: {e}")
        # Try to list all tables for debugging
        try:
            print(f"  Available tables: {[t.preamble.name for t in p4info_helper.p4info.tables]}")
        except:
            pass
        return None


def list_table_match_fields(p4info_helper, table_name):
    """List all match fields for a table (for debugging)"""
    try:
        table = p4info_helper.get("tables", name=table_name)
        if table.match_fields:
            print(f"  Match fields for '{table_name}':")
            for mf in table.match_fields:
                print(f"    - {mf.name} (id: {mf.id}, bitwidth: {mf.bitwidth})")
            return [mf.name for mf in table.match_fields]
        return []
    except Exception as e:
        print(f"  Could not list match fields: {e}")
        return []


def set_quantum_via_table(sw, p4info_helper, queue_idx, quantum_value, reset_quota=True):
    """Set quantum value via P4 table"""
    try:
        # Get table and match field info directly
        table = p4info_helper.get("tables", name="set_quantum_table")
        if not table.match_fields:
            raise Exception("set_quantum_table has no match fields")

        # Get the first match field (we know it exists from debugging)
        match_field = table.match_fields[0]
        match_field_id = match_field.id
        match_field_bitwidth = match_field.bitwidth

        # Build table entry manually using field ID
        table_entry = p4runtime_pb2.TableEntry()
        table_entry.table_id = p4info_helper.get_tables_id("set_quantum_table")

        # Create match field using field ID directly
        field_match = p4runtime_pb2.FieldMatch()
        field_match.field_id = match_field_id
        field_match.exact.value = encode(queue_idx, match_field_bitwidth)
        table_entry.match.extend([field_match])

        # Set action - get action info directly
        action_info = p4info_helper.get("actions", name="set_wrr_quantum")
        action = table_entry.action.action
        action.action_id = action_info.preamble.id

        # Add action parameters - get param IDs directly from action info
        param_map = {p.name: p.id for p in action_info.params}

        action_param1 = action.params.add()
        action_param1.param_id = param_map["queue_idx"]
        action_param1.value = encode(queue_idx, 48)  # bit<48>

        action_param2 = action.params.add()
        action_param2.param_id = param_map["quantum_value"]
        action_param2.value = encode(quantum_value, 48)  # bit<48>

        action_param3 = action.params.add()
        action_param3.param_id = param_map["reset_quota"]
        action_param3.value = encode(1 if reset_quota else 0, 1)  # bit<1>

        sw.WriteTableEntry(table_entry)
        print(f"✓ Set quantum for queue {queue_idx} to {quantum_value} (reset_quota={reset_quota})")
        return True
    except Exception as e:
        print(f"✗ Failed to set quantum: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_quantum_operations(grpc_port=50051, device_id=0, p4info_path=None, bmv2_json_path=None,
                            thrift_port=9090, interface=None):
    """Test quantum operations: read initial -> set new -> send packets -> read updated."""

    paths = get_project_paths()
    project_root = paths['project_root']

    if p4info_path is None:
        p4info_path = os.path.join(project_root, "program", "qos", "qos.json", "qos.p4info.txt")
    if bmv2_json_path is None:
        bmv2_json_path = os.path.join(project_root, "program", "qos", "qos.json", "qos.json")
    if not os.path.isabs(p4info_path) and not os.path.exists(p4info_path):
        p4info_path = os.path.join(project_root, p4info_path)
    if not os.path.isabs(bmv2_json_path) and not os.path.exists(bmv2_json_path):
        bmv2_json_path = os.path.join(project_root, bmv2_json_path)

    if not os.path.exists(p4info_path):
        print(f"✗ P4Info file not found: {p4info_path}")
        sys.exit(1)
    if not os.path.exists(bmv2_json_path):
        print(f"✗ BMv2 JSON file not found: {bmv2_json_path}")
        sys.exit(1)

    print("=" * 70)
    print("WRR Quantum Test – set_quantum via P4Runtime, read updated via register")
    print("=" * 70)

    sw = connect_to_switch(grpc_port, device_id)

    try:
        p4info_helper = helper.P4InfoHelper(p4info_path)
        setup_p4_program(sw, p4info_helper, bmv2_json_path)

        # ----- Step 1: Read initial quantum values -----
        print("\n" + "-" * 70)
        print("Step 1: Read initial quantum values")
        print("-" * 70)

        setup_get_quantum_table(sw, p4info_helper)
        iface = interface or find_interface()
        initial_quantums = {0: None, 1: None, 2: None}

        if iface:
            print("  Sending packets to trigger get_quantum()...")
            for q in range(3):
                if send_packet_to_trigger_get_quantum(q, iface):
                    time.sleep(0.15)
            time.sleep(1.0)
        else:
            print("  ⚠ No interface for packets; register read may fail.")

        print("  Reading quantum_storage register (CLI then Thrift)...")
        for q in range(3):
            value, method = read_register(sw, p4info_helper, "quantum_storage", q, thrift_port=thrift_port)
            if value is not None and value != 0:
                initial_quantums[q] = value
                print(f"    Queue {q}: {value} (via {method})")
            else:
                initial_quantums[q] = None
                print(f"    Queue {q}: (read failed or 0)")

        # ----- Step 2: Modify quantums via P4Runtime (set_quantum_table) -----
        print("\n" + "-" * 70)
        print("Step 2: Modify quantums via P4Runtime (set_quantum_table)")
        print("-" * 70)

        new_quantums = {0: 50000, 1: 15000, 2: 3000}
        for q, v in new_quantums.items():
            set_quantum_via_table(sw, p4info_helper, q, v, reset_quota=True)
            time.sleep(0.1)

        # ----- Step 3: Send packets and read updated values -----
        print("\n" + "-" * 70)
        print("Step 3: Send packets → trigger set_quantum + get_quantum → read updated")
        print("-" * 70)

        # Same packets match both set_quantum_table and get_quantum_table (key = srcAddr[15:0]).
        # P4 applies set_quantum first, then get_quantum, so we set then read in one pass.
        if iface:
            print("  Sending packets (trigger set_quantum, then get_quantum → register)...")
            for q in range(3):
                if send_packet_to_trigger_get_quantum(q, iface):
                    time.sleep(0.15)
            time.sleep(1.0)
        else:
            print("  ⚠ No interface; cannot trigger set/get_quantum. Updated read may fail.")

        print("  Reading quantum_storage register (updated values)...")
        updated_quantums = {}
        for q in range(3):
            value, method = read_register(sw, p4info_helper, "quantum_storage", q, thrift_port=thrift_port)
            if value is not None:
                updated_quantums[q] = value
                print(f"    Queue {q}: {value} (via {method})")
            else:
                updated_quantums[q] = None
                print(f"    Queue {q}: (read failed)")

        print("\n" + "=" * 70)
        print("Summary")
        print("=" * 70)
        print(f"  Initial:  {initial_quantums}")
        print(f"  Set to:   {new_quantums}")
        print(f"  Updated:  {updated_quantums}")
        print("\n  Notes: set_quantum via P4Runtime; get_quantum triggered by packets; register read via CLI/Thrift.")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ShutdownAllSwitchConnections()
        print("\nConnection closed")


def main():
    parser = argparse.ArgumentParser(
        description='Test set_quantum() and get_quantum(): modify quantums via P4Runtime, read updated via register.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sudo python3 test_quantum_p4runtime.py
  sudo python3 test_quantum_p4runtime.py --grpc-port 50051 --device-id 0
  sudo python3 test_quantum_p4runtime.py --p4info ... --json ...
        """
    )
    parser.add_argument('--grpc-port', type=int, default=50051, help='gRPC port')
    parser.add_argument('--device-id', type=int, default=0, help='Device ID')
    parser.add_argument('--thrift-port', type=int, default=9090, help='Thrift port for register read')
    parser.add_argument('--p4info', type=str, default=None, help='P4Info file path')
    parser.add_argument('--json', type=str, default=None, help='BMv2 JSON file path')
    parser.add_argument('--interface', type=str, default=None, help='Interface for sending packets')
    args = parser.parse_args()

    test_quantum_operations(
        grpc_port=args.grpc_port,
        device_id=args.device_id,
        p4info_path=args.p4info,
        bmv2_json_path=args.json,
        thrift_port=args.thrift_port,
        interface=args.interface,
    )


if __name__ == '__main__':
    main()

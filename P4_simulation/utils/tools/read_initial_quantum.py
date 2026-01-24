#!/usr/bin/env python3
"""
Simplified script: Only read initial quantum values from WRR

This script:
1. Connects to switch and initializes P4 program
2. Sets up get_quantum_table entries
3. Sends packets to trigger get_quantum() for each queue
4. Reads quantum_storage register to get REAL initial values (not defaults)

Usage:
    sudo python3 read_initial_quantum.py [--grpc-port 50051] [--device-id 0]

Note: Root privileges (sudo) are required to send raw packets.
      If you cannot use sudo, you can manually send packets via Mininet.
"""

import sys
import os
import argparse
import time

# Helper function to get project paths
def get_project_paths():
    """Get project-related paths based on script location

    Returns:
        dict: Dictionary with keys:
            - script_dir: Directory where this script is located (utils/tools/)
            - utils_dir: utils/ directory
            - project_root: P4_simulation/ root directory
            - p4runtime_lib_path: Path to p4runtime_lib/
            - logs_dir: Path to logs directory
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))  # utils/tools/
    utils_dir = os.path.dirname(script_dir)  # utils/
    project_root = os.path.dirname(utils_dir)  # P4_simulation/
    p4runtime_lib_path = os.path.abspath(os.path.join(utils_dir, 'p4runtime_lib'))
    logs_dir = os.path.join(project_root, "program", "qos", "logs")

    return {
        'script_dir': script_dir,
        'utils_dir': utils_dir,
        'project_root': project_root,
        'p4runtime_lib_path': p4runtime_lib_path,
        'logs_dir': logs_dir
    }

# Initialize paths
_paths = get_project_paths()

# Add P4Runtime library path
# Script is in utils/tools/, p4runtime_lib is in utils/p4runtime_lib/
# IMPORTANT: We need to add utils/ to sys.path for "from p4runtime_lib import ..."
# AND also add p4runtime_lib/ to sys.path for internal relative imports like "from switch import ..."
utils_dir = _paths['utils_dir']
utils_dir = os.path.abspath(os.path.normpath(utils_dir))
p4runtime_lib_path = _paths['p4runtime_lib_path']
p4runtime_lib_path = os.path.abspath(os.path.normpath(p4runtime_lib_path))

# Add utils/ for package imports
if utils_dir not in sys.path:
    sys.path.insert(0, utils_dir)
# Add p4runtime_lib/ for internal relative imports (like "from switch import ...")
if p4runtime_lib_path not in sys.path:
    sys.path.insert(0, p4runtime_lib_path)

# Debug: Print path information if import fails
try:
    from p4runtime_lib.convert import encode
except ImportError as e:
    print(f"Debug: Failed to import from p4runtime_lib.convert: {e}")
    print(f"Debug: utils_dir = {utils_dir}")
    print(f"Debug: p4runtime_lib_path = {p4runtime_lib_path}")
    print(f"Debug: Paths exist: utils={os.path.exists(utils_dir)}, p4runtime_lib={os.path.exists(p4runtime_lib_path)}")
    print(f"Debug: sys.path includes: {[p for p in sys.path if 'utils' in p or 'p4runtime' in p]}")
    # Fallback encode function if import fails
    def encode(x, bitwidth):
        """Encode integer to bytes for P4Runtime"""
        return x.to_bytes((bitwidth + 7) // 8, byteorder='big')

try:
    from p4runtime_lib import bmv2
    from p4runtime_lib import helper
    from p4runtime_lib.switch import ShutdownAllSwitchConnections
    from p4.v1 import p4runtime_pb2
    # Re-import encode if it wasn't imported earlier
    try:
        from p4runtime_lib.convert import encode
    except ImportError:
        pass  # Use fallback if needed
except ImportError as e:
    print(f"Error: Failed to import P4Runtime library: {e}")
    print(f"  Attempted utils directory: {utils_dir}")
    print(f"  Path exists: {os.path.exists(utils_dir)}")
    print(f"  p4runtime_lib path: {_paths['p4runtime_lib_path']}")
    print(f"  p4runtime_lib exists: {os.path.exists(_paths['p4runtime_lib_path'])}")
    print(f"  Current working directory: {os.getcwd()}")
    print(f"  Script location: {_paths['script_dir']}")
    print(f"  sys.path includes: {[p for p in sys.path if 'utils' in p or 'p4runtime' in p]}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Define helper functions directly (to avoid import issues)
def connect_to_switch(grpc_port=50051, device_id=0):
    """Connect to BMv2 switch"""
    try:
        # Create logs directory if it doesn't exist
        # Logs should be in project_root/program/qos/logs/ (where the switch runs)
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


def find_interface():
    """Find available network interface for sending packets"""
    try:
        from scapy.all import get_if_list
        interfaces = get_if_list()

        print(f"  Available interfaces: {interfaces}")

        # Try common interface names (prioritize Mininet interfaces)
        preferred = ["s1-eth0", "s1-eth1", "veth0", "veth1", "eth0", "eth1"]
        for pref in preferred:
            for iface in interfaces:
                if pref in iface:
                    print(f"  Selected interface: {iface} (matched '{pref}')")
                    return iface

        # Return first non-loopback interface
        for iface in interfaces:
            if "lo" not in iface:
                print(f"  Selected interface: {iface} (first non-loopback)")
                return iface

        # Fallback to first interface
        if interfaces:
            print(f"  Selected interface: {interfaces[0]} (fallback)")
            return interfaces[0]
        else:
            print(f"  ⚠ No interfaces found!")
            return None
    except Exception as e:
        print(f"  ⚠ Error finding interface: {e}")
        return None


def send_packet_to_trigger_get_quantum(queue_idx, iface=None):
    """Send a test packet to trigger get_quantum() for a specific queue"""
    try:
        from scapy.all import sendp, Ether, IP, TCP
        import os

        # Check if running as root (required for raw sockets)
        if os.geteuid() != 0:
            print(f"  ⚠ Note: Not running as root. Raw socket operations require root privileges.")
            print(f"    Please run with: sudo python3 read_initial_quantum.py")
            print(f"    Or manually send packets using Mininet or another method.")
            return False

        # Auto-detect interface if not provided
        if iface is None:
            iface = find_interface()
            if iface is None:
                print(f"  ✗ Could not find network interface")
                return False

        # Create packet with srcAddr[15:0] = queue_idx
        src_ip = f"0.0.0.{queue_idx}"
        dst_ip = "10.0.0.1"

        pkt = Ether() / IP(src=src_ip, dst=dst_ip) / TCP()
        sendp(pkt, iface=iface, verbose=False)
        print(f"    ✓ Sent packet for queue {queue_idx} (src={src_ip})")
        return True
    except ImportError:
        print(f"  ✗ scapy not available, cannot send packet for queue {queue_idx}")
        print(f"    Install scapy: pip install scapy")
        return False
    except PermissionError:
        print(f"  ✗ Permission denied: Raw socket operations require root privileges")
        print(f"    Please run with: sudo python3 read_initial_quantum.py")
        return False
    except Exception as e:
        print(f"  ✗ Failed to send packet for queue {queue_idx}: {e}")
        if "Operation not permitted" in str(e) or "Permission denied" in str(e):
            print(f"    Hint: Run with sudo: sudo python3 read_initial_quantum.py")
        return False


def setup_get_quantum_table(sw, p4info_helper):
    """Setup get_quantum_table entries for all queues"""
    print("  Setting up get_quantum_table entries...")
    success_count = 0

    for queue_idx in range(3):
        try:
            # Get table and match field info directly
            table = p4info_helper.get("tables", name="get_quantum_table")
            if not table.match_fields:
                raise Exception("get_quantum_table has no match fields")

            # Get the first match field
            match_field = table.match_fields[0]
            match_field_id = match_field.id
            match_field_bitwidth = match_field.bitwidth

            # Build table entry manually using field ID
            table_entry = p4runtime_pb2.TableEntry()
            table_entry.table_id = p4info_helper.get_tables_id("get_quantum_table")

            # Create match field using field ID directly
            # Note: hdr.ipv4.srcAddr[15:0] is 16 bits, so we match the lower 16 bits of IP address
            # IP 0.0.0.0 has lower 16 bits = 0, 0.0.0.1 has lower 16 bits = 1, etc.
            field_match = p4runtime_pb2.FieldMatch()
            field_match.field_id = match_field_id
            field_match.exact.value = encode(queue_idx, match_field_bitwidth)
            table_entry.match.extend([field_match])

            # Debug: Print match value
            match_value_hex = field_match.exact.value.hex()
            print(f"    Setting match field (bitwidth={match_field_bitwidth}): queue_idx={queue_idx}, encoded={match_value_hex}")

            # Set action - get action info directly
            action_info = p4info_helper.get("actions", name="get_wrr_quantum")
            action = table_entry.action.action
            action.action_id = action_info.preamble.id

            # Add action parameter - get param ID directly from action info
            param_map = {p.name: p.id for p in action_info.params}
            action_param = action.params.add()
            action_param.param_id = param_map["queue_idx"]
            action_param.value = encode(queue_idx, 48)  # bit<48>

            sw.WriteTableEntry(table_entry)
            print(f"    ✓ Set get_quantum table entry for queue {queue_idx} (match: srcAddr[15:0]={queue_idx})")
            success_count += 1
        except Exception as e:
            print(f"    ✗ Failed to set get_quantum table entry for queue {queue_idx}: {e}")

    return success_count == 3


def read_register_via_cli(thrift_port=9090, register_name="quantum_storage", index=0):
    """Read register value using simple_switch_CLI"""
    try:
        import subprocess

        cmd = ['simple_switch_CLI', '--thrift-port', str(thrift_port)]
        input_cmd = f"register_read {register_name} {index}\n"

        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=input_cmd)

        if process.returncode != 0:
            return None

        # Parse output
        for line in stdout.split('\n'):
            if f"{register_name}[{index}]=" in line:
                value_str = line.split('= ', 1)[1].strip()
                try:
                    return int(value_str)
                except ValueError:
                    return None

        return None
    except Exception as e:
        return None


def read_register_via_thrift(thrift_port=9090, register_name="quantum_storage", index=0):
    """Read register value using Thrift API"""
    try:
        # Add BMv2 Thrift API to path
        paths = get_project_paths()
        project_root = paths['project_root']
        bm_runtime_path = os.path.join(project_root, "behavioral-model", "tools")
        if bm_runtime_path not in sys.path:
            sys.path.insert(0, bm_runtime_path)
        sys.path.insert(0, os.path.join(bm_runtime_path, "bm_runtime"))

        from bm_runtime.standard import Standard
        from thrift.transport import TTransport
        from thrift.transport import TSocket
        from thrift.protocol import TBinaryProtocol
        from thrift.protocol import TMultiplexedProtocol

        # Connect to switch via Thrift with multiplexed protocol
        transport = TSocket.TSocket('localhost', thrift_port)
        transport = TTransport.TBufferedTransport(transport)
        protocol = TMultiplexedProtocol.TMultiplexedProtocol(
            TBinaryProtocol.TBinaryProtocol(transport), "Standard")
        client = Standard.Client(protocol)

        transport.open()
        try:
            value = client.bm_register_read(0, register_name, index)
            return value
        finally:
            transport.close()
    except Exception as e:
        return None


def read_register(sw, p4info_helper, register_name, index, thrift_port=9090, method="auto"):
    """Read register value using available methods

    Returns:
        tuple: (value, actual_method_used) where actual_method_used is "cli" or "thrift"
        If value is None, actual_method_used indicates which method was attempted last
    """
    if method == "auto":
        # Try CLI first (most reliable)
        value = read_register_via_cli(thrift_port, register_name, index)
        if value is not None:
            return value, "cli"
        # Fall back to Thrift
        value = read_register_via_thrift(thrift_port, register_name, index)
        return value, "thrift" if value is not None else (None, "thrift")
    elif method == "cli":
        value = read_register_via_cli(thrift_port, register_name, index)
        return value, "cli"
    elif method == "thrift":
        value = read_register_via_thrift(thrift_port, register_name, index)
        return value, "thrift"
    else:
        raise ValueError(f"Unknown method: {method}")


def printRegister(p4info_helper, sw, register_name, index, thrift_port=9090, method="auto", show_method=True):
    """Print register value - similar to printCounter

    Args:
        show_method: If True, display which method was used (cli or thrift)
    """
    try:
        value, actual_method = read_register(sw, p4info_helper, register_name, index, thrift_port, method)
        if value is not None:
            if show_method:
                print(f"  {register_name}[{index}] = {value} (via {actual_method})")
            else:
                print(f"  {register_name}[{index}] = {value}")
            return value, actual_method
        else:
            if show_method:
                print(f"  {register_name}[{index}] = (read failed via {actual_method})")
            else:
                print(f"  {register_name}[{index}] = (read failed)")
            return None, actual_method
    except Exception as e:
        print(f"  Error reading {register_name}[{index}]: {e}")
        return None, None


def read_initial_quantum_values(grpc_port=50051, device_id=0,
                                p4info_path=None, bmv2_json_path=None,
                                thrift_port=9090, interface=None):
    """Read initial quantum values from WRR (real values, not defaults)"""

    # Get project paths
    paths = get_project_paths()
    project_root = paths['project_root']

    if p4info_path is None:
        p4info_path = os.path.join(project_root, "program", "qos", "qos.json", "qos.p4info.txt")
    if bmv2_json_path is None:
        bmv2_json_path = os.path.join(project_root, "program", "qos", "qos.json", "qos.json")

    # Convert to absolute paths if needed
    if not os.path.isabs(p4info_path):
        p4info_path = os.path.join(project_root, p4info_path) if not os.path.exists(p4info_path) else p4info_path
    if not os.path.isabs(bmv2_json_path):
        bmv2_json_path = os.path.join(project_root, bmv2_json_path) if not os.path.exists(bmv2_json_path) else bmv2_json_path

    # Check if files exist
    if not os.path.exists(p4info_path):
        print(f"✗ P4Info file not found: {p4info_path}")
        print(f"  Expected path: {p4info_path}")
        print(f"  Current working directory: {os.getcwd()}")
        print(f"  Script location: {os.path.dirname(os.path.abspath(__file__))}")
        print(f"  Project root: {project_root}")
        sys.exit(1)

    if not os.path.exists(bmv2_json_path):
        print(f"✗ BMv2 JSON file not found: {bmv2_json_path}")
        print(f"  Expected path: {bmv2_json_path}")
        print(f"  Current working directory: {os.getcwd()}")
        sys.exit(1)

    print("=" * 70)
    print("Read Initial Quantum Values from WRR")
    print("=" * 70)
    print("\nThis script will:")
    print("  1. Connect to switch and initialize P4 program")
    print("  2. Set up get_quantum_table entries")
    print("  3. Send packets to trigger get_quantum() for each queue")
    print("  4. Read quantum_storage register to get REAL initial values")
    print("\nNote: This reads actual values from WRR, not default values from WRR.cpp")
    print("=" * 70)

    # Connect to switch
    sw = connect_to_switch(grpc_port, device_id)

    try:
        # Load P4Info
        p4info_helper = helper.P4InfoHelper(p4info_path)

        # Initialize P4 program
        setup_p4_program(sw, p4info_helper, bmv2_json_path)

        print("\n" + "-" * 70)
        print("Step 1: Set up get_quantum_table entries")
        print("-" * 70)

        if not setup_get_quantum_table(sw, p4info_helper):
            print("  ⚠ Warning: Some get_quantum_table entries failed to set")
            print("  Continuing anyway...")

        print("\n" + "-" * 70)
        print("Step 2: Send packets to trigger get_quantum()")
        print("-" * 70)
        print("  Note: Packets will match get_quantum_table and trigger get_wrr_quantum action")
        print("  This will call my_hier.get_quantum() and store the value in quantum_storage register")
        print()
        print("  ⚠ IMPORTANT: Sending raw packets requires root privileges!")
        print("     If you see 'Operation not permitted' errors, run:")
        print("       sudo python3 read_initial_quantum.py")
        print()

        # Check if scapy is available
        try:
            from scapy.all import sendp, Ether, IP, TCP
            scapy_available = True
        except ImportError:
            scapy_available = False
            print("\n  ⚠ Warning: scapy not available. Cannot send packets.")
            print("    Install with: pip install scapy")
            print("    Without packets, register values will be 0.")
            print("    You can manually send packets or use simple_switch_CLI after running this script.")

        packets_sent = 0
        if scapy_available:
            # Use provided interface or auto-detect
            iface = interface if interface else find_interface()
            if iface:
                print(f"  Using interface: {iface}")
            else:
                print(f"  ⚠ Could not auto-detect interface")
                print(f"    You can specify interface with: --interface <iface_name>")
                print(f"    Or send packets manually via Mininet")

            print(f"  Note: If packets don't reach the switch, you may need to:")
            print(f"    1. Check if the switch is running and listening on the correct interface")
            print(f"    2. If using Mininet, send packets from Mininet host instead")
            print(f"    3. Verify interface name matches your setup")
            print()

            if iface:
                for queue_idx in range(3):
                    if send_packet_to_trigger_get_quantum(queue_idx, iface=iface):
                        packets_sent += 1
                        time.sleep(0.2)  # Brief delay between packets
                    else:
                        print(f"    ✗ Failed to send packet for queue {queue_idx}")

            if packets_sent > 0:
                print(f"\n  ✓ Sent {packets_sent} packets successfully")
                print("  Waiting 1.5 seconds for packets to be processed...")
                time.sleep(1.5)  # Give more time for processing
            else:
                print("\n  ⚠ Warning: No packets were sent.")
                print("    Register values will be 0. Please send packets manually.")
                print("    Possible reasons:")
                print("      1. Interface not found or incorrect")
                print("      2. Permission denied (need sudo)")
                print("      3. Switch not running or interface not connected")
                print("    Alternative: Send packets via Mininet if available")
        else:
            print("\n  ⚠ Skipping packet sending (scapy not available)")

        print("\n" + "-" * 70)
        print("Step 3: Read initial quantum values from register")
        print("-" * 70)
        print("  Note: P4Runtime cannot read registers. Using Thrift API or CLI.")
        print("  These are REAL values from WRR, not default values from WRR.cpp")

        initial_quantums = {}
        all_success = True

        for queue_idx in range(3):
            # Try to read from register
            value, actual_method = printRegister(p4info_helper, sw, "quantum_storage", queue_idx,
                                                 thrift_port=thrift_port, method="auto", show_method=True)

            if value is not None and value != 0:
                initial_quantums[queue_idx] = value
                print(f"    ✓ Successfully read initial quantum for queue {queue_idx}: {value} (method: {actual_method})")
            else:
                all_success = False
                if value is None:
                    print(f"    ✗ Failed to read register for queue {queue_idx} (method attempted: {actual_method})")
                    print(f"      Possible reasons:")
                    print(f"        - get_quantum() hasn't been triggered by packet")
                    if actual_method == "cli":
                        print(f"        - simple_switch_CLI not available or failed")
                    elif actual_method == "thrift":
                        print(f"        - Thrift API connection failed")
                else:
                    print(f"    ⚠ Register value is 0 for queue {queue_idx} (method: {actual_method})")
                    print(f"      This means get_quantum() hasn't been triggered yet")
                    print(f"      Please send a packet with srcAddr[15:0] = {queue_idx} to trigger it")
                initial_quantums[queue_idx] = None

        print("\n" + "=" * 70)
        print("Results")
        print("=" * 70)

        if all_success:
            print("\n✓ Successfully read all initial quantum values:")
            for queue_idx in range(3):
                print(f"  Queue {queue_idx}: {initial_quantums[queue_idx]}")
        else:
            print("\n⚠ Some values could not be read:")
            for queue_idx in range(3):
                if initial_quantums[queue_idx] is not None:
                    print(f"  Queue {queue_idx}: {initial_quantums[queue_idx]} ✓")
                else:
                    print(f"  Queue {queue_idx}: (read failed) ✗")

        print("\n" + "-" * 70)
        print("Next Steps")
        print("-" * 70)
        print()
        print("If packets failed to send (Operation not permitted):")
        print("  Run the script with sudo:")
        print("    sudo python3 read_initial_quantum.py")
        print()
        print("To verify values using simple_switch_CLI:")
        print("  1. Open another terminal")
        print("  2. Run: simple_switch_CLI --thrift-port 9090")
        print("  3. Run: register_read quantum_storage <queue_idx>")
        print("  4. Press Ctrl+D to exit")
        print()
        print("Alternative: Send packets manually via Mininet:")
        print("  If you're using Mininet, you can send packets from host h1:")
        print("    mininet> h1 python3 -c \"from scapy.all import *; sendp(Ether()/IP(src='0.0.0.0',dst='10.0.0.1')/TCP(), iface='h1-eth0')\"")
        print("    mininet> h1 python3 -c \"from scapy.all import *; sendp(Ether()/IP(src='0.0.0.1',dst='10.0.0.1')/TCP(), iface='h1-eth0')\"")
        print("    mininet> h1 python3 -c \"from scapy.all import *; sendp(Ether()/IP(src='0.0.0.2',dst='10.0.0.1')/TCP(), iface='h1-eth0')\"")
        print()
        print("If register values are 0, you need to:")
        print("  1. Ensure packets were sent successfully (check script output above)")
        print("  2. Or manually send packets to trigger get_quantum() (see methods above)")
        print("  3. Then read register again")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ShutdownAllSwitchConnections()
        print("\nConnection closed")


def main():
    parser = argparse.ArgumentParser(
        description='Read initial quantum values from WRR (real values, not defaults)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default port and device_id (requires sudo for packet sending)
  sudo python3 read_initial_quantum.py

  # Specify grpc port and device_id
  sudo python3 read_initial_quantum.py --grpc-port 50051 --device-id 0

  # Specify P4Info and JSON file paths
  sudo python3 read_initial_quantum.py \\
      --p4info P4_simulation/program/qos/qos.json/qos.p4info.txt \\
      --json P4_simulation/program/qos/qos.json/qos.json

Note: Root privileges (sudo) are required to send raw packets.
      If you cannot use sudo, you can manually send packets via Mininet.
        """
    )

    parser.add_argument('--grpc-port', type=int, default=50051,
                       help='gRPC port (default: 50051)')
    parser.add_argument('--device-id', type=int, default=0,
                       help='Device ID (default: 0)')
    parser.add_argument('--thrift-port', type=int, default=9090,
                       help='Thrift port (default: 9090)')
    parser.add_argument('--p4info', type=str, default=None,
                       help='P4Info file path')
    parser.add_argument('--json', type=str, default=None,
                       help='BMv2 JSON file path')
    parser.add_argument('--interface', type=str, default=None,
                       help='Network interface to send packets (auto-detect if not specified)')

    args = parser.parse_args()

    read_initial_quantum_values(
        grpc_port=args.grpc_port,
        device_id=args.device_id,
        p4info_path=args.p4info,
        bmv2_json_path=args.json,
        thrift_port=args.thrift_port,
        interface=args.interface
    )


if __name__ == '__main__':
    main()

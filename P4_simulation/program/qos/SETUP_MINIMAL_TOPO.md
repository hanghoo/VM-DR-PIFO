# Setup Guide for Minimal Single-Switch Topology

This guide walks you through setting up and running the minimal topology for single-switch scheduler evaluation.

## Overview

The minimal topology consists of:
- **1 Switch (s1)**: BMv2 switch with DR-PIFO scheduler
- **8 Source Hosts (h1-h8)**: Generate traffic flows
- **1 Receiver Host (h_receiver)**: Monitors output on port 9

All traffic from h1-h8 is routed to h_receiver on port 9 for monitoring.

---

## Step 1: Update Runtime JSON Configuration

Create/update `s1-runtime.json` to route all traffic to port 9:

```json
{
  "target": "bmv2",
  "p4info": "build/qos.p4.p4info.txt",
  "bmv2_json": "build/qos.json",
  "table_entries": [
    {
      "table": "MyIngress.ipv4_lpm",
      "match": {
        "hdr.ipv4.dstAddr": ["10.0.2.1", 32]
      },
      "action_name": "MyIngress.ipv4_forward",
      "action_params": {
        "dstAddr": "08:00:00:00:02:01",
        "port": 9
      }
    },
    {
      "table": "MyIngress.lookup_flow_id",
      "match": {
        "hdr.ipv4.srcAddr": ["10.0.1.1", 32]
      },
      "action_name": "MyIngress.assign_flow_id",
      "action_params": {
        "flow_id": 1
      }
    },
    {
      "table": "MyIngress.lookup_flow_id",
      "match": {
        "hdr.ipv4.srcAddr": ["10.0.1.2", 32]
      },
      "action_name": "MyIngress.assign_flow_id",
      "action_params": {
        "flow_id": 2
      }
    },
    {
      "table": "MyIngress.lookup_flow_id",
      "match": {
        "hdr.ipv4.srcAddr": ["10.0.1.3", 32]
      },
      "action_name": "MyIngress.assign_flow_id",
      "action_params": {
        "flow_id": 3
      }
    },
    {
      "table": "MyIngress.lookup_flow_id",
      "match": {
        "hdr.ipv4.srcAddr": ["10.0.1.4", 32]
      },
      "action_name": "MyIngress.assign_flow_id",
      "action_params": {
        "flow_id": 4
      }
    },
    {
      "table": "MyIngress.lookup_flow_id",
      "match": {
        "hdr.ipv4.srcAddr": ["10.0.1.5", 32]
      },
      "action_name": "MyIngress.assign_flow_id",
      "action_params": {
        "flow_id": 5
      }
    },
    {
      "table": "MyIngress.lookup_flow_id",
      "match": {
        "hdr.ipv4.srcAddr": ["10.0.1.6", 32]
      },
      "action_name": "MyIngress.assign_flow_id",
      "action_params": {
        "flow_id": 6
      }
    },
    {
      "table": "MyIngress.lookup_flow_id",
      "match": {
        "hdr.ipv4.srcAddr": ["10.0.1.7", 32]
      },
      "action_name": "MyIngress.assign_flow_id",
      "action_params": {
        "flow_id": 7
      }
    },
    {
      "table": "MyIngress.lookup_flow_id",
      "match": {
        "hdr.ipv4.srcAddr": ["10.0.1.8", 32]
      },
      "action_name": "MyIngress.assign_flow_id",
      "action_params": {
        "flow_id": 8
      }
    }
  ]
}
```

**Key Points:**
- All traffic routes to `10.0.2.1` (h_receiver) on port 9
- Flow IDs 1-8 assigned to h1-h8 respectively
- Each host sends to destination `10.0.2.1`

---

## Step 2: Compile P4 Program

Ensure your P4 program is compiled:

```bash
cd P4_simulation/program/qos
make build
```

This compiles `qos.p4` (or your chosen P4 program) to `build/qos.json`.

---

## Step 3: Prepare Workload Files

For each host (h1-h8), create workload files in the `workload/` directory:

- `workload/flow_1.txt` - Rank values for flow 1 (from h1)
- `workload/flow_2.txt` - Rank values for flow 2 (from h2)
- ... and so on for flows 3-8

Each file should contain rank values (one per line) that will be embedded in packet IP options.

**Example `workload/flow_1.txt`:**
```
100
200
150
300
...
```

---

## Step 4: Run the Topology

Start the minimal topology:

```bash
cd P4_simulation/program/qos
make run TOPO=topology_minimal.json
```

Or explicitly:
```bash
sudo PYTHONPATH=/home/vagrant/P4_simulation/utils:/home/vagrant/P4_simulation/utils/p4runtime_lib:${PYTHONPATH} \
python3 ../../utils/run_exercise.py -t topology_minimal.json -j build/qos.json
```

This will:
1. Start Mininet with the minimal topology
2. Configure the switch with routing rules
3. Set up host networking
4. Open Mininet CLI

---

## Step 5: Generate and Send Traffic

### Option A: Using send.py script

In separate terminals (or background processes), run send.py on each source host:

```bash
# Terminal 1 - h1 sends to h_receiver
mininet> h1 python3 send.py --h workload/flow_1.txt --des 10.0.2.1

# Terminal 2 - h2 sends to h_receiver
mininet> h2 python3 send.py --h workload/flow_2.txt --des 10.0.2.1

# ... repeat for h3-h8
```

### Option B: Batch-based testing (as per testbed description)

Create a batch generator script that:
1. Reads workload files
2. Generates batches of packets
3. Sends packets sequentially from each flow
4. Waits for scheduler to dequeue before sending next batch

---

## Step 6: Monitor Output

### Monitor on receiver host:

```bash
mininet> h_receiver python3 receive.py
```

Or capture packets:
```bash
mininet> h_receiver tcpdump -i h_receiver-eth0 -w output.pcap
```

### Monitor switch logs:

Check scheduler behavior in:
- `logs/s1.log` - Switch log file
- `logs/s1-p4runtime-requests.txt` - P4Runtime requests

### Capture packets on switch:

PCAP files are automatically saved to `pcaps/` directory if pcap_dump is enabled.

---

## Step 7: Evaluate Results

### Metrics to Collect:

1. **Bandwidth Utilization (BU)**:
   - Compare actual bandwidth assigned to each flow vs. ideal bandwidth
   - Calculate: `BU = actual_bandwidth / ideal_bandwidth`
   - Ideal BU = 1.0

2. **Flow Completion Time (FCT)**:
   - Measure time for each flow to complete
   - Compare with reference model (pFabric/VDS)

3. **Packet Dequeue Sequence**:
   - Monitor order of packets dequeued from scheduler
   - Compare with expected order from reference model

### Analysis Script:

Create a testing script (MATLAB or Python) that:
1. Reads output packet sequence from h_receiver
2. Compares with reference model output
3. Calculates BU and FCT metrics
4. Generates comparison reports

---

## Step 8: Testing Different Schedulers

To test different schedulers, update the P4 program:

1. **DR-PIFO**: Use `DR_PIFO.p4` or `qos.p4` (if it uses DR-PIFO)
2. **PIFO**: Use `pifo.p4`
3. **PIEO**: Use `pieo.p4`
4. **pFabric**: Use `pFabric.p4`
5. **VDS**: Use `P13_VDS.p4`

Recompile and run:
```bash
make clean
# Copy desired P4 program to qos.p4 or update Makefile
make build
make run TOPO=topology_minimal.json
```

---

## Troubleshooting

### Issue: Packets not reaching receiver
- **Check**: Routing table entries in s1-runtime.json
- **Verify**: All hosts send to destination 10.0.2.1
- **Test**: `mininet> pingall`

### Issue: Scheduler not working
- **Check**: P4 program compiles without errors
- **Verify**: Extern library is loaded (DR_PIFO.so)
- **Check logs**: `logs/s1.log` for scheduler errors

### Issue: Flow IDs not assigned
- **Check**: `lookup_flow_id` table entries in s1-runtime.json
- **Verify**: Source IP addresses match topology

---

## Next Steps

1. **Create batch generator**: Implement MATLAB/Python script for batch-based testing
2. **Implement reference model**: Create pFabric/VDS reference scheduler
3. **Build testing code**: Develop BU and FCT evaluation scripts
4. **Run experiments**: Execute test cases with different workloads
5. **Analyze results**: Compare scheduler performance against reference models

---

## References

- Testbed description from: "2025 TN-Enabling Rank-Based P4 Programmable Schedulers"
- Single-switch evaluation methodology from: "2025 TNSM-Reinforcement Learning-Based In-Network Load Balancing"









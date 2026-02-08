from time import sleep

# High-speed mode: use send_enhanced.py --fast (pre-build + sendpfast). No per-packet timestamps (not for latency analysis).
# Requires tcpreplay on each host (apt-get install tcpreplay). If receivers get no "P4 is cool" packets, set FAST_MODE = False.
FAST_MODE = True
FAST_MODE_PPS = 100   # packets per second per flow when FAST_MODE is True
# Normal mode: Python+Scapy per-packet loop can only reach ~18–25 pps regardless of --rate/--pps target. Set target to match.
NORMAL_MODE_PPS = 25  # target pps per flow in normal mode (for latency analysis; actual will be ~18–25)


def sending_function(self):
    # add by hang
    for host in self.net.hosts:
        host.cmd('mkdir -p outputs')

    """Minimal topology: 3 source hosts (h1-h3) sending to 3 receivers (h_r1-h_r3)

    Enhanced version using send_enhanced.py to automatically generate traffic
    with fixed rank and create congestion scenarios for WRR testing.
    """
    h1, h2, h3, h_r1, h_r2, h_r3 = self.net.get(
        'h1', 'h2', 'h3', 'h_r1', 'h_r2', 'h_r3'
    )

    # Start receivers on all receiver hosts
    h_r1.cmd('./receive.py > ./outputs/receiver_h_r1.txt &')
    sleep(0.05)  # Reduced from 0.1 for faster startup
    h_r2.cmd('./receive.py > ./outputs/receiver_h_r2.txt &')
    sleep(0.05)
    h_r3.cmd('./receive.py > ./outputs/receiver_h_r3.txt &')
    sleep(0.5)  # Reduced from 1.0, but still allow receivers to initialize

    # Send traffic: h1->h_r1, h2->h_r2, h3->h_r3
    # Each sender sends to its corresponding receiver
    # Using send_enhanced.py to automatically generate traffic with fixed rank
    # Configuration for congestion scenario (based on scheduler rate ~100 pps with sleep=10ms):
    #   - High send rate (--rate 0.005 = ~200 packets/sec per flow)
    #   - Total send rate: ~600 packets/sec (6x scheduler rate) - ensures strong congestion
    #   - Fixed rank (--rank-value 2000)
    #   - Duration-based sending (--duration 60) to create sustained congestion
    #   - Large packet count (--num-packets 100000) to ensure enough packets
    # Note: Lower rate value = higher send rate = more packets per second
    # When send rate > scheduler rate, queues will build up and WRR weight differences become visible
    # Note: Python time.sleep() has overhead, so actual rate may be lower than theoretical

    # Build send args: normal mode (rate-based, per-packet log) or fast mode (sendpfast, minimal log)
    if FAST_MODE:
        rate_arg = f'--pps={FAST_MODE_PPS} --fast --log-every=100'
        # Fast mode: writes theoretical timestamps after send (no impact on pps) for latency analysis
    else:
        rate_arg = f'--pps={NORMAL_MODE_PPS} --log-every=10'
        # Normal mode: per-packet timestamps for latency analysis; Python loop ceiling ~18–25 pps (use FAST_MODE for high pps)

    # Flow 0 (h1 -> h_r1): high weight flow (quantum=20000)
    h1.cmd('./send_enhanced.py --des=10.0.2.1 --num-packets=100000 '
           f'--rank-value=2000 {rate_arg} --duration=30 --flow-id=0 '
           '> ./outputs/sender_h1.txt &')
    sleep(0.01)
    # Flow 1 (h2 -> h_r2): medium weight flow (quantum=10000)
    h2.cmd('./send_enhanced.py --des=10.0.2.2 --num-packets=100000 '
           f'--rank-value=2000 {rate_arg} --duration=30 --flow-id=1 '
           '> ./outputs/sender_h2.txt &')
    sleep(0.01)
    # Flow 2 (h3 -> h_r3): low weight flow (quantum=2000)
    h3.cmd('./send_enhanced.py --des=10.0.2.3 --num-packets=100000 '
           f'--rank-value=2000 {rate_arg} --duration=30 --flow-id=2 '
           '> ./outputs/sender_h3.txt &')
    sleep(0.01)

from time import sleep

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
    
    # Flow 0 (h1 -> h_r1): high weight flow (quantum=20000)
    # Note: Due to Python time.sleep() overhead and scapy sendp() overhead,
    # actual sending rate is much lower than theoretical rate.
    # Using --rate=0.0001 (theoretical 10000 pps) to achieve actual ~100+ pps per flow
    # All three flows need to use the same high rate to ensure total send rate > scheduler rate
    h1.cmd('./send_enhanced.py --des=10.0.2.1 --num-packets=100000 '
           '--rank-value=2000 --rate=0.0001 --duration=60 --flow-id=0 '
           '> ./outputs/sender_h1.txt &')  # theoretical ~10000 pps, actual ~100-200 pps
    sleep(0.01)  # Small delay to start flows almost simultaneously
    
    # Flow 1 (h2 -> h_r2): medium weight flow (quantum=10000)
    # Important: Must use the same --rate as h1 and h3 to ensure total send rate > scheduler rate
    h2.cmd('./send_enhanced.py --des=10.0.2.2 --num-packets=100000 '
           '--rank-value=2000 --rate=0.0001 --duration=60 --flow-id=1 '
           '> ./outputs/sender_h2.txt &')  # theoretical ~10000 pps, actual ~100-200 pps
    sleep(0.01)
    
    # Flow 2 (h3 -> h_r3): low weight flow (quantum=2000)
    # Important: Must use the same --rate as h1 and h2 to ensure total send rate > scheduler rate
    h3.cmd('./send_enhanced.py --des=10.0.2.3 --num-packets=100000 '
           '--rank-value=2000 --rate=0.0001 --duration=60 --flow-id=2 '
           '> ./outputs/sender_h3.txt &')  # theoretical ~10000 pps, actual ~100-200 pps
    sleep(0.01)  # Small delay to ensure all flows start

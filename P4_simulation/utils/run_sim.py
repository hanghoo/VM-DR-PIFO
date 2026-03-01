from time import sleep

def sending_function(self):
    # add by hang
    for host in self.net.hosts:
        host.cmd('mkdir -p outputs')

    """Minimal topology: 2 source hosts (h1-h2) sending to 2 receivers (h_r1-h_r2)"""
    h1, h2, h_r1, h_r2 = self.net.get('h1', 'h2', 'h_r1', 'h_r2')

    # Start receivers on all receiver hosts
    h_r1.cmd('./receive.py > ./outputs/receiver_h_r1.txt &')
    sleep(0.05)  # Reduced from 0.1 for faster startup
    h_r2.cmd('./receive.py > ./outputs/receiver_h_r2.txt &')
    sleep(0.05)
    sleep(0.5)  # Reduced from 1.0, but still allow receivers to initialize


    # Send traffic: h1->h_r1, h2->h_r2
    # Each sender sends to its corresponding receiver
    # Use VERY high send rate (--rate 0.001) to create queue buildup
    # This makes WRR weight differences more visible and allows queue accumulation
    # Note: Lower rate value = higher send rate = more packets per second
    h1.cmd('./send.py --h=./workload/flow_1.txt --des=10.0.2.1 --rate=0.001 > ./outputs/sender_h1.txt &')
    sleep(0.01)  # Reduced from 0.1 to start flows almost simultaneously
    h2.cmd('./send.py --h=./workload/flow_2.txt --des=10.0.2.2 --rate=0.001 > ./outputs/sender_h2.txt &')
    sleep(0.01)  # Reduced from 0.1 to start flows almost simultaneously
    sleep(0.01)  # Small delay to ensure all flows start

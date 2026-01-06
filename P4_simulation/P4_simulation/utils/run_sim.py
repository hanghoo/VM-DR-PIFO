from time import sleep

def sending_function(self):
    # add by hang
    for host in self.net.hosts:
        host.cmd('mkdir -p outputs')

    """Minimal topology: 3 source hosts (h1-h3) sending to 3 receivers (h_r1-h_r3)"""
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
    # Use high send rate (--rate 0.01) to create queue competition
    # This makes WRR weight differences more visible
    h1.cmd('./send.py --h=./workload/flow_1.txt --des=10.0.2.1 --rate=0.01 > ./outputs/sender_h1.txt &')
    sleep(0.01)  # Reduced from 0.1 to start flows almost simultaneously
    h2.cmd('./send.py --h=./workload/flow_2.txt --des=10.0.2.2 --rate=0.01 > ./outputs/sender_h2.txt &')
    sleep(0.01)  # Reduced from 0.1 to start flows almost simultaneously
    h3.cmd('./send.py --h=./workload/flow_3.txt --des=10.0.2.3 --rate=0.01 > ./outputs/sender_h3.txt &')
    sleep(0.01)  # Small delay to ensure all flows start

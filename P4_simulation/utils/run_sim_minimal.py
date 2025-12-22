from time import sleep 

def sending_function(self): 
    # Get hosts for minimal topology: h1-h8 (sources) and h_receiver (destination)
    h1, h2, h3, h4, h5, h6, h7, h8, h_receiver = self.net.get(
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'h7', 'h8', 'h_receiver'
    )
    
    # Start receiver on h_receiver (single output port for monitoring)
    # All traffic from h1-h8 will be routed to h_receiver on port 9
    h_receiver.cmd('./receive.py > ./outputs/receiver_h_receiver.txt &')
    
    # Wait for receiver to be ready
    sleep(10)
    
    # Send traffic from all source hosts to h_receiver (10.0.2.1)
    # Each host uses its corresponding flow file (flow_1.txt through flow_8.txt)
    # All packets will be routed to port 9 where the scheduler processes them
    h1.cmd('./send.py --h=./workload/flow_1.txt --des=10.0.2.1 > ./outputs/sender_h1.txt &')
    sleep(0.1)
    
    h2.cmd('./send.py --h=./workload/flow_2.txt --des=10.0.2.1 > ./outputs/sender_h2.txt &')
    sleep(0.1)
    
    h3.cmd('./send.py --h=./workload/flow_3.txt --des=10.0.2.1 > ./outputs/sender_h3.txt &')
    sleep(0.1)
    
    h4.cmd('./send.py --h=./workload/flow_4.txt --des=10.0.2.1 > ./outputs/sender_h4.txt &')
    sleep(0.1)
    
    h5.cmd('./send.py --h=./workload/flow_5.txt --des=10.0.2.1 > ./outputs/sender_h5.txt &')
    sleep(0.1)
    
    h6.cmd('./send.py --h=./workload/flow_6.txt --des=10.0.2.1 > ./outputs/sender_h6.txt &')
    sleep(0.1)
    
    h7.cmd('./send.py --h=./workload/flow_7.txt --des=10.0.2.1 > ./outputs/sender_h7.txt &')
    sleep(0.1)
    
    h8.cmd('./send.py --h=./workload/flow_8.txt --des=10.0.2.1 > ./outputs/sender_h8.txt &')
    sleep(0.1)








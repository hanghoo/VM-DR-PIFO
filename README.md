# Implementation of 20 scheduling and shaping policies using the DR-PIFO Traffic Manager, BMv2 target switches, Mininet and P4 language.
# The details of the scheduling policies can be found in the attached technical report.

We provide the implementation of 20 scheduling schemes from P1 to P20. All policies are implemented using either the DR-PIFO TM or the hierarchical TM (P15 and P20), except for (P1, P2, P3, P5). These 4 policies did not utilize the DR-PIFO traffic manager, as they don't have a naturally compatible version (rank-based version).

# To build and run:

1. Download the provided folders in "P4_simulation/" and save them in the main directory of your workspace.

2. Make sure these tools are installed in your workspace : Mininet, P4c, P4runtime and BMv2.
Optional : you can find these tools installed in the provided VM from https://github.com/p4lang/tutorials

3. Copy the files provided in "P4_simulation/BMv2 Files/" to the directory of the simple_switch in your system "behavioral-model/targets/simple_switch" (replace the already existed files, if needed)

4. In "behavioral-model/targets/simple_switch/simple_switch.cpp", for the lines from 42-45, include only the model of the packet scheduler that you would like to test.
https://github.com/Elbediwy/DR-PIFO_20_policies/blob/b6a6cc20bb2aeea6c95e35c610ab184da1e994c8/P4_simulation/BMv2%20files/simple_switch.cpp#L42-L50

For example, if you uncommented only "#include "TM_buffer_dr_pifo.h"", so you will use the DR-PIFO packet scheduler model in the BMv2 model. 

6. In the directory of BMv2 "behavioral-model/", run these commands : 
```bash
./autogen.sh
./configure
sudo make
sudo make install
sudo ldconfig
```
optional, in "behavioral-model/targets/simple_switch" and "behavioral-model/targets/simple_switch_grpc", you can run these commands:
```bash
sudo make
sudo make install
sudo ldconfig
```
6. For the DR-PIFO, in the "P4_simulation/utils/user_externs_dr_pifo/", run these commands : 
```bash
sudo make clean
sudo make
```

7. For the DR-PIFO, in the "P4_simulation/utils/user_externs_dr_pifo/p4runtime_switch.py", uncomment the line refers to the folder "user_externs_dr_pifo", from line 122 to 130 (which is 122 for the DR-PIFO).
https://github.com/Elbediwy/DR-PIFO_20_policies/blob/b6a6cc20bb2aeea6c95e35c610ab184da1e994c8/P4_simulation/utils/p4runtime_switch.py#L122-L130

9. Copy the content of the file corresponding to the desired policy.
For example, to implement (P6) Least Attained Service scheduling policy, choose "P4_simulation/program/qos/p4 programs/P6_LAS.p4" to this file "P4_simulation/program/qos/qos.p4"

10. In "P4_simulation/program/qos/", run these commands :
```bash
sudo make stop
sudo make clean
sudo make
```

10. Then, wait until the simulation is finished. (~ 30 mins)

To find the log files of each switch, go to "P4_simulation/utils/program/qos/logs", and to find the received packets by each receiving host, go to "P4_simulation/utils/program/qos/receiver_h'#host_id'".
You can modify the main run file "P4_simulation/utils/run_execrise.py" to apply different workloads.
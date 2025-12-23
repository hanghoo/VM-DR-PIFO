# WRR调度算法调用流程分析

## 一、整体调用链概览

```
run_exercise.py 
  └─> sending_function() (from run_sim.py)
      └─> send.py (在Mininet主机上执行)
          └─> 发送数据包到交换机
              └─> simple_switch.cpp (BMv2交换机)
                  └─> P2_WRR.p4 (P4程序)
                      └─> my_hier.my_scheduler() (extern函数)
                          └─> WRR.h::hier_scheduler::my_scheduler()
                              └─> run_core()
```

## 二、详细调用流程

### 1. run_sim.py 如何调用 send.py 和 workload

**文件位置**: `P4_simulation/utils/run_sim.py`

**完整代码**:
```3:31:P4_simulation/utils/run_sim.py
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
```

**调用机制详解**:
1. **Mininet主机命令执行**: `h1.cmd('./send.py ...')` 在Mininet虚拟主机h1上执行shell命令
2. **参数传递**:
   - `--h=./workload/flow_1.txt`: 指定workload文件路径，包含每个数据包的rank值
   - `--des=10.0.2.1`: 目标IP地址（对应接收端h_r1）
   - `--rate=0.01`: 发送速率（每包间隔0.01秒）
3. **后台执行**: `&` 使send.py在后台运行，不阻塞主进程
4. **输出重定向**: `> ./outputs/sender_h1.txt` 将输出保存到文件

**workload文件格式**: `P4_simulation/program/qos/workload/flow_1.txt`
```
2000
2000
2000
...
```
- 每行一个整数，表示该数据包的rank值（用于WRR调度）
- 文件有1000行，表示h1将发送1000个数据包

### 2. send.py 如何读取workload并构造数据包

**文件位置**: `P4_simulation/program/qos/send.py`

**完整流程**:
```39:79:P4_simulation/program/qos/send.py
    enq_file_in = open(args.h, "r")

    enq_lines = enq_file_in.readlines()
    enq_file_len = len(enq_lines)
    read_rank = 0
    args.m = "P4 is cool"
    if args.h and args.des and args.m:
        addr = socket.gethostbyname(args.des)
        iface = get_if()

       # pkt = Ether(src=get_if_hwaddr(iface), dst="ff:ff:ff:ff:ff:ff") / IP(src=get_if_addr(iface), dst="10.0.0.0", options=IPOption(bytes(1000))) / TCP() / args.m
       # sendp(pkt, iface=iface, verbose=False)
       # sleep(10)
       # sleep(1)
        for line in enq_lines:
            rank = int(enq_lines[read_rank])
            rank_bytes = struct.pack('>i',rank)
            #sleep(10)
            read_rank = read_rank + 1
            pkt = Ether(src=get_if_hwaddr(iface), dst="ff:ff:ff:ff:ff:ff", type=0x800) / IP(src=get_if_addr(iface), dst=addr, options=IPOption(rank_bytes)) / TCP() / args.m
            #pkt = Ether(src=get_if_hwaddr(iface), dst="ff:ff:ff:ff:ff:ff", type=0x800) / IP(src=get_if_addr(iface), dst=addr, options=IPOption('\x00\x02\x07\x88')) / TCP() / args.m
            #pkt_good = Ether(str(pkt))  # changed by hang. send pkt directly.

            print("This host has sent ",read_rank,"packets until now :", time.time())

            # try:
            #     sendp(pkt, iface=iface, verbose=False)
            #     if read_rank > 4445:
            #     	sleep(0.1)
            #     else:
            #     	sleep(0.1)
            # except KeyboardInterrupt:
            #     raise

            try:
                sendp(pkt, iface=iface, verbose=False)
                # Use configurable sleep time for send rate control
                # Lower sleep time = higher send rate = more queue buildup = better WRR visibility
                sleep(args.rate)
            except KeyboardInterrupt:
                raise
```

**关键步骤**:
1. **打开workload文件**: `open(args.h, "r")` 读取 `./workload/flow_1.txt`
2. **读取所有行**: `enq_lines = enq_file_in.readlines()` 获取所有rank值
3. **循环处理每个数据包**:
   - `rank = int(enq_lines[read_rank])` 读取rank值（例如：2000）
   - `rank_bytes = struct.pack('>i', rank)` 转换为大端字节序（4字节）
   - 构造数据包：将rank值放入IP options字段
   - `sendp(pkt, iface=iface)` 发送数据包
   - `sleep(args.rate)` 控制发送速率

### 3. simple_switch.cpp 接收和处理数据包

**文件位置**: `P4_simulation/BMv2 files/simple_switch.cpp`

**关键流程**:
```cpp
// 1. 接收数据包
int SimpleSwitch::receive_(port_t port_num, const char *buffer, int len) {
    auto packet = new_packet_ptr(port_num, packet_id++, len, ...);
    input_buffer->push_front(InputBuffer::PacketType::NORMAL, std::move(packet));
}

// 2. ingress线程处理数据包
void SimpleSwitch::ingress_thread() {
    while (1) {
        input_buffer->pop_back(&packet);
        
        // 解析数据包
        parser->parse(packet.get());
        
        // 执行P4程序的ingress pipeline
        ingress_mau->apply(packet.get());  // 这里会调用P2_WRR.p4中的MyIngress.apply()
        
        // 将数据包加入egress buffer
        enqueue(egress_port, std::move(packet));
    }
}
```

### 4. P2_WRR.p4 中如何处理数据包

**文件位置**: `P4_simulation/program/qos/p4 programs/P2_WRR.p4`

**关键代码**:
```p4
control MyIngress(inout headers hdr, inout metadata meta, 
                  inout standard_metadata_t standard_metadata) {
    
    // 声明extern对象
    @userextern @name("my_hier")
    hier_scheduler<bit<48>,bit<1>>(1) my_hier;
    
    // 变量定义
    bit <48> level_0_rank;
    bit <48> in_flow_id = 0;
    bit <48> in_pkt_ptr;
    bit <1> in_enq = 1;  // 入队标志
    bit <1> in_deq = 0;   // 出队标志
    
    apply {
        // 1. 查找flow_id
        lookup_flow_id.apply();  // 根据源IP地址查找flow_id
        
        if((hdr.ipv4.dstAddr == 0)||(in_flow_id == 0)) {
            drop();
        } else {
            // 2. 读取并更新packet pointer
            register_last_ptr.read(in_pkt_ptr, 0);
            in_pkt_ptr = in_pkt_ptr + (bit<48>)(1);
            register_last_ptr.write(0, in_pkt_ptr);
            
            // 3. 从IP options字段提取rank值
            level_0_rank = (bit<48>)(hdr.ipv4.options);
            
            // 4. 传递rank值给调度器
            my_hier.pass_rank_values(level_0_rank, 0);
            
            // 5. 调整flow_id (减1，因为数组索引从0开始)
            in_flow_id = in_flow_id - 1;
            
            // 6. 调用调度器的my_scheduler函数
            my_hier.my_scheduler(
                in_flow_id,              // flow_id: 例如 0 (对应h1)
                number_of_levels_used,  // 1
                in_pred,                 // 200000
                in_pkt_ptr,              // 例如 1
                in_shaping,              // 1
                in_enq,                  // 1 (入队)
                in_pkt_ptr,              // 1
                in_deq,                  // 0 (不出队)
                reset_time               // 0
            );
        }
    }
}
```

### 5. 详细示例：一个数据包的完整处理过程（以h1第一个数据包为例）

**场景设定**:
- 主机h1发送第一个数据包
- 源IP: h1的IP地址（例如 10.0.1.1）
- 目标IP: 10.0.2.1 (h_r1)
- rank值 = 2000 (从workload/flow_1.txt第一行读取)
- lookup_flow_id表匹配: srcAddr -> flow_id = 1
- 最终flow_id = 0 (数组索引，1-1=0)

**步骤1: send.py读取workload并发送数据包**

```python
# 在Mininet主机h1上执行
enq_file_in = open('./workload/flow_1.txt', "r")
enq_lines = enq_file_in.readlines()  # 读取所有行

# 处理第一个数据包 (read_rank = 0)
rank = int(enq_lines[0])  # rank = 2000
rank_bytes = struct.pack('>i', 2000)  # 转换为大端字节序: b'\x00\x00\x07\xd0'

# 构造数据包
pkt = Ether(
    src=get_if_hwaddr(iface), 
    dst="ff:ff:ff:ff:ff:ff", 
    type=0x800
) / IP(
    src=get_if_addr(iface),  # h1的IP地址
    dst="10.0.2.1",           # 目标地址
    options=IPOption(rank_bytes)  # rank值存储在IP options字段
) / TCP() / "P4 is cool"

sendp(pkt, iface=iface, verbose=False)  # 发送数据包
sleep(0.01)  # 等待0.01秒后发送下一个
```

**步骤2: simple_switch接收数据包**

```cpp
// simple_switch.cpp
int SimpleSwitch::receive_(port_t port_num, const char *buffer, int len) {
    // port_num = 1 (从h1接收)
    // buffer包含完整的数据包数据
    auto packet = new_packet_ptr(port_num, packet_id++, len, ...);
    input_buffer->push_front(InputBuffer::PacketType::NORMAL, std::move(packet));
    // 数据包被加入输入缓冲区，等待ingress线程处理
}
```

**步骤3: ingress线程解析并执行P4程序**

```cpp
// simple_switch.cpp - ingress_thread()
void SimpleSwitch::ingress_thread() {
    input_buffer->pop_back(&packet);  // 从缓冲区取出数据包
    
    parser->parse(packet.get());  // 解析以太网和IP头
    // 此时 hdr.ipv4.options = 2000 (从IP options字段提取)
    
    ingress_mau->apply(packet.get());  
    // 执行P4程序的MyIngress.apply()，进入P2_WRR.p4的处理流程
}
```

**步骤4: P2_WRR.p4处理数据包并调用my_scheduler**

```177:201:P4_simulation/program/qos/p4 programs/P2_WRR.p4
    apply {

        lookup_flow_id.apply();

        if((hdr.ipv4.dstAddr == 0)||(in_flow_id == 0))
        {
            drop();        
        }
        else
        {
        
        register_last_ptr.read(in_pkt_ptr,0);
        in_pkt_ptr = in_pkt_ptr + (bit<48>)(1);
        register_last_ptr.write(0,in_pkt_ptr);    
		
        reset_time = 0;

	level_0_rank = (bit<48>)(hdr.ipv4.options);

   	my_hier.pass_rank_values(level_0_rank,0);
	//my_hier.pass_rank_values(level_2_rank,2);
	
    in_flow_id = in_flow_id - 1;

            my_hier.my_scheduler(in_flow_id, number_of_levels_used, in_pred, in_pkt_ptr, in_shaping, in_enq, in_pkt_ptr, in_deq, reset_time);
        }
        
        if (hdr.ipv4.isValid()) {   
           ipv4_lpm.apply();
        }  
    }
```

**详细执行过程**:

1. **查找flow_id**:
   ```p4
   lookup_flow_id.apply();
   // 表匹配: hdr.ipv4.srcAddr (h1的IP) -> assign_flow_id(1)
   // 执行action: in_flow_id = 1
   ```

2. **检查有效性**:
   ```p4
   if((hdr.ipv4.dstAddr == 0)||(in_flow_id == 0)) {
       drop();  // 不满足条件，继续执行
   }
   ```

3. **更新packet pointer**:
   ```p4
   register_last_ptr.read(in_pkt_ptr, 0);  // 读取: in_pkt_ptr = 0 (初始值)
   in_pkt_ptr = 0 + 1 = 1;                 // 递增
   register_last_ptr.write(0, 1);          // 写回寄存器
   ```

4. **提取rank值**:
   ```p4
   level_0_rank = (bit<48>)(hdr.ipv4.options);  // level_0_rank = 2000
   ```

5. **传递rank值给调度器**:
   ```p4
   my_hier.pass_rank_values(level_0_rank, 0);
   // 调用WRR.h::pass_rank_values(2000, 0)
   // 将rank值存储到 pkt_levels_ranks[0] = 2000
   ```

6. **调整flow_id（数组索引从0开始）**:
   ```p4
   in_flow_id = in_flow_id - 1;  // in_flow_id = 1 - 1 = 0
   ```

7. **调用my_scheduler**:
   ```p4
   my_hier.my_scheduler(
       in_flow_id,              // 0
       number_of_levels_used,   // 1
       in_pred,                 // 200000
       in_pkt_ptr,              // 1 (作为arrival_time)
       in_shaping,              // 1
       in_enq,                  // 1 (入队标志)
       in_pkt_ptr,              // 1 (作为pkt_ptr)
       in_deq,                  // 0 (不出队)
       reset_time               // 0
   );
   ```

### 6. my_scheduler 如何调用到 run_core（详细追踪）

**文件位置**: `P4_simulation/utils/user_externs_WRR/WRR.h`

**注册机制**: `P4_simulation/utils/user_externs_WRR/WRR.cpp`
```78:79:P4_simulation/utils/user_externs_WRR/WRR.cpp
BM_REGISTER_EXTERN(hier_scheduler)
BM_REGISTER_EXTERN_METHOD(hier_scheduler, my_scheduler, const Data&, const Data&, const Data&, const Data&, const Data&, const Data&, const Data&, const Data&, const Data&);
```
- BMv2通过这个宏注册extern函数，使P4程序可以调用C++函数

**my_scheduler函数完整实现**:
```133:161:P4_simulation/utils/user_externs_WRR/WRR.h
	void my_scheduler(const Data& in_flow_id, const Data& number_of_levels_used, const Data& in_pred, const Data& in_arrival_time, const Data& in_shaping, const Data& in_enq, const Data& in_pkt_ptr, const Data& in_deq, const Data& reset_time)
	{

// copy the inputs values :: Todo : they should be removed later and just use the inputs directly.

	if(reset_time.get<uint32_t>() == 1)
	{
		time_now = 0;
	}
		flow_id = in_flow_id.get<uint32_t>();

		// pkt_levels_ranks contains the ranks of this packet at each level, levels_ranks[number_levels] for the root, and levels_ranks[0] for the leaves
		for (int i = number_of_levels_used.get<int>(); i < int(number_levels); i++)
		{
			pkt_levels_ranks.erase(pkt_levels_ranks.begin() + i);
			pkt_levels_ranks.insert(pkt_levels_ranks.begin() + i, pkt_levels_ranks[number_of_levels_used.get<int>()-1]);
		}

		pred = in_pred.get<uint32_t>();
		arrival_time = in_arrival_time.get<uint32_t>();
		shaping = in_shaping.get<uint32_t>();
		enq = in_enq.get<uint32_t>();
		pkt_ptr = in_pkt_ptr.get<uint32_t>();
		pkt_ptr_queue.push(pkt_ptr);
		deq = in_deq.get<uint32_t>();
		force_deq = 0;
// the core code of the AR-PIFO scheduler, that enqueue, dequeue or force dequeue packets.
		run_core();
	}
```

**以示例数据包为例，my_scheduler的执行过程**:

**输入参数** (从P2_WRR.p4传入):
- `in_flow_id` = 0
- `number_of_levels_used` = 1
- `in_pred` = 200000
- `in_arrival_time` = 1
- `in_shaping` = 1
- `in_enq` = 1
- `in_pkt_ptr` = 1
- `in_deq` = 0
- `reset_time` = 0

**执行步骤**:

1. **检查时间重置**:
   ```cpp
   if(reset_time.get<uint32_t>() == 1) {  // 0 != 1，跳过
       time_now = 0;
   }
   ```

2. **提取flow_id**:
   ```cpp
   flow_id = in_flow_id.get<uint32_t>();  // flow_id = 0
   ```

3. **处理rank值数组** (本例中number_of_levels_used=1, number_levels=1，循环不执行):
   ```cpp
   for (int i = 1; i < 1; i++) {  // 不执行
       // ...
   }
   // pkt_levels_ranks[0] = 2000 (已在pass_rank_values中设置)
   ```

4. **提取其他参数**:
   ```cpp
   pred = 200000;
   arrival_time = 1;
   shaping = 1;
   enq = 1;        // 入队标志
   pkt_ptr = 1;
   deq = 0;        // 不出队
   ```

5. **将pkt_ptr加入队列**:
   ```cpp
   pkt_ptr_queue.push(1);  // 用于后续出队时查找数据包
   ```

6. **调用run_core()**:
   ```cpp
   run_core();  // ← 关键调用点，进入核心调度逻辑
   ```

**run_core函数详细执行**:
```225:253:P4_simulation/utils/user_externs_WRR/WRR.h
	void run_core()
	{
		deq_packet_ptr = NULL;
		if (enq == 1)
		{
			if((start_time == 0)||(time_now == 0))
			{
				//start_time = std::time(0);
				start_time = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::high_resolution_clock::now().time_since_epoch()).count();
				//for (int i = 0; i<100 ;i++)
				//{
				//	quota_each_queue.erase(quota_each_queue.begin() + i);
				//	quota_each_queue.insert(quota_each_queue.begin() + i, quota);
				//}
			}

			number_of_enqueue_packets = number_of_enqueue_packets + 1;
			std::shared_ptr<packet> enq_packet_ptr;
			enq_packet_ptr = std::make_shared<packet>();
			enq_packet_ptr->level3_flow_id = flow_id;
			enq_packet_ptr->flow_id = flow_id;
			enq_packet_ptr->rank = pkt_levels_ranks[0];
			enq_packet_ptr->pred = pred;
			enq_packet_ptr->pkt_ptr = pkt_ptr;
			enq_packet_ptr->levels_ranks = pkt_levels_ranks;
			enq_packet_ptr->arrival_time = arrival_time;

			level_controller(enq_packet_ptr, enq, 0);

		}
```

**run_core执行过程（enq=1的情况）**:

1. **初始化**:
   ```cpp
   deq_packet_ptr = NULL;  // 出队指针初始化为空
   ```

2. **检查入队标志**:
   ```cpp
   if (enq == 1) {  // 1 == 1，执行入队逻辑
   ```

3. **初始化时间戳** (首次调用时):
   ```cpp
   if((start_time == 0)||(time_now == 0)) {
       start_time = 当前时间戳（毫秒）;
   }
   ```

4. **更新入队计数**:
   ```cpp
   number_of_enqueue_packets = number_of_enqueue_packets + 1;  // 例如: 0 -> 1
   ```

5. **创建packet对象**:
   ```cpp
   std::shared_ptr<packet> enq_packet_ptr = std::make_shared<packet>();
   enq_packet_ptr->level3_flow_id = 0;
   enq_packet_ptr->flow_id = 0;
   enq_packet_ptr->rank = pkt_levels_ranks[0];  // 2000
   enq_packet_ptr->pred = 200000;
   enq_packet_ptr->pkt_ptr = 1;
   enq_packet_ptr->levels_ranks = {2000};  // rank数组
   enq_packet_ptr->arrival_time = 1;
   ```

6. **调用level_controller进行入队**:
   ```cpp
   level_controller(enq_packet_ptr, 1, 0);
   // 将数据包加入FIFO bank (FB[0])，按flow_id组织
   ```

7. **出队逻辑** (enq=1时跳过):
   ```cpp
   if ((deq == 1) && (switch_is_ready == 1)) {  // 0 != 1，不执行
       // WRR调度出队逻辑...
   }
   ```

**level_controller入队过程**:
```167:220:P4_simulation/utils/user_externs_WRR/WRR.h
void level_controller(std::shared_ptr<packet>& level_packet_ptr, unsigned int level_enq, unsigned int level_id)
	{
		unsigned int error_detected;
		unsigned int internal_force_flow_id;
		std::shared_ptr<packet> out_deq_pkt_ptr;
		std::shared_ptr<fifo_bank> head_FB =  NULL;
		unsigned int queue_id = 0;
		unsigned int next_flow_id_empty = 0;
		unsigned int sum_number_all_queues = 0;
		unsigned int sum_all_update_rank_flows = 0;

		for(int i = 0; i < int(level_id); i++)
		{
			if(i ==0)
			{
				sum_all_update_rank_flows = (number_of_pkts_per_queue_each_level[0]*number_of_queues_per_level[0]);
			}
			else
			{
				sum_all_update_rank_flows = sum_all_update_rank_flows + number_of_queues_per_level[i-1];
			}
			sum_number_all_queues = sum_number_all_queues + number_of_queues_per_level[i];

		}
		if (level_enq == 1)
		{
			if(level_id < (number_levels - 1))
			{
				queue_id = int(level_packet_ptr->flow_id / number_of_pkts_per_queue_each_level[level_id]);
			}

			if(level_id == 0)
			{
				head_FB = FB[queue_id];
			}

			error_detected = error_detected_each_level[queue_id + sum_number_all_queues];
			internal_force_flow_id = internal_force_flow_id_each_level[queue_id + sum_number_all_queues];

			if(level_id !=0)
			{
				sum_all_update_rank_flows = sum_all_update_rank_flows + (number_of_pkts_per_queue_each_level[0]*number_of_queues_per_level[0]) * (number_levels-1);
			}

			hier(level_packet_ptr, level_enq, head_FB,next_flow_id_empty);

			error_detected_each_level[queue_id + sum_number_all_queues] = error_detected;
			internal_force_flow_id_each_level[queue_id + sum_number_all_queues] = internal_force_flow_id;
			if(level_id == 0)
			{
				FB[queue_id] = head_FB;
			}
		}
	}
```

- `level_id = 0`，`queue_id = 0 / 3 = 0`
- `head_FB = FB[0]` (获取队列0的FIFO bank)
- 调用`hier()`将数据包加入FIFO bank，按flow_id=0组织

**最终结果**:
- 数据包已入队到FB[0]中flow_id=0的队列
- rank=2000存储在packet对象中
- 等待后续出队时，WRR算法会根据quota和rank值决定是否出队

## 三、关键数据结构

### packet结构
```cpp
struct packet {
    unsigned int level3_flow_id;
    unsigned int flow_id;        // 流ID，例如 0, 1, 2
    unsigned int rank;          // rank值，例如 2000
    unsigned int pred;          // 预测值，例如 200000
    unsigned int pkt_ptr;       // 数据包指针，例如 1, 2, 3...
    std::vector<unsigned int> levels_ranks;
    unsigned int arrival_time;   // 到达时间
};
```

### WRR调度相关变量
```cpp
// 每个队列的配额
std::vector<unsigned int> quota_each_queue = {7500, 3000, 4500, ...};

// 每个队列的权重(quantum)
std::vector<unsigned int> quantums = {7500, 3000, 4500, ...};
```

## 四、完整调用链总结

### 调用流程图

```
run_sim.py::sending_function()
    │
    ├─> h1.cmd('./send.py --h=./workload/flow_1.txt --des=10.0.2.1 --rate=0.01')
    │   │
    │   └─> send.py::main()
    │       │
    │       ├─> 打开workload文件: open('./workload/flow_1.txt')
    │       ├─> 读取rank值: rank = 2000
    │       ├─> 构造数据包: IP(options=IPOption(rank_bytes))
    │       └─> 发送: sendp(pkt, iface=iface)
    │
    └─> simple_switch.cpp (BMv2交换机)
        │
        ├─> receive_() 接收数据包
        ├─> ingress_thread() 处理数据包
        │   │
        │   ├─> parser->parse() 解析数据包
        │   └─> ingress_mau->apply() 执行P4程序
        │       │
        │       └─> P2_WRR.p4::MyIngress::apply()
        │           │
        │           ├─> lookup_flow_id.apply() 查找flow_id
        │           ├─> 提取rank: level_0_rank = hdr.ipv4.options (2000)
        │           ├─> pass_rank_values(2000, 0) 传递rank值
        │           └─> my_hier.my_scheduler(...) 调用调度器
        │               │
        │               └─> WRR.h::hier_scheduler::my_scheduler()
        │                   │
        │                   ├─> 提取参数: flow_id=0, rank=2000, enq=1
        │                   ├─> pkt_ptr_queue.push(1)
        │                   └─> run_core()  ← 核心调度函数
        │                       │
        │                       ├─> 创建packet对象
        │                       ├─> level_controller() 入队到FIFO bank
        │                       └─> (出队逻辑在deq=1时执行)
```

### 关键数据流转

**示例数据包（h1第一个数据包）的完整数据流**:

| 阶段 | 位置 | 关键数据 | 值 |
|------|------|----------|-----|
| 1. 读取workload | send.py | rank | 2000 |
| 2. 构造数据包 | send.py | IP.options | b'\x00\x00\x07\xd0' (2000) |
| 3. 接收数据包 | simple_switch.cpp | packet buffer | 原始数据包 |
| 4. 解析 | P2_WRR.p4 | hdr.ipv4.options | 2000 |
| 5. 查找flow_id | P2_WRR.p4 | in_flow_id | 1 → 0 (减1后) |
| 6. 传递rank | WRR.h | pkt_levels_ranks[0] | 2000 |
| 7. 调用my_scheduler | WRR.h | flow_id, enq, pkt_ptr | 0, 1, 1 |
| 8. 创建packet对象 | WRR.h::run_core() | packet->rank | 2000 |
| 9. 入队 | WRR.h::level_controller() | FB[0] | 数据包加入队列 |

### 函数调用层次

```
P4程序层 (P2_WRR.p4)
    │
    ├─> lookup_flow_id.apply()          [P4表查找]
    ├─> my_hier.pass_rank_values()      [P4 extern调用]
    └─> my_hier.my_scheduler()          [P4 extern调用]
        │
        └─> C++实现层 (WRR.h)
            │
            ├─> hier_scheduler::my_scheduler()  [参数提取]
            │   │
            │   └─> hier_scheduler::run_core()  [核心调度]
            │       │
            │       ├─> level_controller()       [层级控制]
            │       │   │
            │       │   └─> hier()               [入队/出队]
            │       │       │
            │       │       ├─> enqueue_FB()   [FIFO bank入队]
            │       │       └─> dequeue_FB()    [FIFO bank出队]
            │       │
            │       └─> (WRR出队逻辑)          [配额检查与更新]
```

### 总结

1. **run_sim.py** 通过Mininet在虚拟主机上启动`send.py`进程，传递workload文件路径
2. **send.py** 从workload文件逐行读取rank值，构造数据包（rank值存储在IP options字段），按指定速率发送
3. **simple_switch.cpp** 接收数据包，通过ingress线程解析并执行P4程序
4. **P2_WRR.p4** 通过表查找获取flow_id，从IP options提取rank值，调用extern函数`my_hier.my_scheduler()`
5. **WRR.h::my_scheduler()** 接收P4传入的参数，提取并存储到成员变量，调用`run_core()`
6. **run_core()** 根据enq/deq标志执行入队或出队操作：
   - **入队** (enq=1): 创建packet对象，调用`level_controller()`将数据包加入FIFO bank
   - **出队** (deq=1): 执行WRR调度算法，检查各队列配额，选择可出队的数据包

整个流程实现了从Python脚本到P4程序，再到C++ extern函数的完整调用链，实现了WRR加权轮询调度算法。数据包在系统中经过多个层次的转换和处理，最终被正确调度和转发。




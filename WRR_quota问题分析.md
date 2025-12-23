# WRR调度算法quota问题分析

## 问题描述

**现象**: 
- `quota_each_queue = {0, 0, 0}` (初始配额)
- `quantums = {500, 500, 1000}` (权重)
- 数据包 `rank = 2000`
- **问题**: 即使quota和quantum都小于rank(2000)，数据包依然能够出队并被接收

## 问题分析

### 1. 出队逻辑流程

WRR算法的出队逻辑在 `WRR.h::run_core()` 中实现：

```284:338:P4_simulation/utils/user_externs_WRR/WRR.h
      for (int i = 0; i<3 ;i++)  // by hang. minimal topology: 3 flows
			{
				head_FS = FB[0];
				while((head_FS != NULL))
				{
					if(head_FS->left != NULL)
					{
						if(head_FS->left->object->flow_id == i)
						{
							if((quota_each_queue[i] >= head_FS->left->object->levels_ranks[0]))
							{
								dequeued_done_right = true;
								dequeue_right_id = head_FS->left->object->flow_id;
								break;
							}
						}
					}
					head_FS = head_FS->bottom;
				}
				if(dequeued_done_right == true)
				{
					break;
				}
			}
			if(dequeued_done_right == false)
			{
//				BMLOG_DEBUG("Invoked ELBEDIWY testing of starting the dequeue operation 2")
				//for (int i = 0; i<72 ;i++)
        for (int i = 0; i<3 ;i++)  // by hang. minimal topology: 3 flows
				{
					unsigned int current_quota = quota_each_queue[i];
					if(current_quota < quantums[i])
					{
						quota_each_queue.erase(quota_each_queue.begin() + i);
						quota_each_queue.insert(quota_each_queue.begin() + i, quantums[i]);
					}

					head_FS = FB[0];
					while((head_FS != NULL) &&(dequeued_done_right == false))
					{
						if(head_FS->left != NULL)
						{
							if(head_FS->left->object->flow_id == i)
							{
								if(quota_each_queue[i] >= head_FS->left->object->levels_ranks[0])
								{
									dequeued_done_right = true;
									dequeue_right_id = head_FS->left->object->flow_id;
								}
							}
						}
						head_FS = head_FS->bottom;
					}
				}
			}
```

### 2. 问题根源

**第一轮检查** (284-307行):
- 初始状态: `quota = {0, 0, 0}`, `rank = 2000`
- 检查: `quota[i] >= rank` → `0 >= 2000` → **false**
- 结果: `dequeued_done_right = false`

**第二轮检查** (308-338行):
- 重置quota: 如果 `quota[i] < quantums[i]`，则 `quota[i] = quantums[i]`
- 重置后: `quota = {500, 500, 1000}`
- 检查: `quota[i] >= rank` → `500 >= 2000` → **false**, `1000 >= 2000` → **false**
- 结果: `dequeued_done_right` 应该仍然是 **false**

**但是**，问题可能出现在 `dequeue_FB` 函数中：

```446:471:P4_simulation/utils/user_externs_WRR/WRR.h
	void dequeue_FB(std::shared_ptr<hier_scheduler::packet>& deq_packet_ptr, unsigned int flow_id, std::shared_ptr<hier_scheduler::fifo_bank>& head_FB, unsigned int in_time)
	{
		std::shared_ptr<hier_scheduler::fifo_bank> cur_ptr_FB;
		cur_ptr_FB = std::shared_ptr<hier_scheduler::fifo_bank>(std::make_shared<hier_scheduler::fifo_bank>());
		deq_packet_ptr = NULL;
		cur_ptr_FB = head_FB;
		while (cur_ptr_FB != NULL)
		{
			if ((cur_ptr_FB->flow_id == flow_id) && (cur_ptr_FB->left != NULL))
			{
				if(cur_ptr_FB->left->object != NULL)
				{
					if(cur_ptr_FB->left->object->pred <= in_time)
					{
//BMLOG_DEBUG("Invoked ELBEDIWY testing of in_time = {}", in_time)
//BMLOG_DEBUG("Invoked ELBEDIWY testing of cur_ptr_FB->left->object->pred = {}", cur_ptr_FB->left->object->pred)
						deq_packet_ptr = cur_ptr_FB->left->object;
						cur_ptr_FB->left = cur_ptr_FB->left->left;
					}
				}

				break;
			}
			cur_ptr_FB = cur_ptr_FB->bottom;
		}
	}
```

### 3. 关键问题

**`dequeue_FB` 函数中的 `pred` 检查**:
- `pred = 200000` (从P2_WRR.p4传入的 `in_pred`)
- 如果 `time_now >= 200000`，即使 `quota < rank`，数据包也会因为 `pred <= time_now` 而出队！

**但是**，`dequeue_FB` 只有在 `dequeued_done_right = true` 时才会被调用（340行），这意味着quota检查应该已经通过了。

### 4. 可能的原因

1. **时间问题**: 如果 `time_now` 增长很快，可能在某些情况下绕过了quota检查
2. **逻辑bug**: 在第二轮检查中，可能存在某个边界情况导致 `dequeued_done_right` 被错误设置为 `true`
3. **初始化问题**: quota可能在某个地方被意外修改

## 解决方案

### 方案1: 确保quota检查严格

在 `dequeue_FB` 函数中，应该**同时检查quota和pred**，而不是只检查pred：

```cpp
void dequeue_FB(std::shared_ptr<hier_scheduler::packet>& deq_packet_ptr, 
                 unsigned int flow_id, 
                 std::shared_ptr<hier_scheduler::fifo_bank>& head_FB, 
                 unsigned int in_time,
                 unsigned int current_quota,  // 添加quota参数
                 unsigned int packet_rank)    // 添加rank参数
{
    // ...
    if(cur_ptr_FB->left->object->pred <= in_time && 
       current_quota >= packet_rank)  // 同时检查quota
    {
        deq_packet_ptr = cur_ptr_FB->left->object;
        // ...
    }
}
```

### 方案2: 增加调试日志

在关键位置添加调试日志，追踪quota和rank的值：

```cpp
// 在run_core()的出队逻辑中
BMLOG_DEBUG("WRR Dequeue Check: flow_id={}, quota={}, quantum={}, rank={}, quota>=rank={}", 
            i, quota_each_queue[i], quantums[i], 
            head_FS->left->object->levels_ranks[0],
            quota_each_queue[i] >= head_FS->left->object->levels_ranks[0]);
```

### 方案3: 修复quantum设置

如果rank值固定为2000，quantum应该设置为**大于等于2000**的值：

```cpp
// 在WRR.cpp中
std::vector<unsigned int> bm::hier_scheduler::quota_each_queue = {0,0,0};
std::vector<unsigned int> bm::hier_scheduler::quantums = {2000, 2000, 2000};  // 改为 >= 2000
```

或者，如果希望保持较小的quantum，需要**减小rank值**（在workload文件中）。

## 建议的修复步骤

1. **立即修复**: 将quantum设置为 >= rank值
   ```cpp
   std::vector<unsigned int> bm::hier_scheduler::quantums = {2000, 2000, 2000};
   ```

2. **长期修复**: 在 `dequeue_FB` 中添加quota检查，确保即使pred条件满足，quota条件也必须满足

3. **验证**: 添加日志验证quota检查是否正常工作

## 验证方法

### 方法1: 添加调试日志

在 `WRR.h::run_core()` 中添加详细的调试日志：

```cpp
// 在出队逻辑开始前（256行后）
BMLOG_DEBUG("=== WRR Dequeue Check Start ===");
BMLOG_DEBUG("quota_each_queue: [{}, {}, {}]", 
            quota_each_queue[0], quota_each_queue[1], quota_each_queue[2]);
BMLOG_DEBUG("quantums: [{}, {}, {}]", 
            quantums[0], quantums[1], quantums[2]);
BMLOG_DEBUG("time_now: {}", time_now);

// 在第一轮检查中（293行）
if((quota_each_queue[i] >= head_FS->left->object->levels_ranks[0]))
{
    BMLOG_DEBUG("First Round: Flow {} dequeued! quota={}, rank={}", 
                i, quota_each_queue[i], head_FS->left->object->levels_ranks[0]);
    dequeued_done_right = true;
    dequeue_right_id = head_FS->left->object->flow_id;
    break;
}

// 在第二轮检查中（328行）
if(quota_each_queue[i] >= head_FS->left->object->levels_ranks[0])
{
    BMLOG_DEBUG("Second Round: Flow {} dequeued! quota={}, rank={}, quantum={}", 
                i, quota_each_queue[i], 
                head_FS->left->object->levels_ranks[0], quantums[i]);
    dequeued_done_right = true;
    dequeue_right_id = head_FS->left->object->flow_id;
}

// 在dequeue_FB调用后（344行）
if((dequeued_done_right == true))
{
    BMLOG_DEBUG("Calling dequeue_FB: flow_id={}, time_now={}", dequeue_id, time_now);
    dequeue_FB(deq_packet_ptr, dequeue_id, FB[0], time_now);
    if(deq_packet_ptr != NULL)
    {
        BMLOG_DEBUG("Dequeued packet: flow_id={}, rank={}, pred={}", 
                    deq_packet_ptr->flow_id, 
                    deq_packet_ptr->levels_ranks[0],
                    deq_packet_ptr->pred);
    }
    else
    {
        BMLOG_DEBUG("dequeue_FB returned NULL!");
    }
}
```

### 方法2: 检查实际值

在运行时打印实际的quota和rank值，确认它们是否真的小于2000。

### 方法3: 临时修复（快速验证）

将quantum设置为大于等于rank的值，验证问题是否消失：

```cpp
// 在WRR.cpp中
std::vector<unsigned int> bm::hier_scheduler::quantums = {2000, 2000, 2000};
```

如果这样修改后问题消失，说明确实是quota检查的问题。

## 最可能的原因

根据代码分析，最可能的原因是：

1. **quota在某个地方被意外增加**：可能在出队后quota更新逻辑有问题
2. **rank值实际上不是2000**：可能workload文件中的值被错误读取或转换
3. **时间相关的绕过**：如果`time_now`很大，`pred <= time_now`可能允许数据包绕过quota检查（但这不应该发生，因为dequeue_FB只在quota检查通过后才调用）

## 立即修复建议

**快速修复**：将quantum设置为 >= rank值：

```cpp
// 在 P4_simulation/BMv2 files/TM_buffer_WRR.h 或 WRR.cpp 中
std::vector<unsigned int> bm::hier_scheduler::quantums = {2000, 2000, 2000};
```

**或者**，修改workload文件，将rank值改为 <= quantum的值（例如500）。


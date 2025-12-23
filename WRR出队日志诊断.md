# WRR出队日志诊断指南

## 问题：没有看到"WRR Dequeue Operation Started"日志

### 原因分析

出队操作**不会在数据包入队时触发**。出队和入队是**分离的两个过程**：

1. **入队（Enqueue）**：在P4程序处理数据包时，调用 `my_scheduler(..., enq=1, deq=0, ...)`
2. **出队（Dequeue）**：在 `TM_buffer_WRR.h` 的 `valid_pop()` 函数中，调用 `dequeue_my_scheduler()`

### 出队触发条件

出队操作在以下条件下才会触发：

```cpp
// 在 TM_buffer_WRR.h::valid_pop() 中
if((dequeue_scheduler.number_of_deq_pkts() < dequeue_scheduler.num_of_read_pkts()) 
   && (dequeue_scheduler.number_of_enq_pkts() == dequeue_scheduler.num_of_read_pkts()))
{
    ptr = dequeue_scheduler.dequeue_my_scheduler();  // 这里才会触发出队
}
```

**条件说明**：
- `number_of_deq_pkts < num_of_read_pkts`：还有未出队的数据包
- `number_of_enq_pkts == num_of_read_pkts`：所有入队的数据包都已被读取

### 已添加的诊断日志

我已经在以下位置添加了日志：

1. **`dequeue_my_scheduler()` 函数开始**：
   - 显示函数被调用
   - 显示出队/入队/读取的包数量
   - 显示 `switch_is_ready` 状态

2. **`run_core()` 函数开始**：
   - 显示 `enq`, `deq`, `switch_is_ready` 的值

3. **出队条件检查**：
   - 如果条件满足：显示"WRR Dequeue Operation Started"
   - 如果条件不满足：显示"Dequeue condition NOT met"及原因

### 如何查看日志

重新编译后，在日志文件中查找：

```bash
# 查找所有WRR相关日志
grep -i "WRR\|my_scheduler\|run_core\|dequeue" logs/*.log

# 查找入队日志
grep "WRR Enqueue Operation" logs/*.log

# 查找出队相关日志
grep -E "dequeue_my_scheduler|Dequeue Operation|Dequeue condition" logs/*.log

# 查看完整的函数调用链
grep -E ">>>|WRR|Dequeue|Enqueue" logs/*.log | head -50
```

### 预期的日志序列

**正常情况下的日志序列**：

1. **模块初始化**：
   ```
   ========================================
   WRR Module INITIALIZED successfully!
   ========================================
   ```

2. **数据包入队**（每个数据包）：
   ```
   >>> my_scheduler CALLED: flow_id=0, enq=1, deq=0, pkt_ptr=1
   >>> run_core CALLED: enq=1, deq=0, switch_is_ready=1
   ========================================
   WRR Enqueue Operation
   flow_id: 0, rank: 2000, pred: 200000, pkt_ptr: 1
   ```

3. **出队操作**（当条件满足时）：
   ```
   >>> dequeue_my_scheduler CALLED
       number_of_deq_pkts=0, num_of_read_pkts=1, number_of_enq_pkts=1
       switch_is_ready=1
       Setting deq=1, force_deq=0
   >>> run_core CALLED: enq=0, deq=1, switch_is_ready=1
   ========================================
   WRR Dequeue Operation Started
   Condition check: deq=1, switch_is_ready=1
   ```

### 如果没有看到出队日志

**可能的原因**：

1. **`dequeue_my_scheduler()` 没有被调用**
   - 检查是否有 `>>> dequeue_my_scheduler CALLED` 日志
   - 如果没有，说明 `valid_pop()` 中的条件不满足

2. **出队条件不满足**
   - 查看 `>>> run_core CALLED` 日志中的 `deq` 值
   - 如果 `deq=0`，说明不会进入出队逻辑
   - 如果 `switch_is_ready=0`，也会阻止出队

3. **数据包还没有被读取**
   - 出队需要先读取数据包（`num_of_read_pkts`）
   - 检查是否有数据包入队但未被读取

### 诊断步骤

1. **检查是否有入队日志**：
   ```bash
   grep "WRR Enqueue Operation" logs/*.log
   ```
   如果没有，说明数据包没有进入调度器。

2. **检查是否有 `dequeue_my_scheduler` 调用**：
   ```bash
   grep "dequeue_my_scheduler CALLED" logs/*.log
   ```
   如果没有，说明出队函数没有被调用。

3. **检查 `run_core` 的调用情况**：
   ```bash
   grep "run_core CALLED" logs/*.log
   ```
   查看 `deq` 的值，确认是否有 `deq=1` 的情况。

4. **检查出队条件**：
   ```bash
   grep "Dequeue condition" logs/*.log
   ```
   查看为什么条件不满足。

### 关键理解

**重要**：在P4程序处理数据包时（`my_scheduler` 调用），`in_deq=0`，所以**不会触发出队**。

出队是在**另一个线程或另一个时机**，通过 `TM_buffer_WRR.h` 的 `valid_pop()` 函数触发的，该函数会调用 `dequeue_my_scheduler()`。

如果您的测试只是发送数据包，可能还没有触发 `valid_pop()` 的调用，所以看不到出队日志。


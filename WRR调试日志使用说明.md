# WRR调试日志使用说明

## 已添加的调试日志位置

我已经在 `WRR.h` 的以下关键位置添加了详细的调试日志：

### 1. 入队操作日志
- **位置**: `run_core()` 函数中，入队时
- **日志内容**: flow_id, rank, pred, pkt_ptr

### 2. 出队操作日志
- **位置**: `run_core()` 函数中，出队开始时
- **日志内容**: 
  - 初始quota和quantum值
  - 第一轮检查：每个flow的quota vs rank比较
  - 第二轮检查：quota重置和检查过程
  - dequeue_FB调用结果
  - quota更新后的值

### 3. dequeue_FB函数日志
- **位置**: `dequeue_FB()` 函数中
- **日志内容**: pred检查过程（pred <= time_now）

## 如何查看日志

### 重要提示

我已经将所有的 `BMLOG_DEBUG` 改为 `BMLOG_INFO`，因为：
1. `BMLOG_DEBUG` 需要编译时定义 `BM_LOG_DEBUG_ON` 宏才能工作
2. `BMLOG_INFO` 默认启用，更可靠
3. 日志会输出到simple_switch的日志文件，而不是Mininet控制台

### 方法1: 实时查看日志文件（推荐）

在运行Mininet时，打开**另一个终端窗口**，运行：

```bash
# 查看交换机日志（假设交换机名为s1）
tail -f logs/s1.log

# 或者如果日志文件在其他位置，查看运行Mininet时显示的路径
# 例如：*** Log file /path/to/program.log
tail -f /path/to/program.log

# 只查看WRR相关的日志
tail -f logs/s1.log | grep -E "WRR|Dequeue|Enqueue|quota|Flow"
```

**注意**: 
- 日志文件路径通常在运行Mininet时会显示
- 如果使用 `run_exercise.py`，日志通常在 `logs/` 目录下
- 日志不会显示在Mininet控制台，必须查看日志文件

### 方法2: 查看完整日志文件

```bash
# 查看整个日志文件
cat logs/s1.log

# 或者使用less分页查看
less logs/s1.log

# 只查看包含"WRR"的行
grep "WRR" logs/s1.log

# 只查看出队相关的日志
grep "Dequeue" logs/s1.log
```

### 方法3: 过滤特定信息

```bash
# 只查看quota相关的日志
grep -E "quota|quantum" logs/s1.log

# 只查看特定flow的日志
grep "Flow 0" logs/s1.log

# 查看出队检查的详细过程
grep -E "Round|SELECTED|check=" logs/s1.log
```

## 日志输出示例

运行后，您应该能看到类似以下的日志：

```
[WRR Enqueue Operation]
flow_id: 0, rank: 2000, pred: 200000, pkt_ptr: 1

========================================
WRR Dequeue Operation Started
time_now: 12345
Initial quota_each_queue: [0, 0, 0]
quantums: [500, 500, 1000]
First Round - Flow 0: quota=0, rank=2000, check=false
First Round - Flow 1: quota=0, rank=2000, check=false
First Round - Flow 2: quota=0, rank=2000, check=false
First Round: No packet selected, entering Second Round
Second Round - Flow 0: quota reset from 0 to 500
Second Round - Flow 0: quota=500, rank=2000, check=false
Second Round - Flow 1: quota reset from 0 to 500
Second Round - Flow 1: quota=500, rank=2000, check=false
Second Round - Flow 2: quota reset from 0 to 1000
Second Round - Flow 2: quota=1000, rank=2000, check=false
No packet selected for dequeue (dequeued_done_right=false)
```

## 关键信息解读

### 1. quota检查失败
如果看到：
```
Second Round - Flow 0: quota=500, rank=2000, check=false
```
说明quota确实小于rank，不应该出队。

### 2. 如果仍然出队了
如果看到：
```
dequeue_FB SUCCESS: flow_id=0, rank=2000, pred=200000, pkt_ptr=1
```
但之前的quota检查都是false，说明问题可能在：
- `dequeue_FB`中的pred检查绕过了quota限制
- 或者quota在某个地方被意外修改

### 3. pred检查
如果看到：
```
dequeue_FB - pred check: 200000 <= 12345 = false
dequeue_FB - pred check FAILED, packet NOT dequeued
```
说明pred检查阻止了出队（这是正常的，因为pred=200000很大）。

## 启用调试日志

### 重新编译WRR.so

修改代码后，**必须重新编译WRR.so**：

```bash
cd P4_simulation/utils/user_externs_WRR
make clean
make
```

### 重新编译P4程序

然后重新编译P4程序：

```bash
cd P4_simulation/program/qos
make clean
make
```

### 查看日志

1. **日志文件位置**：运行Mininet时会显示日志文件路径，例如：
   ```
   *** Log file /path/to/program.log
   ```

2. **如果使用run_exercise.py**：日志通常在 `logs/` 目录下，文件名格式为 `<switchname>.log`

3. **实时查看**：在另一个终端运行：
   ```bash
   tail -f logs/s1.log | grep -E "WRR|Dequeue|Enqueue|quota|Flow"
   ```

### 如果仍然看不到日志

1. **确认WRR.so已重新编译**：检查 `WRR.so` 的修改时间
2. **确认simple_switch加载了新的WRR.so**：检查启动参数中的 `--load-modules` 路径
3. **尝试使用BMLOG_ERROR**：如果INFO也不显示，尝试临时使用 `BMLOG_ERROR` 测试
4. **检查日志级别**：simple_switch默认日志级别可能不够，但INFO级别通常默认启用

## 常见问题

### Q: 看不到日志输出？
A: 
1. 确认日志文件路径正确
2. 确认BMv2编译时包含了调试信息
3. 尝试使用 `BMLOG_INFO` 代替 `BMLOG_DEBUG`（如果日志级别不够）

### Q: 日志太多？
A: 可以使用grep过滤：
```bash
tail -f logs/s1.log | grep "WRR\|Dequeue\|quota"
```

### Q: 想保存日志到文件？
A: 
```bash
tail -f logs/s1.log > wrr_debug.log
```

## 下一步

根据日志输出，您可以：
1. **确认quota和rank的实际值**：验证是否真的quota < rank
2. **追踪出队流程**：看数据包是在哪一步被错误地出队
3. **检查pred检查**：确认pred检查是否绕过了quota限制
4. **验证quota更新**：看quota是否在某个地方被意外修改


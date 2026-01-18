# WRR 测试指南

## 概述

本指南介绍如何测试 WRR (Weighted Round Robin) 调度算法，包括流量生成方法和测试建议。

## 文件说明

### `send_enhanced.py` - 增强版流量发送脚本
- 固定 rank 值（默认 2000）
- 自动停止（基于时间或包数）
- 创建拥塞场景以测试 WRR 权重分配
- 向后兼容（仍支持从文件读取）

### `run_sim.py` vs `run_sim_enhanced.py`
- **`run_sim.py`**：使用 `send.py`，从 workload 文件读取 rank 值（原始版本）
- **`run_sim_enhanced.py`**：使用 `send_enhanced.py`，自动生成流量（推荐用于 WRR 测试）

## 流量生成方法

### 两种实现方式

#### 方式 1: `run_sim.py`（原始版本）
使用 `send.py` 从 workload 文件读取：
- Workload 文件：`program/qos/workload/flow_X.txt`（每行一个 rank 值）
- 需要手动停止发送
- 适合需要精确控制每个包 rank 的场景

#### 方式 2: `run_sim_enhanced.py`（推荐用于 WRR 测试）⭐⭐
使用 `send_enhanced.py`，自动生成流量：
- **不再需要 workload 文件**：使用 `--num-packets` 和 `--rank-value` 参数自动生成
- **固定 rank**：所有包使用相同的 rank 值（默认 2000）
- **自动停止**：通过 `--duration` 参数控制发送时长，创建持续拥塞场景
- **高发送速率**：`--rate=0.001`（1000 包/秒/流）用于创建拥塞

### 增强版流量发送

`send_enhanced.py` 用于创建拥塞场景并测试 WRR 权重分配：

#### 功能特性
- **固定 rank 值**：所有包使用相同的 rank（默认 2000）
- **高发送速率**：通过 `--rate` 参数控制，值越小速率越高
- **自动停止**：基于时间（`--duration`）创建持续拥塞场景

#### 创建拥塞场景

为了测试 WRR 权重分配，需要创建拥塞场景：
- **高发送速率**：`--rate=0.001` 或更小（1000+ 包/秒/流）
- **调度延迟**：在 `WRR.h` 中设置 `sleep_for(10ms)` 或更长
- **持续发送**：使用 `--duration=60` 让流量持续发送

当发送速率 > 调度速率时，队列会积累，WRR 会根据权重分配带宽。

#### 使用示例

```bash
# 1. 创建拥塞场景：高发送速率，持续 60 秒
./send_enhanced.py --des=10.0.2.1 --num-packets=100000 \
    --rank-value=2000 --rate=0.001 --duration=60 --flow-id=0

# 2. 从文件读取（兼容原版）
./send_enhanced.py --h=./workload/flow_1.txt --des=10.0.2.1 --rate=0.001
```

#### 使用 run_sim_enhanced.py

`run_sim_enhanced.py` 使用 `send_enhanced.py` 自动生成流量并创建拥塞场景：

```python
# Flow 0: 高权重 flow
h1.cmd('./send_enhanced.py --des=10.0.2.1 --num-packets=100000 '
       '--rank-value=2000 --rate=0.001 --duration=60 --flow-id=0 '
       '> ./outputs/sender_h1.txt &')

# Flow 1: 中权重 flow
h2.cmd('./send_enhanced.py --des=10.0.2.2 --num-packets=100000 '
       '--rank-value=2000 --rate=0.001 --duration=60 --flow-id=1 '
       '> ./outputs/sender_h2.txt &')

# Flow 2: 低权重 flow
h3.cmd('./send_enhanced.py --des=10.0.2.3 --num-packets=100000 '
       '--rank-value=2000 --rate=0.001 --duration=60 --flow-id=2 '
       '> ./outputs/sender_h3.txt &')
```

**配置说明**：
- `--num-packets=100000`：足够大的包数，确保在 60 秒内不会发送完
- `--rank-value=2000`：固定 rank 值（确保所有 quantum >= 2000）
- `--rate=0.001`：高发送速率（1000 包/秒/流），创建拥塞
- `--duration=60`：持续发送 60 秒，创建持续拥塞场景

**使用方法**：
```bash
# 在 run_exercise.py 中导入 run_sim_enhanced 而不是 run_sim
# 或者直接修改 run_exercise.py 中的导入语句：
# from run_sim_enhanced import sending_function
```

**优势**：
- ✅ 不再需要 workload 文件
- ✅ 自动生成流量，简化测试流程
- ✅ 自动停止，无需手动干预

### 验证 WRR 权重分配

#### 关键问题：如何测量带宽分配？

**问题**：如果 Mininet 一直运行，所有包最终都会被发送，如何检测带宽分配？

**答案**：虽然所有包最终都会被发送，但在**拥塞持续期间**，不同权重的 flow 的包被发送的**速率**不同。我们需要测量**瞬时传输速率**或**时间窗口内的传输速率**，而不是总包数。

#### 测量方法

##### 方法 1: 时间窗口内的接收速率（推荐）⭐⭐⭐

**原理**：在固定时间窗口内（如每 10 秒），统计每个 flow 接收了多少包。

**步骤**：
1. 解析接收端日志（`receiver_h_r*.txt`），提取时间戳
2. 将时间分成窗口（如 10 秒一个窗口）
3. 统计每个窗口内每个 flow 接收的包数
4. 计算每个 flow 的传输速率（包/秒）

**使用分析脚本**：

1. **基本使用**（自动检测时间窗口）：
   ```bash
   cd P4_simulation/utils
   python3 measure_bandwidth_allocation.py ../program/qos/outputs
   ```

2. **指定时间窗口大小**：
   ```bash
   python3 measure_bandwidth_allocation.py ../program/qos/outputs --window-size=10
   ```

3. **手动指定测量时间范围**（可选）：
   ```bash
   # 如果知道确切的开始和结束时间（Unix 时间戳）
   python3 measure_bandwidth_allocation.py ../program/qos/outputs \
       --start-time=1234567890.0 \
       --end-time=1234567950.0 \
       --window-size=10
   ```

**脚本功能**：
- ✅ 自动解析所有接收端日志（`receiver_h_r1.txt`, `receiver_h_r2.txt`, `receiver_h_r3.txt`）
- ✅ 自动确定测量窗口（排除开始和结束的 5 秒，避免启动和停止阶段的影响）
- ✅ 按时间窗口统计每个 flow 的传输速率
- ✅ 计算带宽分配比例
- ✅ 与理论值（基于 quantums 10:5:1）对比

**输出说明**：
- 每个时间窗口的详细统计
- 整体统计（整个测量窗口）
- 实际带宽分配 vs 理论分配对比

**详细使用示例**：

假设你已经运行了实验，数据保存在 `P4_simulation/program/qos/outputs/` 目录下：

```bash
# 1. 进入脚本目录
cd P4_simulation/utils

# 2. 基本分析（使用默认 10 秒窗口）
python3 measure_bandwidth_allocation.py ../program/qos/outputs

# 3. 使用更小的窗口（5 秒）获得更细粒度的时间序列
python3 measure_bandwidth_allocation.py ../program/qos/outputs --window-size=5

# 4. 使用更大的窗口（20 秒）获得更稳定的平均值
python3 measure_bandwidth_allocation.py ../program/qos/outputs --window-size=20
```

**输出示例**：

```
Flow 0: 6234 packets received
Flow 1: 3121 packets received
Flow 2: 625 packets received

Measurement window: 1768101842.34 - 1768101892.34 seconds
Window size: 10 seconds
============================================================

Window 1: 1768101842.34 - 1768101852.34 seconds
------------------------------------------------------------
  Flow 0: 625 packets, 62.50 pps
  Flow 1: 312 packets, 31.20 pps
  Flow 2: 63 packets, 6.30 pps

  Total: 1000 packets, 100.00 pps
  Bandwidth allocation:
    Flow 0: 62.50%
    Flow 1: 31.20%
    Flow 2: 6.30%

...

============================================================
Overall Statistics (entire measurement window):
============================================================
Flow 0: 6234 packets, 62.34 pps
Flow 1: 3121 packets, 31.21 pps
Flow 2: 625 packets, 6.25 pps

Total: 9980 packets, 99.80 pps
Bandwidth allocation:
  Flow 0: 62.46%
  Flow 1: 31.27%
  Flow 2: 6.26%

Expected allocation (quantums 10:5:1):
  Flow 0: 62.50% (actual: 62.46%, diff: 0.04%)
  Flow 1: 31.25% (actual: 31.27%, diff: 0.02%)
  Flow 2: 6.25% (actual: 6.26%, diff: 0.01%)
```

**结果解读**：

1. **总传输速率**：应该接近调度速率（~100 pps），而不是发送速率（150 pps）
2. **带宽分配比例**：应该接近理论值（62.5% : 31.25% : 6.25% = 10:5:1）
3. **差异（diff）**：越小越好，通常 < 5% 表示 WRR 工作正常
4. **时间窗口一致性**：不同窗口的分配比例应该相似，表明 WRR 稳定工作

**常见问题**：

1. **Q: 如果所有 flow 的速率都很低怎么办？**
   - A: 检查发送速率是否太低，或者调度延迟是否太高
   - 确保总发送速率 > 调度速率（100 pps）

2. **Q: 如果分配比例不符合理论值怎么办？**
   - A: 检查 `quantums` 配置（`WRR.cpp`）
   - 检查是否有足够的拥塞（总发送速率应该 > 100 pps）
   - 检查 `rank` 值是否 <= `quantum`（否则该 flow 无法 dequeue）

3. **Q: 如何选择窗口大小？**
   - A: 小窗口（5-10 秒）：观察短期变化
   - 大窗口（20-30 秒）：获得更稳定的平均值
   - 默认 10 秒通常是一个好的平衡

##### 方法 2: 延迟差异分析

**原理**：高权重 flow 的包延迟低，低权重 flow 的包延迟高。

**步骤**：
1. 解析发送端和接收端日志，计算每个包的延迟
2. 比较不同 flow 的平均延迟
3. 高权重 flow 应该延迟明显更低

**预期结果**（基于 quantums=[20000, 10000, 2000]）：
- Flow 0（高权重）：延迟最低
- Flow 1（中权重）：延迟中等
- Flow 2（低权重）：延迟最高
- 延迟差异应该很明显（可能相差数倍）

##### 方法 3: 交换机日志统计（最准确）

**原理**：从 `s1.log` 中统计 `DEQUEUE SUCCESS` 事件，按 flow_id 和时间窗口分组。

**步骤**：
1. 解析 `logs/s1.log`，提取所有 `DEQUEUE SUCCESS` 事件
2. 提取 `flow_id` 和时间戳
3. 按时间窗口统计每个 flow 的 dequeue 次数
4. 计算每个 flow 的 dequeue 速率

**示例命令**：
```bash
# 统计 Flow 0 在 10-20 秒窗口内的 dequeue 次数
grep "DEQUEUE SUCCESS.*flow_id=0" logs/s1.log | \
  awk -F' ' '{print $1, $2}' | \
  # 过滤时间窗口 10-20 秒
  # 计算速率
```

##### 方法 4: 队列长度差异

**原理**：在拥塞期间，高权重 flow 的队列长度短，低权重 flow 的队列长度长。

**步骤**：
1. 从 `s1.log` 中提取队列长度信息（`packet_count`）
2. 统计每个 flow 的平均队列长度
3. 比较不同 flow 的队列长度

**预期结果**：
- Flow 0（高权重）：队列长度短（1-5 个包）
- Flow 2（低权重）：队列长度长（10-50+ 个包）

#### 预期结果（基于 sleep=10ms，发送速率=50 pps/流）

在拥塞持续期间（如 10-50 秒窗口），应该观察到：

| Flow | Quantum | 理论带宽比例 | 预期传输速率 | 预期延迟 | 预期队列长度 |
|------|---------|------------|------------|---------|------------|
| Flow 0 | 20000 | 62.5% | ~62.5 pps | 低（10-50ms） | 短（1-5 包） |
| Flow 1 | 10000 | 31.25% | ~31.25 pps | 中（50-100ms） | 中（5-15 包） |
| Flow 2 | 2000 | 6.25% | ~6.25 pps | 高（100-500ms+） | 长（20-100+ 包） |
| **总计** | - | 100% | **~100 pps** | - | - |

**注意**：
- 总传输速率接近调度速率（100 pps），而不是发送速率（150 pps）
- 带宽分配比例应该接近 quantums 比例（10:5:1）
- 延迟和队列长度差异应该很明显

## 测试配置建议

### 权重配置

| 配置名称 | Quantums | 比例 | 说明 |
|---------|----------|------|------|
| 小差异 | [20000, 15000, 10000] | 2:1.5:1 | 接近公平调度 |
| 中等差异 | [20000, 10000, 2000] | 10:5:1 | 平衡优先级和公平性 |
| 大差异 | [60000, 30000, 2000] | 30:15:1 | 严格优先级调度 |

### 发送速率配置（用于创建拥塞，基于 sleep=10ms）

| 速率名称 | Sleep Time | 包/秒/流 | 总发送速率 | 拥塞程度 | 说明 |
|---------|-----------|---------|-----------|---------|------|
| 轻度 | 0.03 | 33 | 99 pps | 0.99× | 接近调度速率，轻微拥塞 |
| **中度（推荐）** | **0.02** | **50** | **150 pps** | **1.5×** | **最佳测试配置** ⭐ |
| 中高 | 0.015 | 67 | 201 pps | 2.0× | 明显拥塞 |
| 重度 | 0.01 | 100 | 300 pps | 3.0× | 严重拥塞，队列快速增长 |

**注意**：基于当前 `sleep_for(10ms)` = 100 包/秒调度速率：
- 总发送速率应该 > 100 包/秒才能创建拥塞
- 推荐：150-210 包/秒（1.5-2.1倍调度速率）
- 每流：50-70 包/秒（`--rate=0.014` 到 `--rate=0.02`）

## 注意事项

### 1. Packet Rank 约束
- 确保所有包的 `rank <= quantum`
- 如果 `quantum < rank`，该 flow 将无法 dequeue 包
- 当前默认 `rank = 2000`，确保所有 `quantum >= 2000`

### 2. 调度延迟
- 需要手动修改 `WRR.h` 中的 `std::this_thread::sleep_for` 的值
- 建议使用 10ms 进行测试

### 3. 结果文件位置
- 发送端日志: `program/qos/outputs/sender_h*.txt`
- 接收端日志: `program/qos/outputs/receiver_h_r*.txt`
- 交换机日志: `logs/s1.log`

### 4. 带宽分配测量要点

**重要**：虽然所有包最终都会被发送，但需要测量**拥塞期间的瞬时传输速率**：

1. **使用时间窗口**：不要看总包数，而是看固定时间窗口内的传输速率
2. **拥塞期间测量**：在发送持续期间（如 10-50 秒）测量，而不是等所有包发送完
3. **多指标验证**：
   - 传输速率差异（主要指标）
   - 延迟差异（辅助验证）
   - 队列长度差异（辅助验证）

**测量时间窗口建议**：
- 开始时间：发送开始后 5-10 秒（让队列积累）
- 结束时间：发送停止前 5-10 秒（避免发送停止后的影响）
- 窗口大小：10-20 秒（足够统计，但不会太长）

## 瓶颈分析

### 当前拓扑配置

`topology.json` 中没有指定链路带宽和延迟：
```json
"links": [
  ["h1", "s1-p1"], ["h2", "s1-p2"], ["h3", "s1-p3"],
  ["h_r1", "s1-p4"], ["h_r2", "s1-p5"], ["h_r3", "s1-p6"]
]
```

- 当带宽未指定时，`run_exercise.py` 会将 `bandwidth=None` 传递给 Mininet
- Mininet 使用 `TCLink`，理论上无带宽限制
- **但实际瓶颈不是链路带宽**

### WRR 调度器处理速率计算

#### 代码位置
在 `WRR.h` 的 `run_core()` 函数中（第 348 行）：
```cpp
std::this_thread::sleep_for(std::chrono::milliseconds(10));  // 10ms delay
```

#### 调用流程
1. **触发点**：`TM_buffer_WRR.h` 中的 `valid_pop()` 函数
2. **调用条件**：当 `number_of_deq_pkts() < num_of_read_pkts()` 时
3. **调度过程**：
   - `valid_pop()` → `dequeue_my_scheduler()` → `run_core()`
   - `run_core()` 执行一次调度决策（可能 dequeue 一个包）
   - `sleep_for(10 milliseconds)` 延迟，加上代码执行开销

#### 速率计算（更新后：sleep=10ms）

**每次调度周期**：
- Sleep 时间：10 milliseconds
- 代码执行时间：通常 < 1ms（相对于 sleep 时间可忽略）
- **总周期时间**：约 **10ms**

**调度速率**：
```
调度周期 = 10ms = 0.01 秒
调度速率 = 1 / 周期时间 = 1 / 0.01秒 = 100 次/秒
```

**假设每次调度都能成功 dequeue 一个包**：
- **最大处理速率**：约 **100 包/秒**

#### 实际验证调度速率的方法

可以通过以下方式验证实际调度速率：

1. **查看日志统计**：
   ```bash
   # 统计 s1.log 中的 dequeue 事件总数
   grep "DEQUEUE SUCCESS" logs/s1.log | wc -l
   # 除以运行时间（秒）得到实际速率
   # 例如：6000 个事件 / 60 秒 = 100 包/秒
   ```

2. **时间窗口统计**（更准确）：
   ```bash
   # 统计每 10 秒窗口内的 dequeue 次数
   grep "DEQUEUE SUCCESS" logs/s1.log | \
     awk '{print $1, $2}' | \
     # 按时间窗口分组统计
   ```

3. **代码中添加计数器**：
   - 在 `run_core()` 中添加时间戳记录
   - 计算两次 dequeue 之间的时间间隔
   - 统计平均调度周期

4. **实验测量**：
   - 运行固定时长的实验（如 60 秒）
   - 统计总 dequeue 包数
   - 计算：实际速率 = 总包数 / 运行时间

### 瓶颈层次分析（更新后：sleep=10ms）

```
┌─────────────────────────────────────┐
│  发送速率: 150-300 包/秒             │  (3 flows，见下方推荐配置)
│  (总发送速率 > 调度速率，创建拥塞)   │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  WRR 调度器: ~100 包/秒             │  ⚠️ 主要瓶颈
│  (sleep_for 10ms = 100 ops/sec)    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  BMv2 处理: ~100 pps                │  (CPU 限制，通常 > 调度速率)
│  (取决于 CPU 和 P4 程序复杂度)       │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Mininet 链路: 理论上无限制          │  (实际受 CPU 限制)
│  (实际: CPU 限制)                   │
└─────────────────────────────────────┘
```

### 拥塞产生原因（更新后）

1. **调度速率**：~100 包/秒（受 `sleep_for(10ms)` 限制）
2. **发送速率**：需要 > 100 包/秒（总速率）才能创建拥塞
3. **推荐配置**：总发送速率 150-300 包/秒（1.5-3倍调度速率）
   - 既能创建拥塞
   - 又不会导致队列无限增长
   - 给 WRR 足够时间按权重分配带宽

### 发送速率配置建议（基于 sleep=10ms）

#### 调度速率分析
- **当前调度速率**：~100 包/秒（`sleep_for(10ms)`）
- **目标**：创建适度拥塞，测量 WRR 权重分配

#### 推荐发送速率配置

为了有效测量 WRR 带宽分配，建议使用以下配置：

| 场景 | 每流速率 | 总发送速率 | Sleep Time | 说明 |
|------|---------|-----------|-----------|------|
| **轻度拥塞** | 30-40 pps | 90-120 pps | 0.025-0.033s | 接近调度速率，轻微拥塞 |
| **中度拥塞（推荐）** | 50-70 pps | 150-210 pps | 0.014-0.02s | **最佳测试配置**，明显拥塞但稳定 |
| **重度拥塞** | 80-100 pps | 240-300 pps | 0.01-0.0125s | 严重拥塞，队列快速增长 |

#### 推荐配置（中度拥塞）

**每个 flow 发送速率**：50-70 包/秒
- **Sleep time**：`--rate=0.014` 到 `--rate=0.02`（对应 50-70 pps）
- **总发送速率**：150-210 包/秒
- **拥塞程度**：1.5-2.1 倍调度速率

**为什么这个配置好**：
- ✅ 总发送速率 > 调度速率（100 pps），确保队列积累
- ✅ 拥塞程度适中，不会导致队列无限增长
- ✅ 给 WRR 足够时间按权重分配带宽
- ✅ 权重差异会很明显（高权重 flow 获得更多带宽）

#### 更新 run_sim_enhanced.py 配置

```python
# Flow 0: 高权重 flow (quantum=20000)
h1.cmd('./send_enhanced.py --des=10.0.2.1 --num-packets=100000 '
       '--rank-value=2000 --rate=0.02 --duration=60 --flow-id=0 '
       '> ./outputs/sender_h1.txt &')  # 50 pps

# Flow 1: 中权重 flow (quantum=10000)
h2.cmd('./send_enhanced.py --des=10.0.2.2 --num-packets=100000 '
       '--rank-value=2000 --rate=0.02 --duration=60 --flow-id=1 '
       '> ./outputs/sender_h2.txt &')  # 50 pps

# Flow 2: 低权重 flow (quantum=2000)
h3.cmd('./send_enhanced.py --des=10.0.2.3 --num-packets=100000 '
       '--rank-value=2000 --rate=0.02 --duration=60 --flow-id=2 '
       '> ./outputs/sender_h3.txt &')  # 50 pps
```

**总发送速率**：3 × 50 = 150 包/秒
**调度速率**：100 包/秒
**拥塞程度**：1.5 倍（适度拥塞）

#### 预期带宽分配

基于 quantums = [20000, 10000, 2000] (10:5:1)：

| Flow | Quantum | 理论带宽比例 | 理论速率 | 预期实际速率 |
|------|---------|------------|---------|------------|
| Flow 0 | 20000 | 62.5% | ~62.5 pps | 60-65 pps |
| Flow 1 | 10000 | 31.25% | ~31.25 pps | 30-35 pps |
| Flow 2 | 2000 | 6.25% | ~6.25 pps | 5-10 pps |
| **总计** | - | 100% | **~100 pps** | **~100 pps** |

**注意**：实际传输速率会接近调度速率（100 pps），但分配比例应该接近 10:5:1。

### 结论

- **主要瓶颈**：WRR 调度器的处理速率（~100 包/秒，sleep=10ms）
- **推荐发送速率**：每流 50-70 pps（总速率 150-210 pps）
- **拥塞程度**：1.5-2.1 倍调度速率，既能创建拥塞又能稳定测量
- **无需设置链路带宽**：当前配置已能有效测试 WRR 权重分配

### 调整调度速率

如果需要调整瓶颈，可以修改 `WRR.h` 中的 `sleep_for` 值：

```cpp
// 当前：~100 包/秒
std::this_thread::sleep_for(std::chrono::milliseconds(10));  // 10ms

// 降低速率（增加瓶颈）：~50 包/秒
std::this_thread::sleep_for(std::chrono::milliseconds(20));  // 20ms

// 提高速率（减少瓶颈）：~200 包/秒
std::this_thread::sleep_for(std::chrono::milliseconds(5));  // 5ms
```

## 参考

- WRR 算法原理: 见之前的讨论文档
- 代码实现: `user_externs_WRR/WRR.h` 和 `WRR.cpp`
- 流量发送: `program/qos/send.py` 和 `send_enhanced.py`
- 调度器调用: `behavioral-model/targets/simple_switch/TM_buffer_WRR.h`

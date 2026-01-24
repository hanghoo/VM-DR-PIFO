# WRR 使用指南

本文档整合了所有 WRR 调度器的使用指南，包括测试方法、工具使用和结果分析。

---

## 目录

1. [概述](#概述)
2. [流量生成方法](#流量生成方法)
3. [测试配置建议](#测试配置建议)
4. [带宽分配测量](#带宽分配测量)
5. [工具使用指南](#工具使用指南)
6. [延迟 CDF 分析](#延迟-cdf-分析)
7. [常见问题](#常见问题)

---

## 概述

本指南介绍如何测试 WRR (Weighted Round Robin) 调度算法，包括流量生成方法和测试建议。

### 文件说明

**`send_enhanced.py`** - 增强版流量发送脚本
- 固定 rank 值（默认 2000）
- 自动停止（基于时间或包数）
- 创建拥塞场景以测试 WRR 权重分配
- 向后兼容（仍支持从文件读取）

**`run_sim.py` vs `run_sim_enhanced.py`**
- **`run_sim.py`**：使用 `send.py`，从 workload 文件读取 rank 值（原始版本）
- **`run_sim_enhanced.py`**：使用 `send_enhanced.py`，自动生成流量（推荐用于 WRR 测试）

---

## 流量生成方法

### 方式 1: `run_sim.py`（原始版本）

使用 `send.py` 从 workload 文件读取：
- Workload 文件：`program/qos/workload/flow_X.txt`（每行一个 rank 值）
- 需要手动停止发送
- 适合需要精确控制每个包 rank 的场景

### 方式 2: `run_sim_enhanced.py`（推荐用于 WRR 测试）⭐⭐

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

---

## 测试配置建议

### 权重配置

| 配置名称 | Quantums | 比例 | 说明 |
|---------|----------|------|------|
| 小差异 | [20000, 15000, 10000] | 2:1.5:1 | 接近公平调度 |
| 中等差异 | [20000, 10000, 2000] | 10:5:1 | 平衡优先级和公平性 |
| 大差异 | [40000, 10000, 2000] | 20:5:1 | 严格优先级调度 |

### 发送速率配置（基于 sleep=50ms，推荐）

| 速率名称 | Sleep Time | 包/秒/流 | 总发送速率 | 拥塞程度 | 说明 |
|---------|-----------|---------|-----------|---------|------|
| 轻度 | 0.0001 | ~18 | ~54 pps | 2.7× | 较强拥塞 |
| **中度（推荐）** | **0.00005** | **~17** | **~51 pps** | **2.5×** | **最佳测试配置** ⭐ |
| 重度 | 0.00001 | ~20 | ~60 pps | 3.0× | 严重拥塞 |

**注意**：基于当前 `sleep_for(50ms)` = 20 包/秒调度速率：
- 总发送速率应该 > 20 包/秒才能创建拥塞
- 推荐：50-60 包/秒（2.5-3倍调度速率）
- 每流：16-20 包/秒（`--rate=0.00005` 到 `--rate=0.0001`）

### 推荐配置（50ms，最佳效果）⭐⭐⭐

**每个 flow 发送速率**：16-18 包/秒
- **Sleep time**：`--rate=0.00005` 到 `--rate=0.0001`（对应 16-18 pps）
- **总发送速率**：48-54 包/秒
- **拥塞程度**：2.4-2.7 倍调度速率

**为什么这个配置好**：
- ✅ 总发送速率 > 调度速率（20 pps），确保队列积累
- ✅ 拥塞程度适中，不会导致队列无限增长
- ✅ 给 WRR 足够时间按权重分配带宽
- ✅ 权重差异会很明显（高权重 flow 获得更多带宽）

---

## 带宽分配测量

### 关键问题：如何测量带宽分配？

**问题**：如果 Mininet 一直运行，所有包最终都会被发送，如何检测带宽分配？

**答案**：虽然所有包最终都会被发送，但在**拥塞持续期间**，不同权重的 flow 的包被发送的**速率**不同。我们需要测量**瞬时传输速率**或**时间窗口内的传输速率**，而不是总包数。

### 测量方法：时间窗口内的接收速率（推荐）⭐⭐⭐

**原理**：在固定时间窗口内（如每 10 秒），统计每个 flow 接收了多少包。

**步骤**：
1. 解析接收端日志（`receiver_h_r*.txt`），提取时间戳
2. 将时间分成窗口（如 10 秒一个窗口）
3. 统计每个窗口内每个 flow 接收的包数
4. 计算每个 flow 的传输速率（包/秒）

### 使用分析脚本

**基本使用**（自动检测时间窗口）：
```bash
cd P4_simulation/utils
python3 measure_bandwidth_allocation.py ../program/qos/outputs
```

**指定时间窗口大小**：
```bash
python3 measure_bandwidth_allocation.py ../program/qos/outputs --window-size=10
```

**只分析拥塞期间**（推荐）：
```bash
python3 measure_bandwidth_allocation.py ../program/qos/outputs --congestion-only
```

**脚本功能**：
- ✅ 自动解析所有接收端日志（`receiver_h_r1.txt`, `receiver_h_r2.txt`, `receiver_h_r3.txt`）
- ✅ 自动确定测量窗口（排除开始和结束的 5 秒，避免启动和停止阶段的影响）
- ✅ 按时间窗口统计每个 flow 的传输速率
- ✅ 计算带宽分配比例
- ✅ 与理论值（基于 quantums）对比

**输出说明**：
- 每个时间窗口的详细统计
- 整体统计（整个测量窗口）
- 实际带宽分配 vs 理论分配对比

---

## 工具使用指南

### calculate_send_rate.py - 计算实际发送速率

**功能**：计算实际发送速率

**基本用法**：
```bash
# 计算所有 flow 的实际发送速率
python3 calculate_send_rate.py ../program/qos/outputs

# 计算特定 flow 的发送速率
python3 calculate_send_rate.py ../program/qos/outputs --flow-id 0

# 计算特定时间窗口的发送速率
python3 calculate_send_rate.py ../program/qos/outputs \
    --start-time 1768847731.96 \
    --end-time 1768847781.96
```

**输出说明**：

脚本会输出三种计算方法的结果：

1. **Summary method（总结方法）**：
   - 从 sender 日志的最后几行提取总包数和总时间
   - 计算平均发送速率：`平均速率 = 总包数 / 总时间`

2. **Timestamp method（时间戳方法）**：
   - 解析所有包的时间戳
   - 计算第一个包和最后一个包之间的时间差
   - 计算平均发送速率：`平均速率 = 包数 / 时间差`

3. **Interval analysis（间隔分析）**：
   - 计算相邻包之间的时间间隔
   - 计算平均间隔和速率：`平均速率 = 1 / 平均间隔`

### measure_bandwidth_allocation.py - 测量带宽分配

**功能**：测量带宽分配

**用法**：
```bash
python3 measure_bandwidth_allocation.py <outputs_dir> [--congestion-only] [--start-time <time>] [--end-time <time>] [--window-size <seconds>]
```

**输出**：
- 每个窗口的带宽分配
- 总体统计
- 与理论值的对比

### sendpfast 分析

**问题回顾**：
- 使用 `time.sleep()` 控制发送速率
- 理论发送速率：10000 pps（--rate=0.0001）
- 实际发送速率：~18 pps per flow
- **差异：556x** ⚠️

**sendpfast 能否克服问题？**

**答案**：**部分克服，但不能完全克服** ⚠️

**建议的改进方案**：

**方案 1：使用 sendpfast，但调整 pps 值（推荐）⭐⭐⭐**

```python
def send_packets(packets):
    # 使用适中的 pps 值，避免过度拥塞
    # 例如：50-100 pps per flow，总发送速率 150-300 pps
    sendpfast(packets, pps=80, loop=1, iface='eth0')
```

**优势**：
- 提高发送速率（从 ~18 pps 到 ~80 pps）
- 避免过度拥塞（拥塞程度 ~4-15x）
- 保持测试的稳定性

**关于 pps=380**：
- pps=380 可能太高，导致队列积压过大
- 建议使用更低的 pps 值（例如 50-100 pps per flow）

---

## 延迟 CDF 分析

### 使用方法

#### 1. 打开 Jupyter Notebook

```bash
cd ~/P4_simulation/utils
jupyter notebook plot_latency_cdf.ipynb
```

#### 2. 配置 outputs 文件夹（如果需要）

在 notebook 的第 2 个 cell 中，可以更改 `outputs_dir` 路径：

```python
# 默认路径：../program/qos/outputs
# 可以修改为任何包含 sender 和 receiver 日志的文件夹
outputs_dir = Path('../program/qos/outputs')
```

**测量窗口自动检测**：
- Notebook 会自动从 receiver 日志中检测时间范围
- 自动排除前 5 秒和后 5 秒（避免启动/关闭阶段的影响）
- **无需手动更新时间戳** ✅

#### 3. 运行所有 cells

依次运行所有 cells，notebook 会：
1. 自动检测测量窗口（从 receiver 日志中）
2. 解析发送端日志（`sender_h*.txt`）
3. 解析接收端日志（`receiver_h_r*.txt`）
4. 匹配包并计算延迟（在测量窗口内）
5. 绘制 CDF 曲线
6. 显示延迟统计信息

#### 4. 保存图片（可选）

取消注释最后一个 cell 中的代码：

```python
fig.savefig('wrr_latency_cdf_window1-5.png', dpi=300, bbox_inches='tight')
```

### 输出说明

**CDF 曲线**：
- **X 轴**：延迟（毫秒）
- **Y 轴**：CDF（累积分布函数，0-1）
- **三条线**：Flow 0（高权重）、Flow 1（中权重）、Flow 2（低权重）

**预期结果**：

在完整运行周期（自动检测的测量窗口）：
- **Flow 0**（高权重）：延迟最低，CDF 曲线最靠左（中位数 ~50 ms）
- **Flow 1**（中权重）：延迟中等，CDF 曲线在中间（中位数 ~6500 ms）
- **Flow 2**（低权重）：延迟最高，CDF 曲线最靠右（中位数 ~7000 ms）

**关键观察**：
- Flow 0 的延迟优势非常明显（中位数 50 ms vs Flow 1 的 6500 ms）
- 更真实地反映了 WRR 的权重差异
- 测量窗口包含完整的运行周期，而不仅仅是拥塞期间

### 注意事项

1. **包匹配**：代码假设包是按顺序接收的，通过包索引匹配
2. **测量窗口**：自动从数据中检测，排除前 5 秒和后 5 秒
3. **延迟范围**：只包含合理的延迟（0-10 秒）
4. **通用性**：适用于任何 outputs 文件夹，无需手动配置时间戳 ✅

### 故障排除

**问题 1: 找不到日志文件**

**错误**：`Warning: sender_h1.txt not found`

**解决**：
- 确认 `outputs_dir` 路径正确（默认：`../program/qos/outputs`）
- 确认实验已运行并生成了日志文件

**问题 2: 没有延迟数据**

**错误**：`No latencies calculated` 或 `No receive times in measurement window`

**解决**：
- 测量窗口会自动检测，无需手动配置
- 确认日志文件中有足够的数据（至少 10 秒以上的运行时间）
- 检查日志文件的时间戳是否有效

**问题 3: 延迟匹配不准确**

**可能原因**：
- 包丢失或乱序
- 时间戳不匹配

**解决**：
- 检查发送端和接收端的日志是否完整
- 调整匹配逻辑（如果需要）

### 依赖

确保安装了以下 Python 包：

```bash
pip install numpy matplotlib pandas jupyter
```

---

## 常见问题

### 1. 如果所有 flow 的速率都很低怎么办？

**A**: 检查发送速率是否太低，或者调度延迟是否太高
- 确保总发送速率 > 调度速率（20 pps for sleep=50ms）
- 检查 `--rate` 参数是否设置正确

### 2. 如果分配比例不符合理论值怎么办？

**A**: 
- 检查 `quantums` 配置（`WRR.cpp`）
- 检查是否有足够的拥塞（总发送速率应该 > 调度速率）
- 检查 `rank` 值是否 <= `quantum`（否则该 flow 无法 dequeue）
- **关键**：检查调度器速率和实际接收速率的差距是否 < 3 pps

### 3. 如何选择窗口大小？

**A**: 
- 小窗口（5-10 秒）：观察短期变化
- 大窗口（20-30 秒）：获得更稳定的平均值
- 默认 10 秒通常是一个好的平衡

### 4. 如何选择合适的 sleep_for 值？

**原则**：**让调度器速率接近实际接收速率，使调度器速率成为主要瓶颈**

**步骤**：
1. **测量实际接收速率**：
   - 运行测试，测量实际接收速率
   - 例如：50ms 时实际接收 17-19 pps

2. **设置 sleep_for**：
   - 让调度器速率略高于实际接收速率
   - **关键**：确保调度器速率和实际接收速率的差距 < 3 pps
   - 例如：实际接收速率 18 pps → `sleep_for(55ms)` = 18.2 pps ✅

3. **验证瓶颈**：
   - 确保拥塞程度 > 1.0（发送速率 > 调度器速率）✅
   - 确保调度器利用率 > 80%（实际接收速率 / 调度器速率 > 0.8）✅
   - **关键**：确保差距 < 3 pps ✅

### 5. Packet Rank 约束

- 确保所有包的 `rank <= quantum`
- 如果 `quantum < rank`，该 flow 将无法 dequeue 包
- 当前默认 `rank = 2000`，确保所有 `quantum >= 2000`

### 6. 结果文件位置

- 发送端日志: `program/qos/outputs/sender_h*.txt`
- 接收端日志: `program/qos/outputs/receiver_h_r*.txt`
- 交换机日志: `logs/s1.log`

---

**文档版本**：v2.0  
**最后更新**：整合所有使用指南相关的文档  
**状态**：✅ 完成

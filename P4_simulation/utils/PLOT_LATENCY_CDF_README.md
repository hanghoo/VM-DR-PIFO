# WRR Latency CDF Plotting Guide

## 使用方法

### 1. 打开 Jupyter Notebook

```bash
cd ~/P4_simulation/utils
jupyter notebook plot_latency_cdf.ipynb
```

### 2. 配置 outputs 文件夹（如果需要）

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

### 3. 运行所有 cells

依次运行所有 cells，notebook 会：
1. 自动检测测量窗口（从 receiver 日志中）
2. 解析发送端日志（`sender_h*.txt`）
3. 解析接收端日志（`receiver_h_r*.txt`）
4. 匹配包并计算延迟（在测量窗口内）
5. 绘制 CDF 曲线
6. 显示延迟统计信息

**自动检测的输出示例**：
```
Data time range: 1768707464.72 - 1768707746.08 seconds
Measurement window: 1768707469.72 - 1768707741.08 seconds
  (Excluded first 5s and last 5s to avoid startup/teardown effects)
  Duration: 271.36 seconds
```

### 4. 保存图片（可选）

取消注释最后一个 cell 中的代码：

```python
fig.savefig('wrr_latency_cdf_window1-5.png', dpi=300, bbox_inches='tight')
```

## 输出说明

### CDF 曲线

- **X 轴**：延迟（毫秒）
- **Y 轴**：CDF（累积分布函数，0-1）
- **三条线**：Flow 0（高权重）、Flow 1（中权重）、Flow 2（低权重）

### 预期结果

在完整运行周期（自动检测的测量窗口）：
- **Flow 0**（高权重）：延迟最低，CDF 曲线最靠左（中位数 ~50 ms）
- **Flow 1**（中权重）：延迟中等，CDF 曲线在中间（中位数 ~6500 ms）
- **Flow 2**（低权重）：延迟最高，CDF 曲线最靠右（中位数 ~7000 ms）

**关键观察**：
- Flow 0 的延迟优势非常明显（中位数 50 ms vs Flow 1 的 6500 ms）
- 更真实地反映了 WRR 的权重差异
- 测量窗口包含完整的运行周期，而不仅仅是拥塞期间

### 延迟统计

每个 flow 的统计信息：
- Min, 25th, Median, 75th, 95th, 99th, Max
- Mean, Std（平均值和标准差）

## 注意事项

1. **包匹配**：代码假设包是按顺序接收的，通过包索引匹配
2. **测量窗口**：自动从数据中检测，排除前 5 秒和后 5 秒
3. **延迟范围**：只包含合理的延迟（0-10 秒）
4. **通用性**：适用于任何 outputs 文件夹，无需手动配置时间戳 ✅

## 故障排除

### 问题 1: 找不到日志文件

**错误**：`Warning: sender_h1.txt not found`

**解决**：
- 确认 `outputs_dir` 路径正确（默认：`../program/qos/outputs`）
- 确认实验已运行并生成了日志文件

### 问题 2: 没有延迟数据

**错误**：`No latencies calculated` 或 `No receive times in measurement window`

**解决**：
- 测量窗口会自动检测，无需手动配置
- 确认日志文件中有足够的数据（至少 10 秒以上的运行时间）
- 检查日志文件的时间戳是否有效

### 问题 3: 延迟匹配不准确

**可能原因**：
- 包丢失或乱序
- 时间戳不匹配

**解决**：
- 检查发送端和接收端的日志是否完整
- 调整匹配逻辑（如果需要）

## 依赖

确保安装了以下 Python 包：

```bash
pip install numpy matplotlib pandas jupyter
```

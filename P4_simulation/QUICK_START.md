# 快速开始指南

本文档提供在新机器上快速设置和运行项目的步骤。

---

## 前提条件

- Ubuntu 16.04+ 或使用提供的 VM（Vagrant）
- 已有所有依赖（Mininet, P4c, BMv2, P4Runtime）

---

## 5 分钟快速设置

### 1. 更新路径（如果需要）

如果项目不在 `~/P4_simulation/`，需要更新以下文件：

#### 更新 `recompile_all.sh`

编辑 `P4_simulation/utils/user_externs_WRR/recompile_all.sh`：

```bash
# 将硬编码路径改为当前项目路径
cd /path/to/P4_simulation/utils/user_externs_WRR
# 和
cd /path/to/behavioral-model/targets/simple_switch
```

#### 更新 `run_sim_enhanced.py`

确保 Python 脚本中的路径正确。

### 2. 编译 WRR 调度器

```bash
cd P4_simulation/utils/user_externs_WRR
chmod +x recompile_all.sh
./recompile_all.sh
```

### 3. 编译 P4 程序

```bash
cd P4_simulation/program/qos
make clean
make
```

### 4. 运行仿真

```bash
cd P4_simulation/utils
sudo python3 run_sim_enhanced.py
```

### 5. 查看结果

```bash
# 带宽分配
cd P4_simulation/utils
python3 measure_bandwidth_allocation.py ../program/qos/outputs

# 延迟 CDF（可选）
jupyter notebook plot_latency_cdf.ipynb
```

---

## 关键配置

### WRR 调度器配置

**文件**：`P4_simulation/utils/user_externs_WRR/WRR.cpp`

```cpp
// 权重配置（可修改）
std::vector<unsigned int> bm::hier_scheduler::quantums = {20000,10000,2000};
```

### 调度器速率配置

**文件**：`P4_simulation/utils/user_externs_WRR/WRR.h`

```cpp
// 第 352 行：调度器延迟（30ms = 33 pps）
std::this_thread::sleep_for(std::chrono::milliseconds(30));
```

### 发送速率配置

**文件**：`P4_simulation/utils/run_sim_enhanced.py`

```python
# --rate=0.0001 (理论 10000 pps, 实际 ~40-50 pps per flow)
```

---

## 验证安装

```bash
# 1. 检查依赖
sudo mn --version
p4c-bm2-ss --version
simple_switch --help

# 2. 检查 WRR.so
ls P4_simulation/utils/user_externs_WRR/WRR.so

# 3. 测试编译
cd P4_simulation/program/qos
make clean && make
```

---

## 预期结果

### 带宽分配（quantums = {20000,10000,2000}）

- Flow 0: **~61%**（理论 62.5%）
- Flow 1: **~32%**（理论 31.25%）
- Flow 2: **~7%**（理论 6.25%）

### 延迟（中位数）

- Flow 0: **~50 ms**（高权重）
- Flow 1: **~6500 ms**（中权重）
- Flow 2: **~7000 ms**（低权重）

---

## 详细文档

- **完整迁移指南**：`PROJECT_MIGRATION_GUIDE.md`
- **调试完整指南**：`utils/WRR_DEBUG_COMPLETE_GUIDE.md`
- **测试指南**：`utils/WRR_TEST_GUIDE.md`

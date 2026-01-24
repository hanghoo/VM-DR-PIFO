# 使用P4Runtime测试set_quantum()和get_quantum()方法

本指南说明如何使用P4Runtime测试`set_quantum()`和`get_quantum()`方法。

## 概述

本指南提供两种测试方式：

### 方式1：只读取初始 quantum 值（推荐用于快速验证）

使用 `read_initial_quantum.py` 脚本：
1. 初始化运行P4程序
2. 配置 `get_quantum_table` 表项
3. 发送数据包触发 `get_quantum()` 读取**真实的初始值**（不是默认值）
4. 从 register 读取初始 quantum 值

**特点**：
- ✅ 只读取初始值，不修改
- ✅ 读取的是 WRR 中的真实值，不是 WRR.cpp 中的默认值
- ✅ 简单快速，适合验证 `get_quantum()` 功能

### 方式2：完整测试（包括 set_quantum）

使用 `test_quantum_p4runtime.py` 脚本：
1. 初始化运行P4程序
2. 读取初始quantum值（通过数据包触发 `get_quantum()`）
3. 使用P4Runtime动态修改quantums（通过 `set_quantum_table`）
4. 读取更新后的quantums（再次触发 `get_quantum()`）

**特点**：
- ✅ 完整测试 `set_quantum()` 和 `get_quantum()` 功能
- ✅ 验证动态修改是否生效
- ✅ 适合完整的功能测试

## 前提条件

### 1. 确保WRR.so已编译并包含set_quantum()和get_quantum()方法

```bash
cd P4_simulation/utils/user_externs_WRR/
make clean
make

# 验证方法是否存在
nm -D WRR.so | grep -E "set_quantum|get_quantum"
```

**预期输出**：
```
00000000000xxxxx T _hier_scheduler_set_quantum
00000000000xxxxx T _hier_scheduler_get_quantum
```

### 2. 确保P4程序已更新

确保`qos.p4`已包含：
- `set_quantum()`和`get_quantum()`在extern声明中
- `set_quantum_table`和`get_quantum_table`表
- `quantum_storage` register用于存储读取的值

### 3. 编译P4程序

有两种编译方式：

**方式1：使用p4c-bm2-ss（推荐，与项目Makefile一致）**

```bash
cd P4_simulation/program/qos/
p4c-bm2-ss --p4v 16 --p4runtime-files qos.json/qos.p4info.txt -o qos.json/qos.json qos.p4 --emit-externs
```

**方式2：使用p4c（需要禁用unknown警告）**

```bash
cd P4_simulation/program/qos/
p4c --target bmv2 --arch v1model --p4runtime-files qos.json/qos.p4info.txt --Wdisable=unknown qos.p4
```

**注意**：
- 如果遇到 "Unknown extern method" 错误，这是正常的。P4编译器在编译时无法验证extern方法（因为这些方法在运行时通过共享库加载）。
- 使用 `p4c-bm2-ss` 时，`--emit-externs` 选项会告诉编译器这些extern方法将在运行时通过共享库提供。
- 使用 `p4c` 时，需要使用 `--Wdisable=unknown` 选项来禁用这个警告。

### 4. 启动BMv2交换机

有两种方式启动交换机：

**方式1：使用Makefile启动（推荐，包含Mininet拓扑）**

```bash
cd P4_simulation/program/qos/
make run
```

这会：
- 自动编译P4程序（如果还没有编译）
- 启动Mininet拓扑
- 启动simple_switch_grpc交换机（支持P4Runtime）

**方式2：手动启动交换机（仅测试P4Runtime功能）**

```bash
# 确保JSON文件路径正确
cd P4_simulation/program/qos/

# 启动simple_switch_grpc
sudo simple_switch_grpc \
    --device-id 0 \
    --grpc-server-addr 0.0.0.0:50051 \
    --thrift-port 9090 \
    --log-console \
    -- --load-modules=/home/vagrant/P4_simulation/utils/user_externs_WRR/WRR.so \
    qos.json/qos.json
```

**检查交换机是否在运行**：

```bash
# 检查交换机是否在运行
ps aux | grep simple_switch

# 检查gRPC端口（默认50051）
netstat -tlnp | grep 50051
```

## 使用方法

### 场景1：只读取初始 quantum 值（不测试 set_quantum）

如果你只想读取初始 quantum 值，而不测试 `set_quantum()` 功能，可以使用简化脚本：

#### 步骤1：启动交换机

**如果使用Makefile（推荐）**：

```bash
cd P4_simulation/program/qos/
make run
```

**如果手动启动交换机**：

```bash
cd P4_simulation/program/qos/
sudo simple_switch_grpc \
    --device-id 0 \
    --grpc-server-addr 0.0.0.0:50051 \
    --thrift-port 9090 \
    --log-console \
    -- --load-modules=/home/vagrant/P4_simulation/utils/user_externs_WRR/WRR.so \
    qos.json/qos.json
```

#### 步骤2：运行简化脚本读取初始值

在另一个终端：

```bash
cd P4_simulation/utils/
python3 read_initial_quantum.py
```

**这个脚本会**：
- ✅ 连接交换机并初始化 P4 程序
- ✅ 配置 `get_quantum_table` 表项
- ✅ 发送数据包触发 `get_quantum()` 读取初始值
- ✅ 从 register 读取**真实的初始值**（不是 WRR.cpp 中的默认值）
- ❌ **不会**测试 `set_quantum()` 功能

**预期输出**：
```
======================================================================
Read Initial Quantum Values from WRR
======================================================================

Step 1: Set up get_quantum_table entries
  ✓ Set get_quantum table entry for queue 0
  ✓ Set get_quantum table entry for queue 1
  ✓ Set get_quantum table entry for queue 2

Step 2: Send packets to trigger get_quantum()
  ✓ Sent packet for queue 0 (src=0.0.0.0)
  ✓ Sent packet for queue 1 (src=0.0.0.1)
  ✓ Sent packet for queue 2 (src=0.0.0.2)

Step 3: Read initial quantum values from register
  quantum_storage[0] = 40000
    ✓ Successfully read initial quantum for queue 0: 40000
  quantum_storage[1] = 10000
    ✓ Successfully read initial quantum for queue 1: 10000
  quantum_storage[2] = 2000
    ✓ Successfully read initial quantum for queue 2: 2000

Results
✓ Successfully read all initial quantum values:
  Queue 0: 40000
  Queue 1: 10000
  Queue 2: 2000
```

#### 步骤3：使用 simple_switch_CLI 验证（可选）

在另一个终端验证：

```bash
simple_switch_CLI --thrift-port 9090
> register_read quantum_storage 0
quantum_storage[0]= 40000
> register_read quantum_storage 1
quantum_storage[1]= 10000
> register_read quantum_storage 2
quantum_storage[2]= 2000
```

### 场景2：完整测试（包括 set_quantum）

如果你想完整测试 `set_quantum()` 和 `get_quantum()` 功能，使用完整测试脚本：

#### 步骤1：启动交换机

（同场景1）

#### 步骤2：运行完整测试脚本

```bash
cd P4_simulation/utils/
python3 test_quantum_p4runtime.py
```

**这个脚本会**：
- ✅ 读取初始 quantum 值
- ✅ 通过 P4Runtime 修改 quantum 值
- ✅ 读取更新后的 quantum 值

### 基本用法（如果交换机已运行）

**只读取初始值**：
```bash
cd P4_simulation/utils/
python3 read_initial_quantum.py
```

**完整测试**：
```bash
cd P4_simulation/utils/
python3 test_quantum_p4runtime.py
```

### 指定参数

**简化脚本**：
```bash
# 指定gRPC端口和device_id
python3 read_initial_quantum.py --grpc-port 50051 --device-id 0

# 指定P4Info和JSON文件路径
python3 read_initial_quantum.py \
    --p4info P4_simulation/program/qos/qos.json/qos.p4info.txt \
    --json P4_simulation/program/qos/qos.json/qos.json
```

**完整测试脚本**：
```bash
# 指定gRPC端口和device_id
python3 test_quantum_p4runtime.py --grpc-port 50051 --device-id 0

# 指定P4Info和JSON文件路径
python3 test_quantum_p4runtime.py \
    --p4info P4_simulation/program/qos/qos.json/qos.p4info.txt \
    --json P4_simulation/program/qos/qos.json/qos.json
```

## 完整测试流程说明

### 测试目标

完整测试流程包括：
1. **读取初始quantum值**：通过发送数据包触发`get_quantum()`，从register读取真实的初始值
2. **动态修改quantums**：使用P4Runtime通过`set_quantum_table`修改quantum值
3. **验证修改结果**：再次触发`get_quantum()`并读取register，验证新值

### 步骤1：读取初始quantum值

脚本执行以下子步骤：

#### Step 1.1: 配置get_quantum_table表项

脚本首先为所有队列配置`get_quantum_table`表项，使数据包能够匹配并触发`get_wrr_quantum` action。

**表项配置**：
- 匹配字段：`hdr.ipv4.srcAddr[15:0]` = queue_idx (0, 1, 2)
- Action：`get_wrr_quantum(queue_idx)`
- 作用：当数据包的源IP地址低16位等于队列索引时，触发`get_quantum()`调用

#### Step 1.2: 发送数据包触发get_quantum()

脚本自动发送测试数据包来触发`get_quantum()`：

**数据包格式**：
- 队列 0: `src="0.0.0.0"` (srcAddr[15:0] = 0)
- 队列 1: `src="0.0.0.1"` (srcAddr[15:0] = 1)
- 队列 2: `src="0.0.0.2"` (srcAddr[15:0] = 2)

**执行流程**：
```
数据包进入交换机
  ↓
匹配 get_quantum_table (srcAddr[15:0] = queue_idx)
  ↓
执行 get_wrr_quantum action
  ↓
调用 my_hier.get_quantum(queue_idx, quantum_read_value)
  ↓
将读取的值写入 quantum_storage.register[queue_idx]
```

**注意**：
- 需要安装scapy：`pip install scapy`
- 如果scapy不可用，脚本会显示警告，但仍会尝试读取register（可能得到0或默认值）

#### Step 1.3: 从register读取初始值

脚本使用以下方法读取`quantum_storage` register：

**读取方法（按优先级）**：
1. **simple_switch_CLI**（最可靠）：通过subprocess调用CLI命令
2. **Thrift API**：使用TMultiplexedProtocol连接（已修复多路复用问题）
3. **默认值回退**：如果读取失败，使用WRR.cpp中的默认值

**预期初始值**（来自WRR.cpp）：
- 队列 0: 40000
- 队列 1: 10000
- 队列 2: 2000

**输出示例**：
```
Step 1.3: Reading quantum values from register...
  quantum_storage[0] = 40000
    ✓ Successfully read initial quantum for queue 0: 40000
  quantum_storage[1] = 10000
    ✓ Successfully read initial quantum for queue 1: 10000
  quantum_storage[2] = 2000
    ✓ Successfully read initial quantum for queue 2: 2000

  Initial quantum values: {0: 40000, 1: 10000, 2: 2000}
```

### 步骤2：通过P4Runtime动态修改quantums

脚本通过`set_quantum_table`表设置新的quantum值。

**表项配置**：
- 匹配字段：`hdr.ipv4.srcAddr[15:0]` = queue_idx
- Action：`set_wrr_quantum(queue_idx, quantum_value, reset_quota)`

**设置的新值**：
- 队列 0: 40000 → 50000
- 队列 1: 10000 → 15000
- 队列 2: 2000 → 3000

**执行流程**：
```
P4Runtime写入表项到 set_quantum_table
  ↓
当数据包匹配时（或通过控制平面触发）
  ↓
执行 set_wrr_quantum action
  ↓
调用 my_hier.set_quantum(queue_idx, quantum_value, reset_quota)
  ↓
更新WRR内部的quantum值
```

**输出示例**：
```
Step 2: Dynamically modify quantums via P4Runtime
  Debugging table match fields:
  Match fields for 'set_quantum_table':
    - hdr.ipv4.srcAddr[15:0] (id: 1, bitwidth: 16)
✓ Set quantum for queue 0 to 50000 (reset_quota=True)
✓ Set quantum for queue 1 to 15000 (reset_quota=True)
✓ Set quantum for queue 2 to 3000 (reset_quota=True)
```

### 步骤3：读取更新后的quantum值

#### Step 3.1: 配置get_quantum_table表项

脚本再次配置`get_quantum_table`表项（如果Step 1中已配置，这里会更新）。

#### Step 3.2: 发送数据包触发get_quantum()

脚本再次发送数据包来触发`get_quantum()`，读取更新后的值。

#### Step 3.3: 从register读取更新后的值

脚本从`quantum_storage` register读取更新后的quantum值。

**预期更新后的值**：
- 队列 0: 50000（从40000更新）
- 队列 1: 15000（从10000更新）
- 队列 2: 3000（从2000更新）

**输出示例**：
```
Step 3: Read updated quantum values
  Reading quantum values from register:
  quantum_storage[0] = 50000
  quantum_storage[1] = 15000
  quantum_storage[2] = 3000
```

## 只读取初始 Quantum 值（不测试 set_quantum）

如果你只想读取初始 quantum 值，而不测试 `set_quantum()` 功能，可以使用简化脚本 `read_initial_quantum.py`。

### ⚠️ 重要区别

**使用 `read_initial_quantum.py`**：
- ✅ 读取的是 **WRR 中的真实初始值**（通过 `get_quantum()` 从 WRR 内部读取）
- ✅ 不修改任何值，只读取
- ✅ 不测试 `set_quantum()` 功能

**使用 `test_quantum_p4runtime.py`**：
- ⚠️ 如果 register 为 0，会使用 WRR.cpp 中的默认值作为回退
- ✅ 会测试 `set_quantum()` 功能
- ✅ 会修改并验证 quantum 值

### 快速开始

#### 步骤1：启动交换机

```bash
cd P4_simulation/program/qos/
make run  # 或手动启动交换机
```

#### 步骤2：运行简化脚本（在另一个终端）

```bash
cd P4_simulation/utils/
python3 read_initial_quantum.py
```

### 脚本功能

`read_initial_quantum.py` 脚本会：
1. ✅ 连接交换机并初始化 P4 程序
2. ✅ 配置 `get_quantum_table` 表项
3. ✅ 发送数据包触发 `get_quantum()` 读取**真实的初始值**
4. ✅ 从 register 读取初始 quantum 值（**不是 WRR.cpp 中的默认值**）
5. ❌ **不会**测试 `set_quantum()` 功能
6. ❌ **不会**修改任何 quantum 值

### 完整终端操作步骤

#### 终端1：运行简化脚本

```bash
[vagrant@p4:~/P4_simulation/utils]$ python3 read_initial_quantum.py
======================================================================
Read Initial Quantum Values from WRR
======================================================================

This script will:
  1. Connect to switch and initialize P4 program
  2. Set up get_quantum_table entries
  3. Send packets to trigger get_quantum() for each queue
  4. Read quantum_storage register to get REAL initial values

Note: This reads actual values from WRR, not default values from WRR.cpp
======================================================================

✓ Successfully connected to switch (grpc_port=50051, device_id=0)

Initializing P4 program...
  Performing master arbitration...
  ✓ Master arbitration successful
  Setting forwarding pipeline config...
✓ P4 program initialized successfully

----------------------------------------------------------------------
Step 1: Set up get_quantum_table entries
----------------------------------------------------------------------
  Setting up get_quantum_table entries...
    ✓ Set get_quantum table entry for queue 0
    ✓ Set get_quantum table entry for queue 1
    ✓ Set get_quantum table entry for queue 2

----------------------------------------------------------------------
Step 2: Send packets to trigger get_quantum()
----------------------------------------------------------------------
  Note: Packets will match get_quantum_table and trigger get_wrr_quantum action
  This will call my_hier.get_quantum() and store the value in quantum_storage register
    ✓ Sent packet for queue 0 (src=0.0.0.0)
    ✓ Sent packet for queue 1 (src=0.0.0.1)
    ✓ Sent packet for queue 2 (src=0.0.0.2)

  Waiting 1 second for packets to be processed...

----------------------------------------------------------------------
Step 3: Read initial quantum values from register
----------------------------------------------------------------------
  Note: P4Runtime cannot read registers. Using Thrift API or CLI.
  These are REAL values from WRR, not default values from WRR.cpp
  quantum_storage[0] = 40000
    ✓ Successfully read initial quantum for queue 0: 40000
  quantum_storage[1] = 10000
    ✓ Successfully read initial quantum for queue 1: 10000
  quantum_storage[2] = 2000
    ✓ Successfully read initial quantum for queue 2: 2000

======================================================================
Results
======================================================================

✓ Successfully read all initial quantum values:
  Queue 0: 40000
  Queue 1: 10000
  Queue 2: 2000
```

#### 终端2：使用 simple_switch_CLI 验证（可选）

```bash
[vagrant@p4:~/P4_simulation/utils]$ simple_switch_CLI --thrift-port 9090
Obtaining JSON from switch...
Done
Control utility for runtime P4 table manipulation

RuntimeCmd: register_read quantum_storage 0
quantum_storage[0]= 40000

RuntimeCmd: register_read quantum_storage 1
quantum_storage[1]= 10000

RuntimeCmd: register_read quantum_storage 2
quantum_storage[2]= 2000

RuntimeCmd: [按 Ctrl+D 退出]
```

**退出 CLI 的方法**：
- ✅ **按 `Ctrl+D`** - 推荐，正常退出（发送 EOF）
- ⚠️ **按 `Ctrl+C`** - 强制退出，不推荐
- ❌ **`exit` 命令不可用** - 会显示 "Unknown syntax: exit"
- ❌ **`quit` 命令不可用**

### 关键点说明

1. **真实值 vs 默认值**：
   - 脚本读取的是 WRR 内部的真实初始值
   - 不是 WRR.cpp 中硬编码的默认值
   - 如果 WRR 内部的值被修改过，读取的会是修改后的值

2. **必须发送数据包**：
   - `get_quantum()` 必须通过数据包触发才能执行
   - 脚本会自动发送数据包
   - 如果不发送数据包，register 值会是 0

3. **不修改任何值**：
   - 脚本只读取，不修改
   - 不会调用 `set_quantum()`
   - 适合验证当前 WRR 中的真实 quantum 值

### 预期输出

```
======================================================================
Read Initial Quantum Values from WRR
======================================================================

Step 1: Set up get_quantum_table entries
  ✓ Set get_quantum table entry for queue 0
  ✓ Set get_quantum table entry for queue 1
  ✓ Set get_quantum table entry for queue 2

Step 2: Send packets to trigger get_quantum()
  ✓ Sent packet for queue 0 (src=0.0.0.0)
  ✓ Sent packet for queue 1 (src=0.0.0.1)
  ✓ Sent packet for queue 2 (src=0.0.0.2)

Step 3: Read initial quantum values from register
  quantum_storage[0] = 40000
    ✓ Successfully read initial quantum for queue 0: 40000
  quantum_storage[1] = 10000
    ✓ Successfully read initial quantum for queue 1: 10000
  quantum_storage[2] = 2000
    ✓ Successfully read initial quantum for queue 2: 2000

Results
✓ Successfully read all initial quantum values:
  Queue 0: 40000
  Queue 1: 10000
  Queue 2: 2000
```

### 使用 simple_switch_CLI 验证

脚本运行后，可以在另一个终端使用 CLI 验证：

```bash
simple_switch_CLI --thrift-port 9090
> register_read quantum_storage 0
quantum_storage[0]= 40000
> register_read quantum_storage 1
quantum_storage[1]= 10000
> register_read quantum_storage 2
quantum_storage[2]= 2000
```

### ⚠️ 重要说明：为什么 register 值可能是 0？

**关键点**：`quantum_storage` register 只有在数据包触发 `get_quantum()` action 时才会被写入。

**这意味着**：
- 如果直接读取 register，值可能是 0（因为 `get_quantum()` 还没有被触发）
- **必须先运行脚本发送数据包触发 `get_quantum()`，然后才能读取到值**
- 或者手动发送数据包来触发 `get_quantum()`

### 完整流程概述

要读取初始 quantum 值，必须按以下顺序操作：

```
1. 启动交换机
   ↓
2. 运行 read_initial_quantum.py 脚本
   - 配置 get_quantum_table 表项
   - 发送数据包触发 get_quantum()
   ↓
3. 使用 simple_switch_CLI 读取 register 值（可选验证）
```

**如果不运行脚本**：
- register 值会是 0（因为 `get_quantum()` 还没有被触发）
- 无法读取到真实的初始 quantum 值

### 前提条件

1. **确保交换机正在运行**：
   ```bash
   # 检查交换机进程
   ps aux | grep simple_switch
   
   # 检查Thrift端口（默认9090）
   netstat -tlnp | grep 9090
   ```

2. **必须先运行测试脚本**（重要！）：
   ```bash
   cd P4_simulation/utils/
   python3 test_quantum_p4runtime.py
   ```
   
   **测试脚本会执行以下操作**：
   - ✅ 配置 `get_quantum_table` 表项（使数据包能够匹配并触发 action）
   - ✅ 发送数据包触发 `get_quantum()` 读取初始值（将值写入 register）
   - ✅ 配置 `set_quantum_table` 表项
   - ✅ 通过 P4Runtime 修改 quantum 值
   - ✅ 再次发送数据包触发 `get_quantum()` 读取更新后的值
   
   **如果不运行脚本**：
   - ❌ register 值会是 0
   - ❌ 无法读取到初始 quantum 值
   - ❌ 无法验证 `set_quantum()` 是否生效

## 使用 simple_switch_CLI 验证 Quantum 值（推荐方法）

这是最可靠和直接的验证方法。以下是完整的终端操作步骤。

### 场景选择

**场景A：只读取初始值（不测试 set_quantum）**
- 使用 `read_initial_quantum.py` 脚本
- 只读取初始 quantum 值，不修改
- 适合快速验证 `get_quantum()` 功能

**场景B：完整测试（包括 set_quantum）**
- 使用 `test_quantum_p4runtime.py` 脚本
- 读取初始值 → 修改值 → 读取更新后的值
- 适合完整的功能测试

### 场景A：只读取初始值

#### 步骤1：运行简化脚本（必须先执行！）

**在终端1中运行**：

```bash
cd P4_simulation/utils/
python3 read_initial_quantum.py
```

**脚本会执行**：
1. 连接交换机并初始化 P4 程序
2. 配置 `get_quantum_table` 表项
3. **发送数据包触发 `get_quantum()`** ← 这一步很重要！
4. 从 register 读取**真实的初始值**（不是默认值）

#### 步骤2：使用 CLI 验证（在另一个终端）

**在终端2中运行**：

```bash
simple_switch_CLI --thrift-port 9090
```

然后读取值：

```bash
RuntimeCmd: register_read quantum_storage 0
quantum_storage[0]= 40000

RuntimeCmd: register_read quantum_storage 1
quantum_storage[1]= 10000

RuntimeCmd: register_read quantum_storage 2
quantum_storage[2]= 2000
```

### 场景B：完整测试（包括 set_quantum）

#### 步骤1：运行完整测试脚本（必须先执行！）

**在终端1中运行**：

```bash
cd P4_simulation/utils/
python3 test_quantum_p4runtime.py
```

**脚本会执行**：
1. 连接交换机并初始化 P4 程序
2. 配置 `get_quantum_table` 表项
3. **发送数据包触发 `get_quantum()`** ← 这一步很重要！
4. 从 register 读取初始值
5. 通过 P4Runtime 修改 quantum 值
6. 再次发送数据包并读取更新后的值

**预期输出**：
```
Step 1: Read initial quantum values
  Step 1.1: Setting up get_quantum_table entries...
    ✓ Set get_quantum table entry for queue 0
    ✓ Set get_quantum table entry for queue 1
    ✓ Set get_quantum table entry for queue 2
  Step 1.2: Sending packets to trigger get_quantum()...
    ✓ Sent packet for queue 0 (src=0.0.0.0)
    ✓ Sent packet for queue 1 (src=0.0.0.1)
    ✓ Sent packet for queue 2 (src=0.0.0.2)
  Step 1.3: Reading quantum values from register...
    quantum_storage[0] = 40000
    quantum_storage[1] = 10000
    quantum_storage[2] = 2000
```

**重要**：只有运行脚本后，register 中才会有值。如果不运行脚本，register 值会是 0。

#### 步骤2：打开 simple_switch_CLI（在另一个终端）

**在终端2中运行**：

```bash
simple_switch_CLI --thrift-port 9090
```

**预期输出**：
```
Obtaining JSON from switch...
Done
Control utility for runtime P4 table manipulation
RuntimeCmd: 
```

现在你进入了 CLI 交互模式，提示符是 `RuntimeCmd: `。

#### 步骤3：读取初始 quantum 值

**在脚本运行后**（Step 1 完成后），读取初始值：

```bash
RuntimeCmd: register_read quantum_storage 0
quantum_storage[0]= 40000

RuntimeCmd: register_read quantum_storage 1
quantum_storage[1]= 10000

RuntimeCmd: register_read quantum_storage 2
quantum_storage[2]= 2000
```

**说明**：
- 这些是 WRR.cpp 中定义的默认初始值
- **如果值为 0**：说明 `get_quantum()` 还没有被数据包触发
  - 可能原因：脚本没有成功发送数据包，或数据包没有匹配表项
  - 解决方法：确保脚本成功运行，或手动发送数据包（见下方）

#### 步骤4：验证 set_quantum() 是否生效

**在脚本执行 Step 2（修改 quantum 值）后**，读取更新后的值：

```bash
RuntimeCmd: register_read quantum_storage 0
quantum_storage[0]= 50000

RuntimeCmd: register_read quantum_storage 1
quantum_storage[1]= 15000

RuntimeCmd: register_read quantum_storage 2
quantum_storage[2]= 3000
```

**预期结果**：
- 队列 0: 50000（从 40000 更新）
- 队列 1: 15000（从 10000 更新）
- 队列 2: 3000（从 2000 更新）

**注意**：如果某个队列的值仍然是 0，说明该队列的 `get_quantum()` 还没有被数据包触发。

#### 步骤4：查看表项配置（可选）

验证表项是否正确配置：

```bash
# 查看 get_quantum_table 表项
RuntimeCmd: table_dump get_quantum_table

# 查看 set_quantum_table 表项
RuntimeCmd: table_dump set_quantum_table
```

#### 步骤5：退出 CLI

**重要**：`simple_switch_CLI` **不支持** `exit` 或 `quit` 命令。

正确的退出方法：

**方法1：按 Ctrl+D（推荐，正常退出）**
```bash
RuntimeCmd: [直接按 Ctrl+D]
```

这会发送 EOF（End of File），正常退出 CLI。

**方法2：按 Ctrl+C（强制退出）**
```bash
RuntimeCmd: [直接按 Ctrl+C]
```

注意：Ctrl+C 会强制退出，可能不会正常清理连接，不推荐。

**推荐使用方法1（Ctrl+D）**，这是最干净的方式。

**注意**：
- ❌ `exit` 命令不可用（会显示 "Unknown syntax: exit"）
- ❌ `quit` 命令不可用
- ✅ `Ctrl+D` 是唯一推荐的正常退出方法

### 完整终端会话示例

以下是一个完整的终端会话示例，展示正确的操作顺序：

```bash
# ============================================
# 终端1：运行测试脚本（必须先运行！）
# ============================================
[vagrant@p4:~/P4_simulation/utils]$ python3 test_quantum_p4runtime.py
======================================================================
WRR Quantum Test - Using P4Runtime
======================================================================
✓ Successfully connected to switch (grpc_port=50051, device_id=0)

Initializing P4 program...
  Performing master arbitration...
  ✓ Master arbitration successful
  Setting forwarding pipeline config...
✓ P4 program initialized successfully

----------------------------------------------------------------------
Step 1: Read initial quantum values
----------------------------------------------------------------------
  Step 1.1: Setting up get_quantum_table entries...
    ✓ Set get_quantum table entry for queue 0
    ✓ Set get_quantum table entry for queue 1
    ✓ Set get_quantum table entry for queue 2
  Step 1.2: Sending packets to trigger get_quantum()...
    ✓ Sent packet for queue 0 (src=0.0.0.0)
    ✓ Sent packet for queue 1 (src=0.0.0.1)
    ✓ Sent packet for queue 2 (src=0.0.0.2)
  Step 1.3: Reading quantum values from register...
    quantum_storage[0] = 40000
    quantum_storage[1] = 10000
    quantum_storage[2] = 2000
  Initial quantum values: {0: 40000, 1: 10000, 2: 2000}

----------------------------------------------------------------------
Step 2: Dynamically modify quantums via P4Runtime
----------------------------------------------------------------------
✓ Set quantum for queue 0 to 50000 (reset_quota=True)
✓ Set quantum for queue 1 to 15000 (reset_quota=True)
✓ Set quantum for queue 2 to 3000 (reset_quota=True)

----------------------------------------------------------------------
Step 3: Read updated quantum values
----------------------------------------------------------------------
  Reading quantum values from register:
    quantum_storage[0] = 50000
    quantum_storage[1] = 15000
    quantum_storage[2] = 3000

# ============================================
# 终端2：使用 simple_switch_CLI 验证（在脚本运行后）
# ============================================
[vagrant@p4:~/P4_simulation/utils]$ simple_switch_CLI --thrift-port 9090
Obtaining JSON from switch...
Done
Control utility for runtime P4 table manipulation

# 读取初始值（脚本已触发 get_quantum()）
RuntimeCmd: register_read quantum_storage 0
quantum_storage[0]= 40000

RuntimeCmd: register_read quantum_storage 1
quantum_storage[1]= 10000

RuntimeCmd: register_read quantum_storage 2
quantum_storage[2]= 2000

# 注意：如果脚本执行了 set_quantum()，需要再次触发 get_quantum() 才能看到新值
# 脚本会在 Step 3 中自动发送数据包并读取更新后的值
# 此时读取应该看到更新后的值（如果脚本成功执行）

RuntimeCmd: register_read quantum_storage 0
quantum_storage[0]= 50000

RuntimeCmd: register_read quantum_storage 1
quantum_storage[1]= 15000

RuntimeCmd: register_read quantum_storage 2
quantum_storage[2]= 3000

RuntimeCmd: [按 Ctrl+D 退出]
```

### ⚠️ 常见情况说明

#### 情况1：register 值为 0（正常情况，如果还没运行脚本）

```bash
RuntimeCmd: register_read quantum_storage 0
quantum_storage[0]= 0
```

**原因**：还没有运行测试脚本，`get_quantum()` 还没有被数据包触发。

**解决方法**：
1. 运行测试脚本：`python3 test_quantum_p4runtime.py`
2. 脚本会自动发送数据包触发 `get_quantum()`
3. 然后再次读取 register

#### 情况2：部分队列值为 0（如你遇到的情况）

```bash
RuntimeCmd: register_read quantum_storage 0
quantum_storage[0]= 50000  # ✅ 有值

RuntimeCmd: register_read quantum_storage 1
quantum_storage[1]= 0      # ❌ 还是 0

RuntimeCmd: register_read quantum_storage 2
quantum_storage[2]= 0      # ❌ 还是 0
```

**原因**：
- Queue 0 的 `get_quantum()` 已被触发（可能是脚本发送的数据包，或其他数据包）
- Queue 1 和 Queue 2 的 `get_quantum()` 还没有被触发

**解决方法**：
1. 确保脚本成功发送了所有队列的数据包
2. 检查脚本输出是否显示 "✓ Sent packet for queue X"
3. 如果脚本没有发送数据包（scapy 不可用），需要手动发送（见下方）

### 常见问题排查

#### 问题1：register 值为 0

**现象**：
```bash
RuntimeCmd: register_read quantum_storage 0
quantum_storage[0]= 0
```

**可能原因**：
1. **最常见**：还没有运行测试脚本，`get_quantum()` 还没有被数据包触发
2. 测试脚本运行了，但数据包发送失败（scapy 不可用）
3. 数据包没有匹配 `get_quantum_table` 表项
4. 表项未正确配置

**解决方案**：

**方案1：运行测试脚本（推荐）**
```bash
cd P4_simulation/utils/
python3 test_quantum_p4runtime.py
```
脚本会自动发送数据包触发 `get_quantum()`。

**方案2：检查脚本是否成功发送数据包**
查看脚本输出，应该看到：
```
Step 1.2: Sending packets to trigger get_quantum()...
  ✓ Sent packet for queue 0 (src=0.0.0.0)
  ✓ Sent packet for queue 1 (src=0.0.0.1)
  ✓ Sent packet for queue 2 (src=0.0.0.2)
```

如果没有看到这些输出，说明数据包发送失败。

**方案3：检查表项配置**
```bash
RuntimeCmd: table_dump get_quantum_table
```
应该看到 3 个表项（queue 0, 1, 2）。

**方案4：手动发送数据包触发 get_quantum()**（见下方）

#### 问题2：无法连接到交换机

**错误**：
```
Could not connect to thrift client on port 9090
```

**解决方案**：
1. 检查交换机是否运行：`ps aux | grep simple_switch`
2. 检查端口：`netstat -tlnp | grep 9090`
3. 确认 Thrift 端口号正确（默认 9090）

#### 问题3：表项未找到

**错误**：
```
Unknown table: get_quantum_table
```

**解决方案**：
1. 确保 P4 程序已正确编译
2. 确保测试脚本已运行并配置了表项
3. 检查表名是否正确（区分大小写）

### 手动触发 get_quantum()（如果需要）

如果 register 值为 0，可以手动发送数据包触发 `get_quantum()`：

#### 方法1：使用 Python 脚本

创建临时脚本 `trigger_get_quantum.py`：

```python
#!/usr/bin/env python3
from scapy.all import sendp, Ether, IP, TCP

# 触发队列 0 的 get_quantum()
pkt0 = Ether() / IP(src="0.0.0.0", dst="10.0.0.1") / TCP()
sendp(pkt0, iface='s1-eth0', verbose=False)

# 触发队列 1 的 get_quantum()
pkt1 = Ether() / IP(src="0.0.0.1", dst="10.0.0.1") / TCP()
sendp(pkt1, iface='s1-eth0', verbose=False)

# 触发队列 2 的 get_quantum()
pkt2 = Ether() / IP(src="0.0.0.2", dst="10.0.0.1") / TCP()
sendp(pkt2, iface='s1-eth0', verbose=False)

print("Packets sent to trigger get_quantum()")
```

运行：
```bash
python3 trigger_get_quantum.py
```

然后再次读取 register：
```bash
RuntimeCmd: register_read quantum_storage 0
quantum_storage[0]= 40000
```

#### 方法2：使用测试脚本

测试脚本已经包含了自动发送数据包的功能。只需确保：
1. 已安装 scapy：`pip install scapy`
2. 脚本成功运行并显示 "✓ Sent packet for queue X"

### 快速验证命令总结

```bash
# 1. 启动 CLI
simple_switch_CLI --thrift-port 9090

# 2. 读取所有队列的 quantum 值
register_read quantum_storage 0
register_read quantum_storage 1
register_read quantum_storage 2

# 3. 查看表项（可选）
table_dump get_quantum_table
table_dump set_quantum_table

# 4. 退出 CLI
# 按 Ctrl+D  # 推荐：正常退出（发送 EOF）
# 或按 Ctrl+C  # 不推荐：强制退出
```

**退出 CLI 的方法**：
- ✅ **按 `Ctrl+D`** - **推荐**，正常退出（发送 EOF）
- ⚠️ **按 `Ctrl+C`** - 强制退出，不推荐
- ❌ **`exit` 命令不可用** - simple_switch_CLI 不支持此命令
- ❌ **`quit` 命令不可用** - simple_switch_CLI 不支持此命令

**注意**：`simple_switch_CLI` 基于 Python 的 `cmd.Cmd` 类，只支持 `Ctrl+D`（EOF）来正常退出。

### 验证 set_quantum() 是否生效的完整流程

**重要**：必须按顺序执行，否则无法读取到值。

#### 流程概览

```
1. 启动交换机
   ↓
2. 运行测试脚本（必须！）
   - 配置表项
   - 发送数据包触发 get_quantum() 读取初始值
   - 通过 P4Runtime 修改 quantum 值
   - 再次发送数据包触发 get_quantum() 读取更新后的值
   ↓
3. 使用 CLI 验证（可选，脚本已经读取了值）
```

#### 详细步骤

**步骤1：运行测试脚本**（终端1，必须先执行）

```bash
cd P4_simulation/utils/
python3 test_quantum_p4runtime.py
```

**脚本会自动完成**：
- ✅ 配置 `get_quantum_table` 表项
- ✅ 发送数据包触发 `get_quantum()` 读取初始值
- ✅ 通过 P4Runtime 修改 quantum 值
- ✅ 再次发送数据包触发 `get_quantum()` 读取更新后的值

**步骤2：使用 CLI 验证**（终端2，可选）

```bash
simple_switch_CLI --thrift-port 9090
```

**读取值**：
```bash
# 读取初始值（脚本 Step 1 后）
RuntimeCmd: register_read quantum_storage 0
quantum_storage[0]= 40000

RuntimeCmd: register_read quantum_storage 1
quantum_storage[1]= 10000

RuntimeCmd: register_read quantum_storage 2
quantum_storage[2]= 2000

# 读取更新后的值（脚本 Step 3 后）
RuntimeCmd: register_read quantum_storage 0
quantum_storage[0]= 50000

RuntimeCmd: register_read quantum_storage 1
quantum_storage[1]= 15000

RuntimeCmd: register_read quantum_storage 2
quantum_storage[2]= 3000
```

**对比结果**：
- 初始值：{0: 40000, 1: 10000, 2: 2000}
- 更新后：{0: 50000, 1: 15000, 2: 3000}

#### ⚠️ 重要提醒

**如果不运行测试脚本**：
- ❌ register 值会是 0
- ❌ 无法读取到初始 quantum 值
- ❌ 无法验证 `set_quantum()` 是否生效

**原因**：
- `quantum_storage` register 只有在数据包触发 `get_quantum()` action 时才会被写入
- 测试脚本会发送数据包来触发 `get_quantum()`
- 如果不运行脚本，就没有数据包触发，register 值就是 0

**解决方法**：
1. **推荐**：运行测试脚本，脚本会自动处理所有步骤
2. **手动**：如果不运行脚本，需要手动发送数据包触发 `get_quantum()`（见下方）

### 其他验证方法（参考）

#### 方法2：使用脚本中的printRegister函数

脚本已经实现了`printRegister()`函数，用法类似`printCounter()`：

```python
# 在脚本中
printRegister(p4info_helper, sw, "quantum_storage", 0)
printRegister(p4info_helper, sw, "quantum_storage", 1)
printRegister(p4info_helper, sw, "quantum_storage", 2)

# 或者循环读取（类似printCounter示例）
while True:
    sleep(2)
    print('\n----- Reading quantum values -----')
    printRegister(p4info_helper, sw, "quantum_storage", 0)
    printRegister(p4info_helper, sw, "quantum_storage", 1)
    printRegister(p4info_helper, sw, "quantum_storage", 2)
```

#### 方法3：使用sw.ReadRegisters()方法

脚本在`switch.py`中实现了`ReadRegisters()`方法，用法类似`ReadCounters()`：

```python
# 读取单个register值
for value in sw.ReadRegisters(register_name="quantum_storage", index=0, thrift_port=9090):
    print(f"quantum_storage[0] = {value}")

# 读取所有register值
for value in sw.ReadRegisters(register_name="quantum_storage", thrift_port=9090):
    print(f"Value: {value}")
```

**注意**：`ReadRegisters()`内部使用Thrift API，因为P4Runtime不支持读取register。

**推荐使用方法1（simple_switch_CLI）**，因为它最简单、最可靠，不需要额外的Python代码。

## 重要说明

### P4Runtime的限制

**P4Runtime不能读取register**：
- P4Runtime只能用于创建和配置表项（table entries）
- 读取register必须使用Thrift API或simple_switch_CLI
- 脚本已实现自动回退机制：先尝试CLI，失败时使用Thrift API

### get_quantum()的工作原理

**关键点**：
1. `get_quantum()`需要通过数据包触发才能执行
2. 数据包必须匹配`get_quantum_table`表项
3. 匹配后执行`get_wrr_quantum` action
4. Action调用`my_hier.get_quantum()`并将结果写入`quantum_storage` register
5. 然后才能通过Thrift API或CLI读取register值

**为什么register可能为0**：
- 如果register值为0，可能的原因：
  1. `get_quantum()`还没有被数据包触发
  2. 数据包没有匹配`get_quantum_table`表项
  3. WRR内部的quantum值确实是0（不太可能）

### set_quantum()的工作原理

**关键点**：
1. `set_quantum()`通过P4Runtime写入`set_quantum_table`表项
2. 当数据包匹配表项时，执行`set_wrr_quantum` action
3. Action调用`my_hier.set_quantum()`直接更新WRR内部的quantum值
4. **注意**：`set_quantum()`不会自动更新`quantum_storage` register
5. 要验证`set_quantum()`是否生效，需要：
   - 发送数据包触发`get_quantum()`读取新值
   - 然后从register读取验证

## 完整测试流程示例

### 自动化测试（推荐）

脚本已经实现了完整的自动化测试流程，只需运行：

```bash
cd P4_simulation/utils/
python3 test_quantum_p4runtime.py
```

脚本会自动：
1. 连接交换机并初始化P4程序
2. 配置`get_quantum_table`表项
3. 发送数据包触发`get_quantum()`读取初始值
4. 通过P4Runtime修改quantum值
5. 再次发送数据包并读取更新后的值

### 手动测试步骤

如果需要手动执行每个步骤：

#### 1. 运行测试脚本设置表项

```bash
python3 test_quantum_p4runtime.py
```

这会：
- 配置`get_quantum_table`和`set_quantum_table`表项
- 自动发送数据包触发`get_quantum()`
- 读取初始值并修改quantum值

#### 2. 验证quantum值（使用simple_switch_CLI）

在另一个终端：

```bash
simple_switch_CLI --thrift-port 9090
> register_read quantum_storage 0
quantum_storage[0]= 50000
> register_read quantum_storage 1
quantum_storage[1]= 15000
> register_read quantum_storage 2
quantum_storage[2]= 3000
```

#### 3. 手动发送数据包触发get_quantum()（可选）

如果需要手动触发，使用scapy：

```python
from scapy.all import sendp, Ether, IP, TCP

# 触发队列0的get_quantum()
pkt = Ether() / IP(src="0.0.0.0", dst="10.0.0.1") / TCP()
sendp(pkt, iface='s1-eth0', verbose=False)  # 替换为实际接口名

# 触发队列1的get_quantum()
pkt = Ether() / IP(src="0.0.0.1", dst="10.0.0.1") / TCP()
sendp(pkt, iface='s1-eth0', verbose=False)

# 触发队列2的get_quantum()
pkt = Ether() / IP(src="0.0.0.2", dst="10.0.0.1") / TCP()
sendp(pkt, iface='s1-eth0', verbose=False)
```

**注意**：数据包的`srcAddr[15:0]`必须等于队列索引才能匹配`get_quantum_table`。

## 预期结果

### 成功的情况

运行脚本后，应该看到：

1. **Step 1成功**：
   ```
   Step 1: Read initial quantum values
     Step 1.1: Setting up get_quantum_table entries...
       ✓ Set get_quantum table entry for queue 0
       ✓ Set get_quantum table entry for queue 1
       ✓ Set get_quantum table entry for queue 2
     Step 1.2: Sending packets to trigger get_quantum()...
       ✓ Sent packet for queue 0 (src=0.0.0.0)
       ✓ Sent packet for queue 1 (src=0.0.0.1)
       ✓ Sent packet for queue 2 (src=0.0.0.2)
     Step 1.3: Reading quantum values from register...
       quantum_storage[0] = 40000
         ✓ Successfully read initial quantum for queue 0: 40000
       quantum_storage[1] = 10000
         ✓ Successfully read initial quantum for queue 1: 10000
       quantum_storage[2] = 2000
         ✓ Successfully read initial quantum for queue 2: 2000
     Initial quantum values: {0: 40000, 1: 10000, 2: 2000}
   ```

2. **Step 2成功**：
   ```
   Step 2: Dynamically modify quantums via P4Runtime
     ✓ Set quantum for queue 0 to 50000 (reset_quota=True)
     ✓ Set quantum for queue 1 to 15000 (reset_quota=True)
     ✓ Set quantum for queue 2 to 3000 (reset_quota=True)
   ```

3. **Step 3成功**：
   ```
   Step 3: Read updated quantum values
     Reading quantum values from register:
       quantum_storage[0] = 50000
       quantum_storage[1] = 15000
       quantum_storage[2] = 3000
   ```

### 验证方法

#### 方法1：使用simple_switch_CLI验证（最可靠）

```bash
simple_switch_CLI --thrift-port 9090
> register_read quantum_storage 0
quantum_storage[0]= 50000
> register_read quantum_storage 1
quantum_storage[1]= 15000
> register_read quantum_storage 2
quantum_storage[2]= 3000
```

#### 方法2：检查交换机日志

```bash
tail -f /tmp/p4s.s1.log | grep -i quantum
```

应该看到`set_quantum()`和`get_quantum()`的调用记录。

#### 方法3：验证set_quantum生效（通过流量测试）

- 发送流量测试，观察带宽分配是否反映新的权重比例
- 例如：如果队列0的权重从40000改为50000，其带宽占比应该增加
- 这需要实际的流量测试，不在本测试脚本范围内

#### 方法4：使用脚本的printRegister函数

```python
# 在脚本中或交互式Python中
printRegister(p4info_helper, sw, "quantum_storage", 0)
printRegister(p4info_helper, sw, "quantum_storage", 1)
printRegister(p4info_helper, sw, "quantum_storage", 2)
```

## 常见问题

### Q1: 连接失败

**错误**：
```
✗ 连接交换机失败: [Errno 111] Connection refused
```

**解决方案**：
1. 确保交换机正在运行：`ps aux | grep simple_switch`
2. 检查gRPC端口是否正确：`netstat -tlnp | grep 50051`
3. 确认防火墙没有阻止连接

### Q2: P4Info文件未找到

**错误**：
```
✗ P4Info文件不存在: ...
```

**解决方案**：
1. 确保P4程序已编译
2. 使用`--p4info`参数指定正确的路径
3. 检查文件路径是否正确

### Q3: get_quantum()无法读取

**问题**：register中的值始终为0或None

**可能原因**：
1. `get_quantum()`还没有被数据包触发
2. 数据包的`srcAddr[15:0]`不等于队列索引，没有匹配`get_quantum_table`
3. `get_quantum_table`表项未正确设置
4. 网络接口不正确，数据包没有到达交换机

**解决方案**：
1. **确保已发送数据包**：
   ```bash
   # 使用脚本自动发送（推荐）
   python3 test_quantum_p4runtime.py
   
   # 或手动发送
   from scapy.all import sendp, Ether, IP, TCP
   pkt = Ether() / IP(src="0.0.0.0", dst="10.0.0.1") / TCP()
   sendp(pkt, iface='s1-eth0', verbose=False)
   ```

2. **验证表项设置**：
   ```bash
   simple_switch_CLI --thrift-port 9090
   > table_dump get_quantum_table
   ```

3. **检查交换机日志**：
   ```bash
   # 查看交换机日志，确认action是否被执行
   tail -f /tmp/p4s.s1.log | grep -i quantum
   ```

4. **使用simple_switch_CLI验证**：
   ```bash
   simple_switch_CLI --thrift-port 9090
   > register_read quantum_storage 0
   ```
   如果值为0，说明`get_quantum()`还没有被触发。

### Q4: set_quantum()不生效

**问题**：修改quantum后，带宽分配没有变化

**解决方案**：
1. 检查交换机日志确认`set_quantum()`是否被调用
2. 确保`reset_quota=True`以立即重置配额
3. 等待几个调度周期让新权重生效
4. 验证WRR.so是否包含最新的`set_quantum()`实现

## 技术细节

### P4程序修改

1. **Extern声明**：添加`set_quantum()`和`get_quantum()`方法
2. **Register**：添加`quantum_storage` register存储读取的值
3. **表**：添加`set_quantum_table`和`get_quantum_table`表

### 数据包格式

触发`get_quantum()`或`set_quantum()`的数据包：
- `hdr.ipv4.srcAddr[15:0]` = 队列索引（0, 1, 2, ...）
- 其他字段可以是任意值
- 注意：这些表在正常数据包处理流程中也会被调用，但只有匹配的表项才会执行action（默认是NoAction，不影响正常数据包）

### Register读取

`quantum_storage` register：
- 大小：3个元素（对应3个队列）
- 类型：`bit<48>`
- 索引：0-2对应队列0-2

## 下一步

1. **集成到控制平面**：将quantum调整功能集成到您的控制平面代码中
2. **添加错误处理**：实现重试逻辑和错误处理
3. **性能优化**：考虑批量更新多个队列
4. **状态持久化**：实现quantum值的保存和恢复机制

---

**文档版本**：1.0  
**最后更新**：2024年

# 项目迁移与设置指南

本文档说明如何将此项目迁移到另一台电脑并正确配置运行环境。

---

## 目录

1. [系统要求](#系统要求)
2. [文件结构说明](#文件结构说明)
3. [依赖安装](#依赖安装)
4. [项目配置](#项目配置)
5. [编译与运行](#编译与运行)
6. [验证安装](#验证安装)
7. [常见问题](#常见问题)

---

## 系统要求

### 操作系统

- **推荐**：Ubuntu 16.04 或更高版本（已在 Ubuntu 16.04 上测试）
- **替代方案**：使用提供的 VM（基于 Vagrant）

### 必需软件

1. **Mininet**
2. **P4c** (P4 编译器)
3. **BMv2** (Behavioral Model v2)
4. **P4Runtime**
5. **Python 3** 及相关包

---

## 文件结构说明

### 核心目录

```
VM-DR-PIFO/
├── P4_simulation/              # 主项目目录
│   ├── program/
│   │   └── qos/               # P4 程序和配置文件
│   │       ├── qos.p4         # P4 程序（主文件）
│   │       ├── topology.json  # 网络拓扑配置
│   │       └── outputs/       # 运行结果输出目录
│   ├── utils/                 # 工具脚本
│   │   ├── user_externs_WRR/ # WRR 调度器实现
│   │   │   ├── WRR.h         # WRR 调度器头文件
│   │   │   ├── WRR.cpp       # WRR 调度器实现
│   │   │   └── recompile_all.sh  # 编译脚本
│   │   ├── run_sim_enhanced.py    # 增强版运行脚本
│   │   ├── measure_bandwidth_allocation.py  # 带宽分析脚本
│   │   ├── plot_latency_cdf.ipynb  # 延迟 CDF 绘图 notebook
│   │   └── WRR_DEBUG_COMPLETE_GUIDE.md  # 完整调试指南
│   └── vm/                    # VM 配置（可选）
├── behavioral-model/          # BMv2 源码（需要单独下载）
└── README.md                  # 项目说明
```

### 关键文件

| 文件 | 说明 |
|------|------|
| `P4_simulation/program/qos/qos.p4` | P4 主程序文件 |
| `P4_simulation/utils/user_externs_WRR/WRR.h` | WRR 调度器实现 |
| `P4_simulation/utils/user_externs_WRR/recompile_all.sh` | WRR 编译脚本 |
| `P4_simulation/utils/run_sim_enhanced.py` | 仿真运行脚本 |
| `P4_simulation/utils/measure_bandwidth_allocation.py` | 带宽分析工具 |

---

## 依赖安装

### 方法 1：使用提供的 VM（推荐）

使用 Vagrant 创建 VM，自动安装所有依赖：

```bash
cd P4_simulation/vm
vagrant up
vagrant ssh
```

VM 会自动安装：
- Mininet
- P4c
- BMv2
- P4Runtime
- 所有必需的依赖包

### 方法 2：手动安装（Ubuntu 16.04+）

#### 1. 系统依赖

```bash
sudo apt-get update
sudo apt-get install -y automake cmake libgmp-dev \
    libpcap-dev libboost-dev libboost-test-dev \
    libboost-program-options-dev libboost-system-dev \
    libboost-filesystem-dev libboost-thread-dev \
    libevent-dev libtool flex bison pkg-config g++ \
    libssl-dev python3 python3-pip
```

#### 2. 安装 Thrift

```bash
# 下载 thrift 0.11.0 或更高版本
wget https://github.com/apache/thrift/archive/v0.11.0.tar.gz
tar -xzf v0.11.0.tar.gz
cd thrift-0.11.0
./bootstrap.sh
./configure
make
sudo make install
sudo ldconfig
cd ..
```

#### 3. 安装 nanomsg

```bash
git clone https://github.com/nanomsg/nanomsg.git
cd nanomsg
git checkout 1.0.0
cmake .
cmake --build .
sudo cmake --build . --target install
sudo ldconfig
cd ..
```

#### 4. 安装 BMv2

```bash
git clone https://github.com/p4lang/behavioral-model.git
cd behavioral-model
git checkout b447ac4c0cfd83e5e72a3cc6120251c1e91128ab

# 安装 BMv2 依赖
./install_deps.sh

# 编译和安装
./autogen.sh
./configure --enable-debugger --with-pi
make
sudo make install
sudo ldconfig
cd ..
```

#### 5. 安装 P4c

```bash
git clone --recursive https://github.com/p4lang/p4c.git
cd p4c
git checkout 69e132d0d663e3408d740aaf8ed534ecefc88810
mkdir build
cd build
cmake ..
make
sudo make install
cd ../..
```

#### 6. 安装 PI (P4Runtime)

```bash
git clone https://github.com/p4lang/PI.git
cd PI
git checkout 41358da0ff32c94fa13179b9cee0ab597c9ccbcc
git submodule update --init --recursive
./autogen.sh
./configure --with-proto
make
sudo make install
sudo ldconfig
cd ..
```

#### 7. Python 包

```bash
sudo pip3 install scapy numpy matplotlib jupyter ipython
sudo pip3 install nnpy grpcio protobuf
```

---

## 项目配置

### 1. 配置 BMv2 simple_switch

**重要**：需要将 WRR 调度器文件复制到 BMv2 目录。

```bash
# 假设 behavioral-model 在 ~/behavioral-model
cp P4_simulation/BMv2\ files/TM_buffer_WRR.h \
   ~/behavioral-model/targets/simple_switch/TM_buffer_WRR.h

# 编辑 simple_switch.cpp，包含 WRR 头文件
cd ~/behavioral-model/targets/simple_switch
# 在 simple_switch.cpp 第 42-45 行，取消注释或添加：
# #include "TM_buffer_WRR.h"
```

### 2. 编译 WRR 调度器

```bash
cd P4_simulation/utils/user_externs_WRR
chmod +x recompile_all.sh
./recompile_all.sh
```

**注意**：`recompile_all.sh` 会：
- 编译 WRR 调度器
- 安装到系统（可能需要 sudo）
- 更新库路径

### 3. 配置 Python 路径

编辑 `P4_simulation/utils/p4runtime_switch.py`，确保包含 WRR 路径：

```python
# 在 p4runtime_switch.py 中，确保包含：
sys.path.insert(0, '/path/to/P4_simulation/utils')
sys.path.insert(0, '/path/to/P4_simulation/utils/user_externs_WRR')
```

或者设置环境变量：

```bash
export PYTHONPATH=/path/to/P4_simulation/utils:/path/to/P4_simulation/utils/p4runtime_lib:$PYTHONPATH
```

### 4. 配置 P4 程序

确保 `P4_simulation/program/qos/qos.p4` 正确配置了 WRR extern：

```p4
// 确保包含 WRR extern
extern hier_scheduler {
    void my_scheduler(...);
}
```

---

## 编译与运行

### 1. 编译 P4 程序

```bash
cd P4_simulation/program/qos
make clean
make
```

这会生成：
- `build/qos.json` - P4 编译后的 JSON 文件

### 2. 运行仿真

#### 使用增强版脚本（推荐）

```bash
cd P4_simulation/utils
sudo python3 run_sim_enhanced.py
```

#### 使用原始脚本

```bash
cd P4_simulation/program/qos
sudo make run
```

### 3. 查看结果

运行完成后，结果在以下位置：

- **发送端日志**：`P4_simulation/program/qos/outputs/sender_h*.txt`
- **接收端日志**：`P4_simulation/program/qos/outputs/receiver_h_r*.txt`
- **交换机日志**：`P4_simulation/utils/logs/s*.log`

### 4. 分析结果

#### 带宽分配分析

```bash
cd P4_simulation/utils
python3 measure_bandwidth_allocation.py ../program/qos/outputs
```

#### 延迟 CDF 绘图

```bash
cd P4_simulation/utils
jupyter notebook plot_latency_cdf.ipynb
```

在 notebook 中：
1. 更新 `outputs_dir` 路径（如果需要）
2. 运行所有 cells
3. 查看延迟 CDF 图

---

## 验证安装

### 1. 检查依赖

```bash
# 检查 Mininet
sudo mn --version

# 检查 P4c
p4c-bm2-ss --version

# 检查 BMv2
simple_switch --help

# 检查 Python 包
python3 -c "import scapy; import numpy; import matplotlib; print('OK')"
```

### 2. 测试编译

```bash
cd P4_simulation/program/qos
make clean
make
# 应该生成 build/qos.json 且无错误
```

### 3. 测试 WRR 调度器

```bash
cd P4_simulation/utils/user_externs_WRR
ls -la WRR.so  # 应该存在
# 检查是否在系统路径中
ldconfig -p | grep WRR
```

### 4. 运行简单测试

```bash
cd P4_simulation/utils
# 运行一个短时间的仿真
sudo python3 run_sim_enhanced.py
# 检查 outputs 目录是否有结果文件
ls ../program/qos/outputs/
```

---

## 常见问题

### 问题 1：找不到 WRR.so 库

**错误**：`ImportError: cannot open shared object file: No such file or directory`

**解决**：
```bash
cd P4_simulation/utils/user_externs_WRR
./recompile_all.sh
# 或手动：
sudo ldconfig
```

### 问题 2：P4c 编译失败

**错误**：`p4c-bm2-ss: command not found`

**解决**：
1. 确认 P4c 已安装：`which p4c-bm2-ss`
2. 如果未安装，按照[依赖安装](#依赖安装)步骤安装 P4c
3. 确保 PATH 包含 P4c 目录

### 问题 3：权限错误

**错误**：`Permission denied` 或 `Operation not permitted`

**解决**：
- 大部分命令需要 `sudo` 权限
- 确保当前用户在 `sudoers` 中
- Mininet 相关命令通常需要 `sudo`

### 问题 4：Python 模块导入错误

**错误**：`ModuleNotFoundError: No module named 'xxx'`

**解决**：
```bash
# 安装缺失的 Python 包
sudo pip3 install <module_name>

# 或者检查 PYTHONPATH
export PYTHONPATH=/path/to/P4_simulation/utils:$PYTHONPATH
```

### 问题 5：BMv2 编译失败

**错误**：`undefined reference` 或链接错误

**解决**：
1. 确保所有依赖已安装（Thrift, nanomsg, PI）
2. 清理并重新编译：
   ```bash
   cd behavioral-model
   make clean
   ./autogen.sh
   ./configure --enable-debugger --with-pi
   make
   sudo make install
   sudo ldconfig
   ```

### 问题 6：网络仿真无法启动

**错误**：`Could not create namespace` 或网络相关错误

**解决**：
```bash
# 清理 Mininet 环境
sudo mn -c

# 检查是否有残留进程
sudo ps aux | grep simple_switch
sudo killall simple_switch  # 如果需要

# 重新运行
```

---

## 项目备份建议

### 需要备份的文件

1. **源代码**：
   - `P4_simulation/utils/user_externs_WRR/`（WRR 调度器）
   - `P4_simulation/program/qos/qos.p4`（P4 程序）
   - `P4_simulation/utils/*.py`（Python 脚本）

2. **配置文件**：
   - `P4_simulation/program/qos/topology.json`
   - `P4_simulation/utils/plot_latency_cdf.ipynb`

3. **文档**：
   - `P4_simulation/utils/WRR_DEBUG_COMPLETE_GUIDE.md`
   - `P4_simulation/utils/WRR_TEST_GUIDE.md`
   - `P4_simulation/utils/PLOT_LATENCY_CDF_README.md`

### 不需要备份的文件

- `P4_simulation/program/qos/outputs/`（运行时生成的结果）
- `P4_simulation/program/qos/build/`（编译生成的 JSON 文件）
- `*.pyc`、`__pycache__/`（Python 缓存文件）
- `*.so`、`*.o`（编译生成的二进制文件）

### 打包建议

```bash
# 创建项目备份
cd /path/to/repository
tar -czf VM-DR-PIFO-backup.tar.gz \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='*.so' \
    --exclude='*.o' \
    --exclude='outputs/*' \
    --exclude='build/*' \
    --exclude='logs/*' \
    VM-DR-PIFO/
```

---

## 快速开始检查清单

在新机器上设置项目时，按此清单检查：

- [ ] 系统要求满足（Ubuntu 16.04+ 或 VM）
- [ ] 所有依赖已安装（Mininet, P4c, BMv2, P4Runtime）
- [ ] WRR 调度器已编译（`recompile_all.sh`）
- [ ] BMv2 simple_switch 已配置（包含 WRR 头文件）
- [ ] P4 程序编译成功（`make`）
- [ ] Python 路径配置正确（PYTHONPATH）
- [ ] 运行测试成功（`run_sim_enhanced.py`）
- [ ] 分析工具可用（`measure_bandwidth_allocation.py`）

---

## 联系方式与参考

### 主要文档

- **完整调试指南**：`P4_simulation/utils/WRR_DEBUG_COMPLETE_GUIDE.md`
- **测试指南**：`P4_simulation/utils/WRR_TEST_GUIDE.md`
- **延迟分析指南**：`P4_simulation/utils/PLOT_LATENCY_CDF_README.md`

### 相关链接

- **BMv2**：https://github.com/p4lang/behavioral-model
- **P4c**：https://github.com/p4lang/p4c
- **Mininet**：http://mininet.org/

---

**最后更新**：基于项目完整调试过程  
**状态**：✅ 可用

# WRR调试日志问题排查指南

## 问题：日志生成了，但没有BMLOG_INFO信息

### 可能的原因

1. **WRR.so没有被正确加载**
2. **代码路径没有被执行**（enq=0且deq=0）
3. **日志级别设置问题**

## 排查步骤

### 步骤1: 验证模块是否加载

我已经在 `init()` 函数中添加了日志。如果看到以下日志，说明模块已加载：

```
========================================
WRR Module INITIALIZED successfully!
========================================
```

**如果没有看到这条日志**，说明WRR.so没有被加载。检查：
- simple_switch启动参数中的 `--load-modules` 路径是否正确
- WRR.so文件是否存在且可读
- 文件路径是否匹配（注意 `/home/vagrant/` vs 实际路径）

### 步骤2: 验证函数是否被调用

我已经在 `my_scheduler()` 和 `run_core()` 函数开始处添加了日志。

**如果看到**：
```
>>> my_scheduler CALLED: flow_id=0, enq=1, deq=0, pkt_ptr=1
>>> run_core CALLED: enq=1, deq=0
```
说明函数被调用了。

**如果没有看到**，可能原因：
- P4程序没有调用 `my_hier.my_scheduler()`
- 检查P2_WRR.p4中的调用是否正确

### 步骤3: 检查日志文件位置

确认您查看的是正确的日志文件：

```bash
# 查找所有日志文件
find . -name "*.log" -type f

# 查看simple_switch的启动命令，确认日志文件路径
ps aux | grep simple_switch

# 查看Mininet启动时显示的日志路径
# 通常在运行时会显示：*** Log file /path/to/program.log
```

### 步骤4: 验证WRR.so路径

检查simple_switch是否正确加载了WRR.so：

```bash
# 查看simple_switch进程的完整命令行
ps aux | grep simple_switch | grep -v grep

# 应该看到类似：
# --load-modules=/home/vagrant/P4_simulation/utils/user_externs_WRR/WRR.so
```

### 步骤5: 检查WRR.so是否是最新的

```bash
# 检查WRR.so的修改时间
ls -lh P4_simulation/utils/user_externs_WRR/WRR.so

# 确认WRR.so包含我们的代码（使用strings查看）
strings P4_simulation/utils/user_externs_WRR/WRR.so | grep "WRR Module INITIALIZED"
```

### 步骤6: 强制重新编译

```bash
# 完全清理并重新编译
cd P4_simulation/utils/user_externs_WRR
make clean
rm -f WRR.so
make

# 确认编译成功
ls -lh WRR.so

# 重新编译P4程序
cd ../../program/qos
make clean
make
```

### 步骤7: 使用BMLOG_ERROR测试

如果INFO级别仍然不显示，尝试使用ERROR级别（一定会显示）：

```cpp
// 在init()函数中
BMLOG_ERROR("WRR Module INITIALIZED - THIS IS AN ERROR TEST");
```

如果ERROR级别能看到，说明模块已加载，但INFO级别被过滤了。

### 步骤8: 检查simple_switch日志级别

simple_switch可能设置了日志级别过滤。检查启动参数：

```bash
# 查看simple_switch启动参数
ps aux | grep simple_switch

# 应该看到 --log-level 参数
# 如果没有，默认应该是INFO级别
```

## 快速验证方法

运行以下命令，应该能看到至少一条日志：

```bash
# 查看日志文件，搜索WRR相关
grep -i "WRR\|my_scheduler\|run_core" logs/*.log

# 或者查看所有INFO级别的日志
grep "INFO" logs/*.log | head -20
```

## 如果仍然没有日志

1. **确认使用的是正确的simple_switch**：可能系统中有多个版本
2. **检查是否有其他日志文件**：可能日志输出到了其他地方
3. **尝试直接使用BMLOG_ERROR**：确认日志系统是否工作
4. **检查编译错误**：确认WRR.so编译时没有错误

## 下一步

如果按照以上步骤仍然没有看到日志，请提供：
1. simple_switch的完整启动命令
2. 日志文件的完整路径
3. WRR.so的路径和修改时间
4. 日志文件的前几行内容（确认日志系统正常工作）


# MRI qdepth=0 调试指南

## 根因分析

MRI 教程使用**标准** BMv2 simple_switch，队列在 `egress_buffers` 中，`deq_qdepth` 正确反映队列深度。

P4_simulation 使用**修改版** simple_switch（含 TM_buffer + WRR）：
1. Ingress 后包先进入 `egress_buffers`
2. Egress 线程从 `egress_buffers` 取出包，**移入** TM_buffer（WRR 调度队列）
3. 实际排队发生在 **TM_buffer**，`egress_buffers` 很快被排空
4. 必须使用 TM_buffer 的深度设置 `deq_qdepth`，而非 `egress_buffers.size(port)`

### 关键发现：scheduler 不匹配导致 qdepth 全 0

**根因**：behavioral-model 原先使用 `TM_buffer_dr_pifo.h`（DR_PIFO 调度器），而 qos.p4 使用 `hier_scheduler`（WRR）。两者不同步：
- Ingress 调用 `my_hier.my_scheduler()` → 更新 `hier_scheduler::number_of_enqueue_packets`
- TM_buffer 使用 `DR_PIFO_scheduler` 的计数器 → 始终为 0

**修复**：将 simple_switch 切换为 `TM_buffer_WRR.h`，与 qos.p4 的 hier_scheduler 一致。

## 已实施的修复

### 1. 切换 TM_buffer 为 WRR 版本

`behavioral-model/targets/simple_switch/simple_switch.cpp` 中（项目根目录下的 behavioral-model）：
```cpp
// 原：#include "TM_buffer_dr_pifo.h"
#include "TM_buffer_WRR.h"
```

### 2. 添加 buffer_head 原子计数（更可靠）

在 `TM_buffer_WRR.h` 中：
- 新增 `static std::atomic<unsigned int> buffer_packet_count`
- push 时 `buffer_packet_count++`，pop 时 `buffer_packet_count--`
- 新增 `get_buffer_depth()` 返回当前 buffer 中包数

该计数与 scheduler 无关，直接反映 `buffer_head` 链表长度，多线程安全。

### 3. 修正 deq_qdepth 语义

`deq_qdepth` 应为**出队时刻**的队列深度。pop 后 `get_buffer_depth()` 为剩余包数，故：
```cpp
tm_depth = TM_buffer_obj.get_buffer_depth() + 1u;  // 出队时深度 = 剩余 + 当前包
```

## 部署步骤（VM 上）

### 步骤 1：确认源码路径

实际使用的是**项目根目录**下的 `behavioral-model/`（非 `P4_simulation/behavioral-model/`）。recompile_all.sh 使用 `~/behavioral-model`，若 VM 中该路径指向项目根，则修改已在本仓库的 `behavioral-model/targets/simple_switch/` 中。

**注意**：`TM_buffer_WRR.h` 中 include 路径为 `/home/vagrant/P4_simulation/utils/user_externs_WRR/WRR.h`，VM 需有该路径或修改为实际路径。

### 步骤 2：重新编译

```bash
cd ~/P4_simulation/utils/user_externs_WRR
./recompile_all.sh
```

或手动：
```bash
cd ~/behavioral-model/targets/simple_switch && make clean && make -j$(nproc)
cd ~/behavioral-model/targets/simple_switch_grpc && make clean && make -j$(nproc)
```

### 步骤 3：确认编译使用的是 WRR 版本

检查 simple_switch.cpp 的 include：
```bash
grep "TM_buffer" ~/behavioral-model/targets/simple_switch/simple_switch.cpp
# 应看到 #include "TM_buffer_WRR.h" 且 TM_buffer_dr_pifo 被注释
```

### 步骤 4：运行测试

按 `MRI_STYLE_TEST_GUIDE.md` 执行：h1 发 MRI 探测，h2 发 iperf 制造拥塞，h_r1 运行 receive.py。拥塞时 qdepth 应显示非零值。

## 若仍为 0 的进一步调试

1. **确认 TM_buffer_WRR.h 被正确 include**  
   编译时若找不到 TM_buffer_WRR.h，会报错。确认该文件在 `targets/simple_switch/` 或 include 路径中。

2. **确认 WRR.h 路径**  
   TM_buffer_WRR.h 中有 `#include </home/vagrant/P4_simulation/utils/user_externs_WRR/WRR.h>`。若 VM 用户/路径不同，需修改为实际路径。

3. **添加调试输出**（临时）  
   在 simple_switch.cpp 设置 deq_qdepth 处加：
   ```cpp
   unsigned int tm_depth = TM_buffer_obj.get_buffer_depth() + 1u;
   BMLOG_DEBUG("deq_qdepth: get_buffer_depth={}, tm_depth={}", 
               TM_buffer_obj.get_buffer_depth(), tm_depth);
   phv->get_field("queueing_metadata.deq_qdepth").set(tm_depth);
   ```
   然后 `make` 并运行，观察日志中 tm_depth 是否非零。

4. **验证写死 qdepth**  
   在 qos.p4 的 add_swtrace 中临时写死 `hdr.swtraces[0].qdepth = (qdepth_t)17`。若 receive 能收到 17，说明 P4→MRI→receive 链路正常，问题在 simple_switch 的 deq_qdepth 设置。

## 文件路径参考

- **实际使用**：`behavioral-model/targets/simple_switch/`（项目根目录下）
  - simple_switch.cpp
  - TM_buffer_WRR.h
- 备份/参考：`P4_simulation/BMv2 files/`、`P4_simulation/behavioral-model/`
- 编译脚本：`P4_simulation/utils/user_externs_WRR/recompile_all.sh`（编译 `~/behavioral-model`）

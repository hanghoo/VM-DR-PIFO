# Quantum 和 Rank 不匹配问题分析

## 问题描述

用户设置：
- `quota_each_queue = {0, 0, 0}`（初始配额）
- `quantums = {500, 500, 2000}`（每个 flow 的 quantum 值）
- **结果**：只有 flow3（flow_id=2）能够成功发送包

## 根本原因分析

### 1. Dequeue 逻辑回顾

```cpp
// First Round: 检查当前 quota
for (int i = 0; i<3 ;i++) {
    bool quota_check = quota_each_queue[i] >= packet_rank;
    if(quota_check) {
        // 可以出队
        break;
    }
}

// Second Round: 重置 quota 并检查
if(dequeued_done_right == false) {
    for (int i = 0; i<3 ;i++) {
        if(current_quota < quantums[i]) {
            quota_each_queue[i] = quantums[i];  // 重置到 quantum
        }
        bool quota_check = quota_each_queue[i] >= packet_rank;
        if(quota_check) {
            // 可以出队
        }
    }
}
```

### 2. 关键问题：`quantum < packet_rank`

**如果 `packet_rank > quantum`，那么即使重置了 quota，也无法出队！**

#### 场景分析

假设所有包的 `packet_rank = 600`：

**第一次 dequeue 调用**：
1. First Round:
   - Flow 0: quota (0) >= rank (600)? ❌ **失败**
   - Flow 1: quota (0) >= rank (600)? ❌ **失败**
   - Flow 2: quota (0) >= rank (600)? ❌ **失败**
2. Second Round:
   - Flow 0: 重置 quota = 500, 检查 500 >= 600? ❌ **失败**
   - Flow 1: 重置 quota = 500, 检查 500 >= 600? ❌ **失败**
   - Flow 2: 重置 quota = 2000, 检查 2000 >= 600? ✅ **成功！**

**结果**：只有 Flow 2 能够出队！

### 3. 为什么只有 Flow 2 能成功？

- **Flow 0**: quantum = 500 < rank (600) → **无法出队**
- **Flow 1**: quantum = 500 < rank (600) → **无法出队**
- **Flow 2**: quantum = 2000 >= rank (600) → **可以出队**

## 解决方案

### 方案 1：调整 quantums 值（推荐）

**确保所有 flow 的 `quantum >= packet_rank`**

```cpp
// 如果 packet_rank = 600
std::vector<unsigned int> quantums = {600, 600, 2000};  // 或者更大
```

**或者**：

```cpp
// 如果 packet_rank = 500
std::vector<unsigned int> quantums = {500, 500, 2000};  // 可以工作
```

### 方案 2：调整 packet_rank 值

**确保所有包的 `packet_rank <= min(quantums)`**

```cpp
// 如果 quantums = {500, 500, 2000}
// 确保所有包的 rank <= 500
```

### 方案 3：修改 dequeue 逻辑（不推荐）

修改逻辑允许 `quota < rank` 时也能出队，但这会破坏 WRR 的公平性。

## 验证步骤

### 1. 检查 packet_rank 的值

查看日志或代码，确认实际使用的 `packet_rank` 值：

```bash
# 在日志中搜索 rank 值
grep "rank=" your_log_file.log
```

### 2. 检查 quantums 设置

确认 `WRR.cpp` 或 `TM_buffer_WRR.h` 中的 quantums 值：

```cpp
std::vector<unsigned int> bm::hier_scheduler::quantums = {500, 500, 2000};
```

### 3. 确保 `quantum >= rank`

**规则**：对于每个 flow i，必须满足 `quantums[i] >= packet_rank`

## 当前配置分析

### 用户配置
- `quantums = {500, 500, 2000}`
- `quota_each_queue = {0, 0, 0}`

### 可能的情况

#### 情况 1：`packet_rank = 600`
- Flow 0: 500 < 600 → ❌ 无法出队
- Flow 1: 500 < 600 → ❌ 无法出队
- Flow 2: 2000 >= 600 → ✅ 可以出队

#### 情况 2：`packet_rank = 500`
- Flow 0: 500 >= 500 → ✅ 可以出队
- Flow 1: 500 >= 500 → ✅ 可以出队
- Flow 2: 2000 >= 500 → ✅ 可以出队

**如果只有 Flow 2 能出队，说明 `packet_rank > 500`**

## 建议的修复

### 选项 A：增加 Flow 0 和 Flow 1 的 quantum

```cpp
std::vector<unsigned int> bm::hier_scheduler::quantums = {2000, 2000, 2000};
```

### 选项 B：根据实际 rank 值调整

如果 `packet_rank = 600`：
```cpp
std::vector<unsigned int> bm::hier_scheduler::quantums = {600, 600, 2000};
```

如果 `packet_rank = 1000`：
```cpp
std::vector<unsigned int> bm::hier_scheduler::quantums = {1000, 1000, 2000};
```

## 总结

**问题根源**：`quantum < packet_rank` 导致某些 flow 无法出队

**解决方法**：确保所有 flow 的 `quantum >= packet_rank`

**验证方法**：检查实际的 `packet_rank` 值，然后调整 `quantums` 使其满足条件


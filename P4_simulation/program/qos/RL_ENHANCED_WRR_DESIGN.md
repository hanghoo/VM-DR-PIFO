# RL-enhanced WRR 设计总结

> 本文档总结自 Agent Q-learning enhanced WRR bandwidth allocation 对话中的设计方案与实现要点。

---

## 一、目标与现有基础

### 1.1 目标

通过 Q-learning 增强 rotating WRR，实现**自适应 EF quantum 调整**，在负载变化时自动优化 EF 延迟与 AF 吞吐。

### 1.2 可直接复用的基础设施

| 组件 | 说明 |
|------|------|
| **WRR 动态权重接口** | `set_quantum(queue_idx, quantum_value, reset_quota)` 已通过 P4Runtime 暴露 |
| **遥测数据** | `qos.p4` 已有 MRI，`switch_t` 包含 `qdepth`、`flow1_qdepth`、`flow2_qdepth`、`latency` |
| **遥测接收** | `telemetry_receiver.py` 可解析 MRI 并计算延迟 |
| **拓扑** | h1/h2 为发送端，h_r1/h_r2 为接收端，s1/s2 为交换机 |

---

## 二、状态空间设计

### 2.1 状态维度

| 维度 | 含义 | 离散化 |
|------|------|--------|
| `qdepth` | EF 队列深度（用于 Q-learning 主状态） | [0, 10]，参考 QCMP |
| `weight_ratio` | EF/(AF+EF) 比例 | 5 个 bin |
| `q_af` | AF 队列深度 | [0, 10] |
| `q_ef` | EF 队列深度 | [0, 10] |

### 2.2 状态编码

- 状态索引：`state_idx = qdepth_disc * n_ratio_bins + ratio_disc`
- 总状态数：`(NQ + 1) * n_ratio_bins = 11 * 5 = 55`
- 队列深度范围 [0, 10] 参考 QCMP 设计

---

## 三、动作空间设计

### 3.1 简化设计（当前实现）

- **仅调整 EF quantum**，AF 固定为 6000
- **离散动作**：3 个
  - `decrease`：EF -= Δ
  - `hold`：保持不变
  - `increase`：EF += Δ
- **步长**：Δ = 1500（与 rank 值一致）
- **EF 范围**：[3000, 30000]

### 3.2 动作到 quantum 映射

```
action 0 → decrease → EF -= 1500
action 1 → hold     → EF 不变
action 2 → increase → EF += 1500
```

---

## 四、奖励函数设计

### 4.1 公式（按设计图实现）

```
r_t = r'_t - w_e(t)
```

其中：

- **r'_t**（延迟相关）：
  ```
  r'_t = ε_ub · λ    若 d_t ≤ d_ub
  r'_t = -(1-ε_ub)·λ 若 d_t > d_ub
  ```
- **w_e(t)**（EF 权重成本）：
  ```
  w_e(t) = EF_quantum / EF_QUANTUM_MAX = EF_quantum / 30000
  ```

### 4.2 目标函数

```
J = λ · (P(d ≤ d_ub) - (1 - ε_ub)) - E[w_e]
```

- 最大化满足延迟约束的概率
- 最小化 EF 权重占用（避免过度偏向 EF）

### 4.3 参数

| 参数 | 默认值 | 含义 |
|------|--------|------|
| `d_ub` | 50 ms | 延迟上限 |
| `eps_ub` | 0.05 | 违反概率 |
| `λ` | 1.0 | QoS 与权重的权衡 |

---

## 五、闭环控制流程

```
遥测收集 → 状态提取 → Q-learning 决策 → 奖励计算 → Q 表更新 → P4Runtime 下发
```

### 5.1 数据流

1. **h3**：`telemetry_sender.py` 周期性发送 MRI 探测包到 c1
2. **c1**：`telemetry_receiver.py` 解析 MRI，写入 `qos_qlearning_state.txt`（格式：`q_ef,q_af,latency_ms`）
3. **宿主机**：`qos_runtime.py` 读取 state 文件 → Q-learning 决策 → P4Runtime 下发 EF quantum

### 5.2 Q-learning 更新规则

```
Q(s,a) += α · (r + γ · max_a' Q(s',a') - Q(s,a))
```

- **ε-greedy**：探索率 ε 随训练衰减（如 0.4 → 0.1）
- **衰减**：每 20 步 `decay_epsilon(factor=0.95)`

---

## 六、拓扑与路由

### 6.1 拓扑扩展

| 节点 | 角色 | IP | 连接 |
|------|------|-----|------|
| h3 | 遥测发送端 | 10.0.1.4 | s1-p3 |
| c1 | 遥测接收端 | 10.0.2.3 | s1-p5 |

### 6.2 路由（s1-runtime.json）

- 10.0.2.3 → port 5（c1）
- 10.0.1.4 → port 3（h3）

### 6.3 重要配置

- **lookup_flow_id**：需为 h3 (10.0.1.4) 添加表项，否则遥测包会被 `in_flow_id == 0` 丢弃

---

## 七、代码结构

```
P4_simulation/program/qos/
├── qlearning_controller.py   # Q-learning 主逻辑
├── telemetry_receiver.py    # c1 遥测接收，解析 MRI，写 state 文件
├── telemetry_sender.py      # h3 遥测发送，周期性 MRI 探测
├── qos_runtime.py           # 闭环主程序：读遥测 → Q-learning → P4Runtime
├── qos_qlearning_state.txt  # 遥测状态文件（q_ef,q_af,latency_ms）
└── logs/
    └── qlearning_decisions.csv  # 决策日志
```

---

## 八、关键参数

### 8.1 Q-learning 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| α | 0.2 | 学习率 |
| γ | 0.9 | 折扣因子 |
| ε | 0.4 | 探索率（建议可降至 0.1–0.2 提高稳定性） |
| 控制周期 | 0.5 s | `--interval` 可调 |

### 8.2 常量

| 常量 | 值 |
|------|-----|
| AF_QUANTUM_FIXED | 6000 |
| EF_QUANTUM_MIN | 3000 |
| EF_QUANTUM_MAX | 30000 |
| DELTA | 1500 |
| NQ | 10 |

---

## 九、实现要点与调试

### 9.1 flow1_qdepth / flow2_qdepth

- 需在 P4 ingress 中从 WRR extern 获取每队列深度并写入 `meta.flow1_qdepth`、`meta.flow2_qdepth`
- 若未正确填充，state 中 q_ef、q_af 可能为 0，Q-learning 主要依赖 latency 决策

### 9.2 遥测路径

- 当前：h3 → s1 → c1
- 可扩展：h3 → s1 → s2 → s1 → c1，采集多跳信息

### 9.3 端口约定

| 端口 | 用途 |
|------|------|
| 4321 | 遥测（h3 → c1） |
| 4322 | 数据（h1→h_r1，h2→h_r2） |

### 9.4 run_exercise 主机判断

- 需支持以 `c` 开头的节点（如 c1）作为主机，否则 `parse_switch_node("c1")` 会失败

---

## 十、验证与后续优化

### 10.1 端到端闭环验证

1. 启动 Mininet（含 h1/h2 流量）
2. 启动 c1 遥测接收、h3 遥测发送
3. 启动宿主机 `qos_runtime.py`
4. 观察 EF quantum 是否随 (q_ef, q_af, latency) 持续调整

### 10.2 对比实验

- **Baseline**：静态 WRR（EF=6000, AF=6000）
- **RL-enhanced**：Q-learning 动态调整 EF quantum
- **指标**：EF 延迟、AF 吞吐、EF quantum 变化轨迹

### 10.3 可选增强

- 状态平滑（滑动平均/指数平滑）
- Q 表持久化
- 多跳遥测
- 奖励函数平滑（避免 d_ub 附近阶跃）

---

## 十一、参考

- 对话来源：Agent Q-learning enhanced WRR bandwidth allocation
- 相关文件：`QLEARNING_README.md`、`QLEARNING_TASKS.md`

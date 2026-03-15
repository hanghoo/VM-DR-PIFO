# Q-learning 增强 WRR 快速入门

## 概述

本实现将 Q-learning 与 rotating WRR 集成，实现自适应 EF quantum 调整。

- **状态**: [qdepth, weight_ratio]，qdepth 范围 [0, 10]（QCMP 风格）
- **动作**: 仅调整 EF quantum，Δ=1500，范围 [3000, 30000]
- **AF quantum**: 固定 6000
- **奖励**: r_t = r'_t - w_e(t)，其中 r'_t 由延迟与 d_ub 关系决定

## 拓扑

- h1 (AF) → h_r1
- h2 (EF) → h_r2
- h3: 遥测发送端
- c1: 遥测接收端（控制器侧）

遥测路径: h3 → s1 → c1（当前简化版，仅经 s1）

## 运行步骤

### 1. 启用 Q-learning 模式

编辑 `P4_simulation/utils/run_sim_enhanced.py`：

```python
QLEARNING_MODE = True
```

并取消 `run_exercise.py` 中 `sending_function(self)` 的注释。

### 2. 启动 Mininet

```bash
cd P4_simulation/utils
sudo python3 run_exercise.py -t ../program/qos/topology.json -j ../program/qos/build/qos.json -b simple_switch_grpc
```

### 3. 在另一终端启动 Q-learning 控制器

```bash
cd P4_simulation/program/qos
python3 qos_runtime.py --grpc-port 50051
```

### 4. 手动启动遥测（若 QLEARNING_MODE 未自动启动）

在 Mininet CLI 中：

```
xterm c1
# 在 c1 中:
./telemetry_receiver.py --state-file=./qos_qlearning_state.txt

xterm h3
# 在 h3 中:
./telemetry_sender.py --des 10.0.2.3 -r 2 -d 120
```

## 参数说明

- `--d-ub`: 延迟上限 (ms)，默认 50
- `--eps-ub`: 违反概率，默认 0.05
- `--lambda`: QoS 与权重的权衡，默认 1.0
- `--interval`: 控制周期 (s)，默认 0.5

## 注意事项

1. **flow1_qdepth / flow2_qdepth**: 若 P4 中 meta 未正确填充，可能为 0，需后续在 ingress 中从 WRR extern 获取并写入。
2. **遥测路径**: 当前为 h3→s1→c1，后续可扩展为 h3→s1→s2→s1→c1 以采集多跳信息。
3. **队列深度**: 参考 QCMP，范围 [0, 10]。

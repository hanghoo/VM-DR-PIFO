# RL-enhanced WRR 任务清单（可执行步骤）

按顺序完成每个任务，完成后将结果反馈，再继续下一任务。

---

## 任务 1：端到端闭环验证

**目标**：确认 h1/h2 流量 + h3 遥测 + c1 接收 + qos_runtime 控制器能同时运行并形成闭环。

**步骤**：

1. 修改配置：
   - 编辑 `P4_simulation/utils/run_sim_enhanced.py`，确认 `QLEARNING_MODE = True`
   - 编辑 `P4_simulation/utils/run_exercise.py`，找到 `# sending_function(self)`，去掉注释改为 `sending_function(self)`

2. 启动 Mininet：
   ```bash
   cd ~/P4_simulation/program/qos
   make run
   ```

3. 等待 Mininet CLI 出现。配置正确时，h1/h2 流量、h_r1/h_r2 接收、h3 遥测发送、c1 遥测接收会自动在后台启动。

4. 在 **宿主机** 新开一个终端，执行：
   ```bash
   cd ~/P4_simulation/program/qos
   python3 qos_runtime.py --grpc-port 50051
   ```

5. 保持运行约 30 秒，观察 **qos_runtime** 输出是否出现类似：
   ```
   [n] q_ef=X lat=YY.Yms -> increase/decrease/hold -> EF=ZZZZ r=...
   ```

**成功标准**：
- qos_runtime 持续输出决策
- `qos_qlearning_state.txt` 内容在更新（非 0,0,0.0）
- EF 值在 3000–30000 之间变化

**若自动启动失败，手动执行**（在 Mininet CLI 中依次 `xterm <主机名>`，在对应 xterm 中执行）：

| 主机 | 命令（仅需指定有区别的参数） |
|------|------------------------------|
| h_r1 | `./receive.py --port 4322` |
| h_r2 | `./receive.py --port 4322` |
| h1 | `./send_enhanced.py --des=10.0.2.1 --flow-id=1` |
| h2 | `./send_enhanced.py --des=10.0.2.2 --flow-id=2` |
| c1 | `python3 telemetry_receiver.py --state-file=./qos_qlearning_state.txt` |
| h3 | `python3 telemetry_sender.py --des=10.0.2.3 -r 2 -d 120` |

说明：`send_enhanced.py` 已内置默认参数（--pps=100, --fast, --num-packets=100000, --duration=30, --rank-value=1500 等），h1/h2 只需指定 `--des` 和 `--flow-id`。

**请反馈**：任务 1 是否成功？若失败，请贴出 qos_runtime 输出、`qos_qlearning_state.txt` 内容，以及 Mininet 启动时的报错（如有）。

---

## 任务 2：增加 qos_runtime 日志，记录每次决策

**目标**：将每次决策写入日志文件，便于后续分析。

**步骤**：

1. 运行 qos_runtime 时，决策会自动写入 `logs/qlearning_decisions.csv`。
2. 可选：指定日志路径 `python3 qos_runtime.py --log-file=./my_log.csv`
3. 日志格式（CSV）：`timestamp,step,q_ef,q_af,latency_ms,action,EF,reward`

**成功标准**：运行后 `logs/qlearning_decisions.csv` 存在且每行对应一次决策。

---

## 任务 3：Baseline vs RL-enhanced 对比实验

**目标**：比较静态 WRR 与 RL-enhanced WRR 的 EF 延迟和 AF 吞吐。

**步骤**：执行本任务前，请先完成任务 2。收到任务 2 的反馈后，我会提供任务 3 的实验脚本和对比方法。

---

## 任务 4：参数调优

**目标**：根据任务 3 的结果调整 d_ub、λ、控制周期等参数。

**步骤**：执行本任务前，请先完成任务 3。收到任务 3 的反馈后，我会提供任务 4 的调参建议。

---

## 任务 5：可选增强（Q 表持久化、多跳遥测等）

**目标**：视需求实现 Q 表持久化、多跳遥测等增强功能。

**步骤**：执行本任务前，请先完成任务 4。收到任务 4 的反馈后，我会提供任务 5 的实施方案。

---

**当前请执行：任务 2**，运行 qos_runtime 后检查 `logs/qlearning_decisions.csv`。

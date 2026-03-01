# MRI 风格测试指南

模拟 MRI 教程的双流场景：h1 发低速率 MRI 探测包，h2 发高速拥塞流，二者共享 s1→s2 瓶颈链路。

## 拓扑对应

| MRI 教程 | P4_simulation |
|----------|---------------|
| h1 → h2 (低速率 MRI 探测) | h1 → h_r1 (send.py) |
| h11 → h22 (iperf 拥塞) | h2 → h_r2 (iperf 或 send_enhanced) |
| s1→s2 瓶颈 | s1-p4→s2-p1 (bandwidth=0.1 Mbps) |

## 测试步骤

### 1. 启动 Mininet
```bash
make run
```

### 2. 打开 4 个 xterm
```bash
mininet> xterm h1 h2 h_r1 h_r2
```

### 3. 在 h_r1 上启动 MRI 接收（显示完整包结构含 qdepth）
```bash
python3 receive.py
```

### 4. 在 h_r2 上启动 iperf 服务端（UDP）
```bash
iperf -s -u
```

### 5. 在 h1 上发送低速率 MRI 探测包（约 1 pps，持续 30 秒）
```bash
python3 send.py 10.0.2.1 "P4 is cool" 30
```
或使用默认参数（目标 10.0.2.1，消息 "P4 is cool"，30 秒）：
```bash
python3 send.py
```

### 6. 在 h2 上发送高速拥塞流（iperf 15 秒）
```bash
iperf -c 10.0.2.2 -t 15 -u
```

**顺序**：先启动 h_r1 的 receive.py 和 h_r2 的 iperf -s，再启动 h1 的 send.py，最后启动 h2 的 iperf -c。

## 备选：用 send_enhanced 代替 iperf

若 iperf 不可用或效果不佳，可用 send_enhanced 制造拥塞：

在 h2 上：
```bash
python3 send_enhanced.py --des 10.0.2.2 --num-packets 50000 --fast
```

此时 h_r2 需运行 receive.py 接收（或仅作为 sink，不一定要解析）。

## 预期结果

h_r1 的 receive.py 应显示完整包结构（pkt.show2()），其中 MRI options 含 swid、qdepth 等信息，尤其在 s1（swid=1）处，因为 h1 和 h2 的流量在 s1 的 s1-p4 出口共享同一队列。

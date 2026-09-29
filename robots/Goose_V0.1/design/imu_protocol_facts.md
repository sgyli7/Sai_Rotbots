# WT901C-TTL 的标准 WIT 串口协议事实

核查日期：2026-09-28。适用对象是 [IMU 接口事实](imu_interface_facts.md) 中的 WT901C-TTL + 原厂 CH340 USB-TTL 线；不适用于 RS485 Modbus、WT901WIFI 的 WT55 帧或 JY61 三字节配置协议。本文件供后续接收器实现；没有修改源代码、配置或观测协议，没有硬件验证 200Hz USB。

主要依据：[官方 Standard Communication Protocol](https://wit-motion.gitbook.io/witmotion-sdk/wit-standard-protocol/wit-standard-communication-protocol)；WT901C-TTL 官方 README 所指向的 `WITMOTION/WitStandardProtocol_JY901`。本次读取其 main 为 **`e8f4e3afc02263e2ef15052dc758f45efaebe12f`**（提交时间 2024-08-29），下方源码链接固定到此提交。[WT901C-TTL README](https://drive.google.com/file/d/1AAaDOPd2sXi-5pQWUDwpS_L6-fmQwuTc/view)、[源码提交](https://github.com/WITMOTION/WitStandardProtocol_JY901/commit/e8f4e3afc02263e2ef15052dc758f45efaebe12f)。

## 接收帧与数值类型

传输为二进制字节。UART 使用 **8N1**；波特率必须匹配设备实际配置，WT901C 资料默认值存在 9600 / 115200 差异，不能只靠默认值。标准自动回传帧固定 **11 字节**：[Linux serial.c](https://github.com/WITMOTION/WitStandardProtocol_JY901/blob/e8f4e3afc02263e2ef15052dc758f45efaebe12f/Linux_C/normal/serial.c)、[官方 Python 解析器](https://github.com/WITMOTION/WitStandardProtocol_JY901/blob/e8f4e3afc02263e2ef15052dc758f45efaebe12f/Python/Python-WitProtocol/chs/lib/protocol_resolver/roles/wit_protocol_resolver.py)。

| 零起点字节索引 | 0 | 1 | 2–3 | 4–5 | 6–7 | 8–9 | 10 |
|---|---|---|---|---|---|---|---|
| 内容 | `0x55` | TYPE | 第 1 个低 / 高字节 | 第 2 个低 / 高字节 | 第 3 个低 / 高字节 | 第 4 个低 / 高字节 | SUM |

`SUM = sum(frame[0:10]) & 0xFF`，是八位求和，**不是 CRC8 / CRC16**。负数按二补码有符号 int16、小端序解码：先 `u = low | (high << 8)`，再 `s = u if u < 32768 else u - 65536`。版本、配置、时间毫秒等字段须按自身语义处理，不能把所有负载一概当有符号量。[官方 C 帧解析与分发](https://github.com/WITMOTION/WitStandardProtocol_JY901/blob/e8f4e3afc02263e2ef15052dc758f45efaebe12f/Linux_C/normal/wit_c_sdk.c)、[Python 有符号转换](https://github.com/WITMOTION/WitStandardProtocol_JY901/blob/e8f4e3afc02263e2ef15052dc758f45efaebe12f/Python/Python-WitProtocol/chs/lib/device_model.py)。

| TYPE | 2–3 | 4–5 | 6–7 | 8–9 | 换算 |
|---|---|---|---|---|---|
| `0x51` 加速度 | Ax，int16LE | Ay | Az | 温度 T，int16LE | 加速度 `s / 32768 × 16`，单位 g；T `s / 100`，℃ |
| `0x52` 角速度 | Wx，int16LE | Wy | Wz | Vol，**非蓝牙产品无效** | `s / 32768 × 2000`，单位 °/s；TTL 不使用 Vol |
| `0x53` Euler | Roll，int16LE | Pitch | Yaw | VERSION，uint16LE | 角度 `s / 32768 × 180`，单位 °；版本不缩放 |
| `0x59` 四元数 | Q0，int16LE | Q1 | Q2 | Q3 | 每项 `s / 32768`，无量纲；原生顺序 `(q0,q1,q2,q3)` |

这些布局由官方协议和 C / Python 分发交叉核实。Python 示例把原生 Q0–Q3 命名为 `q1`–`q4`，不能因此错移一项；其温度计算没有符号扩展，负温度实现应遵循协议 signed short 与 C 的 int16 寄存器语义。[官方协议各输出章节](https://wit-motion.gitbook.io/witmotion-sdk/wit-standard-protocol/wit-standard-communication-protocol)、[Python 解析器](https://github.com/WITMOTION/WitStandardProtocol_JY901/blob/e8f4e3afc02263e2ef15052dc758f45efaebe12f/Python/Python-WitProtocol/chs/lib/protocol_resolver/roles/wit_protocol_resolver.py)、[C 的 sReg 类型](https://github.com/WITMOTION/WitStandardProtocol_JY901/blob/e8f4e3afc02263e2ef15052dc758f45efaebe12f/Linux_C/normal/wit_c_sdk.h)。

SI 单位转换：加速度再乘工程采用的重力常数；厂商 ROS 示例用 9.8m/s²。角速度 / Euler 再乘 `π / 180`，分别得 rad/s / rad。加速度静止时含重力分量，不能直接当已去重力的平移加速度。线路公式仍使用 16g 与 2000°/s；标准文档虽然列内部自动加速度量程，官方解析器没有按该寄存器改变线路缩放。[官方 ROS 解析与 SI 换算](https://github.com/WITMOTION/WitStandardProtocol_JY901/blob/e8f4e3afc02263e2ef15052dc758f45efaebe12f/ROS/wit/wit_ros_ws/src/scripts/wit_normal_ros.py)、[WT901C 官方 FAQ](https://cdn.shopify.com/s/files/1/0601/1712/3269/files/FAQ-WT901C.pdf?v=1770278615)。

## 时间、坐标与四元数的边界

- 可选 `0x50` 时间帧：字节 2–7 依次为年（+2000）、月、日、时、分、秒；8–9 为 uint16LE 毫秒。它是单独回传的芯片日历时间，**各测量帧没有共同序号或内嵌采样时间**。没有证据说明它已与 Linux 时钟同步。[Python get_chiptime](https://github.com/WITMOTION/WitStandardProtocol_JY901/blob/e8f4e3afc02263e2ef15052dc758f45efaebe12f/Python/Python-WitProtocol/chs/lib/protocol_resolver/roles/wit_protocol_resolver.py)。
- WT901C datasheet 指明传感器正放时 X 向前、Y 向左、Z 向上，Euler 按 Z–Y–X 顺序；pitch 在 ±90° 附近有奇异性。这些是传感器原生定义，安装后到 Goose 机体轴的变换必须另行测量确认。[WT901C TTL datasheet 第 6、12 页](https://cdn.shopify.com/s/files/1/0601/1712/3269/files/WT901C_TTL_Datasheet.pdf?v=1770278616)。
- **四元数字节顺序明确，但本轮官方材料没有明确写出 Q0 是 w 还是 x、以及主动 / 被动旋转方向。** 官方 ROS 示例从 Euler 重算四元数，未解析 `0x59`，所以不能把它当作原始 Q0→w 的证据。接收层可先保留 `q_native`；映射成模型四元数前需要厂商明确说明或受控轴向旋转实测，不允许仅凭惯例猜定。[官方 quaternion 字段定义](https://wit-motion.gitbook.io/witmotion-sdk/wit-standard-protocol/wit-standard-communication-protocol)、[官方 ROS 源码](https://github.com/WITMOTION/WitStandardProtocol_JY901/blob/e8f4e3afc02263e2ef15052dc758f45efaebe12f/ROS/wit/wit_ros_ws/src/scripts/wit_normal_ros.py)。
- 标准 `AXIS6=0` 是九轴磁场融合，`=1` 是六轴积分相对航向。**磁力计融合航向不可作为可靠的整机朝向**；六轴 yaw 同样有积分累计误差。读到有效姿态帧不代表获得可靠世界航向。[WT901C 当前官方产品页](https://wit-motion.cn/proztsz/43.html)、[官方协议 AXIS6](https://wit-motion.gitbook.io/witmotion-sdk/wit-standard-protocol/wit-standard-communication-protocol)。

## 配置写入、读回和频率

写指令固定五字节 `FF AA ADDR VALUE_LO VALUE_HI`，**无帧末校验字节**；必须发送二进制而不是字符串。官方规定先解锁 `FF AA 69 88 B5`（KEY=0xB588），写配置，再保存 `FF AA 00 00 00`；命令窗口约 10 秒后自动锁定。SDK 文档建议多次写之间通常隔 50–100ms；C 示例使用 20ms，不能据此跳过具体固件的确认。[官方命令与写格式](https://wit-motion.gitbook.io/witmotion-sdk/wit-standard-protocol/wit-standard-communication-protocol)、[官方 SDK 操作间隔](https://wit-motion.gitbook.io/witmotion-sdk/wit-standard-protocol/sdk/python_sdk-quick-start)、[C 配置函数](https://github.com/WITMOTION/WitStandardProtocol_JY901/blob/e8f4e3afc02263e2ef15052dc758f45efaebe12f/Linux_C/normal/wit_c_sdk.c)。

| 寄存器 | 用途与 WT901C 相关编码 | 二进制指令示例 |
|---|---|---|
| `RSW 0x02` | 位 0 时间、1 加速度、2 角速度、3 Euler、4 磁场、9 四元数；对应掩码 0x001、0x002、0x004、0x008、0x010、0x200 | `FF AA 02 0E 00`：加速度 + 角速度 + Euler；`FF AA 02 0F 02`：时间 + 前三项 + 原生四元数，关闭磁场包 |
| `RRATE 0x03` | 0x01=0.2Hz，02=0.5，03=1，04=2，05=5，06=10，07=20，08=50，09=100，**0x0B=200Hz** | `FF AA 03 0B 00`：配置为 200Hz；0x0A 的 125Hz 在源码注明仅 WT931，不给 WT901C 使用 |
| `BAUD 0x04` | 01=4800，02=9600，03=19200，04=38400，05=57600，06=115200，07=230400 | `FF AA 04 06 00` 或 `FF AA 04 07 00`；变更时主机端也须匹配新速率，转换线支持更高速度不代表 IMU 支持 |
| `AXIS6 0x24` | 0=九轴，1=六轴；配置值应读回记录 | `FF AA 24 01 00`：六轴，仍不保证无漂移 |

编码依据是 [固定提交的 REG.h](https://github.com/WITMOTION/WitStandardProtocol_JY901/blob/e8f4e3afc02263e2ef15052dc758f45efaebe12f/Linux_C/normal/REG.h)。500 / 1000Hz 及 460800 / 921600bps 的其他型号特殊编码不可套用 WT901C。以上只是指令示例，**本轮没有向设备发送**。

`BANDWIDTH 0x1F` 和 `RRATE` 不同：官方文档的索引 0–6 对应 256、188、98、42、20、10、5Hz；同提交 C 宏却命名为 256、184、94、44、21、10、5Hz。保留此差异，按实际固件确认，不能把 200Hz 回传说成已获得 200Hz 新样本 / 姿态带宽。[官方 BANDWIDTH 表](https://wit-motion.gitbook.io/witmotion-sdk/wit-standard-protocol/wit-standard-communication-protocol)、[REG.h 带宽宏](https://github.com/WITMOTION/WitStandardProtocol_JY901/blob/e8f4e3afc02263e2ef15052dc758f45efaebe12f/Linux_C/normal/REG.h)。

读寄存器指令 `FF AA 27 START_LO START_HI`；例如 `FF AA 27 02 00` 读取 RSW 起的四个连续寄存器（RSW、RRATE、BAUD、0x05）。回复是 **`55 5F` + 四个 uint16LE 值 + SUM**，仍为 11 字节，**不含起始地址或事务编号**。后续接收器应一次只挂起一个读请求，并把回包关联到该请求的起始地址；超时后不能把迟来的回复关联到下一个请求。C 的正常协议忽略请求数量的线路表达，最多四寄存器，不能猜成 Modbus 帧。[C WitReadReg 与分发](https://github.com/WITMOTION/WitStandardProtocol_JY901/blob/e8f4e3afc02263e2ef15052dc758f45efaebe12f/Linux_C/normal/wit_c_sdk.c)。

**本地发送成功不是设备配置成功。** 保存后须在实际波特率读回 `RSW/RRATE/BAUD`、`BANDWIDTH`、`AXIS6` 与 VERSION（0x2E），记录原始值。若更改 BAUD，必须先确认新速度能收到合法帧再依该固件行为完成保存 / 读回，不假定设备有写 ACK。

## 接收器实现依据与未完成验收

下列是基于以上帧事实的工程要求，不是厂商已验证的整机能力：

1. USB read 的分块边界不是帧边界。维护跨 read 的缓冲区，找 `0x55`，不足 11 字节则继续等待；完整候选校验失败时只前移一字节重同步，合法帧消费 11 字节。载荷内的 `0x55` 是普通数据，不可截断已完整且校验有效的帧。
2. 每种帧独立更新字段、主机单调接收时间、新鲜标志与计数，保留分类型速率 / 校验失败 / 重同步 / 超时信息。不要把最近一次字典拼成“同一时刻采样”。官方 Python 在加速度、陀螺、Euler 后不触发 `onUpdate`，主要在磁场或四元数后触发；关闭这两种包时不能照搬其回调发整组数据。
3. 对字段缺失、陈旧、配置不符、无效四元数范数或未确认坐标变换应提供明确无效状态。不要补造单位四元数、默认为零角速度或假时间，使上层误认为传感器正常。
4. 8N1 下每个 11 字节帧至少 110bit。三种包 ×200Hz 为 66,000bit/s；时间 + 加速度 + 角速度 + 四元数四种包为 88,000；再加 Euler 五种包为 **110,000bit/s**。后者占 115200 的约 95.5%，230400 更有线路余量。这些是算式，不是 USB 吞吐、丢包或延迟实测。
5. 后续硬件验收应闭合字段有效刷新率、重复样本、端到端延迟、芯片 / 主机时间映射、三轴符号与量纲、四元数语义、重插后的设备绑定，以及伺服 / 音频通电后的漂移。该验收完成前不能宣称可稳定 200Hz 控制，也不能把磁场 yaw 用作可靠整机朝向。

以下是本轮人工构造、已复算校验和的解析样例，**不是硬件采样证据**：

| 完整 11 字节（十六进制） | 解码预期 |
|---|---|
| `55 51 00 00 00 00 00 08 C4 09 7B` | 加速度 (0,0,1)g；温度 25℃ |
| `55 52 00 20 00 C0 00 00 00 00 87` | 角速度 (500,-1000,0)°/s；末两字节忽略 |
| `55 53 00 40 00 E0 00 00 D2 04 9E` | Euler (90,-45,0)°；VERSION=1234 |
| `55 59 FF 7F 00 00 00 00 00 00 2C` | 原生四元数 (32767/32768,0,0,0)；未确认语义前不命名“单位姿态” |

本轮事实已足以实现可靠的字节解析与配置读回。原生四元数到工程旋转定义的映射仍是明确缺口；可以实现原生接收与诊断，不能以未经确认的映射放行姿态闭环。

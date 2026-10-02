# Goose IMU 的 USB 接口与型号事实

核查日期：2026-09-28。范围：一手型号、采购接口、机械包络与 Linux 开发依据；不决定最终 IMU、不修改 BOM、模型或观测协议。输入条件来自当前方案：相机与两 U2D2 占四口 USB hub 的三个口，余一口可用于 IMU。

## 型号与可采购证据

**本轮未找到 `WT901CUSB` / `WT901C-USB` 的明确官方独立 SKU，不能按这个名称放行采购。** 官方中英目录中的真实系列为 `WT901C`，英文目录标 TTL / RS232 / RS485。官方购买页链接到下列官方店，中文官网链接到维特智能天猫店；仅证明厂商采购渠道存在，未取得中国本地库存、人民币含税价或交期承诺。[英文目录](https://wit-motion.com/product.html)、[中文目录](https://wit-motion.cn/product.html)、[厂商购买页](https://wit-motion.com/purchase.html)、[中文官网购买入口](https://weitezhineng.tmall.com/)。

| 明确型号 / 套装 | 厂商官方店 SKU 与读取时状态 | USB 接入事实 |
|---|---|---|
| WT901C-TTL | `A.002533`；官方商品 JSON `available=true`，标价 US$23.90 | 传感器本身为 UART TTL，需转换器，不能直接插 USB |
| WT901CTTL+TTLcable | `A.002533-A.000057`；`available=true`，US$34.90 | 官方列出的传感器与 TTL 线套装；USB 转串口路线，传感器与转换线必须分别计件 / 留包络 |
| WT901WIFI | `A.000496`；`available=true`，US$35.60，商品页划线 US$45.90 | 官方规格明确 Type-C 兼具充电与串口数据；无需外置 TTL 转换器 |

以上是美元店读取快照，不是人民币预算或到货承诺。没有创建订单。商品页标题以 WT901C-485 为默认变体，必须选择 TTL 或 TTLcable 变体，不能用整页最低价 US$7 的 Strap 配件价当传感器价。官方 JSON 中各变体 `grams=200` 未注明净重，**不得拿来计算 IMU 质量**。[WT901C 官方商品及变体](https://witmotion-sensor.com/products/mpu9250-high-precision-accelerometer-magnetometer-wt901c-for-pc-arduino-raspberry-pi)、[WT901WIFI 官方商品](https://witmotion-sensor.com/products/9-axis-wifi-accelerometer-ahrs-mpu9250-angular-velocity-acceleration-angle-magnet-android)、[本次读取的官方商品 JSON](https://witmotion-sensor.com/products.json?limit=250)。

套装里的 `A.000057` 也能单独购买：官方商品名 `[Converter Cable] USB to TTL/232/485 UART, Serial Adapter (1m/3.28ft)`，选择 `USB-TTL Cable`。官方明确 USB 2.0、CH340 驱动、Linux 兼容、300bps–1.5Mbps、VCC 5V / Tx / Rx / GND，线长 1m；未给转换器壳体尺寸、净重、输出电流或 VCC 容差。它是 USB 串口桥，不是 IMU 自带 USB。[原厂转换线商品页](https://witmotion-sensor.com/products/usb-to-ttl-232-485-uart-converter-cable-with-ch340-chip-terminated)。

## 机械、电气与输出

| 项目 | WT901C-TTL | WT901WIFI，官方 new 资料 |
|---|---|---|
| 外形与质量 | 参数表：51.3 × 36 × 15mm，各 ±0.1mm；13 ±1g。**同 PDF 壳体图却为 51.5 × 36.1 × 15mm** | 壳体图：51.5 × 36.1 × 15mm；本轮官方规格未给净重 |
| 固定接口 | 图中两个长槽，标 12、3.1、R1.5，底板厚 3mm；没有独立完整槽中心距标注 | 同类两长槽与 3mm 底板；没有完整槽中心距标注 |
| 电源 | 官方 TTL 手册写 5V，警告超过 5V 可永久损坏；接口 VCC / RX / TX / GND，TX→转换器 RX，RX→转换器 TX | Type-C 充电 5V；内置 3.7V / 260mAh 电池；200Hz 工作电流典型 80mA，充电典型 250mA；不把两者当最大 USB 电流 |
| 可输出内容 | 三轴加速度、角速度、磁场、Euler 角、时间、四元数 | 标准输出含设备 ID、芯片时间、加速度、角速度、磁场、Euler、温度、电量、信号、版本；协议另列四元数寄存器 |
| 输出速率 | 0.2–200Hz，默认 10Hz；陀螺 / 加速度带宽参数 5–256Hz | 速率表为 1–200Hz、默认 10Hz；功能文字另写 0.2–200Hz，保留这个差异 |
| 陀螺量程 | ±2000°/s | ±2000°/s |

WT901C 数据来自官方店当前链接的 datasheet v23-0627 第 6、10、11、14 页与 manual v2023-06-28 第 5、7 页；机械图已直接读图。其 `<40mA` 为概览规格，电流表却把工作电流写成 `5.7V`，不能擅自修正为 5.7mA。波特率正文 / 协议页默认 9600，而参数表默认 115200；角精度概览 0.05°，详细表与当前中文官网 0.2°。这些矛盾必须留到具体版本确认 / 上机读回，不能取较好数字作验收保证。[WT901C TTL 官方 datasheet](https://cdn.shopify.com/s/files/1/0601/1712/3269/files/WT901C_TTL_Datasheet.pdf?v=1770278616)、[WT901C TTL 官方 manual](https://cdn.shopify.com/s/files/1/0601/1712/3269/files/WT901C_TTL_Manual.pdf?v=1770278615)、[当前中文 WT901C 产品页](https://wit-motion.cn/proztsz/43.html)。

WT901WIFI 数据来自厂商产品页链接的 Product Specifications 第 7–9 页，机械页已直接读图。Type-C 接口定义是充电与串口数据，不是仅供电。其 Operation Manual v25-02-07 第 1–2 页明确 Type-C 直连电脑，但演示为 Windows COM 口；旧版设备 ID 以 `WT53` 开头，新版以 `WT55` 开头，采购时需确认实际交付版本。[WT901WIFI 官方产品页](https://www.wit-motion.com/WirelessInclinometer/79.html)、[Product Specifications](https://drive.google.com/file/d/1-55nZgm_q8X75OSHwXckGibrrFdWEByS/view)、[Operation Manual](https://drive.google.com/file/d/1PTN27Hnj6A5XSocw7Iw-IbvnQ4k18kuM/view)。

## 官方协议、SDK 与 Linux 支持边界

- **WT901C-TTL 有官方 Linux 开发依据。** 其官方文件夹 README 直接指向 `WitStandardProtocol_JY901`；仓库含 `Linux_C/normal` 和 Python 串口 SDK。Linux C 使用 POSIX termios、8N1；Python 示例有 Linux 分支 `/dev/ttyUSB0`，串口通过 pyserial 打开。结合原厂 CH340 线的 Linux 兼容声明，可以核实其 Linux USB 串口接入路线，**不等于这个套装已在 Radxa Zero 3W 上实测通过**。尚缺具体 USB VID:PID、实际驱动枚举、转换器壳体尺寸与净重。官方 Linux C 主循环还有 500ms 延时，仅是演示，不能照搬作 200Hz 控制采集。[WT901C-TTL 官方 README](https://drive.google.com/file/d/1AAaDOPd2sXi-5pQWUDwpS_L6-fmQwuTc/view)、[官方 Linux C README](https://github.com/WITMOTION/WitStandardProtocol_JY901/blob/main/Linux_C/README.md)、[Linux serial.c](https://github.com/WITMOTION/WitStandardProtocol_JY901/blob/main/Linux_C/normal/serial.c)、[Linux main.c](https://github.com/WITMOTION/WitStandardProtocol_JY901/blob/main/Linux_C/normal/main.c)、[Python JY901S 示例](https://github.com/WITMOTION/WitStandardProtocol_JY901/blob/main/Python/Python-WitProtocol/chs/JY901S.py)。
- WT901C-TTL 标准 WIT 协议为 `0x55` 开头、每包 11 字节，写指令以 `FF AA` 开头。官方解析器识别时间 `0x50`、加速度 `0x51`、角速度 `0x52`、角度 `0x53`、磁场 `0x54`、四元数 `0x59`，带校验。不同测量包依次发送，不能把 SDK 当前字典自动当作同一采样时刻的整组观测。[官方 Python SDK 文档](https://wit-motion.gitbook.io/witmotion-sdk/wit-standard-protocol/sdk/python_sdk-quick-start)、[官方解析器源码](https://github.com/WITMOTION/WitStandardProtocol_JY901/blob/main/Python/Python-WitProtocol/chs/lib/protocol_resolver/roles/wit_protocol_resolver.py)。
- **WT901WIFI 的官方 SDK 主要证明 TCP / UDP 路线。** Python `test.py` 启动 TcpService / UdpService，解析器读取以 12 字节设备 ID 开头的测量帧。new 协议 v25-02-19 第 6–10 页规定 54 字节输出帧、芯片毫秒时间、尾部 CR/LF；第 28–29 页用 RATE（0x68）定义毫秒周期，5ms 对应 200Hz。四元数有 0x26–0x29 寄存器，但不在该 54 字节普通输出帧中。本轮未找到明确的 **WT55 USB 串口 Linux 示例、USB 标识或实测波特率**；不能直接复用 11 字节 JY901 解析器作为整个 WIFI 输出解析器。[官方 WIFI SDK](https://github.com/WITMOTION/WitWIFI_WT901WIFI)、[Python test.py](https://github.com/WITMOTION/WitWIFI_WT901WIFI/blob/main/Python/901WIFI_python_sdk/test.py)、[device_model.py](https://github.com/WITMOTION/WitWIFI_WT901WIFI/blob/main/Python/901WIFI_python_sdk/device_model.py)、[官方 new 协议](https://drive.google.com/file/d/1b_MMSaEH-HZtBWI3AdXZHycX-RWfQ-Sl/view)。

## 工程推断与本轮保留的缺口

1. WT901CTTL+TTLcable 通过一个转换器占一个 USB hub 下行口，符合当前余一口的数量假设；转换线包络与 Linux 枚举尚需闭合。若坚持传感器本体集成 USB，WT901WIFI 是明确真实型号，但其 USB / Linux 高速链路还不能宣布通过。
2. **输出率、滤波带宽、有效新样本率与传输延迟是四件事。** 按 8N1 计算，WT901C 的加速度 + 角速度 + Euler 三种 11 字节包在 200Hz 至少需 `3×11×200×10 = 66,000bit/s`；9600 不够，115200 对此内容有余量，额外启用时间 / 四元数 / 磁场后需重算。WT901WIFI 的 54 字节帧在 200Hz 至少需 `108,000bit/s`；其规格表只给 UART 默认 9600，不能据此证明 USB 200Hz 成立。这些是线路预算推算，不是实测结论。
3. 9 轴融合航向依赖磁场；官方注明须校准并避开磁干扰，6 轴航向会累计漂移。WIFI 规格更要求远离电子设备、磁铁、扬声器等至少 20cm，紧凑 Goose 未证明能满足。不得把广告航向精度直接用于伺服通电后的整机状态估计保证。[WT901C 官方 FAQ](https://cdn.shopify.com/s/files/1/0601/1712/3269/files/FAQ-WT901C.pdf?v=1770278615)、[WIFI 官方规格第 4 页](https://drive.google.com/file/d/1-55nZgm_q8X75OSHwXckGibrrFdWEByS/view)。
4. 待具体型号确认后，再验证：稳定设备绑定、配置读回、实际包间隔 / 重复样本 / 丢包、延迟与时间映射、IMU 轴到机器人轴的变换、伺服与扬声器通电时漂移。当前没有修改既有 IMU + 编码器观测，也没有宣称任何候选已通过控制闭环。

需要一起对齐的实质问题只有三个：是否接受 WT901C-TTL + 原厂 USB 转换线；实际版本及 CAD 尺寸 / 转换线包络；所需观测内容与有效刷新率。余项属于选定后硬件验收，不需要在本事实报告中替用户决定架构。

# Goose 音频器件事实核查

核查日期：**2026-09-28**，中国采购语境。范围限定为 DFRobot DFR0299、Pololu 可调降压器和一个小扬声器候选；仅记录一手器件资料，不修改 BOM／接线／最终方案。其他电源与 USB 约束见 [power_bus_facts.md](power_bus_facts.md)。

## 1. DFPlayer Mini，DFRobot DFR0299

| 项目 | 官方事实 | 工程边界／缺口 |
|---|---|---|
| 电源 | 当前 [DFRobot 商品页](https://www.dfrobot.com/product-1121.html)与 [Wiki](https://wiki.dfrobot.com/dfr0299)均列 **DC 3.2–5.0 V**。[厂家发布的 datasheet V1.0，PDF 第 1–2 页](https://dfimg.dfrobot.com/wiki/20532/DFR0299_mp3-player-module_datasheet_V1.0.pdf)也列 3.2–5.0 V、typical 4.2 V、standby 20 mA。 | 以 **5.0 V** 为本轮供电上限；不使用中文旧 pin 注释“不要超过 5.2 V”扩大允许范围。20 mA 是手册待机数值，**不是播放峰值或最大电流**；缺最大音量／启动／读卡时的电流证据。 |
| 功放与扬声器 | 官方商品说明内置 **3 W mono amplifier**；SPK1／SPK2 可直接接扬声器，Wiki／手册称驱动小于 3 W 喇叭；DAC_L／DAC_R 用于耳机或外部功放。来源同上。[官方配套扬声器 FIT0502](https://www.dfrobot.com/product-1506.html)标为被动 **3 W／8 Ω**。 | 3 W 是模块宣传功放能力，未取得其对应供电电压、阻抗、THD／连续条件；**不证明 4.5 V、8 Ω 可输出 3 W**。只记录 8 Ω 官方配套负载证据；本轮未核 4 Ω 或更低阻抗允许范围。扬声器接 SPK1／SPK2，不能把其中一端按普通信号地处理。 |
| 控制与存储 | UART TTL，默认 **9600 baud**；当前官方示例用 9600／8N1；TF／MicroSD 最大 32 GB、FAT16／FAT32，预存 MP3／WAV／WMA，音量 0–30。[官方例程与接线说明](https://wiki.dfrobot.com/dfr0299/docs/20906)、[Wiki](https://wiki.dfrobot.com/dfr0299) | 播放预存文件，不自动成为 Linux USB 声卡或实时流式语音输出。Radxa UART 软件与引脚复用尚未实机验证。官方给 Arduino TX→DFPlayer RX 串 1 kΩ 的建议；这是信号调理建议，不能当作通用电平转换器证明。 |
| 尺寸与版本 | 商品正文／中英文 Wiki 写 **20 ×20 mm**；官方另提供 [dimension v1.1 图](https://dfimg.dfrobot.com/wiki/20532/DFR0299_mp3-player-module_dimension_v1.1.jpg)与 [SVG v1.0](https://dfimg.dfrobot.com/wiki/20532/DFR0299_mp3-player-module_svg_1.0.zip)。2026-09-16 商品外观更新说明仅给 TF 卡座增加 DFRobot logo，并称尺寸／功能未改。 | **尺寸差异未闭合**：项目原候选采用 24 ×22 mm，本轮文字资料无法统一到该值；SVG 是器件图形，不能当制造尺寸图。未取得可核总高、排针装配后包络、机械安装孔径／孔距与板净重；不得凭电气焊盘生成 M2 固定孔。父任务的 **28 ×26 mm 可调槽／无孔边夹**是结构预留，非厂商本体尺寸。 |
| 中国采购 | [中国官方目录 DFR0299](https://www.dfrobot.com.cn/goods-891.html)与 [中文 Wiki](https://wiki.dfrobot.com.cn/_SKU_DFR0299_DFPlayer_Mini%E6%A8%A1%E5%9D%97)确有此精确 SKU。 | 页面目录存在不等于本轮已核实际库存／交期；本报告不承诺人民币报价或到货。采购需确认原厂 SKU、到货芯片／丝印版本和 TF 卡。 |

## 2. 降压器型号纠正与 4.5 V 候选条件

**“D24V5ALV、可调 500 mA”未取得 Pololu 官方精确 SKU。**官方 D24V5Fx 是固定输出系列；旧可调 [D24V6ALV #2103](https://www.pololu.com/product/2103)标为 discontinued／Special Order Only，厂商指向当前 **D36V6ALV #3798**。本轮按父任务更新核后者，不采用相似名称补造器件。

| 项目 | D36V6ALV #3798 官方事实 |
|---|---|
| 输入／输出 | 输入 **4–50 V**；板载电位器可调 **2.5–7.5 V**，包含 4.5 V 设置。输入仍须高于目标输出至少一个随负载／输出电压变化的 **dropout voltage**，不能把“最低输入 4 V”当作能由 4 V 稳定输出 4.5 V。[厂家产品页](https://www.pololu.com/product/3798) |
| 电流与保护 | 官方列 **typical max 600 mA**；连续上限取决于输入／输出、电压、环境温度、气流与散热。连续曲线条件为室温、静止空气、无额外散热。具有过流／短路与过温关断，**无反接保护**。[产品页](https://www.pololu.com/product/3798)、[规格与脚注](https://www.pololu.com/product/3798/specs) |
| 尺寸／孔型 | 官方正文取整 **15 ×10 ×4 mm**；规格 **0.6 ×0.4 ×0.15 inch**、0.6 g、不含附送排针。机械图第 2 页精确 PCB 外缘 **15.2 ×10.2 mm**；PCB 1.02 mm、上方件高 2.7 mm；四个 **Ø1.02 mm** 电气连接孔，间距 **2.54 mm**。这些是焊线／排针孔，非螺丝安装孔。板边公差 ±0.3 mm、孔位 ±0.1 mm。[官方 PDF（2018-08-31，覆盖 #3798）](https://www.pololu.com/file/0J1571/step-down-voltage-regulator-d24v3x-d24v6x-d36v6x-dimensions.pdf) |
| 接线／调压 | VIN、GND、VOUT、SHDN；默认启用，SHDN 可悬空，拉低 <1.25 V 关断；顺时针调高输出，调完须移开螺丝刀再测量，因为接触调节器会影响读数。可焊线或附送排针。[厂家使用说明](https://www.pololu.com/product/3798) |
| 在售口径 | 厂商当前标 **Active and Preferred**，有现成 #3798 商品及 [STEP／DXF 资源](https://www.pololu.com/product/3798/resources)。 |

**项目设定与推断：**“从逻辑 5 V 降至 4.5 V、音频预算 ≤500 mA”是待验证工作点，既不是 DFPlayer 自带电流上限，也不是 Pololu 的 500 mA 硬件限流门槛。若逻辑轨为 5 V ±4%，其范围为 **4.8–5.2 V**；直接接 DFR0299 会超过其 5.0 V 上限。调到 4.5 V 提供名义电压余量，但最低输入 4.8 V 时只剩 **0.3 V dropout 余量**，本轮未证明在 500 mA、温度／启动变化下仍能稳定输出 4.5 V。**不能据可调范围直接放行这个工作点。**

`4.5 V ×0.5 A =2.25 W` 是音频轨输入预算，含解码／存储／功放损耗，不能同时承诺持续 3 W 扬声器输出。必须量测目标音量下的启动与播放电流、DFPlayer 端电压、上游逻辑电压跌落和温升；确认整个启动／稳态／卸载过程满足 **3.2–5.0 V**，并核所需 dropout。调压器机械图的裸板包络还需加排针／线头、调节工具和散热空间。

## 3. 一个精确小扬声器候选

**Same Sky（原 CUI Devices）CMS-3058-18L200**：圆形、PET 振膜、钕磁体、引线型；官方目录在正常产品列表，未标 discontinued。本轮只保留这一候选，未证明中国现货／人民币价格。

| 项目 | 已核厂商资料 |
|---|---|
| 阻抗／功率 | **8 Ω** nominal（2 kHz 下范围 6.8–9.2 Ω）；input power typical **1.5 W**、max **2.0 W**。max power 的测试条件为 IEC-60268-5 滤波信号、**60 s 开／120 s 关、10 cycles、室温**，不能改写为已验证持续 2 W。 |
| 尺寸 | 引线型机械图第 3 页：**外缘 Ø30 ±0.2 mm**、背面圈 Ø28.8 ±0.2 mm、总厚 **5.8 ±0.2 mm**；背部直径 Ø26.5 ±0.2 mm。网页表格的 28.8 mm 不是最大外缘；CAD 采用带 30 mm 外缘的包络。 |
| 引线／质量 | **200 ±10 mm** 引线、UL1571 **28 AWG**；红正／黑负，剥线 1.5 ±0.5 mm；引线型质量 **8.35 g**，不同于焊盘型 7.6 g。无螺丝固定孔图，应以环形边缘固定而非打穿振膜／磁体。 |
| 声学与结构 | 共振频率典型 **550 Hz**；厂商建议 enclosure。焊盘型机械图注明振膜前方至少 **1.0 mm** 运动空间；引线型外形也不能被压盖接触振膜。安装腔、开孔和机器人外壳的声学表现均未实测。 |
| 来源／版本 | [精确型号官方产品页](https://www2.sameskydevices.com/product/audio/speakers/miniature-%2810-mm~40-mm%29/cms-3058-18l200)、[厂家 datasheet CMS-3058-18X，rev 1.0，日期原文 06/11/2026，第 1–4 页](https://www.sameskydevices.com/product/resource/cms-3058-18x.pdf)。本轮已实际读取 PDF 并核引线型机械图，未用商品表的 28.8 mm 代替最大外缘。 |

该器件满足“8 Ω、额定 1–3 W、最大外缘 ≤36 mm”的文档条件；不是已完成整机声压、音质、跌落或热验证。DFPlayer 的“3 W amplifier”与扬声器自身 1.5 W 额定值也不能直接决定音量 0–30 中哪个值安全／清晰。

## 4. 集中保留的闭合项

- DFR0299 到货版本的实际 PCB 外形／总高、排针或焊线高度、卡槽插拔空间；目前 20×20 文字与项目 24×22 输入不统一，28×26 是可调整结构预留。
- D36V6ALV 在实际上游最低电压、4.5 V 设置及目标音量电流下的 dropout、启动过冲／跌落与热稳定；没有这组数据就不把 5 V→4.5 V／≤500 mA 称为供电已通过。
- DFR0299 最大播放／启动电流与 8 Ω 实际输出；同一份手册的旧图与表可能有引脚文字差异，最终以到货丝印和当前官方 pin map 核对。
- 中国精确 SKU 的原厂供货与扬声器到货可得性，音频文件与 Radxa UART 接入；本轮没有采购或实物测试。

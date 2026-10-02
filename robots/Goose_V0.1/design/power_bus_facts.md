# Goose 双电源总线与 USB 外设事实核查

核查日期：**2026-09-28（中国地区采购语境）**。候选为 XM430-W350-T（推荐 12 V）与 XC330-M288-T（推荐 5 V）、Radxa ZERO 3W、单眼 USB 相机及小扬声器。本记录只核器件事实与待选类别；不冻结关节数量、功率、容量、保险规格或接线，不修改 BOM。执行器原始条件见 [actuator_options_review.md](actuator_options_review.md)，旧外围器件差异见 [primary_sources_review.md](primary_sources_review.md)。

## 1. 已核结论：分轨供电不等于电气隔离

| 项目 | 官方事实 | 对候选方案的含义／推断 |
|---|---|---|
| ROBOTIS U2D2 | 现成 SKU **902-0132-000**，48 × 18 × 14.9 mm、9 g；USB 转 TTL／RS-485／UART，最高 6 Mbps；**不向 DYNAMIXEL 供电**。来源：[eManual](https://emanual.robotis.com/docs/en/parts/interface/u2d2/)、[产品页](https://robotis.us/products/u2d2)。 | USB 给适配器自身供电；舵机需另外供电。UART 的 3.3 V 功能不能作为 5 V 舵机电源。 |
| 同一 U2D2 的接口 | TTL 与 RS-485 收到相同 USB 发送数据；官方要求共享连接设备的 ID 唯一，批量／同步读取使用同类通信接口。[eManual](https://emanual.robotis.com/docs/en/parts/interface/u2d2/) | 不能把同一块的 TTL 与 RS-485 叫作两个独立 USB 串口。两种候选均为 **-T TTL**，两块 U2D2 可形成两个逻辑通信域，但这不是最终数量决策。 |
| U2D2 电气隔离 | 本轮官方资料**未声明 USB／TTL 间的电气隔离**；官方连接图含 GND 参考。[eManual](https://emanual.robotis.com/docs/en/parts/interface/u2d2/) | “12 V 和 5 V 电源正极分开、信号有参考地”与“USB 数据及电源均隔离”必须区分。两块 U2D2 本身不构成后者。 |
| U2D2 Power Hub Board Set | 现成 SKU **902-0145-001**，48 × 57 mm；输入 3.5–24 V，官方字段 **Maximum Current 10 A**；套装不含 U2D2。[eManual](https://emanual.robotis.com/docs/en/parts/interface/u2d2_power_hub/)、[产品页](https://robotis.us/products/u2d2-power-hub-board-set) | 是外部电源分配板，**不是降压／稳压／隔离器**。未取得 Goose 安装条件下 10 A 连续温升证据，也不能把 10 A 分配给每一个 JST 接口。 |
| Hub 的供电口 | 圆口 DC（外径 5.5、内径 2.5 mm、中心正极）、Molex 2P、螺丝端子为供电入口；官方明确一次只能使用一个供电输入。[eManual](https://emanual.robotis.com/docs/en/parts/interface/u2d2_power_hub/) | 同一 Hub 不能同时接 12 V 与 5 V；电池和台架电源也不能直接并接这些入口。普通板载电源开关不能直接代替经核算的急停。 |
| TTL 电缆与引脚 | U2D2、XM430、XC330 使用 X 系列 JST 3P：**1 GND、2 VDD、3 DATA**；EHR-03／B3B-EH-A；XC330 逻辑为 3.3 V 且兼容 5 V TTL。来源：[U2D2](https://emanual.robotis.com/docs/en/parts/interface/u2d2/)、[XM430](https://emanual.robotis.com/docs/en/dxl/x/xm430-w350/)、[XC330](https://emanual.robotis.com/docs/en/dxl/x/xc330-m288/)。 | 连接器外形相同不会防止误插。12 V 与 5 V 轨必须通过物理布置、标签／防误接等设计避免互连；不能整串接完再靠软件区分电压。 |

**版本核对：** U2D2 eManual 记载 2025-08 起 Micro-B 改 USB-C；当前产品页说明 USB-C，但包装表仍出现 Micro USB cable。采购需确认到货批次与实际线缆。中国 ROBOTIS 官方 [联系页](https://robotis.com/zh/contactus.php) 导向 [中国官方淘宝店](https://shop292418244.taobao.com)；这是渠道证据，本轮未取得 U2D2／Hub 精确 SKU 的中国库存、含税报价或交期。

## 2. 电源／保护候选：有 SKU 与仅类别分别列出

| 功能 | 已核器件／类别 | 原始额定口径与边界 | 中国采购证据／尚缺 |
|---|---|---|---|
| 5 V 非隔离降压 | **Pololu D24V90F5，#2866**，现成板 | 5–38 V 输入，5 V ±4%；官方主文写典型最大连续电流 **4–8 A**，取决于输入、气流和散热；不能凭标题“9 A”按 9 A 连续设计。[产品页](https://www.pololu.com/product/2866)、[规格](https://www.pololu.com/product/2866/specs) | [官方渠道页](https://www.pololu.com/distributors)列中国相关 DigiKey、TME、TinySine；本轮未核 #2866 中国现货。需在实际 3S 输入、壳内温度与导线条件下测持续输出与瞬态。 |
| 5 V 隔离 DC/DC | **DFRobot DFR0929**，现成模块 | 9–18 V 输入、5 V／0–10 A、**50 W 最大**，页面效率 83%，输入／输出隔离 1500 VDC／800 VAC；CNT 控制，短路及输入欠压保护。[中国官方产品页](https://www.dfrobot.com.cn/goods-3403.html)、[全球官方页](https://www.dfrobot.com/product-2500.html) | 中国官方商品页确有 SKU，未核到货与温度降额曲线／全负荷持续条件。**10 A 不记作已验证连续能力**。模块隔离若被 USB／TTL 接地旁路，不等于整系统隔离。 |
| 12 V 台架供电 | **MEAN WELL LRS-350-12**，现成电源 | 12 V、29 A／348 W；可调 10.2–13.8 V；115／230 VAC 档位；有风扇和温度降额曲线。常规参数条件 230 VAC、额定负载、25°C；150% 峰值仅最长 1 s，超时进入 hiccup。[官方规格 PDF（2025-09-12）](https://www.meanwell.com/Upload/PDF/LRS-350/LRS-350-SPEC.PDF) | 这是**台架类别参考**，不是移动电池转换器或最终购买建议；未核中国精确报价。电源能力大于 Hub 10 A 不会抬高 Hub／电缆能力。机壳接地、端子防触碰、安装散热要按该电源安装说明完成。 |
| 12 V 移动供电 | **3S 直供并限制可用 SOC**，或**12 V 升降压转换器**；仅类别 | 3S 锂离子名义 11.1 V、满充 12.6 V；XM430 官方允许 10–14.8 V。直供不能保证恒定 12 V，必须确保最远舵机带载端电压仍 ≥10 V。单纯降压不能在输入低于 12 V 时维持 12 V。来源：[XM430](https://emanual.robotis.com/docs/en/dxl/x/xm430-w350/)、[3S 模块资料](https://www.dfrobot.com.cn/goods-3383.html)；拓扑含义为工程推断。 | **未选具体升降压 SKU**；尚缺连续／脉冲输出、低电池输入电流、热降额、使能与电机回馈兼容证据。 |
| 3S 电池保护示例 | **DFRobot FIT0869／HX-3S-01**，现成板 | 3 串 18650／聚合物锂电保护；页面“最大瞬间电流 **9–10 A**”，50 ×16 ×1 mm。过放检测每节 2.3–3.0 V；不是 XM 的 ≥10 V 运行保证。[中国官方页](https://www.dfrobot.com.cn/goods-3383.html) | 有中国 SKU；**连续电流、均衡、温度监控未取得证据**。不凭“3S 10A”名称放入整机 BOM。候选类别是带明确连续／脉冲、均衡与温度规格的成品电池包／配套保护及充电系统，精确 SKU 待核。 |
| 保险丝 | **Littelfuse 297 MINI 32 V 系列**，现成系列；电流型号未选 | 32 V DC、2–30 A 系列；必须按时间—电流曲线、分断能力、线束／座额定值选具体 SKU。[官方数据表](https://www.littelfuse.com/assetdocs/littelfuse-datasheet-297-mini32v?assetguid=42c9dd21-a88e-4328-8e67-2f832444faf1) | 仅证明系列事实，未核中国库存／保险座。电池近端主保险、分支保险是待评估类别，不能用堵转和数直接决定保险安数。 |
| 急停输入 | **Schneider Harmony XB5AS8442**，现成按钮示例 | Ø22 mm 安装、Ø40 mm 蘑菇头、保持／旋转释放、1NC、强制断开。10 A 是自由空气热电流；官方 DC-13 电气耐久示例是 **24 V／0.5 A**。[官方数据表](https://iportal.se.com/Contents/docs/SQD-XB5AS8442_DATA%20SHEET.PDF) | 未核中国精确到货。该按钮不能凭“10 A”直接当数十安电机总线开断器；应作为硬件控制输入，另核适合 DC 负载的继电器／接触器／电子断电器件，尚无最终 SKU。 |

本轮**不提供精确人民币预算项**：中国官方目录存在、授权渠道存在、当前选项可下单、含税库存报价是不同证据级别。也未将模块“最大／峰值”、电池板“瞬间”、急停“热电流”改写为整机连续能力。

## 3. Radxa、USB 相机和扬声器

### 3.1 主机与 USB 供电

Radxa ZERO 3W 当前 [官方 Product Brief，rev 1.12／2026-09-20](https://dl.radxa.com/zero3/docs/hw/3w/radxa_zero_3w_product_brief.pdf) 指定 USB-C 1 的 5 V／2 A 输入，USB-C 2 为 USB 3 Host，且写 **Host 最大 500 mA**。不能套用泛称“USB 3 900 mA”覆盖板级限制；5 V／2 A 输入要求也不是当前运行功耗实测。两块 U2D2＋一相机至少三个设备，原生 Host 口只有一个。

**待选类别／推断：** 带独立电源及明确上游防反灌说明的 USB Hub；逻辑 5 V 与舵机 5 V 至少分别核电压跌落、回流和启停。是否采用独立转换器由负载与噪声实测决定。未选 Hub SKU，未证明其每口电流与 Radxa 兼容。USB 声卡再增加端口／功耗。

### 3.2 单眼 USB 相机事实（目标工作距离约 80–300 mm）

| 当前精确候选 | 已核官方事实 | 当前放行缺口 |
|---|---|---|
| **Arducam A219／B0292-1**（无金属壳标准模块） | 当前官方独立 SKU 页；USB2 UVC、Linux，自动／手动焦距控制；38 ×38 mm、5 V、页面功耗 1 W；1920×1080 MJPG 30 fps；**默认对焦 10 cm–∞**。[当前 SKU 页](https://www.arducam.com/4k-8mp-imx219-autofocus-usb-camera-module-with-microphone-1080p-mini-uvc-usb2-0-webcam-standard-module.html)、[当前比较表](https://www.arducam.com/arducam-usb-autofocus-imx219-b0292.html) | 文档支持 100–300 mm，不保证 80 mm。旧 B0292 的 40 mm–∞、34／28 mm 孔距不能继承；**尚未取得 B0292-1 对应版本的孔距／总高图与中国到货证据**。其可下单页面不是已完成实机试验。 |
| **Arducam B029202**（HDR、金属壳版本） | 同当前比较表：32 ×32 ×1.6 mm 是**板**尺寸，不是金属壳包络；5 V、页面功耗 1.75 W，默认焦距也是 10 cm–∞。[当前独立 SKU 页](https://www.arducam.com/8mp-hdr-autofocus-usb-camera-module-with-metal-housing-1080p-mini-uvc-usb2-0-webcam-a219.html) | 不能把它与 B0292-1 混作同一 CAD 包络；80 mm、壳体和孔距仍待核。 |
| **Waveshare OV5693 5MP USB Camera (A)，SKU 24710**，Arducam 之外的后备 | 官方 Wiki：USB2、自动焦、Linux／V4L2 使用；FAQ 明确约 **5 cm–5 m**。[Wiki](https://www.waveshare.com/wiki/OV5693_5MP_USB_Camera_%28A%29) 当前[商品页](https://www.waveshare.com/ov5693-5mp-usb-camera-a.htm)实际读取：5 V ±5%、工作电流 **500 mA**、板18 ×40 mm、镜头18 ×18 ×19.69 mm；135°(D)／95°(H)／70°(V)，1080p MJPG 15 fps。 | 焦距覆盖目标；500 mA 已用满 Radxa 文档 Host 预算，不能再依靠该口总电流给两 U2D2／声卡供电。Wiki 外形仍写18 ×36 mm；Wiki 链出的[尺寸 PDF](https://www.waveshare.net/w/upload/3/32/OV5693-5MP-USB-Camera-A-Dimension.pdf)本轮返回网页验证内容，**未取得有效当前孔图与中国到货证据**，因此不直接放行外壳。 |

**核查结果：** 当前常规 Arducam 候选可收敛到 **B0292-1、工作距暂按 ≥100 mm** 的文档条件，尚不能声称已找到“80–300 mm 全覆盖＋当前确切孔图＋中国可到货”的合格件。B0447 同样标 10 cm；B0441 未取得精确近焦数值，旧厂商 PDF 与当前选型表还有传感器差异，均不额外扩成候选。Arducam B0494-1 虽明确 8 cm，但 108MP／官方 USD 299.99 的定位与此首版任务不匹配，不据此推荐升级：[其官方页](https://www.arducam.com/arducam-108mp-motorized-focus-usb-3-0-camera-module-without-enclosure.html)。

目标识别是否稳定仍需在到货精确 SKU 上验证 80／100／150／300 mm 清晰度、固定曝光与焦距后的标记定位、USB 同时接两总线时的稳定性。Linux UVC 与 USB Host 接口相容是软件接入依据，**不是 Radxa 实测通过**；单目给出的尺度须由标记／已知物尺寸／标定等任务条件建立，不自动获得三维抓取精度。

### 3.3 音频

先保留“**USB 声卡／DAC＋有明确输入、5 V 电源和 4 Ω／8 Ω 负载规格的小功放＋匹配扬声器**”这一常见类别；本轮未选具体 SKU、焊点或声压目标。扬声器标称 3 W 不是持续固定取电 3 W；供电应按所选功放的实际音量、效率、静态电流及启动峰值核算。USB 声卡不能直接驱动任意无源扬声器。

## 4. 供后续评审使用的算式（估算，不是最终预算）

令 `nM` 为 XM430-W350-T 个数，`nC` 为 XC330-M288-T 个数。

- 官方堵转条件参考：`I12_stall_sum = 2.3 × nM A`（12 V）；`I5_stall_sum = 1.80 × nC A`（5 V）。这些是故障／同步高负载参考，**不是持续正常电流、热稳定能力或应选电源额定值**。[XM430](https://emanual.robotis.com/docs/en/dxl/x/xm430-w350/)、[XC330](https://emanual.robotis.com/docs/en/dxl/x/xc330-m288/)
- `I_battery ≈ [12×I12/η12 + 5×I5_servo/η5_servo + 5×I5_logic/η5_logic] / V_battery_loaded`。直供 XM 时用实际电池轨电压替代式中 12 V；容量与输入额定应核低电压、高温和瞬态条件，而不是仅用满充 12.6 V。
- `P_loss = P_out × (1/η − 1)`。例如若按 DFR0929 页面 83% 且输出 50 W 估算，损耗约 **10.2 W**；这是该效率假设下的热量估算，不证明该模块在机器人壳内可持续 50 W。
- `ΔV = I × R_loop`；线束、连接器与地回路压降决定最远舵机／主机端电压。瞬态电容初估 `C ≥ ΔI×Δt/ΔV` 还未含 ESR 和控制环响应，不能补救持续功率不足；电机回馈时也需核电源是否允许吸收或承受反向能量。
- `Wh_nominal = 11.1 × Ah`；`t ≈ Wh_usable / P_average`。XM 直供时可用能量受其端电压 ≥10 V 约束，不能把 BMS 最低断电前全部容量当作可用运行时间。小功放输入约 `P_audio_out/η_audio + P_idle`，按实际声卡／功放规格补值。

下一次供电评审需先取得：各轨同步峰值与持续任务负载、舵机端最低电压／温升、电池与降压器具体型号的连续条件、保险座和导线能力、急停开断执行器、USB Hub 防反灌及端口预算；相机需确定工作距离下限与精确供货版本。以上缺口集中评审，不通过“最大电流相加”或先买通用板来隐式冻结方案。

## 5. 采购接口闭合（RC2 追加，2026-09-28）

本节接口核查最初针对 12 × XM430、1 × XM540、3 × XC330 的早期候选；**现行 RC2 已改为 12 × XM430-W350-T＋2 × XM540-W270-T（12 V TTL）＋2 × XC330-M288-T（5 V TTL）**，以 [规格](../configs/robot_spec.json) 和 [现行 BOM](../hardware/goose_rc2_bom.xlsx) 为准。RC2 采用 12 V 分支注电与拟议的分支熔断、两块 U2D2 仅承担通信、5 V 舵机与逻辑分别降压；启动时需读回硬件限流配置，否则禁止全机运行。这里记录接口与机械事实，**不代表分支线束、保险或转换器已经完成额定／温升验证**。

### 5.1 确切 TTL 接头与可购电缆

| 对象 | 官方接口／SKU | 闭合结果 |
|---|---|---|
| XM430-W350-T、XM540-W270-T、XC330-M288-T | 三者 TTL 插座均为 **JST B3B-EH-A**，线端 housing **EHR-03**，端子 **SEH-001T-P0.6**；1 GND、2 VDD、3 DATA；官方线规 21 AWG。[XM430](https://emanual.robotis.com/docs/en/dxl/x/xm430-w350/)、[XM540](https://emanual.robotis.com/docs/en/dxl/x/xm540-w270/)、[XC330 当前 Docs](https://docs.robotis.com/docs/dxl/model_reference/x_series/xc_series/xc330-m288/) | 同一 EH 3P 接口；**330 不需要专用转接线**连接当前 U2D2／Hub。相同插头无法防止 5 V／12 V 误连。XM540 的 3P Sync／5P 外部接口另属其他接口，不当作 TTL 总线插头。 |
| U2D2、U2D2 Power Hub | TTL 同为上述 EHR-03／B3B-EH-A。[U2D2 当前 Docs](https://docs.robotis.com/docs/parts/interface/u2d2/)、[Hub 当前 Docs](https://docs.robotis.com/docs/parts/interface/u2d2_power_hub/) | 直连标准 X3P JST–JST 线。Hub 套装含 **X3P 100 mm ×1**、X4P 100 mm ×1；TTL 域只需前者。[官方套装](https://en.robotis.com/shop_en/item.php?it_id=902-0145-001) |
| 增补标准 TTL 线 | **Robot Cable-X3P 180 mm（10 pcs），903-0249-000**，两端 JST，官方列 X 系列 TTL。[现成商品](https://robotis.us/products/robot-cable-x3p-180mm-10pcs) | 可作为直接购买线缆 SKU；确切长度／数量按最终走线选。官方商品存在不等于已取得中国现货报价。 |
| 旧接口适配线 | **Robot Cable-X3P 180 mm Convertible（10 pcs），903-0251-000**，Molex–JST。[现成商品](https://robotis.us/products/robot-cable-x3p-180mm-convertible-10pcs) | 针对旧 Molex 设备；**不是 RC2 的 330→U2D2 转换需求**。XM 包装附送它也不意味着本方案要用它。 |

### 5.2 Hub 的 5 V 支持与电源 pin 行为

Hub 官方 **3.5–24 V** 输入范围包含 5 V；它将外部电源送到 DYNAMIXEL 的 **pin 2 VDD**，pin 1 为共同 GND，开关控制舵机供电。它不会把 12 V 转成 5 V，U2D2 的 USB 也不会经它变成舵机电源。官方连接顺序与 pinout 见 [Hub Docs](https://docs.robotis.com/docs/parts/interface/u2d2_power_hub/)。只使用一个供电入口，不能把两种电压接在同一 Hub。

U2D2 的 TTL pin 2 官方同样标为 VDD，但官方明确 **U2D2 不供应 DYNAMIXEL 电源**；UART 可开关的 3.3 V 是另一个 4P 端口的功能。[U2D2 Docs](https://docs.robotis.com/docs/parts/interface/u2d2/) 本轮未取得 U2D2 内部原理图，故不声明 TTL／RS-485 的 VDD 内部是否相连，也不把标准三芯线称为“只接数据”。两块 U2D2、各自外部供电域的布置必须避免跨域 VDD；需要 GND 参考，未声明电气隔离。

现行 RC2 按厂家堵转条件简单相加为 `12 ×2.3 +2 ×4.4 =36.4 A`（12 V）、`2 ×1.80 =3.6 A`（5 V）。XM540 的 4.4 A 条件见 [精确 -T 官方商品规格](https://www.robotis.com/shop/item.php?it_id=902-0137-000)。**36.4 A 不是正常持续需求，但超过单 Hub 官方 Maximum 10 A**；每域一 Hub 不能解释为整个 12 V 域电流均通过该板／开关／单根 EH 线。分支注电只解决单点额定不匹配的拓扑问题；各分支硬件电流上限、保险与线束仍需形成可检验的约束。

### 5.3 CAD 内部预留的官方尺寸和孔型

下表是器件本体与安装基准，不包含插入后的线头、线缆弯曲半径、散热间距或装配工具空间。ROBOTIS 图纸均注明仅供参考，最终孔位及高度还须核到货版本。

| 器件 | 本体／安装事实 | 图纸与版本／未闭合项 |
|---|---|---|
| Pololu D24V90F5 #2866 | 名义 **40.6 ×20.3 ×7.6 mm**，规格脚注不含随附硬件；**4 ×Ø2.18 mm** 安装孔，中心矩形 **35.6 ×15.2 mm**，适用 #2／M2 螺钉。图中 PCB 1.57 mm、上方元件高度 6.1 mm；整高与 0.3 inch 规格有取整差异。板外缘公差 ±0.3 mm、孔位公差 ±0.1 mm。 | [官方尺寸 PDF（2018-09-21，覆盖 #2865／#2866）](https://www.pololu.com/file/0J1581/step-down-voltage-regulator-d24vxf5-dimensions.pdf)、[产品规格](https://www.pololu.com/product/2866/specs)、[官方 STEP／DXF 入口](https://www.pololu.com/product/2866/resources)。不能凭板高省略接线／排针与热空间。 |
| U2D2 Power Hub Board Set，902-0145-001 | 板外缘 **48 ×57 mm**；官方图四角孔中心矩形 **42.07 ×48.04 mm**，标注 **Ø4 mm**，另有其他孔排。套装附四个 **Support M3×10×6** 与 M3 螺母，底面针脚突出须架空。 | [官方 PDF（2020-03-13）](https://www.robotis.com/service/download.php?no=1914)、[官方 STEP](https://www.robotis.com/service/download.php?no=2202)、[套装尺寸与附件](https://en.robotis.com/shop_en/item.php?it_id=902-0145-001)。PDF 没有标出元件总高；**不能用 PCB 外缘直接当装配总包络**。 |
| U2D2，902-0132-000 | 壳体 **48 ×18 ×14.9 mm**，底面四角安装基准中心矩形 **42 ×12 mm**；官方要求 **M2 Tap bolt**，有效孔深 **4.7 mm**、从表面深 **5.5 mm**。不是贯穿 M2 孔。 | [官方 PDF（2026-04-10，含旧 Micro-B／新 Type-C）](https://www.robotis.com/service/download.php?no=2250)、[官方 STEP](https://www.robotis.com/service/download.php?no=2251)、[孔型／深度 Docs](https://docs.robotis.com/docs/parts/interface/u2d2/)。按实物 USB 批次核插头空间。 |
| Radxa ZERO 3W | 板 **65 ×30 mm**，机械图明确 **4 ×Ø2.8 mm** 安装孔。孔距未在当前 PDF 中完整标注，不直接继承树莓派 Zero 孔距；板厚／双面元件总高／GPIO 排针与散热器高度也不由 65×30 推出。 | [固定版本 Product Brief rev 1.12，2026-09-20，PDF 第 6 页／页码 5](https://dl.radxa.com/zero3/docs/hw/3w/rad-doc-0084_radxa_zero_3w_product_brief__revision_1.12_gd8a4657.pdf)、[官方 STEP／DXF／PCBA 下载目录](https://dl.radxa.com/zero3/docs/hw/3w/)。官方 DXF 包为 v1110；必须与到货板修订配对。 |

本轮已实际读取上述机械 PDF，其中 U2D2／Hub 的下载页跳转到厂家发布的 Dropbox 文件；源 URL 保留官方入口，未将中转内容误作图纸。U2D2 安装到 Hub 后的组合高度、Hub 元件总高与 USB Hub 型号包络仍需相应 CAD／实物，不填猜测值。

### 5.4 Radxa 与 USB Hub 供电闭合边界

Radxa 当前 rev 1.12 指定 **USB-C 1 输入 5 V／2 A**，也支持 GPIO pin 2／4 的 5 V；中文 [硬件接口说明](https://docs.radxa.com/zero/zero3/hardware-design/hardware-interface)要求只输入 5 V，推荐 5 V／2 A 及以上电源。USB-C 2 Host 官方限制 **500 mA**。[固定版本 Product Brief，PDF 第 7 页／页码 6](https://dl.radxa.com/zero3/docs/hw/3w/rad-doc-0084_radxa_zero_3w_product_brief__revision_1.12_gd8a4657.pdf)

RC2 两 U2D2、UVC 相机与可选 USB 声卡需要扩口；U2D2 自身最大 USB 电流本轮未得，不能凭接口标准补数。**工程推断：采用独立外供的 USB Hub 类别，并在逻辑供电预算中包括 Hub 和每个外设**；若相机采用前述 Waveshare 500 mA 版本，已单独用满板级 Host 预算。任何无外供方案须先证明所有设备与 Hub 总需求符合 500 mA。具体 Hub 尚未选定，必须核上游 VBUS 不反灌、各口及合计连续供电能力、Linux／相机带宽和 U2D2 同时通信稳定性。

### 5.5 输出 horn、idler 与厂家供货状态

| 对象 | 单机／套装包装事实 | 需另计与来源 |
|---|---|---|
| XM430-W350-T，902-0124-000 | 单机包装列 **HN12-N101 normal horn ×1**、标准 X3P 180 mm ×1、convertible 180 mm ×1；**未列 idler**。 | [精确 -T 官方包装](https://www.robotis.com/shop/item.php?it_id=902-0124-000)；**HN12-I101 Set，903-0240-000** 是另售 idler／轴承／cap／螺钉套装，不含完整 hinge frame。[另售 SKU](https://robotis.us/products/hn12-i101-set) |
| XM540-W270-T，902-0137-000 | 单机包装列 **HN13-N101 normal horn ×1**、thrust washer ×1、标准／convertible X3P 180 mm 各 ×1、3P Sync 160 mm ×1；**未列 idler**。 | [精确 -T 官方包装](https://www.robotis.com/shop/item.php?it_id=902-0137-000)；**HN13-I101 Set，903-0267-000** 另售 idler／6701ZZ 轴承／cap／螺钉，不含完整 hinge frame。[另售 SKU](https://robotis.us/products/hn13-i101-set) |
| X330 hinge／idler 套装 | 正式名称 **FPX330-H101 4pcs Set，903-0302-000**，含 hinge ×4、idler ×4、idler cap ×4 与相应紧固件；“XC330-H101”不是此商品正式名称。 | [厂家商品与包装](https://robotis.us/products/fpx330-h101-4pcs-set)。2026-09-28 本轮读取的 **ROBOTIS AMERICA** 页面标 **LEAD TIME REQUIRED、estimated 2 months**；美洲店仅向美洲发货。仅记录厂家页面状态，**不承诺中国库存或交期**。 |

### 5.6 3S 1500 mAh 电池机械候选（补充，不是采购承诺）

中国品牌 CNHL 的 **Black Series V2.0 1500 mAh／11.1 V／3S1P／XT60，stock number 1501303BK** 厂家页给出 **78 ×39 ×21.5 mm、约 125 g**，满充 12.6 V，12 AWG 输出线、JST-XH 4P 平衡接口；页面声明尺寸约 **1–5 mm** 变化、质量约 **±5 g**。[厂家精确商品页](https://chinahobbyline.com/products/cnhl-black-series-v2-0-1500mah-11-1v-3s-130c-lipo-battery-with-xt60-plug)

仅作机械／质量候选。厂家标称 130C continuous／260C burst，本轮没有原始温升、内阻、放电时间／温度测试条件，**不据 C 数字推定已验证持续输出**；未证明内置 BMS／均衡保护，也未取得中国库存或人民币报价。CAD 预留需涵盖厂家尺寸变化、引线、插头、固定与更换空间；名义能量 `11.1×1.5=16.65 Wh` 不是全部可用运行能量，也不是续航保证。

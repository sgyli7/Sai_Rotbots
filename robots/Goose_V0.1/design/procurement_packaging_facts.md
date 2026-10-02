# ROBOTIS 采购包装与公开标价事实

检索：2026-09-28（Asia/Chongqing；网页下载于 2026-09-27 21:56–22:01 UTC）。仅核 XM430-W350-T、XM540-W270-T、XC330-M288-T、U2D2，以及配套后侧 idler、随附/官方线材；不改变设计、不下订单、不联络供应商。

已读取 [robot_spec.json](../configs/robot_spec.json)，revision `rc2`，读取时 SHA256 `7c4e8946a8bda5b1ae703b68aee89ee1d4c2c5ba465c4a57212bcbce40e119a6`。关节计数：**12 XM430、2 XM540、2 XC330**，分别落在现有 12 V 和 5 V TTL bus；本轮指定 **2 U2D2**。后侧支承采购量以下按“每台均需 1 个后 idler”的条件核算，最终按实际采用的支架/套装扣除；关节数量本身不证明每个关节必须购买独立 idler。

以下 **fact** 为当前官方商品正文；数量汇总与差额为 **derived**。网页商业数据可变，没有 Git commit。原 HTML 与美国官方公开商品 JSON 的取证副本/哈希仅留 `.scratch/procurement_packaging/`。

## 1. 裸舵机和接口包装：先扣随附件

| 订购型号 / SKU | 每个零售包的官方清单 | 本批已包含的主要附件 |
|---|---|---|
| [XM430-W350-T / 902-0124-000](https://en.robotis.com/shop_en/item.php?it_id=902-0124-000) ×12 | 舵机×1；HN12-N101 前输出 horn×1；thrust washer×1；X3P JST–JST 180 mm×1；X3P Molex–JST convertible 180 mm×1；WB M2.5×4×16（side frame）；WB M2.5×6×1（horn 中心）；WB M2×3×10（horn/frame）；spacer ring×8 | **HN12-N101×12、washer×12、普通 X3P×12、convertible X3P×12**；WB M2.5×4×192、M2.5×6×12、M2×3×120、rings×96 |
| [XM540-W270-T / 902-0137-000](https://en.robotis.com/shop_en/item.php?it_id=902-0137-000) ×2 | 舵机×1；HN13-N101 前输出 horn×1；washer×1；X3P JST–JST 180 mm×1；convertible X3P 180 mm×1；专用 3P-Sync 160 mm×1；WB M2.5×5×16（side frame）；WB M2.5×4×10（horn/frame）；WB M3×8×1（horn 中心）；rings×8 | **HN13-N101×2、washer×2、普通 X3P×2、convertible X3P×2、Sync×2**；WB M2.5×5×32、M2.5×4×20、M3×8×2、rings×16 |
| [XC330-M288-T / 902-0173-000](https://en.robotis.com/shop_en/item.php?it_id=902-0173-000) ×2 | 舵机×1（本体已有输出盘）；X3P JST–JST 180 mm×1；PHS M2×6 TAP×6（horn）；PHS M2×8 TAP×10（frame）。官方明确 frame 另购，idler/cap 在 FPX330-H101 中，**不单独售卖** | **普通 X3P×2、M2×6 TAP×12、M2×8 TAP×20**；没有随包后 idler/cap |
| [U2D2 / 902-0132-000](https://en.robotis.com/shop_en/item.php?it_id=902-0132-000) ×2 | U2D2×1；**USB Type-C Cable×1**；convertible X3P 180 mm×1；convertible X4P 180 mm×1 | **USB 线×2、convertible X3P×2、convertible X4P×2**；包装不含 Power Hub Board 或电源 |

**derived：**本批已包含 HN12-N101×12、HN13-N101×2；为这些舵机再次购买同型前 horn 套装属于重复（维修备件另记）。XC330 前输出盘见 [官方 X330 图纸入口](https://en.robotis.com/service/download.php?no=1986)，没有据其他型号补造一个额外标准 horn SKU。上表紧固件按用途分列，同尺寸不能因此算作适合任意孔位。

**官方页差异：**[美国 XM430 T 页](https://robotis.us/products/dynamixel-xm430-w350-t) 的包装表误写 `XM430-W350-R`，螺钉表也不同于全球 T 页；[美国 XM540 T 页](https://robotis.us/products/dynamixel-xm540-w270-t) 的包装表写 `XM540-W270-R`，并将 M3×8 的用途写成 frame。[美国 U2D2 页](https://robotis.us/products/u2d2) 开头明确升级 USB-C，但旧包装表仍写 Micro USB。以上不改成一个折衷清单：本报告采用 SKU 对应全球 T 页和已更新全球 U2D2 包装，实际订单要求供应商确认同 SKU、T/TTL、USB-C 修订及完整随附件。

全球商品页与 [U2D2 官方手册](https://emanual.robotis.com/docs/en/parts/interface/u2d2/)明确从 **2025-08** 将 Micro-B 改为 Type-C，并明确 U2D2 不给 DYNAMIXEL 提供驱动电源。不能把 USB 线或 convertible cable 的存在解释为已经提供舵机供电。

## 2. 后侧 idler：裸舵机不含，H 框架套餐须扣除

| 可订购 SKU | 一包内容 | 全覆盖条件下的差额数量 |
|---|---|---|
| [HN12-I101 Set / 903-0240-000](https://en.robotis.com/shop_en/item.php?it_id=903-0240-000) | plastic bearing×1；HN12-I101 idler×1；DC12 cap×1；WB M2×3×18；**不含 hinge frame** | 12 个 XM430 若都用后支承：**12 包**，减去已购、已包含 HN12-I101 的 frame 套装数量 |
| [HN13-I101 Set / 903-0267-000](https://en.robotis.com/shop_en/item.php?it_id=903-0267-000) | 6701ZZ bearing×1；HN13-I101 idler×1；DC13 cap×1；WB M2.5×5×8（side frame）；WB M2.5×4×18（frame）；**不含 hinge frame** | 2 个 XM540 全覆盖：**2 包**，扣除已含配套 idler 的 frame 套装数量 |
| [FPX330-H101 4PCS SET / 903-0302-000](https://en.robotis.com/shop_en/item.php?it_id=903-0302-000) | **H101 hinge frame×4、idler×4、cap×4**；BHS M2.6×6 TAP×8（idler 中心）；普通 M2 nuts×20、PHS M2×4×20（frame）；PHS M2×4 TAP×36（horn/frame） | 2 个 XC330 的后 idler 需求：**1 包就有 4 组**，使用 2 组后余 2 组；不能按每个舵机 1 包购买，亦不能虚设单独 idler SKU |

[FR12-H101K Set / 903-0239-000](https://en.robotis.com/shop_en/item.php?it_id=903-0239-000) **已含 HN12-I101 Set×1**；采用该套装的轴不能再重复计独立 HN12-I101。其余明确清单：H frame×1、FHS M2.5×14×4、WB M2×3×10、WB M2.5×4×8、rings×10。

[FR13-H101K Set / 903-0270-300](https://en.robotis.com/shop_en/item.php?it_id=903-0270-300) 标题和描述明确 **含 idler set**；不过组件表把名称写成 `FR13-I101 Set`，而独立 idler 商品/手册为 HN13-I101。应让供应商确认配件，不另造 FR13-I101 独立 SKU。该套餐当前明确 **Out of stock**。这里只记录扣重关系，没有为设计增加 H frame。

**derived：**采用独立 idler 且全覆盖时额外为 **12 HN12-I101 包 + 2 HN13-I101 包 + 1 FPX330-H101 四件包**。若本批已有任何 330 H101 套装，先累计它所含的 4 个 idler，再计算差额。430/540 每包 bearing/cap 已齐，不另为同一支承重复买通用轴承或盖帽。

## 3. 线材：数量与接口匹配，长度另核

本批裸器件的已含数量为：

| 随附线材 | 合计 | 采购含义 |
|---|---:|---|
| X3P **JST–JST** 180 mm | **16 根**（12+2+2） | 这批 X 舵机与 U2D2 的 TTL 接口为 JST 三芯；先按路径复用，不能按16台舵机默认再买16根同线 |
| X3P **Molex–JST convertible** 180 mm | **16 根**（12+2+2 U2D2） | 是转接线，不等于两端 JST；不能在本批纯 JST 串接中当普通 X3P 自动扣用 |
| 3P-Sync 160 mm | **2 根** | XM540 专用 dual-joint 同步线，不计入普通 TTL bus 连线数 |
| X4P convertible 180 mm | **2 根** | 来自 U2D2；本配置使用三芯 TTL，不当三芯线替代品 |
| USB Type-C Cable | **2 根** | 来自两 U2D2；不默认另买 Micro-B 线；电脑/USB hub 端接头与所需实际长度仍由订单确认 |

[Robot Cable-X3P 180mm 10pcs / 903-0249-000](https://en.robotis.com/shop_en/item.php?it_id=903-0249-000) 是普通 TTL X 系列线，**10 根一包**；[Robot Cable-X3P (Convertible) 180mm 10pcs / 903-0251-000](https://en.robotis.com/shop_en/item.php?it_id=903-0251-000) 是 Molex–JST，亦 **10 根一包**。convertible 商品正文还把 U2D2 列作 Molex 产品示例，与当前 U2D2 自身的 JST 接口说明不一致；核配应按两端实际连接器，不按该旧示例替代。

**derived：**若走线后确有 `r` 根普通 180 mm 线的净缺额，标准补货包数为 `ceil(r/10)`；先从随附 16 根中扣可用的根数。不同长度、分支/电源注入点和运动余量没有在本轮完成路由核算，故**额外普通线包数保留待核，不能认定 16 根一定足够**；没有为更长线编造 SKU 或价格。官方 JST 接口和线规见 [U2D2 Connector Information](https://emanual.robotis.com/docs/en/parts/interface/u2d2/#connector-information)。

## 4. 330 自攻预孔、frame 螺钉与壳体螺钉不能混记

本轮重新实际查看 [X330 官方参考图 no=1986](https://en.robotis.com/service/download.php?no=1986)（`XL,XC-330.pdf`，28-May-20，SHA256 `948b707cb26a64501c03fc45b1a9557b69a554dd5d6934f02e8e6f86cf2b46c2`）：

- **输出 horn / 后 idler 圆周孔**：4×Ø1.6 自攻预孔，PCD Ø12，`DP3.0(Max.)`，使用 M2 tapping screw。该标注不是已有 M2×0.4 金属螺纹，也不是“最小有效完整牙 3 mm”。
- **静态机身 frame 孔**：图指定 M2 tapping，另见 Detail A/B 的不同阶孔；图中 **3.5 / 4.5 mm 属 Ø2 引导段**，不是可用自攻牙深。不可将 horn 的 DP3 套用到 case/frame 孔。
- 舵机随包 **M2×6 TAP（horn）/M2×8 TAP（frame）** 和 H101 随包 **M2×4 TAP（horn/frame）/M2.6×6 TAP（idler 中心）** 都是不同用途的**螺钉总长**，不是允许全长进入塑料孔的深度。用户支架、垫片厚度必须从总长中扣除后再核侵入长度。
- 图中的已有十字壳体闭合螺钉，与空闲 frame 自攻孔是不同位置；不得把已有 case 螺钉的标称总长、阶孔引导长度或中心 idler 螺钉长度当作 horn 的侵入依据。

case/frame 的有效接合牙长、中心 idler 预孔有效深度、允许重复装拆次数与公差仍缺官方完整数据；本报告不补造。430/540 的 horn 中心紧固件、圆周 frame 螺钉和已有壳体闭合螺钉也须分别记账。官方 [Frame and Horn Assembly Precautions](https://emanual.robotis.com/docs/en/dxl/x/xm430-w350/#frame-and-horn-assembly-precautions)要求根据安装点深度核螺钉长度；随包不代表适合任意用户板厚。详细几何事实仍在 [既有安装接口核查](servo_mount_geometry_review.md)，本轮不修改接口。

## 5. 公示价格、交期与中国询价边界

下表均为 **USD**；“全批”是公开单价乘数量的算术，未加运费、目的地税费、代理价、批量折扣或汇率。全球店相关商品卡中的 Lead Time 是网页字段，不是中国到货承诺，也不把通用“有库存三工作日发货”条款当本 SKU 现货证明。

| 项目 | 全球官方公示单价 USD | 全批数量/条件 | 官方公开可得性 |
|---|---:|---|---|
| XM430-W350-T | **269.90** | 12；3,238.80 USD | 全球店 [XM540 页相关卡](https://en.robotis.com/shop_en/item.php?it_id=902-0137-000) 与 U2D2 页标 **Lead Time 50 days**；未确认中国现货 |
| XM540-W270-T | **419.90** | 2；839.80 USD | [XM430 页相关卡](https://en.robotis.com/shop_en/item.php?it_id=902-0124-000) 标 **40 days**；未确认中国现货 |
| XC330-M288-T | **89.90** | 2；179.80 USD | [U2D2 页相关卡](https://en.robotis.com/shop_en/item.php?it_id=902-0132-000) 标 **40 days**；未确认中国现货 |
| U2D2 | **32.10** | 2；64.20 USD | [XM430 页相关卡](https://en.robotis.com/shop_en/item.php?it_id=902-0124-000) 标 **10 days**；USB-C 包装版本需确认 |
| HN12-I101 Set | **17.80** | 全覆盖且无套餐抵扣时12包；213.60 USD | [XM430 页相关卡](https://en.robotis.com/shop_en/item.php?it_id=902-0124-000) 标 **40 days** |
| HN13-I101 Set | **42.90** | 全覆盖且无抵扣时2包；85.80 USD | [XM540 页相关卡](https://en.robotis.com/shop_en/item.php?it_id=902-0137-000) 标 **1 day**；不等于已验证现货件数 |
| FPX330-H101 四件包 | **9.80** | 需两个 idler 且未购该套装时1包 | [XC330 页相关卡](https://en.robotis.com/shop_en/item.php?it_id=902-0173-000) 标 **1 day**；须确认中国供货 |
| 普通 X3P 180 mm十根包 | **19.00** | 额外包数待路径补差 | [XM430 页相关卡](https://en.robotis.com/shop_en/item.php?it_id=902-0124-000) 标 **1 day** |
| Convertible X3P十根包 | **15.50** | 当前已有16根；没有本轮新增需求 | [全球商品页](https://en.robotis.com/shop_en/item.php?it_id=903-0251-000)有公示价；实际中国库存未知 |
| FR12-H101K（仅供扣重识别） | **40.60** | 每包已含1组430 idler；不加入本轮新设计采购 | [XM430 页相关卡](https://en.robotis.com/shop_en/item.php?it_id=902-0124-000) 标 **1 day** |
| FR13-H101K（仅供扣重识别） | **66.70** | 每包已含1组540 idler；名称差异须确认 | [主商品页](https://en.robotis.com/shop_en/item.php?it_id=903-0270-300)明确 **Out of stock** |

**derived：**16 个舵机 + 2 U2D2 的全球公示价合计 **4,322.60 USD**。再按独立后 idler 全覆盖且无套装抵扣条件加 **309.20 USD**，得到 **4,631.80 USD**；此合计不含新增线材、frame、电源或其他机器人零件，不是整机预算或中国报价。

美国官方同 SKU 公示价分别为 XM430 **310.39 USD**、XM540 **482.89 USD**、XC330 **103.39 USD**、U2D2 **36.92 USD**（[XM430](https://robotis.us/products/dynamixel-xm430-w350-t)、[XM540](https://robotis.us/products/dynamixel-xm540-w270-t)、[XC330](https://robotis.us/products/dynamixel-xc330-m288-t)、[U2D2](https://robotis.us/products/u2d2)）。本轮对应官方公开 `.js` 商品 variant 均 `available=true`，只能支持系统允许订购，不能证明现货数量；XC330 页面另列约两周 lead time。美国店声明只配送北、中、南美洲，不能把它的价格/availability 当中国供货依据。

**missing / 询价：**未取得以上型号的可靠官方中国 RMB 报价和中国现货数量，因此中国价格统一记 **询价**，没有把 USD/KRW/JPY 数字当人民币。实际询价需要列明本报告的 SKU/数量、前 horn/washer/线材是否随包、idler 套餐抵扣、USB-C 修订、含税/运费及交期；本轮仅形成事实清单，没有发送询价消息。

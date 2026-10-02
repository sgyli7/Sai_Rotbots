# Waveshare USB HUB HAT (B) 一手事实核查

检索日期：2026-09-28（Asia/Chongqing；下载发生于 2026-09-27 UTC）。对象为 **USB HUB HAT (B)，Waveshare SKU 20317，4×USB 2.0**，不含带 RJ45 的 ETH/USB HUB HAT (B)、旧非 B 型号或外壳套件 USB-HUB-BOX。本文只记录事实、由图推导和缺口，不确定接线方案。

## 已取得的证据与限制

官方商品页和 Wiki 正文直取返回 403；其官方域名搜索索引仍可读。官方文件站的原理图 PDF 和两份 STEP 归档均实际下载。已**查看原理图第 1 页图像**，并读取、渲染较新 STEP 的两面及侧面，提取真实圆柱面轴线和包络；没有实板、USB 枚举或电气测试。搜索中的图像说明不等同于实际看过尺寸图。

供应商 CAD/PDF 仅私有暂存于 `.scratch/usb_hub_facts/`。未取得明确 CAD 使用/再分发许可，不复制到正式 CAD 交付；归档中的 EXE 未运行。网页和文件无可用 Git commit；以下固定内容 SHA256，不把文件日期称作板硬件版本。

## 1. 上行连接：USB 线成立，Radxa 尚未实测

**fact（官方商品页索引）：**普通 USB 接口可通过 USB 线接其他 Raspberry Pi 或 PC；pogo 专用于 Zero 系列。四个扩展端口兼容 USB 2.0/1.1。官方包装列表为板 ×1、螺钉包 ×1，没有列出 USB 线。商品页 Weight 为 0.024 kg，但没有区分裸 PCBA、附件或包装质量。[官方商品页](https://www.waveshare.com/usb-hub-hat-b.htm)

**fact（官方 Wiki 索引）：**硬件连接章节分别列 pogo 和 USB 线；FAQ 要求用 USB 线接电脑检查是否识别，并提到 Pi Zero 必须处于 USB host 模式。FAQ 的支柱型号为 M2.5；其 pogo 电流表述为最大 3 A，未给整个板、每口的温升、线损或保护限流保证。[官方 Wiki](https://www.waveshare.com/wiki/USB_HUB_HAT_%28B%29)

**derived：**该板不依赖 Raspberry Pi GPIO 协议才能作为 USB hub 使用；USB 线上行符合官方 PC 用法。将上行接 Radxa 的可用性仍取决于相应口的 host 角色、系统、线缆和供电；未取得官方 ZERO 3W 兼容测试，不把 PC 支持当成已完成 Radxa 验证。

## 2. 5 V 电路与回灌：有直接通路，无图示隔离

下列 **fact** 来自实际查看的 [官方原理图 PDF](https://files.waveshare.com/upload/5/5c/USB_HUB_HAT_%28B%29_SchDoc.pdf) 第 1 页；第 2 页为 PCB 装配位置图，未带机械尺寸。

| 接口/器件 | 图中连接 |
|---|---|
| 上行 micro-USB `USB.J1` | pin 1 `VBUS` → `5V`；pin 2 `D−` → `USBU_N`；pin 3 `D+` → `USBU_P`；pin 5 与外壳 → GND |
| pogo/单针 `P6`、`P5` | 分别 → `5V`、GND；`P3`、`P4` 分别 → `USBU_P`、`USBU_N` |
| 四个下行 `H1…H4` | 各 pin 1 `VBUS` 直接接同一 `5V` 总线，各 GND 共地 |
| 控制器 `U2` | 型号标为 `FE1_1S`；pin 20 `VDD5` → 同一 `5V` 网络 |
| 输入/端口电源路径 | 上述连接中未画串联二极管、理想二极管、隔离开关、保险丝或每口限流芯片；四个 330 µF/6.3 V 电容跨接 5 V 与 GND |
| 图中 `PWR`、`L_USB1…4` | 是电源/端口**指示 LED**，不是电源接线端子、输出保护器或串联电感 |

**derived（严格限定于这份电路）：**若独立电源接入这个 `5V` 网络（如已定义的 `P6` 5 V 触点/焊盘），上行 VBUS 也会接到外部 5 V，板图没有阻断反向电流的元件。因此存在向 host VBUS 供电的通路，不能称为“独立供电且已隔离的 hub”。是否实际流入 host、流多少，取决于 host 内部电路、两电源压差和线阻；本轮没有取得 Radxa/PC 侧的测量，不能给回灌电流值或断言 host 内部必然被反供电。

**missing：**未实际取得官方接口标注图，不能将某一未标识的实板焊盘确定为独立电源输入；PDF 也未定义独立“外接 5 V 端子”。没有官方允许双电源同时接入的说明、实板版本匹配、连续性测试、整板/每口额定电流或 USB 合规试验。这里不指定电源接法。

**文档差异：**Wiki 索引称 onboard USB-to-UART 并列 CP2102 驱动，但 SKU 20317 商品页没有这项功能，所读原理图只有 FE1_1S，没有 CP2102 或 UART 接口。不能据驱动链接认定本板具备 UART。[商品页](https://www.waveshare.com/usb-hub-hat-b.htm)、[Wiki](https://www.waveshare.com/wiki/USB_HUB_HAT_%28B%29)、[原理图](https://files.waveshare.com/upload/5/5c/USB_HUB_HAT_%28B%29_SchDoc.pdf)

## 3. 安装接口与高度：参考 STEP 的可追溯测量

**fact（官方模型）：**Wiki 搜索索引列有 3D Drawing；同名资料的资源引用定位到 [官方 ZIP](https://files.waveshare.com/wiki/UPS_HAT_B/usb-hub-hat_b%203d%20drawing.zip)，含 `usb-hub-hat_b__asm.stp`、`usb-hub-hat_b__asm.exe`。因 Wiki 正文 403，不能保证其当前链接仍指向该归档。STEP header 为 `USB_HUB_HAT_B__ASM`，Creo 导出时间 `2023-12-18T11:03:29`；几何内核可读取 121 个实体，渲染可辨四个 USB-A 插座、micro-USB 与 pogo。单位为 mm。

以下为 **derived（该 STEP 中的几何测量，不是实物/公差规格）**：

| 项目 | 测得值及基准 |
|---|---|
| PCB 主平面 | `z=0` 与 `z≈−1.600`；约 1.6 mm 板厚，装饰/几何细节不计入板厚 |
| 安装孔 | 4 个贯穿 PCB 的圆柱孔，模型半径 `1.49999954 mm`，即名义 **Ø3.0 mm**；不是从 M2.5 支柱反推孔径 |
| 孔轴中心，STEP XY | `(3.5,3.5)`、`(61.5,3.5)`、`(3.5,26.5)`、`(61.5,26.5)`；圆柱面贯穿 `z≈−1.6…0` |
| 孔中心距 | **58×23 mm**，四角中心相对 65×30 主轮廓各内缩约 3.5 mm |
| PCB 单体包络 | 约 `65.022×30.022×1.700 mm`；包含约 0.1 mm 表面细节，不应据此把标称板厚改成 1.7 mm |
| 完整参考装配包络 | `x≈−0.107…65.398`、`y≈−0.011…30.608`、`z≈−8.200…+6.500 mm`，约 **65.505×30.619×14.700 mm**；连接器突出板边，pogo 纳入高度 |
| 板面上下占用 | 以 STEP `z=0` 板面计：USB-A 等向 −Z，最低约 −8.2；pogo 向 +Z，最高约 +6.5。以上轴向来自模型，不是采购板安放方向建议 |

原点与轴约定：此参考模型的 PCB 主轮廓约在 `x=0…65, y=0…30`，`z=0` 为 pogo 侧板面；从 +Z 看，micro-USB 位于 +X 短边，pogo 在 +Y 一侧。坐标是圆柱轴提取结果，不是从外观图估孔位。CAD 的小数尾差不能作为加工精度保证。[测量来源：较新官方 STEP 归档](https://files.waveshare.com/wiki/UPS_HAT_B/usb-hub-hat_b%203d%20drawing.zip)

**official-index-only：**[官方尺寸图 URL](https://www.waveshare.com/img/devkit/accBoard/USB-HUB-HAT-B/USB-HUB-HAT-B-details-size.jpg) 的搜索图像说明给出 65×30 mm 和 3.5 mm 边距；图片直取仍 403，本轮没有实际视觉确认标注、公差或孔径。故 65×30 可作为索引所述轮廓，与模型近似一致，但本报告的精确孔接口和包络依据是上列 STEP。

**版本差异：**还有 [旧官方 ZIP](https://files.waveshare.com/upload/6/65/USB_HUB_HAT_%28B%29.zip)，内含 `USB HUB HAT (B).step`，header 日期 `2021-07-26T17:38:35`，113 个实体；其四孔坐标/半径与上表一致，但全包络约 `65.022×30.022×9.086 mm`。两份参考模型的高度不一致，不能将较小包络当当前完整含 pogo 板的尺寸，或据此断言历史板的真实板厚/高度。没有供应商修订说明能将两份模型绑定到采购 PCB revision。

**missing：**实际产品含 pogo 时的高度公差、pogo 压缩/工作高度、安装支柱长度与紧固件长度、PCB 孔公差、机械装配图、连接器插头与电缆弯曲所需外部空间；没有采用 Raspberry Pi 标准孔径或标准叠板间距补造。

## 4. 固定文件、来源与许可

| 资料 | 来源/版本 | SHA256 |
|---|---|---|
| 原理图 PDF，387,222 B，2 页 | [官方文件](https://files.waveshare.com/upload/5/5c/USB_HUB_HAT_%28B%29_SchDoc.pdf)；PDF metadata：Altium Designer，2021-07-26 08:00:00 CST；未标 PCB revision | `212ec6ddc0e74d935a635f025ba3359bd9de0bfbc8d2ec01ccf710e26387cb2e` |
| 较新 ZIP，20,158,570 B | [官方 3D Drawing 下载](https://files.waveshare.com/wiki/UPS_HAT_B/usb-hub-hat_b%203d%20drawing.zip) | `7d402e463986b4f9ac72909bd1ed7cb52f5fea6709f69d4f99473e54d18d2155` |
| 较新 STEP，3,340,118 B | 上述 ZIP 中 `usb-hub-hat_b__asm.stp`，2023-12-18 header | `878067a0e357848357202308414d0cb9ad8b31b9cfc0cf96c14c5775add87272` |
| 旧 ZIP，612,061 B | [旧官方资源](https://files.waveshare.com/upload/6/65/USB_HUB_HAT_%28B%29.zip) | `cbc07b6490faa09dfe6fa54e4e26ac14b2c41b851ae2c08ecf9b310488b6c03e` |
| 旧 STEP | 上述旧 ZIP 中 `USB HUB HAT (B).step`，2021-07-26 header | `eaf0562134d0f8080aa9b0dae6ca91184d657ecefb50a13111c013cc8b9b83be` |

两份归档文件清单未见 LICENSE/使用条款。公开可下载不等于允许随机器人正式交付再分发；本轮仅私有读取、测量、记事实。供应商实际制造公差、PCB revision 对应、双电源用法和参考 CAD 许可均保留为缺口。

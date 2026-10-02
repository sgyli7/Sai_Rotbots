# ROBOTIS 舵机安装几何一手资料核查

检索日期：2026-09-28（Asia/Chongqing）。范围：XM430-W350-T + HN12-N101/HN12-I101；XC330-M288-T + 内置输出盘/X330 idler（FPX330-H101 套装）；追加 XM540-W270-T + HN13-N101/HN13-I101。本报告只记录安装接口事实与缺口，不冻结机器人驱动布局，也不作实机连续能力结论。

## 证据等级与取得状态

- **fact**：官方图明确标注、官方产品页直接说明，或官方 STEP 实体数值与已观看图纸交叉吻合。
- **derived**：从明确尺寸作算术转换，注明本报告自定义坐标；不是供应商另行给出的坐标表。
- **missing**：未取得、图未标注或本轮未完成几何验证；不得据外观补造。
- **assumption**：须在后续装配中验证的条件，不作为制造事实。

实际下载并逐页渲染观看了 XM430 总装 2D、XC330 2D、两组惯量坐标示意、HN12-N101 和 HN12-I101 独立 2D。两份 STEP 已下载，并读过文件头、产品名称与部分圆柱实体/坐标系记录；**未使用 CAD 内核打开三维实体或完成装配变换、干涉及拓扑检查**。STEP 可下载不等于已经完成安装面核验。

官方参考文件与本地渲染只存于私有忽略目录 `.scratch/vendor_geometry/`；未复制到正式 `cad/` 或 `meshes/`。图上均有 `FOR REFERENCE ONLY`。本轮未取得 CAD/PDF 的明确使用与再分发许可；“可公开下载”不能替代再分发许可。下载入口的网页版本未提供固定 commit SHA，因此以真实文件 SHA-256 固定本轮证据。

## 原文件及来源

所有以下条目均于 2026-09-28 检索。`download.php` 是 ROBOTIS 官方入口；其转出的 Dropbox 地址是本轮实际取得文件的来源，不是第三方重建 CAD。

| 编号 | 官方入口 / 实际文件 URL | 本地文件、版本和响应 |
| --- | --- | --- |
| G1 | [XM430 eManual](https://emanual.robotis.com/docs/en/dxl/x/xm430-w350/)、[PDF no=157](https://en.robotis.com/service/download.php?no=157) → [实际 PDF](https://www.dropbox.com/s/ytwcjx54iti4j4b/XM%2CH-430_idler.pdf?dl=1) | `XM,H-430_idler.pdf`；237317 B；响应 application/binary，内容为 PDF；标题 XM430/XH430 (HINGE)，2019/03/19，mm。实际文件 1 页，标题栏写 **1 of 2**；第二页未取得。 |
| G2 | [XM430 惯量 no=717](https://en.robotis.com/service/download.php?no=717) → [实际 PDF](https://www.dropbox.com/s/smmedgrjaqhuy6b/XM430%2CXH430%20Moment%20of%20Inertia.pdf?dl=1) | `XM430,XH430 Moment of Inertia.pdf`；132466 B；1 页；发布 Feb. 2023。 |
| G3 | [XC330 eManual](https://emanual.robotis.com/docs/en/dxl/x/xc330-m288/)、[PDF no=1986](https://en.robotis.com/service/download.php?no=1986) → [实际 PDF](https://www.dropbox.com/s/gxgye7wt5sbt4i4/XL,XC-330.pdf?dl=1) | `XL,XC-330.pdf`；149731 B；响应 application/binary，内容为 PDF；标题 X330，28-May-20，mm，1 of 1。 |
| G4 | [XC330 惯量 no=2136](https://en.robotis.com/service/download.php?no=2136) → [实际 PDF](https://www.dropbox.com/s/88jbmlyv8v1o73t/XL330%2CXC330%20Moment%20of%20Inertia.pdf?dl=1) | `XL330,XC330 Moment of Inertia.pdf`；137692 B；1 页；发布 Feb. 2023。 |
| G5 | [HN12-N101 PDF no=1735](https://en.robotis.com/service/download.php?no=1735) → [实际 PDF](https://www.dropbox.com/s/u1fib367r6wercu/HN12_N101.pdf?dl=1) | `HN12_N101.pdf`；51747 B；1 页；22-May-19，mm。 |
| G6 | [HN12-I101 PDF no=1757](https://en.robotis.com/service/download.php?no=1757) → [实际 PDF](https://www.dropbox.com/s/7ksyma4244ghb97/HN12_I101.pdf?dl=1) | `HN12_I101.pdf`；84608 B；1 页；22-May-19，mm。 |
| G7 | [XM430 STEP no=158](https://en.robotis.com/service/download.php?no=158) → [实际 STEP](https://www.dropbox.com/scl/fi/5h3gp05sd9kjgtma5nuw1/XM_H-430_idler.stp?rlkey=09db2f2uz3b9lkacbp31tsu6r&dl=1) | `XM_H-430_idler.stp`；698785 B；ISO-10303-21 / CONFIG_CONTROL_DESIGN；FILE_NAME `XM_H-430_IDLER_ASM`，文件头时间 2026-07-10T10:04:13，CREO PARAMETRIC。含 `DUMMY` 名称，是参考简化装配。 |
| G8 | [XC330 STEP no=1987](https://en.robotis.com/service/download.php?no=1987) → [实际 STEP](https://www.dropbox.com/s/qlzmp8mlvzrxmzu/XL,XC-330.stp?dl=1) | `XL,XC-330.stp`；791238 B；ISO-10303-21 / CONFIG_CONTROL_DESIGN；FILE_NAME `DC15_A01_DUMMY_ASSY_IDLE_ASM`，2020-07-27T17:44:15，CREO PARAMETRIC。 |

| 文件 | SHA-256 |
| --- | --- |
| G1 | `dc51987999be9a3e7605b60b9fdc4d832d9dd905c1c5a4b9be7980e7f1da4e7e` |
| G2 | `4d4781d13bfba7c6b9563516306b9406bf6e31db0f26484ab027634f41a13043` |
| G3 | `948b707cb26a64501c03fc45b1a9557b69a554dd5d6934f02e8e6f86cf2b46c2` |
| G4 | `dacd173dfde3de78effa6ccb94baeea98edf378d63424aa3b26af81adc0c3df2` |
| G5 | `0d6c309f8a45d81ffaabdb45982b7de0b6e7f74742cae850cff4e938b86a81fa` |
| G6 | `3cc6042dba0f183bbd06c45e234fdb1e55f7d3cc3ace8e2df4d81c0a8f7e1e33` |
| G7 | `7ff4e39475245d5c1fc4f703e9241fca1a09d57aed920274498dbe2cd5e31e22` |
| G8 | `e2f7b060801a1d6a21f23bca2554f29a402f7d73b8498cb201c9e6adf3139eb6` |

## 坐标与有效深度的口径

**fact，G2/G4 实际观看**：惯量图正视图以输出轴为 X/Y 原点，+X 向右、+Y 向机身顶部；侧视图 +Z 指向输出盘前方。图未用尺寸明确 Z=0 究竟在盘面、壳体面还是另一基准面。不能直接宣称惯量原点就是某安装面，也未完成惯量图与 STEP 原点之间的变换核验。

**本报告二维接口坐标定义**：正面看输出盘，轴心投影为 `(u,v)=(0,0)`，+u 向右，+v 向顶部。侧面/顶底面的 `d` 从**机身正面壳体平面**量起，向后为正。这个定义只用于记录图纸的标称孔位；不是正式 Goose 关节坐标。后视图必须镜像转换，不能把后视画面向右直接当 +u。

**fact，G1/G3/G5/G6 与官方装配说明**：`DP … Max` 是图给出的最大深度限制，不能当最小有效完整牙长度或连续承载能力；自攻预孔没有已经存在的 M2×0.4 螺纹。完整牙最小长度、孔口倒角、生产公差、锁紧扭矩、允许重复装拆次数和材料接合强度，本轮图纸均未完整给出。使用螺钉总长须扣除支架、垫片和间隔环占用，比较进入舵机的长度；不能直接令螺钉标称总长等于 DP。[官方安装深度说明](https://emanual.robotis.com/docs/en/dxl/x/xm430-w350/#frame-and-horn-assembly-precautions)

## XM430-W350-T：机身与 HN12-N101 / HN12-I101

### 配套零件与固定方式

**fact**：HN12-N101（SKU 903-0238-000）是 XM/XH430 标准输出 horn，套装含 WB M2.5×6 中心紧固件、WB M2×3 框架螺钉及 thrust washer。HN12-I101（903-0240-000）是对应后部 idler，含塑料轴承、DC12 cap 和 WB M2×3；idler 与机身采用 hook 结构，附带螺钉用于框架连接，不应凭总装剖面中的 M2.5 中孔臆造一个后端中心锁紧螺钉。[HN12-N101 原厂页](https://robotis.us/products/hn12-n101-set)、[HN12-I101 原厂页](https://robotis.us/products/hn12-i101-set)

**fact**：官方装配要求 washer 正确就位，horn 的 index marking 与输出轴 marking 对齐；这只是安装相位事实，不能自动定义 Goose 的关节零位或编码器零位。[XM430 官方装配说明](https://emanual.robotis.com/docs/en/dxl/x/xm430-w350/#normal-horn-assembly)

### 实际看图后的接口表

| 接口 | fact：原图标注 / derived：本报告转换 | 制造解释及缺口 |
| --- | --- | --- |
| 机身 | G1：28.5 W ×46.5 H ×34 D mm；轴心距顶边 11.25 mm | D=34 在侧视图量机身前后壳体面；不是含所有 horn、螺钉头的装配总深度。 |
| 前面静态框架孔 | G1：2×M2.5×0.45 TAP、DP3.0 Max；横向孔距22，位于轴下8 | derived：`(-11,-8)`、`(+11,-8)` mm。前面四角标 `WB M2.5×12 SCREW` 是现有壳体紧固件，不能当四个空闲安装孔。 |
| 左右侧静态框架孔 | G1：每侧4×M2.5×0.45 TAP、DP3.0 Max；深度方向11起、再跨12；上行在轴下4，上下跨24 | derived：每侧 `(d,v)=(11,-4),(23,-4),(11,-28),(23,-28)` mm。安装面侧别、孔轴朝内方向应保留，避免翻面对换。 |
| 顶面静态孔 | G1：2×M2.5×0.45 TAP、DP3.0 Max，d=11；G7 圆柱轴记录横向u=±8 | `u=±8,d=11`；由壳宽换算的侧面位置不是一个新采购接口。 |
| 底面静态孔 | G1：4×M2.5×0.45 TAP、DP3.0 Max；横向跨16，d=11/23 | derived：`(u,d)=(-8,11),(8,11),(-8,23),(8,23)` mm。 |
| HN12-N101 输出连接孔 | G5：Ø19.5外盘；8×M2×0.4 **TAP THRU**、PCDØ16；盘片厚2；G1 总装却限制 DP2 Max | 单件通牙与装机最大进入深度须分开记录。derived：环孔 `(u,v)=(8cosθ,8sinθ)`，θ=0°,45°,…315°，按图中上下左右孔相位；斜角约±5.656854。G7圆柱记录与这个孔圆相符。 |
| HN12-N101 中央凸台/轴配合 | G5：中心凸台Ø8，剖面总厚4.2，另有3.45台阶；DC12 serration示意20齿、92°、Ø5.8/Ø5.2 | 可识别配套接口；没有齿形完整公差和配合等级，不能把示意图当自制花键验收规格。 |
| HN12-I101 框架连接孔 | G6：Ø19.5；8×M2×0.4 TAP DP2，PCDØ16，盘片厚2 | 与输出盘同孔圆；后视的相位/坐标镜像仍须按装配方向处理。 |
| HN12-I101 轴承/通道 | G6剖面：Ø12.2、Ø9.5、Ø13；明确有 PLASTIC BEARING | 这些直径对应独立图剖面的位置，不能把任一个直接称作舵机花键孔径或螺纹孔。通道净空还需 cap、导线和机身总装核验。 |

**derived，G1 侧视图**：普通 horn 外盘相对机身前壳面突出2 mm，后 idler 外盘相对后壳面突出2 mm；前后框架盘面间距标称 `34+2+2=38 mm`。中央Ø8 boss 比前盘面再突出2.2 mm；此38 mm不含中心螺钉头，也不是对供应商公差的保证。已看侧视局部图，而非通过未标注像素比例测量。

### STEP 与图纸的交叉核验限度

**fact，G7 原始文本**：PCD16 的圆柱轴心记录存在 `(0,±8)`、`(±8,0)`、`(±5.656854249492,±5.656854249492)`；前面两个框架孔轴记录 `u=±11,v=-8`；侧面轴记录 `v=-4/-28`。图纸的 M2/M2.5 螺纹在参考 STEP 中简化为圆柱，并未建模成完整螺旋牙。**不能用参考圆柱半径0.8或1.025自行改写图纸的 M2/M2.5 螺纹规格。**

**missing**：G7 产品时间为2026，而2D为2019；未取得供应商修订记录说明是否仅导出时间变更。总装图标题栏缺失的第二页未取得。三维模型坐标 Z 与惯量 Z原点、实际 horn 接触面、零位 indexing 的刚性变换未全部核验；没有完成“带公差、带装配方向的完整制造接口”验收。

## XC330-M288-T：机身、内置输出盘与 X330 idler

### 配套零件与紧固件

**fact**：XC330 自带输出盘；官方产品页含 PHS M2×6 TAP（horn）与 PHS M2×8 TAP（frame）。后端 idler/cap 属 FPX330-H101 4PCS SET（903-0302-000），并非同页面可单买独立 idler。该套装列 BHS M2.6×6 TAP（idler）、PHS M2×4 TAP（horn-to-frame），以及普通 M2螺钉/螺母（frame）。不同连接位置与板厚使用不同长度，不能把包装里的6/8 mm当可直接全长进入塑料的深度。[XC330-M288-T 原厂页](https://en.robotis.com/shop_en/item.php?it_id=902-0173-000)、[FPX330-H101 原厂页](https://en.robotis.com/shop_en/item.php?it_id=903-0302-000)

**missing**：官方套装称零件为 `Idler`，没有本轮可证实的独立 horn/idler SKU；本报告不编造 HNxx 名称。参考 STEP 内部零件 `DC15_A01_HORN_IDLE2_DUMMY` 和紧固件 `BTS2_M2_6X8` 不是售卖件号；它与当前套装 M2.6×6 的长度不同，须保留文件版本差异，不据此替换采购螺钉。

### 实际看图后的接口表

| 接口 | fact：原图标注 / derived：转换 | 制造解释及缺口 |
| --- | --- | --- |
| 机身和轴心 | G3：20 W ×34 H；机身深23、前盘突出3；轴距顶9.5 | 标准外深 `23+3=26 mm`；装后idler图外深29，即前3+机身23+后3。不含未知螺钉头突出。 |
| 输出盘 | G3：外Ø16；4×Ø1.6 HOLE、DP3.0 Max，PCDØ12；Using M2 Tapping Screw | **不是M2×0.4预攻牙**。derived：四孔 `(0,6),(6,0),(0,-6),(-6,0)` mm；PCD与孔径、孔深各是不同参数。 |
| 后 idler 盘 | G3 `[X330 IDLER]`：外Ø16；相同4×Ø1.6 DP3.0 Max、PCDØ12、M2 tapping | 与430的PCD16/8孔不能互换。后视坐标变换仍要定义镜像。 |
| 前后四个静态机身框架孔 | G3：水平16、垂直30；Using M2 Tapping Screw；前看 Detail A，后看 Detail B | fact，G8圆柱实体与G3图吻合：孔心 `u=±8,v=+7.5/-22.5` mm。前后不同引导段，不能仅用相同二维孔位宣称前后深度相同。壳体自带十字螺钉的位置另列，不是这四个空闲孔。 |
| Detail A（前静态孔） | G3剖面：Ø2引导/光孔段长度3.5，后接Ø1.6预孔 | **3.5不是有效牙长度**。该剖面未给Ø1.6段完整长度/允许螺钉最大侵入，本轮不能补成某个螺纹深度。 |
| Detail B（后静态孔） | G3剖面：Ø2引导/光孔段长度4.5，接Ø1.6预孔 | **4.5不是有效牙长度**；与前段3.5存在真实差别。同样缺完整最小有效接合深度。 |
| idler 中心紧固接口 | 官方套装列 BHS M2.6×6 TAP | G3未标出中心预孔径、完整深度或装配扭矩；本轮未自行编制中心孔精确制造坐标。 |

**fact，G8 数值交叉核对**：机身件的 `CYLINDRICAL_SURFACE` Ø1.6 和 Ø2轴线记录出现 `(+8,+7.5),(-8,+7.5),(+8,-22.5),(-8,-22.5)`。机身前件坐标变换记录为 identity，后件平移记录 `(0,0,-19.5)`；本报告只把共同二维投影用于孔位交叉证实，未将这个平移量直接当23 mm机身总深或安装面距离。输出盘是另一局部坐标系，其Ø1.6四孔位于局部半径6；装配中还带旋转，不能把原始零件局部 XYZ直接粘到机身坐标表。

**missing**：G3未给侧面安装孔，不应移植XM430侧面的4孔模板。塑料自攻孔螺钉牙形、孔材真实壁厚、允许装拆次数、制造公差和最小接合长度均未取得；本轮只形成孔位/孔类型事实，不宣称接口已达到实物制造放行。

## 惯量图和安装几何的分界

**fact**：G2 的 XM430-W350 行质量82 g；G4 的 XC330-M288 行质量23 g。相应 CG分别为 `(-0.40710295,-15.312099,-16.718279)` 和 `(-0.23138703,-7.5535115,-11.165635)` mm，均由各自图中轴系表示。两页还给 `g·mm²` 的惯量张量，但没有本轮可核明的“关于何点”的补充说明；这里不做平行轴转换、不生成机器人惯量，也不把参考质量视为带线缆/支架装配的称重结果。[G2 官方惯量入口](https://en.robotis.com/service/download.php?no=717)、[G4 官方惯量入口](https://en.robotis.com/service/download.php?no=2136)

## 本轮可用于工程映射的差异与仍需补证的事项

1. **430与330不是同一输出接口**：430为PCD16的8个M2×0.4孔；330为PCD12的4个Ø1.6塑料自攻预孔。螺钉类型、孔数、分布和可进入深度不能共用模板。
2. **同一430 horn，单件与装机深度口径不同**：HN12-N101单件是通牙，装机总图是DP2 Max；决定板厚后的螺钉侵入长度需要独立计算。
3. **330前后框架孔同投影、不同引导段**：3.5/4.5 mm属于Ø2光孔部分，不是可用牙长。中心 idler 紧固接口仍缺完整孔图。
4. **安装盘间距是装配值**：430标称38 mm；330带idler29 mm总外深。不能用产品裸壳深度直接替代支架开档；仍缺公差闭合、cap与螺钉头净空核验。
5. **参考CAD尚未成为正式制造交付**：已取得官方STEP本体且有哈希；全三维原点、朝向、干涉及许可未闭合，不能描述为“制造CAD已确认可再分发”。

## XM540-W270-T 追加核查

### 官方型号、电气与估计口径

以下网页于2026-09-28实际读取；ROBOTIS新Docs与旧eManual均可访问，新Docs对应页已交叉核对。

| 项目 | fact | 一手来源 |
| --- | --- | --- |
| 型号、尺寸、质量 | XM540-W270-T/R共用手册几何：33.5×58.5×44 mm，165 g；272.5:1 | [当前 ROBOTIS Docs](https://docs.robotis.com/docs/dxl/model_reference/x_series/xm_series/xm540-w270/)、[旧 eManual](https://emanual.robotis.com/docs/en/dxl/x/xm540-w270/) |
| 供电与待机 | 10.0–14.8 V；推荐12.0 V；standby40 mA | 同上 |
| 12 V 工作点 | **堵转**10.6 N·m、4.4 A；**空载**30 rpm | 同上；二者不是同一个可持续工作点 |
| 11.1/14.8 V | 堵转分别10.0/12.9 N·m，4.2/5.5 A；空载28/37 rpm | 同上 |
| 模式、T接口 | Current、Velocity、Position、Extended Position、Current-based Position、PWM；T为TTL half duplex，3pin GND/VDD/DATA | [Docs控制与连接器表](https://docs.robotis.com/docs/dxl/model_reference/x_series/xm_series/xm540-w270/#connector-information)、[型号T官方店](https://robotis.us/products/dynamixel-xm540-w270-t) |
| 店面估计“rated torque” | 美国官方店给2.12 N·m，并明确为以堵转力矩20%计算的**连续力矩估计**；算术10.6×0.2=2.12 | [美国官方店](https://robotis.us/products/dynamixel-xm540-w270-t) |

**missing/差异**：没有取得2.12 N·m的连续热稳态试验条件、环境温度、占空比或寿命证据；本报告不得将其写为已经实测的连续额定力矩。手册也明确区分瞬时堵转与连续/实际工作表现。官方US店深度为45 mm，当前Docs与下列总装图为44 mm；保留这个1 mm资料差异。US店T页面的Package Contents误写XM540-W270-R并同时列TTL线缆，不能凭该行改变已明确的T型号接口或直接冻结BOM版本。

### 新取得且实际观看的540参考图

所有文件位于同一私有`.scratch/vendor_geometry/`，响应application/binary但内容为PDF，均已渲染实际观看；许可状态与前文相同，没有移入正式交付。

| 编号 | 官方入口 → 实际来源 | 本轮文件/版本/SHA-256 |
| --- | --- | --- |
| G9 | [总装PDF no=2083](https://en.robotis.com/service/download.php?no=2083) → [实际文件](https://www.dropbox.com/s/ij7egaiuzsoprki/XM%2CH%2CD-540.N101.I101.pdf?dl=1) | `XM,H,D-540.N101.I101.pdf`，260599 B；标题XM540/XH540/XD540(HINGE)，2019/03/18；PDF元数据创建2021-08-26；实际1页，标题栏1 of 2，第二页未取得。SHA `7580d96cb2c03ee256d52b89d0bfc3f5b9fe45fbbe5aa090dcb2c9e1e0d62b31` |
| G10 | [惯量PDF no=718](https://en.robotis.com/service/download.php?no=718) → [实际文件](https://www.dropbox.com/s/47ubccyj9dh6myw/XM540%2CXH540%20Moment%20of%20Inertia.pdf?dl=1) | `XM540,XH540 Moment of Inertia.pdf`，144451 B，1页，Feb.2023；SHA `5d71a6f462fedb5e8529ad8c62c9e82b8ed123ea3a2a4b40df63b2ea337cbaa7` |
| G11 | [HN13-N101 PDF no=1737](https://en.robotis.com/service/download.php?no=1737) → [实际文件](https://www.dropbox.com/s/ry89g6jkfavwr6l/HN13_N101.pdf?dl=1) | `HN13_N101.pdf`，66317 B，1页，22-May-19；首次请求超时，第二次成功并看图；SHA `761a049309bce2242ab295332a488d024c0a68b5af8560c892f016db3ba93f44` |
| G12 | [HN13-I101 PDF no=1753](https://en.robotis.com/service/download.php?no=1753) → [实际文件](https://www.dropbox.com/s/v6cza08i9oxrv5h/HN13_I101.pdf?dl=1) | `HN13_I101.pdf`，40204 B，1页，22-May-19；SHA `5f4aed8ba809107aa9fca20ece692095d3304f322f11548d387f2ac966c6a1aa` |

### 配套horn/idler及可映射的接口

**fact**：HN13-N101（903-0276-000）为X540标准horn，中心使用WB M3×8，框架使用WB M2.5×4，带thrust washer。HN13-I101（903-0267-000）为X540 idler，含6701ZZ轴承和DC13 cap，框架螺钉WB M2.5×4；与机身仍通过hook连接，套装没有把中心螺钉作为idler固定方案。[HN13-N101官方页](https://robotis.us/products/hn13-n101-set)、[HN13-I101官方页](https://robotis.us/products/hn13-i101-set)

| 接口 | fact：实际看图标注 / derived：本报告转换 | 缺口及解释 |
| --- | --- | --- |
| 输出轴位置 | G9：距机身顶边13.75 mm | +u/+v沿用前文正视定义，不自动成为颈关节安装零位。 |
| 机身前静态孔 | G9：2×M2.5×0.45 TAP、DP4.0 Max；孔距27，在轴下10.5 | derived：`(±13.5,-10.5)` mm。四角WB M2.5×17是壳体已有紧固件。 |
| 两侧静态孔 | G9：每侧4×M2.5×0.45 TAP、DP4.0 Max；d=14起，再跨16；上行轴下6、上下跨32 | derived：`(d,v)=(14,-6),(30,-6),(14,-38),(30,-38)` mm。不能沿用430的DP3或11/23、-4/-28模板。 |
| 顶底面 | G9：顶2孔、底4孔，均M2.5×0.45 DP4.0 Max；顶d=14，底d=14/30、横向跨20 | 底孔derived：`u=±10,d=14/30`；顶横向数值未单独标注，未以外观补精确坐标。 |
| HN13-N101标准螺纹圈 | G11：外盘Ø26；8×M2.5×0.45 TAP THRU，PCDØ22；盘片2.6厚；G9装机DP2.5 Max | derived：`(u,v)=(11cosθ,11sinθ)`，θ=0°,45°,…315°；斜角约±7.7781746。单件通牙不能覆盖装机2.5 mm最大侵入限制。 |
| HN13-N101附加孔 | G11：4×Ø2 HOLE THRU，PCDØ16；G9总装DP2.5 Max | 四个光孔，derived：`(0,±8),(±8,0)`。这不等于430的8个M2螺纹孔，不能宣称“PCD16所以直接兼容”。 |
| HN13-N101轴接口 | G11：中央bossØ10，总厚4.9，另有3.7台阶；DC13 serration示意32齿、90°、Ø8/Ø7.4 | 齿形公差/配合等级仍缺，不是自行制造替代horn的验收图。 |
| HN13-I101框架圈 | G12：Ø26外盘；8×M2.5×0.45 TAP DP2.5，PCDØ22；盘片2.5厚 | 与N101共孔圆，后视方向仍须镜像；非M2紧固件。 |
| HN13-I101剖面 | G12：Ø18.2、Ø10、Ø12及BEARING | 这些是不同剖面位置的几何，不应当作相同孔径；6701ZZ件号来自官方套装表。 |

**derived，G9已看侧视局部**：机身44，前盘突出2.6、后盘突出2.5，前后框架盘面距离标称 `44+2.6+2.5=49.1 mm`。同一图另标51.9的尺寸链端点涉及前部中心紧固件与机身后面，不能不看端点就写成带后idler的完整总深度。螺钉头、cap和导线实际最大包络/装配公差未闭合。

**fact，G10**：XM540-W270行165 g，CG `(-0.40371505,-19.876023,-21.321536)` mm。实际观看图中的+X正视右、+Y向顶部、+Z向输出前方；Z=0面同样未明确尺寸化。惯量图已取得不代表已建立供应商CAD、安装面和机器人惯量之间的精确转换。

**missing**：540 STEP官方入口[no=2084](https://en.robotis.com/service/download.php?no=2084)存在，但本轮未下载/三维打开；没有核验制造公差、最小完整牙长度、装配面全变换和长期负载能力。颈根轴是否采用540由根agent结合整体工程预算判断，本报告没有给出定型建议。


## 追加：原厂 H/S frames 的用户连接接口（2026-09-28 限时核查）

### 范围、实际检查与关键更正

本轮只核对 FPX330-H101/S101/S102、FR12-H101K/S101K/S102K、FR13-H101K/S101K 的原始接口与供应商包装，未选择最终骨架。**H101 是随 horn/idler 转动的输出铰链框架；静态机身安装对应 S 类框架。采购 H101 本身不能替代静态机身固定。**330 H 套装确有4个hinge frame、4个idler、4个cap；不能把“4个frame”理解为四个静态机身框架。[330 H 官方套装](https://en.robotis.com/shop_en/item.php?it_id=903-0302-000)

**检查状态 fact**：下面8个框架的官方二维 PDF 均已下载、渲染并实际观看；官方装配爆炸图也已实际看图。8个单件 STEP 均已用本工作树的 build123d 0.11.1 / OpenCascade 读取，返回有效实体；提取真实圆柱面坐标、包围盒，不从外观编孔位。330 H 的 STEP 另已生成底面等轴投影视图并实际观看；其他 STEP 的“已打开”指几何内核解析，不声称另有交互三维检查。原始文件与衍生预览只在私有 `.scratch/vendor_geometry/`，未复制到正式 CAD 目录。

**许可 missing**：ROBOTIS页面页脚可见CC BY 4.0说明，但本轮未找到把该许可明确适用于这些独立 STEP/PDF 的逐文件授权；PDF仍为参考图，未给制造公差。公开可下载不等于已确认再分发/衍生制造资产许可。所有文件无固定Git commit；以供应商标题日期、STEP header和SHA-256固定取证版本。

### 330：静态 S101 / S102 与输出 H101

| 真正型号/官方SKU | 包装 fact | 装配用途 fact |
| --- | --- | --- |
| [FPX330-S101，903-0301-000](https://en.robotis.com/shop_en/item.php?it_id=903-0301-000) | 4 frames；NUT M2×20；普通PHS M2×4×20；PHS M2×4 TAP×20（horn）；PHS M2×8 TAP×20（body） | 实际爆炸图：长框架安装在机身左右侧，四个耳孔使用原厂M2×8 TAP连接壳体前/后角孔。 |
| [FPX330-S102，903-0300-000](https://en.robotis.com/shop_en/item.php?it_id=903-0300-000) | 数量和螺钉种类与S101相同 | 实际爆炸图：短框架用于机身顶/底，耳孔同样使用M2×8 TAP。 |
| [FPX330-H101，903-0302-000](https://en.robotis.com/shop_en/item.php?it_id=903-0302-000) | 4 hinge frames、4 idlers、4 caps；M2 nuts×20，普通M2×4×20，M2×4 TAP×36，M2.6×6 TAP×8 | 两臂固定在输出horn与后idler上，用M2×4 TAP；中心idler/cap用M2.6×6 TAP。包装写BHS，爆炸图标BTS，长度均6。不是静态frame。 |

图像来源：[S101左右侧爆炸图](https://en.robotis.com/data/item/sharedfile/210603164453_RVAZuvB1_dd1e6df59d7d2eac2c046fe3bff3f84077cd3bae.jpg)、[S102顶底爆炸图](https://en.robotis.com/data/item/sharedfile/210603164437_gGtLuejR_6fca35d79f33a1bbec4737fc650c69dea8f9051d.jpg)、[H101输出铰链爆炸图](https://en.robotis.com/data/item/explain/1893207946_5f761778_xl330_h101_ECA084EAB09CEB8F84.png)。前两张同时出现在S101商品页；第二张图内明确标S102，未把商品页归属当图中零件型号。

**检索时供货信号 fact**：全球官方S101页明确缺货；S102全球页可选数量，但美国官方页另提示约2个月准备期，并存在页面销售控件状态混杂。这里只记录供应商页面信号，不承诺库存/中国可采购交期。[S101全球页](https://en.robotis.com/shop_en/item.php?it_id=903-0301-000)、[S102美国页](https://robotis.us/products/fpx330-s102-4pcs-set)

330 静态框架仍使用原厂自攻螺钉连接机身；它提供的是已配套的供应商机身侧接口和**用户侧普通螺钉/螺母通孔**，没有公布自攻有效深度的新数据。用户接板无需因此自行假设机身孔的有效自攻深度；同样不能以套装M2×8长度倒推出机身允许8 mm侵入。

下面坐标均为 **derived from vendor reference STEP / PDF**，单位mm；不是公差/承载验收值。S框架用户平板局部坐标 `(u,v)=(STEP X,STEP Z)`，平板外表面STEP Y=3、名义内表面Y=0；O为平板几何中心，+u沿S101长34/S102长20方向，+v沿跨机身深度方向28.6。H框架用户平板定义 `(u,v)=(STEP Z,STEP X)`，O为中央Ø8孔中心，+u沿34.6长边，+v沿20短边。该局部定义不是机器人关节零位。

| 框架 | 外形、安装内档 fact/derived | 连接用户平板的光孔与孔距 |
| --- | --- | --- |
| S101 | STEP bbox X±17、Y[-4,3]、Z±14.3；外档34×28.6×7；跨机身内档23，用户平板名义厚3；两Ø8中心u=±7.5，即中心距15 | 20×Ø2.05通孔：每一中心各4孔PCD12 cardinal、4孔PCD16 diagonal；另4孔 `(u,v)=(±10.5,±9)`，形成**21×18矩形**。4×Ø1.6在 `(±4,±8)`，不能当M2光孔。耳孔每端2×Ø2.05，孔距30；属于机身装配接口。 |
| S102 | STEP bbox X±10、Y[-4,3]、Z±14.3；外档20×28.6×7；内档23、平板厚3；Ø8中心O | 12×Ø2.05：PCD12 cardinal4孔、PCD16 diagonal4孔、另 `(±3,±9)`4孔形成**6×18矩形**。4×Ø1.6在 `(±8,±8)`。耳孔每端2×Ø2.05，孔距16，属于机身装配接口。 |
| H101 | STEP bbox X±10、Y[-22,3]、Z±17.3；外档20×25×34.6，两臂内档29，平板厚3；输出臂孔中心距用户板外表面17（STEP Y=-14到Y=3） | 顶板18×Ø2.05：PCD12 cardinal4、PCD16 diagonal4、`(u,v)=(±9,±3)`4、`u=±12,v=-6/0/+6`6；其中四孔 `(±12,±6)` 为**24×12矩形**。4×Ø1.6在 `(±8,±8)`，中央Ø8。两输出臂各4×Ø2.05 PCD12和中央Ø6，另3×Ø1.6间距6。 |

PCD12 cardinal：相对各中心 `(±6,0),(0,±6)`；PCD16 diagonal：`(±5.656854249,±5.656854249)`。上述大通孔底面含螺母/螺钉头退让结构，STEP小圆柱直段通常只覆盖Y=1.8–3，不应把这个1.2 mm直段当作整块板厚。实际观看底面图与 H101 CAD 投影，确认有螺母槽/加强筋；无槽宽、公差或可使用任何标准螺母品牌的验收数据。普通M2×4和M2 nuts是官方用户连接配套；**自研接板厚度、垫片、螺母和螺钉头会改变所需螺钉长度，不能默认套装4 mm足够**。

### 430/540：真实SKU、H/S用途与版本差异

| 官方型号 / SKU | fact：包装关键件、用途 | 当前供应/资料差异 |
| --- | --- | --- |
| [FR12-H101K / 903-0239-000](https://en.robotis.com/shop_en/item.php?it_id=903-0239-000) | 输出hinge；1 frame+1 HN12-I101 set；FHS M2.5×14×4，WB M2×3×10、M2.5×4×8、spacer rings×10 | 对应XM430/XH430；本轮未核中国渠道库存。 |
| [FR12-S101K / 903-0241-000](https://en.robotis.com/shop_en/item.php?it_id=903-0241-000) | 长静态side frame，1件；与S102相同：FHS M2.5×14×4、WB M2×3×10、WB M2.5×4×8、rings×10、spacers×5 | 官方XM430爆炸图实际为侧面安装。 |
| [FR12-S102K / 903-0242-000](https://en.robotis.com/shop_en/item.php?it_id=903-0242-000) | 短静态frame，1件；与S101相同配套 | 官方XM430爆炸图实际为底面安装。 |
| [FR13-H101K / 903-0270-300](https://en.robotis.com/shop_en/item.php?it_id=903-0270-300) | X540输出hinge，1件；FWB M2.5×17×4、WB M2.5×5×8、WB M2.5×4×18、rings×10；附idler set | **全球店本轮明确Out of stock**。组件表将idler写成“FR13-I101 Set”，而舵机手册/独立idler商品为HN13-I101（903-0267-000），命名未闭合，不能把网页文字当另一真实SKU。 |
| [FR13-S101K / 903-0268-300](https://en.robotis.com/shop_en/item.php?it_id=903-0268-300) | X540长静态frame，1件；FWB M2.5×17×4、WB M2.5×5×8、WB M2.5×4×10、rings×10 | 文案写bottom side，但实际配图是侧面长frame，与图内S101标注一致；报告记录文案/图示差异，不据文案改变几何。 |

**fact**：上述FR12/FR13商品页均公告Q1 2026外观running change、功能与安装方法保持，库存中旧外观仍可能出货。下载中心本轮返回的是**2026-01-07**新PDF/STEP。商品存在不等于版本/配套库存已经锁定；若按新外形设计贴合槽，必须对应实际交付版本。FR12/13的正式商品名包含K，不能用不带K的口头简称代替采购SKU。[官方Frame下载目录](https://en.robotis.com/service/downloadpage.php?ca_id=7030)

**实际装配图 fact**：FR12 S安装先取下现有WB M2.5×12壳体角螺钉，然后装spacer rings，以FHS M2.5×14替换；FR13 S图先取下WB M2.5×17，再配ring/FWB M2.5×17。S通过原厂壳体闭合孔固定，不是把这些四角孔解释为空的新增用户孔。H通过horn与idler圆周孔连接，不固定在静态壳体上。[430 S101图](https://en.robotis.com/data/item/explain/1893207946_40cfba87_fr12-xh430_05.png)、[430 S102图](https://en.robotis.com/data/item/explain/1893207946_36d070e3_fr12-xh430_06.png)、[540 S101图](https://en.robotis.com/data/item/explain/1893207946_030ca760_fr13-xh540_02.png)

### 430/540 用户板接口：仅给已核的可映射孔组

FR H用户面为STEP XZ平面，`(u,v)=(X,Z)`，O为顶板中心孔；FR S用户面为STEP XY平面，`(u,v)=(X,Y)`，O为上方中心孔。S第二组中心在v=-24（430 S101）或v=-31（540 S101）。坐标只对应下面固定参考版本；后视/翻转安装须另做变换。

| 型号 | fact/derived：单件包络、内档、用户板厚 | fact：用户接板光孔 |
| --- | --- | --- |
| FR12-H101K | STEP外档41×30.5×24；PDF两臂内档38、板厚1.5、平板直段宽36；非含舵机/线缆整机包络 | 顶板8×Ø2 HOLE THRU、PCD16；另4×Ø2.5普通通孔，STEP精确位置 `(-8,+3.5),(-3.5,-8),(+3.5,+8),(+8,-3.5)`。 |
| FR12-S101K | STEP外档37×46×11.5；PDF内档34、板厚1.5；侧耳安装孔距40 | 每中心8×Ø2 PCD16、另4×Ø2 PCD22的45°斜角孔；普通4×Ø2.5位置 `(-8,-3.5),(-3.5,+8),(+3.5,-8),(+8,+3.5)`，第二组平移v=-24。 |
| FR12-S102K | STEP外档37×28×11.5；PDF内档34、板厚1.5；耳孔距22 | 单组光孔与S101上方组相同；只一组中心。 |
| FR13-H101K | STEP外档53×34.5×32；PDF内档49、板厚2、平板直段宽47 | 顶板8×Ø2.5 HOLE THRU、PCD22：`(11cosθ,11sinθ)`，θ每45°；另4×Ø2.5矩形 `(±16,±8)`，即32×16。 |
| FR13-S101K | STEP外档48×58×13；PDF内档44、板厚2；侧耳孔距52 | 每中心8×Ø2.5 PCD22；第二组中心v=-31；本轮不把其他带牙孔混记为普通通孔。 |

**差异与 missing**：FR12/13平板还有多组M2.5×0.45 TAP THRU与其他光孔；不得只看标称2.5大径或二维圆形就当光孔。上述普通通孔位置由PDF标签与STEP贯穿圆柱交叉核对；其他带牙孔未展开完整映射。430的Ø2 nominal孔与M2螺钉外径同名义值，无公差保证；需配合原厂件实际孔和用户板工艺，不能宣称已经完成任意M2螺栓间隙验证。540 H的内档49与前文舵机horn/idler名义面间49.1来自不同参考图，0.1 mm差异保留，未形成公差闭合结论。所有包络均单个frame，不含spacer、螺钉头、servo、horn、idler、线缆与打印接板的总装最大包络。

**没有取得**：frame材料具体牌号/质量、制造公差、推荐连接力矩、实际供货版外形、国内渠道可采购数量、用户接板螺母/扳手全部空间、任意用户板厚下的螺钉长度和完整防干涉验证。报告没有把这些缺失项补成机器人设计结论。

### 本轮新增参考文件与固定版本

以下均检索于2026-09-28（UTC 2026-09-27）；官方入口实际转向ROBOTIS提供的Dropbox，响应application/binary，实质分别PDF或ISO-10303-21 STEP。保存名为私有取证名称；右侧实际URL中的名字才是供应商原文件名。

| 私有取证文件 | 官方入口 → 实际文件 | 字节 / SHA-256 / 标题版本 |
| --- | --- | --- |
| `fpx330-h101.pdf` | [no=2016](https://en.robotis.com/service/download.php?no=2016) → [供应商文件](https://www.dropbox.com/scl/fi/sh1c6jnlwfzivh3cou5b0/fpx330-h101.pdf?rlkey=d6q47aq7djfc0i3g6fd8nlknc&dl=1) | 113037 B；SHA `3a2fea7f8002adc2e7e76b3f170a72aec9309e2bf5f26ee63b769980c34e775a`；PDF：Mar-19-21 |
| `fpx330-h101.stp` | [no=2017](https://en.robotis.com/service/download.php?no=2017) → [供应商文件](https://www.dropbox.com/scl/fi/tl2hh62ikesv59918pase/fpx330-h101.stp?rlkey=4d1i8afwgeeklycky22xn96y3&dl=1) | 1134483 B；SHA `c284cc3a0d420c3ac8096ab4c74e8b3e01ec3379e5d565b409a3fea654170a21`；2023-09-27T09:41:19 |
| `fpx330-s101.pdf` | [no=2020](https://en.robotis.com/service/download.php?no=2020) → [供应商文件](https://www.dropbox.com/s/ty8x4406mq84l1f/fpx330-s101.pdf?dl=1) | 86902 B；SHA `177c5f3ea6803cd1f68dc1342c5ba6f687e3580eeb8c8d90f53b523e1606c357`；PDF：Mar-19-21 |
| `fpx330-s102.pdf` | [no=2024](https://en.robotis.com/service/download.php?no=2024) → [供应商文件](https://www.dropbox.com/s/y93i0bnf8x16wsy/fpx330-s102.pdf?dl=1) | 74158 B；SHA `b9e4cfa2986fb362b83eac0ae385a1ef53b400ea7730a51802d59bad8f320f27`；PDF：Mar-19-21 |
| `fr12-h101k.pdf` | [no=312](https://en.robotis.com/service/download.php?no=312) → [供应商文件](https://www.dropbox.com/scl/fi/2ioem4gs9gh0e5bqf3qq2/fr12_h101_k.pdf?rlkey=y5ojc4do2oi0tl3kcipeiwhg9&dl=1) | 117961 B；SHA `50c41e8d6548f0a89becbb569dd41a250914fe673e20624c1460b0b298a381bf`；PDF：2026/01/07 |
| `fr12-s101k.pdf` | [no=315](https://en.robotis.com/service/download.php?no=315) → [供应商文件](https://www.dropbox.com/scl/fi/55ix904zmeow3r63tykwg/fr12_s101_k.pdf?rlkey=etktki9jegho26lliql3588oc&dl=1) | 217489 B；SHA `7c42220837046bd534d7346c34c448b830f7e3f7dc6b9bb1979eb047f71031ee`；PDF：2026/01/07 |
| `fr12-s102k.pdf` | [no=318](https://en.robotis.com/service/download.php?no=318) → [供应商文件](https://www.dropbox.com/scl/fi/g9yl2pelhti4seadghtop/fr12_s102_k.pdf?rlkey=avwn6z88jt5xv3ysci5knz1q1&dl=1) | 148223 B；SHA `4bd94a30b2c8a6cd61634871099b717f5e683db72358b81840e6f60c67c104f8`；PDF：2026/01/07 |
| `fr13-h101k.pdf` | [no=694](https://en.robotis.com/service/download.php?no=694) → [供应商文件](https://www.dropbox.com/scl/fi/wrcrvkgq46hppr480rfnm/fr13_h101_k.pdf?rlkey=irq00iz270chu2qrv7s9sbdcl&dl=1) | 181222 B；SHA `5932d7ac888527235ec0135943e10ea75497d2deff27423908d044fcc9c68ba6`；PDF：2026/01/07 |
| `fr13-s101k.pdf` | [no=697](https://en.robotis.com/service/download.php?no=697) → [供应商文件](https://www.dropbox.com/scl/fi/n3ve7xjh4y0cnanytzs4f/fr13_s101_k.pdf?rlkey=nbywdiouhksdhb8ywsr5lnb4z&dl=1) | 270266 B；SHA `d15db2c6cebbbed22e8ba8173ce71a3bd4687b7971bd48162da4518c2cb3fafa`；PDF：2026/01/07 |
| `fpx330-s101.stp` | [no=2021](https://en.robotis.com/service/download.php?no=2021) → [供应商文件](https://www.dropbox.com/s/0r7j3hrj1vbjeab/fpx330-s101.stp?dl=1) | 933875 B；SHA `4ffee845a49fadf7b91862ebecee8debfe3801e7213f35bebc3d9007cc25300e`；2021-03-26T10:14:28 |
| `fpx330-s102.stp` | [no=2025](https://en.robotis.com/service/download.php?no=2025) → [供应商文件](https://www.dropbox.com/s/fkaish4t16zn4r8/fpx330-s102.stp?dl=1) | 595462 B；SHA `2a29d92d7a56bf977031191fdd14ec168bca6480632b2518cd4a879c70b5d904`；2021-03-26T10:11:31 |
| `fr12-h101k.stp` | [no=313](https://en.robotis.com/service/download.php?no=313) → [供应商文件](https://www.dropbox.com/scl/fi/rfzl0et75ubwjznqbiy9z/fr12_h101_k.stp?rlkey=15orcbnp2zs870khfh5mxhyuq&dl=1) | 258799 B；SHA `18c2021eb0df523e5879b745d58201ff30fc4e812df8a2e83829a59a8d9fee4c`；2026-01-07T19:15:40 |
| `fr12-s101k.stp` | [no=316](https://en.robotis.com/service/download.php?no=316) → [供应商文件](https://www.dropbox.com/scl/fi/oqzlefjrc093mywl2mx01/fr12_s101_k.stp?rlkey=ks5ndlwxhojfplxf9pe0byfca&dl=1) | 351240 B；SHA `e273aab290327a36d28829f46b7f647b2bb61db77f2ce28add08931f1e687bbb`；2026-01-07T19:15:57 |
| `fr12-s102k.stp` | [no=319](https://en.robotis.com/service/download.php?no=319) → [供应商文件](https://www.dropbox.com/scl/fi/rx4phdprtb29uxf3n3ljz/fr12_s102_k.stp?rlkey=xrdr2b9a8fzhd6dxpqtqoif6m&dl=1) | 192032 B；SHA `671c847a9a946f5f3bb0b42ef9816a8476becebb36d1b0cc8b826ff2fa7667a8`；2026-01-07T19:16:13 |
| `fr13-h101k.stp` | [no=695](https://en.robotis.com/service/download.php?no=695) → [供应商文件](https://www.dropbox.com/scl/fi/fge60rwblquypaoo52p8z/fr13_h101_k.stp?rlkey=fqpjvwgy21kdg2l25l6wsse05&dl=1) | 387676 B；SHA `269291e14f47a793a3c915358dd4a90b2b3f2aa4d2168e40d14f683c1bd21b1c`；2026-01-07T19:15:11 |
| `fr13-s101k.stp` | [no=698](https://en.robotis.com/service/download.php?no=698) → [供应商文件](https://www.dropbox.com/scl/fi/sxc8pop8bx6w79ncc27vq/fr13_s101_k.stp?rlkey=0mz5h0qkvyw4iou76qhua15pn&dl=1) | 414978 B；SHA `b10d902cea8f96889d69dffa11c6f4ae57d9674f20feb84fc1ce244a0fab1246`；2026-01-07T19:16:27 |

装配图片也在私有取证目录，所有引用的图已实际观看；本轮将可疑型号文字与图中标签分开记录。

| 图文件 | 一手原URL | 字节 / SHA-256 |
| --- | --- | --- |
| `fpx330_s101_install1.jpg` | [官方图](https://en.robotis.com/data/item/sharedfile/210603164453_RVAZuvB1_dd1e6df59d7d2eac2c046fe3bff3f84077cd3bae.jpg) | 86824 B；SHA `b23250772c1cac74811a5f3600b5cd09041c80b397fb175139be98a8bf8e3373` |
| `fpx330_s101_install2.jpg` | [官方图](https://en.robotis.com/data/item/sharedfile/210603164437_gGtLuejR_6fca35d79f33a1bbec4737fc650c69dea8f9051d.jpg) | 70351 B；SHA `275e3b9f7784778fd6e90eb90f61e84fe16893905fa7f0476137ac9ff7943a2a` |
| `fr12_s101_install.png` | [官方图](https://en.robotis.com/data/item/explain/1893207946_40cfba87_fr12-xh430_05.png) | 30819 B；SHA `085a068c6af5f54d676b91701efc9f0d704d8573be9f5ffb1e7c0fba0956ae94` |
| `fr12_s102_install.png` | [官方图](https://en.robotis.com/data/item/explain/1893207946_36d070e3_fr12-xh430_06.png) | 28957 B；SHA `1e31f26803ab3d4538c4a23b92b4cfb65c2d53e2f567a8d1b8a9762a33fbe4cf` |
| `fr12_h101_install.png` | [官方图](https://en.robotis.com/data/item/explain/1893207946_534a9370_fr12-xh430_01.png) | 30127 B；SHA `307c23b9482e83ad9c39656e26a65dd08b10f798165fe772275a244df272cd66` |
| `fr13_h101_install.png` | [官方图](https://en.robotis.com/data/item/explain/1893207946_e08fac2a_fr13-xh540_01.png) | 37752 B；SHA `d0e84ed82757f643528d704947e0b783f89d65e10dba39fad2b5ee7bc508e0d2` |
| `fr13_s101_install.png` | [官方图](https://en.robotis.com/data/item/explain/1893207946_030ca760_fr13-xh540_02.png) | 36407 B；SHA `25a0ce7fa13af540bdf882664635e3c73c0f66b78a0b24b29329332490ae5cc4` |
| `fpx330_h101_installation.png` | [官方图](https://en.robotis.com/data/item/explain/1893207946_5f761778_xl330_h101_ECA084EAB09CEB8F84.png) | 579620 B；SHA `2739edaf926a354b53f998fd1ecba51dc77a2fb8b8c9e1ab2fa4713b465b9b06` |

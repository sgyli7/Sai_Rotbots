# Gorilla V0.1 内部模块研究

核查日期：2026-10-02。用途：为内部装配、空间与宏观物理预算提供模块依据。本文没有选择驱动架构、采购型号或关节数量，没有修改外观模型、结构或 SI 参数，也不构成红线放行。用户允许为真实装配小幅调整壳体细节；主体比例仍由当前设计入口约束。

## 1. 公开资料能支持什么

下表区分实机公开事实、机构披露与未知。不同年代的机器人不能拼成同一套规格。照片和公开视频可说明部件存在，不能据此测出隐藏尺寸、质量、传动比或连续额定。

| 对象与版本 | 已核实的内部组成或工程方法 | 当前公开资料不能闭合的内容 |
|---|---|---|
| Tesla Optimus，Gen 2 实机说明及 2022 起的机构申请 | Tesla 的 Gen 2 官方说明确认自研执行器和传感器。[T1] Tesla 公开专利披露旋转与线性两类机构：旋转实施例包含电机、应变波传动、高速侧角接触轴承/机械离合、低速侧交叉滚子支承；线性实施例包含倒置滚柱丝杠、转子/定子、滚珠及四点接触支承。[T2] | 专利实施例不等于最新 Optimus 的量产 BOM；无法据此确定每个关节实际采用何种实施例。最新逐轴质量、持续曲线、制动策略、母线/回馈、散热、线束与检修尺寸均未闭合。未找到厂商公开的整机制造 CAD。 |
| Figure 03，2025 发布 / 当前产品 | 自研执行器、电池、传感器、结构和电子模块；BotQ 官方说明明确涉及电机、带润滑的齿轮箱及执行器装配。[F1][F2] 手掌相机、指尖触觉与升级音频属于实机公开硬件。[F1] | 没有公开逐轴减速/丝杠型号、完整执行器剖面尺寸、输出支承与制动明细、连续热曲线。主关节不能根据壳体渲染猜为某种工业减速器。未找到厂商公开的整机制造 CAD。 |
| Figure 03 电池 | 官方公开 2.3 kWh、宣称 5 h 运行、2 kW 快充；电池进入躯干并承担结构功能，壳体采用冲压钢、压铸铝及结构胶；充电冷却部件集成进压铸件，使用强制对流，并包含 BMS、保险/开关、互连及泄压/阻火结构。[F3] | “5 h”对应厂家工况，不能推导 Gorilla 续航或驱动平均功率。电池串数、电压、质量、完整包络、回馈接收功率未公开。该充电冷却事实不能外推为全部关节采用相同冷却。 |
| Boston Dynamics 电驱 Atlas，2024 原型与 2026 产品分开 | 2024 官方宣布全电驱替代液压。[A1] 2026 官方工程访谈说明：两个可接近的电池用于轮换；复用两类主要执行器及可互换肢体；执行器依靠外部散热翅片被动冷却，机器人唯一风扇位于头部，软垫后仍保留气流通道；相机围绕头部布置。[A2] | 未公开电机/减速器内部类型、逐轴连续额定、制动和旋转过线方案、电池 kWh/质量及完整装配尺寸。头部风扇事实不支持猜测其计算板型号。未找到厂商公开的整机制造 CAD。 |
| 电驱 Atlas，2026 规格范围 | 官方规格为 1.9 m、90 kg、56 DoF；指掌触觉、360°相机视野；典型续航 4 h、重搬运 2 h，换电约 3 min；模块可现场更换。[A3] | 这些是 Atlas 整机数据，不能作为 Gorilla 的轴数、质量密度、额定载荷或续航。规格表不是制造图纸或本项目验证证据。 |
| 旧液压 Atlas，2013 DRC / 后续研究机器人 | DARPA 对 2013 版公开机载实时计算机、液压泵、热管理、28 个液压关节以及激光雷达/立体视觉头。[H1] 后期 Boston Dynamics 维修报道确认电池、阀、传感器/电气组件及液压维修真实存在。[H2] | 不能把 2013 的轴数/质量归到后期 HD Atlas。未从本轮主源获得完整泵阀管、油箱/补偿器、蓄能器、散热器尺寸与持续效率。未找到厂商公开的完整液压制造 CAD；公开仿真模型不等于这些制造资料。 |

本次获得的是可核实的模块类型及少量装配原则，未获得以上机器人的完整内部复制方案。Tesla 的 [AI Day 2022 原视频][T3] 可从其投资者关系页面进入，但本轮未取得可核对的完整官方字幕，故不把媒体转述的电池或执行器数字写入预算。

## 2. 四条驱动路线需要装进哪些东西

以下为 Gorilla 后续必须逐项预算的工程模块清单，不声称某家机器人已经采用每个项目。模块可共壳、共母线或共冷却，但相应质量和空间只能算一次，不能省略其功能。

| 路线 | 驱动到结构的实际模块链 | 必须另算的系统与装配空间 | 宏观物理核查入口 |
|---|---|---|---|
| 旋转电驱 | 电机定转子 → 传动/减速 → 输出轴与承力支承 → 轴座、紧固和结构；另有编码/温度反馈、驱动电子与按风险确定的制动/保持机构 | 驱动板/母线、接插件与过线；轴承预紧/润滑/密封；壳体导热或风/液冷；可达的紧固和轴承更换路径 | 同时满足扭矩—转速—温度工作点、传动寿命、输出六维载荷、反驱与停机保持、回馈接收能力；减速器额定不等于完整关节连续能力 |
| 丝杠线性电驱 | 电机 → 必要的传动 → 丝杠/螺母 → 推杆/防转/导向 → 两端铰支或连杆 → 关节轴支承；另有位置/力/温度反馈及需要的制动 | 完整伸缩长度、行程与连杆扫掠；防尘、润滑、支承、杆端铰座；电机/驱动散热和拔出维修空间 | 以真实姿态力臂计算力与速度；校核屈曲、丝杠寿命/临界转速、背驱及保持；不能把“行程”当成执行器全长 |
| 集中电供液压 | 电池/母线 → 逆变器/电机 → 泵 → 压力与保护阀/过滤 → 分配阀与管路 → 缸或液压旋转执行器 → 连杆及独立支承 → 回油/补偿与热管理 | 油液、油箱或相应补偿/储能、阀块、压力传感器、软管接头与弯曲半径；冷却器、泵安装隔振、加油排气和泄压检修路径 | 算同时动作流量与压力、泵/阀/管损和热；逐轴缸力/杆端载荷；断电保持、泄漏、空化与故障排油。干缸质量不能代表完整液压路线 |
| 分布电液/电静液 EHA | 母线/驱动 → 局部电机泵 → 阀块/补偿或蓄能 → 液压执行器与支承；外围保留反馈、保护和散热 | 局部液体、补偿/保护、冷却及维护仍占空间；减少长管路不等于没有液压外围 | 按电机泵、液压执行器和热系统共同工作点核算；能量回收必须落实到驱动与母线接收路径。Moog 的 EPS 官方组成是 EPU 加带蓄能器阀块，且**不含执行器**。[E1] |

分布电液是与集中阀控液压不同的系统选择。Moog 官方说明 EPU 可以直接接作动器，并以四象限运行实现泵控；这说明“局部电机泵＋液压缸”的路线真实存在，但不证明任何 Atlas 版本采用该方案，也不代表现成模块适合 Gorilla。[E2]

## 3. 公开尺寸标尺

这些是建立真实模块边界的标尺，**不是采购表或候选架构定案**。没有证据表明 Tesla、Figure 或 Atlas 使用以下具体器件。下载状态以本轮核查为准；未提交任何注册或下载表单。

| 标尺 | 已核对尺寸、质量与能力条件 | 能支持的建模边界 |
|---|---|---|
| Harmonic Drive CSG-65-100-2UH 减速器/支承单元 | 外径约 260 mm、轴向 115 mm，20.9 kg；比值 100；Rated Torque L10 1236 N·m，平均输入转速上限 1900 rpm；输出支承允许弯矩 1860 N·m。[C1][C2] | 官方 DXF/尺寸图可作输入；仍缺电机、驱动、制动、安装、线束、散热及外部结构。L10 与平均输入速度是目录条件，不能合成为机器人持续动作认证。 |
| Tecnotion QTR-A-160-34-Z 无框电机 | 外径 160 mm、最大轴向 34.5 mm；定转子合计 1.613 kg，线缆不含；连续 15.3 N·m 对应线圈 100°C、安装面 20°C；Z 绕组，目录另给电压/转速工作点。[C3] | 官方二维尺寸可重建**标注为厂商尺寸包络**的电磁件；不含轴承、壳体、减速器、制动和驱动。不能把安装面 20°C 条件变成封闭机体持续能力。官网三维 CAD 入口需表单，未取得三维文件。[C4] |
| RealSense D455 深度相机 | 124×29×26 mm，名义质量 116 g（114–118 g）；2022 数据表最大列示模式：深度 1280×720@30 Hz、彩色 1920×1080@30 Hz，组件功耗约 3.461 W、TDP 3.101 W。[C5] | 官方三维外形可直接取作感知装配标尺。数据表模式功耗不是所有固件模式功耗；安装还需 USB 接头/线缆、光学视场、保护窗及散热，机身尺寸不包括这些空间。 |

实际下载入口与核查位置：

- CSG65 [官方 DXF 直链][C2]：HTTP 200，337,767 bytes，读取到 DXF 文件头；[同源尺寸 PDF][C6]。页面列出的 `CSG-65-XXX-2UH.STEP` 裸链接本轮返回 404，**未取得 STEP**。
- QTR160 [参数/二维尺寸 PDF][C3]：Brochure 2.5，打印 p20–21，订货表 p35；[三维 CAD 页面][C4]公开入口存在，但要表单，未提交。后续只按可核对的尺寸图重建包络，并保留源版本。
- D455 [官方 CAD ZIP 直链][C7]：HTTP 200，15,041,868 bytes，内存读取清单确认包含 `D455_Solid.SLDPRT`；不是凭第三方模型命名判断。[参数 PDF][C5]版号 337029-013，p66 表3-52、p101 表7-9。三维文件并非整台机器人或光学标定模型。

上述三项是上一轮在内存核查的结果，没有将第三方 CAD 拷入受控模型或 Git。作为受控建模输入前须确认许可并记录版本/哈希；未确认再分发许可的原始 CAD 只保存在忽略的 `artifacts/` 中。空间摆放不等于装配、碰撞、驱动或承力放行。

### 3.1 C15 内部设计补充：大驱动、缸与电池

下表只给宏观预算标尺。工业目录器件的重量与空间是真实参照，不表示 Gorilla 必须采用相同结构。减速器、干缸和电池本身均不是完整的关节或能源系统。

| 标尺及固定条件 | 已核实的器件尺度 | 额定或压力条件与未包含内容 |
|---|---|---|
| Nabtesco RV-320E，取比值 101、螺栓夹持输出类型作比较 | 减速器主体 Ø325×125 mm；安装配合径 Ø245h7；44.3 kg。内置主支承。[M1][M2] | 额定 3136 N·m、15 rpm、额定寿命 6000 h；100% duty 的 35 rpm 是目录参考转速，不能自动与额定力矩同时使用。输出允许弯矩 7056 N·m、推力 19,600 N 对应该输出类型，不能把两者当作同时全额的六维承载证明。输入齿轮突出、外壳密封/润滑、电机、驱动、制动、安装及散热另计。[M1] |
| Parker HMI 63/28，BB 固定尾叉 / ISO MP1；200 mm 行程、1号杆、标准外螺纹端 | 缸径63、杆径28 mm；主体横向 E=90 mm。回缩目录参考尺寸 `XC+S=400 mm`、`ZC+S=420 mm`；杆端螺纹 A=28 mm。干重 `10.1+0.19×20=13.9 kg`。[M3] | HMI 系列名义工作压力最高21 MPa，实际还取决于杆端及疲劳工况。BB 尾叉销径20 mm；杆端球铰、两端支架、油液、接头/管线、位移/力反馈、阀与保持保护不在干重内。标准1组密封为−20～80°C，不能用可选150°C密封上限替代。[M3] |
| Parker HMI 80/36，同一目录与安装条件 | 缸径80、杆径36 mm；E=115 mm。回缩 `XC+S=429 mm`、`ZC+S=457 mm`；A=36 mm。干重 `19.5+0.27×20=24.9 kg`；BB 尾叉销径28 mm。[M3] | 与上一项相同的外围和工况缺口。行程200 mm不能当成缸体全长；改为100 mm行程时，两参考长度均减少100 mm、干重分别减少1.9/2.7 kg。这不是短缸定制后的质量承诺。 |
| Victron Lithium NG BAT524110620，25.6 V / 100 Ah | 名义2.56 kWh（25°C、放电≤1C）；厂家估计质量19 kg。[M4] 图纸列示341.2×160.3×234.7 mm，手册为宽341×深160×高235 mm；实际导入完整STEP的AABB为 **341.202481542×160.260794060×235.795325916 mm**，约12.89 L，后续占位保留其凸出包络，见§3.2。[M5][M6] | 最大连续充/放100 A，10 s放电脉冲200 A；放电−20～50°C、充电5～50°C。M8电源端、通讯线和拆盖/工具空间另加；外置 Lynx Smart BMS NG 不包含在电池重量/包络内。手册最多两只25.6 V模块串联，**不能四串用作102.4 V系统的现成依据**。连续充电电流不是已验证的机器人回馈接收方案。[M4] |

液压缸总长的参考必须保留：`XC` 是到尾部销轴中心的安装基准，`ZC` 是尾叉外端的目录基准，不是两个球铰中心距。当前可按 `ZC+S+A` 暂留 **448 / 493 mm** 裸缸轴向保守占位，再加杆端接头与两端铰座；这是由目录基准重建的预算包络，尚未用精确配置 CAD 核对杆端起止及全部突出物，不能称完整装配尺寸已闭合。端口接头、软管弯曲和缸体扫掠另计。[M3]

用于整体功率筛查的**本项目推导**：假定1–3 kN·m、0.5–0.8 rad/s及有效力臂0.08–0.15 m，则轴上机械功率0.5–2.4 kW、缸力约6.7–37.5 kN、缸速0.04–0.12 m/s。按 `F=pA`，14–21 MPa下63/28缸理想推/拉力43.6–65.5 / 35.0–52.5 kN，80/36为70.4–105.6 / 56.1–84.2 kN；这是未扣摩擦、背压和姿态变化的面积计算。按 `Q=Av`，伸出侧每缸流量分别约7.5–22.4、12.1–36.2 L/min。多缸同时动作必须汇总；不能把几千瓦轴上功率当作电机泵输入，也不能省略阀损、油液与冷却。

电池同样只支持比例粗算：N个相同模块是约 `2.56N kWh / 19N kg / 12.89N L`（空间改用完整STEP的AABB），名义电压×连续电流为每模块2.56 kW；实际接法、电压、BMS/配电、温升及可用能量须另闭合。这里没有提出N或母线电压。

资料落盘与 CAD 状态（2026-10-02）：

- 原始资料、下载失败记录及清单位于忽略的 `artifacts/gorilla_v0_1/internal_module_sources/source_manifest.json`。成功文件均校验以下 SHA-256；第三方原始 STEP 未入 Git，未提交任何注册表单。
- RV-320E [官方 CAD 下载页][M2]列出 DXF/STEP；对应公开下载端点本轮返回503，**未取得其 CAD**。尺寸只能重建并注明“厂商目录主体包络”。[M1]是已落盘的 Rev.003.1-D 产品目录，打印p20（PDF第11页）。
- HMI [官方 EU 目录][M3]能通过网页读取，核查p3、12、25、27、30；本机直链下载返回403，**未保存原PDF、无原文件哈希，未取得精确配置 CAD**。本表统一使用这一目录，不与其他地区图纸拼接。
- 电池[外形图直链][M5]与[STEP直链][M6]均HTTP200；图纸Rev02，STEP文件头为`ISO-10303-21`。下载核查阶段尚未导入Gorilla；随后已导入忽略目录中的OEM空间候选，现状见§3.2。手册§3.1 / §4.5.3与§8给串联及能力边界。[M4]

| 下载文件 | SHA-256 |
|---|---|
| `nabtesco_product_guide_current.pdf` | `3aa9260789878a552daedd35abb4d6a23c126783fb679d37c8a406389d22201f` |
| `victron_lithium_ng_25_6_manual.pdf` | `364b88de54dc130a6bb8614af419d9dd8a43e043ca9c088d4c60e2fe1110cad9` |
| `victron_ng_25_6v100ah_drawing.pdf` | `40242b5c34597b55921ab2328c45ad028c1a3ec53ebbf28b164532bdff9bab78` |
| `victron_ng_25_6v100ah.step` | `ae0fc44a4acdb6d0369787c3aca0436ff68e880ba4e80f2d8b531a6ca3da7f35` |

### 3.2 本地 OEM CAD 导入现状

依据忽略目录内 `imported_geometry/import_manifest.json`、`cubemars_ak80_64_import_manifest.json` 与 `victron_ng_25_6v100ah_import_manifest.json` 核对。两份原STEP导入后哈希未变；原文件长度单位均为毫米，线性比例 **0.001** 转成米，保持源XYZ轴、旋转为单位矩阵，再以AABB中心平移到局部原点：`q_local_m = 0.001 × (q_source_mm − c_source_mm)`。这不是Gorilla关节坐标变换或安装基准确认。

| 本地资产 | 原文件与来源追溯 | SI外形与拓扑边界 |
|---|---|---|
| CubeMars AK80-64 | [官方CAD ZIP直链][M7]内的 `ak80-64.stp`，入口归属[官方技术下载页][M10]；STEP SHA-256 `dabe73fd22a27ed922bea0971b39ea8fd74de31cf45c495bee96945c63fc68ea`，原ZIP SHA-256 `8679c522af66c1870b5dfd67fd2e470a86af4d27f3faba45f09b45f957ab6776`。单件manifest的`source_manifest_entry=null`，原总来源清单未登记此项；此处记录已实际下载来源与本地哈希，不伪称该字段完整。 | 源中心`(-30.95,0,0)` mm；导入局部AABB尺寸`(0.0619,0.098,0.098)` m，即61.9×98×98 mm。1个有效CAD solid；OBJ闭合、流形、绕序一致。厂商48 N·m nominal /120 N·m peak仅作尺寸/能力标尺，不代表该腕部负载或持续热能力已经匹配；控制指令范围不替代额定。[M8][M9] |
| Victron BAT524110620 | 原STEP来源[M6]，哈希见上表。 | 源中心`(1911.7919203815748,585.4776895892188,-110.49766295752009)` mm；导入AABB尺寸`(0.341202481542,0.160260794060,0.235795325916)` m。BRep有效、2737个CAD面均已三角化，但15个solid以外还含非solid显示面；显示面有1156条边界边/64条非流形边，solid 1的三角网格另有36条缝边。完整OBJ**不能当作闭合碰撞体**，未删面或补盖伪造闭合。 |

当前忽略的OEM候选已摆入 **4个电池＋6个AK80-64实例**，用于同源局部空间观察；默认受控模型仍采用项目自有参数包络。源CAD、派生OEM mesh/Blend/GLB均留在ignored artifacts，未确认再分发许可、未选型。闭合AK网格也不授权碰撞契约；两类器件均不从CAD体积猜质量或惯量。此次导入不构成几何、驱动或承力放行。

## 4. 宏观预算与模块装配的下一份输入

以下为本研究提出的工作输入，不是已通过的物理结论：

1. 先确定任务工况和各轴负载范围，再为旋转电驱、线性电驱和液压/电液分别列完整模块树；同一版本同时记录质量、实体尺寸、活动扫掠、线管弯曲、热交换及工具/拔出空间。
2. 头/胸部至少要预算感知安装与视场、计算/网络、电源转换、线束与冷却；相机自带深度处理板不等于自主规划计算机。手/腕需要反馈、机构、接触面与动态过线，不能只预算手指外壳。
3. 电源预算包括电芯、BMS、保险/开关、接触与预充、配电、充电或换电接口和回馈路径。分别记录可用能量、峰值/连续电流和回馈功率，不以名义 kWh 代替这些约束。
4. 先用厂商参数形成有上下界的完整模块包络，再把模块装进可编辑布局；壳体小幅修正要显示具体占用或扫掠冲突及最小调整量，保持原设计美观。
5. 必须关闭的物理未知包括连续输出/温升、支承与制动、供电与回馈、油路同时流量、管线及检修空间。可定制/暂缺采购才是黄线；一个模块只有尺寸渲染或峰值宣传时，相关物理仍为红线未知。

## 来源

均为厂家网页/视频说明、公开原始专利文献或 DARPA 官方资料；本轮不引用媒体器件猜测。网页摘要保持精简，公开型号数字仅用于上文明确的版本与条件。

[T1]: https://www.youtube.com/watch?v=cpraXaw7dyc "Tesla 官方 Optimus Gen 2，2023-12-13"
[T2]: https://patentimages.storage.googleapis.com/57/09/54/cf5ead653dec6d/WO2024072984A1.pdf "Tesla 原始公开专利 WO2024072984A1，机构实施例 [0113]–[0116] / Fig.5E–5J；公开原文复本"
[T3]: https://www.youtube.com/watch?v=ODSJsviD_SU "Tesla AI Day 2022；Tesla 投资者关系页面列出的原视频"
[F1]: https://www.figure.ai/news/introducing-figure-03 "Figure 03 官方发布，2025-10-09"
[F2]: https://www.figure.ai/news/botq "Figure BotQ 官方模块及制造说明，2025-03-15"
[F3]: https://www.figure.ai/news/f-03-battery-development "Figure 03 官方电池说明，2025-07-17"
[A1]: https://bostondynamics.com/blog/electric-new-era-for-atlas/ "Boston Dynamics 2024 电驱 Atlas 公告"
[A2]: https://bostondynamics.com/webinars/form-function-enterprise-humanoid-design/ "Boston Dynamics 官方工程访谈：actuator/battery/thermal/modularity"
[A3]: https://bostondynamics.com/wp-content/uploads/2026/01/atlas-spec-sheet.pdf "Boston Dynamics 2026 产品规格，p1–2"
[H1]: https://www.darpa.mil/news/2013/atlas-robot-unveiled "DARPA 2013 Atlas 官方模块清单，2013-07-11"
[H2]: https://bostondynamics.com/blog/build-it-break-it-fix-it/ "Boston Dynamics 旧液压 Atlas 官方维修报道"
[E1]: https://www.moog.com/products/actuators-servoactuators/industrial/electrohydrostatic-actuators/eps.html "Moog EPS 官方组成与边界"
[E2]: https://www.moog.com.cn/products/electrohydrostatic-pump-unit.html "Moog 官方 EPU 泵控与四象限说明"
[C1]: https://www.harmonicdrive.net/products/gear-units/gear-units/csg-2uh/csg-65-100-2uh "Harmonic Drive 精确型号参数"
[C2]: https://www.harmonicdrive.net/_hd/content/caddownloads/dxf/csg-2uh_gearheads/csg-65-xxx-2uh.dxf "Harmonic Drive 官方机械 DXF，已核实响应及文件头"
[C3]: https://www.tecnotion.com/wp-content/uploads/2022/05/Torque_Brochure_EN_2-5.pdf "Tecnotion Torque Brochure 2.5，p20–21 / p35"
[C4]: https://www.tecnotion.com/downloads/qtr-160yz-series-cad-file/ "Tecnotion 官方 CAD 入口，需表单；本轮未获取三维文件"
[C5]: https://www.realsenseai.com/wp-content/uploads/2022/04/Intel-RealSense-D400-Series-Datasheet-April-2022-v2.pdf "RealSense D400 datasheet 337029-013，p66 / p101"
[C6]: https://www.harmonicdrive.net/_hd/content/caddownloads/dxf/csg-2uh_gearheads/csg-65-xxx-2uh.pdf "Harmonic Drive 同源尺寸 PDF"
[C7]: https://dev.realsenseai.com/download/41950 "RealSense 官方 D400 相机机械 CAD ZIP，含 D455_Solid.SLDPRT"
[M1]: https://precision.nabtesco.com/img/area/leaflet_pdf/en/en_cat_product-guide.pdf "Nabtesco Product Guide Rev.003.1-D，打印p20 / PDF第11页"
[M2]: https://www.nabtescoprecision.com/product/rv-e/ "Nabtesco RV-E 官方产品与CAD下载页；本轮具体CAD端点503"
[M3]: https://www.parker.com/content/dam/Parker-com/Literature/Accumulator---Cooler-Division---Europe/catalogues/cylinder/hmi/HMI_1150-9-uk.pdf "Parker HY07-1150/UK HMI，p3 / p12 / p25 / p27 / p30；网页已读取，本机PDF下载403"
[M4]: https://www.victronenergy.com/upload/documents/Lithium_NG_battery_25%2C6_V/173204-Lithium_NG_battery_manual-pdf-en.pdf "Victron Lithium NG 25.6V手册，§3.1 / §4.5.3 / §8"
[M5]: https://www.victronenergy.com/upload/documents/LiFePO4-Battery-25.6V100Ah-NG.pdf "Victron BAT524110620外形图Rev02，公开PDF直链"
[M6]: https://www.victronenergy.com/upload/documents/LiFePO4-Battery-25.6V100Ah-NG-(stp-).STEP "Victron BAT524110620官方STEP直链，已HTTP200取得，原CAD仅存ignored artifacts"
[M7]: https://www.cubemars.com/data/cms/202602/ak80-64-robotic-actuator-3d-drawing.zip "CubeMars AK80-64官方CAD ZIP已实际下载来源，包内ak80-64.stp"
[M8]: https://store.cubemars.com/products/ak80-64 "CubeMars官方AK80-64店页，Rated Torque 48 N·m；仅标尺"
[M9]: https://www.cubemars.com/categorys/knee-joint-motor "CubeMars官方分类页，AK80-64 Peak Torque 120 N·m；仅标尺"
[M10]: https://www.cubemars.com/technical-support-and-software-download.html "CubeMars官方Technical Support & Download入口"

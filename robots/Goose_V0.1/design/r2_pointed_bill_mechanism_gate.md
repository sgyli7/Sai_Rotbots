# 指定尖嘴 R2：外形与机构一致性审查

外观仍以[用户指定的收尖闭嘴图](concepts/r2_pointed_beak_closed_reference.jpg)和[平行张嘴图](concepts/r2_pointed_beak_parallel_open_reference.jpg)为准。本次把当前 `280 × 190 × 180 mm` 小机箱视觉候选的尖嘴上下两片实体与原[R2 四连杆复核](kinematic_review.md)放在同一坐标系检查。结果只推进了**可审查的外形和理想机构运动**；仍无可以装入舵机、打印拼装和叼物的嘴部总成。

## 原视觉实体的具体故障与修正

原[小机箱视觉候选](../cad/exports/goose_r2_compact_front_reach_v53_visual_candidate_manifest.json)在闭嘴时，上下橙色喙壳的精确 CAD 布尔交集约 `9.13 cm³`（喙长系数 `1.10`）。这种实体重叠会阻止两片零件按图闭合；先前的图片不能作为制造几何。另一个不一致是其张嘴图把下喙纯竖直下移 `30 mm`，而原 R2 平行四边形在目标开口时还会前移约 `1.608 mm`。

新的[闭嘴近景](../images/r2_nonintersecting_bill_v55_closed_detail_candidate.png)、[平行张嘴近景](../images/r2_nonintersecting_bill_v55_open_detail_candidate.png)、[站姿侧视](../images/r2_nonintersecting_bill_v55_side_candidate.png)与[斜视](../images/r2_nonintersecting_bill_v55_three_quarter_candidate.png)由同一修正参数生成。[闭嘴视觉 STEP](../cad/exports/goose_r2_nonintersecting_bill_v55_visual_closed_candidate.step)、[张嘴视觉 STEP](../cad/exports/goose_r2_nonintersecting_bill_v55_visual_open_candidate.step)和[两份清单](../cad/exports/goose_r2_nonintersecting_bill_v55_visual_closed_manifest.json)、[张嘴清单](../cad/exports/goose_r2_nonintersecting_bill_v55_visual_open_manifest.json)保留原图、机构说明及生成脚本哈希。上喙外背仍从宽根拱起后收至圆钝尖端，但嘴内侧抬高为可分离的夹持腔；下喙前段略薄。九个理想角度样点（闭合 `+40°` 至目标 `−33.863°`）的**两片橙色视觉壳**布尔交集均为 `0 mm³`。这项检查只覆盖两片视觉壳，不含软垫、齿轮、连杆、轴承、螺钉和装配公差。

| R2 几何量 | 原交接目标／本版视觉运动 | 验证范围 |
| --- | ---: | --- |
| 左右两侧摆杆长、固定轴间距 | `25 / 14 mm` | 理想平面几何；实体孔和双侧同轴未完成 |
| 闭合到 30 mm 目标的摆杆角度 | `+40° → −33.863°` | 由原 R2 公式反解；实际净开口要扣软垫与止挡 |
| 下喙目标位移 | 前 `1.608 mm`、下 `30 mm`，姿态不变 | 视觉下喙和显示连杆使用同一变换 |
| 行程中最大前移 | `5.849 mm` | 九点视觉壳避让通过；真实零件需连续扫掠 |

## 不能把 RC2 嘴部直接换皮

现行[旧 RC2 规格](../configs/robot_spec.json)写的是 `XC330-M288-T` 直驱、`18 mm` 轴间距、传动比 `1:1`；旧[RC2 可编辑 CAD](../cad/exports/cad_manifest.json)及 MuJoCo／Jolt 证据都按这一机构生成。被选中的[原 R2 方案](beak_r2.md)则是单台 `XL330-M288-T`、约 `2:1` 传动、`14 mm` 轴间距，外形还要求固定上喙和有厚度的平行下喙。两者的连杆、轴位、传动、电源假设和软垫基准不能互换。**旧 RC2 夹取／拖拽试验不得拿来证明此尖嘴版通过。**新候选必须单独构建头架、传动、双侧摆杆、下喙、软垫、止挡和制造 BOM，再重做接触与跨引擎测试；不得悄悄覆盖历史规格。

[ROBOTIS 官方 XL330-M288-T 手册](https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/)列裸机质量 `18 g`、外形 `20 × 34 × 26 mm`、推荐 `5 V`，支持 Current-based Position Control Mode。该模式下 Min/Max Position Limit 不起作用，机械止挡和控制端限位都要设计；电流读数也不能直接视为夹持力。手册的 `0.52 N·m @ 5 V` 为**堵转**条件，不能用作持续夹拖力矩。

按现有视觉机构的固定下轴 A `(x,z)=(152.85,474) mm`，做[XL330 同轴包络筛查](../evidence/r2_pointed_bill_v55_xl330_coaxial_package_rejected.json)：若输出轴沿左右方向，`20 × 34 × 26 mm` 电机本体顶端仍低于白色头壳底面 `26.5 mm`、低于现有可见橙色铰罩底端 `15.52 mm`，电机底端比现有两片喙壳最低处还低约 `30.09 mm`。**把 XL330 直接同轴装在当前 A 会裸露在鹅头／喙外，破坏用户指定轮廓；本布置否决。** 后续只能把电机移入头内并设计清楚到 A 的约 `2:1` 传动，或连同 A/D 轴、下喙刚性立耳和两颊外壳一起重排。任一方案都须做实体全程扫掠，不能只把电机藏进视觉头壳。

## 尺度和质量的早期警报

原 R2 说明里的 `60–65 mm` 外露喙长、`≤65 g` 嘴部模块质量是**当时的原型目标**，不是用户概念图实测尺寸。当前视觉实体两片喙壳的前后包络约 `132 mm`，比早期喙长目标明显更长。[PETG 表面积与等厚壁代理](../evidence/r2_pointed_bill_v55_mass_screen.json)显示：若橙色上下壳都按 `1.6 mm` 等厚壁估算，两片约 `58.44 g`；加 `18 g` 的 XL330 已约 `76.44 g`，还没有齿轮、双侧连杆、轴、嘴垫、头架和线。这个代理**不是打印件称重，也不证明 65 g 绝对做不到**，但旧质量目标已不能作为当前长尖嘴的验收上限直接使用。后续需以真实中空 CAD 与打印参数计量，并将增重反馈到颈根、头俯仰、跌倒保护和 50 g／拖拽动作的负载核算。

此版外形仍有明显差距：头罩、相机座、颈部包覆和机身翼门的表面尚未复刻原图；喙根与头架目前是相交视觉实体。`appearance_review_pass=false`，嘴部制造／采购亦不放行。接下来的实体设计先闭合**可装入 XL330 与 2:1 传动的 R2 口腔承力模块**，再以同版打印件质量和真实物体接触验证，而不是继续在旧 RC2 上改颜色。

### 内藏电机与传动带的必要包络初筛

为避免上一版同轴电机裸露，以及外置大黑颊罩破坏指定形象，另做了一版**未通过外观的机构占位候选**：[闭嘴近景](../images/r2_internal_belt_v61_closed_rejected_candidate.png)、[张嘴近景](../images/r2_internal_belt_v61_open_rejected_candidate.png)与[闭嘴清单](../cad/exports/r2_internal_belt_v61_closed_visual_manifest.json)／[张嘴清单](../cad/exports/r2_internal_belt_v61_open_visual_manifest.json)。固定输出轴 A 试放于视觉坐标 `(148,0,505) mm`，XL330 输出轴试放于头壳内部 `(135,0,540) mm`，两轴距约 `37.34 mm`。`16/32` 齿、2 mm 节距的 `2:1` 传动带只是候选；算出的节线长度约 `123.37 mm`，**尚未验证有合适的现货带、齿轮外径和 XL330 舵盘接口**。

[实体包络记录](../evidence/r2_internal_belt_gross_package_v61.json)用厂商公布的 `20×34×26 mm` 电机本体尺寸、假定的 `9.5 mm` 输出轴偏置、`2.7 mm` 外壳内缩和多留 `0.5 mm` 半径的带轮占位检查：电机盒未穿出内缩头壳，也未与相机面板或颈部叉架相交；33 个带路采样截面未穿出头壳／橙色铰罩内缩联合包络。九个理想张合位置中，上下橙色喙壳、固定铰罩与运动下喙无布尔交集；两侧下喙立耳与下喙实体确实相接。这只是**粗包络必要条件**，不是连续扫掠或可装配证明。头壳仍是实心视觉件，皮带张紧、轴承座、联轴器、可拆壳体、螺钉、布线、打印强度和真实夹持力都未解决。厂商本体尺寸来自[ROBOTIS 手册](https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/)；输出轴偏置目前仅为布局假设，须再用厂商 CAD 核对。

**外观门槛仍失败。** 侧面橙色罩明显凸成一块，张嘴时两根细长立耳过于显眼，和用户选定的圆润头壳、短小铰点、完整尖嘴不够一致。这版证明“藏进头内”有值得继续的空间，并没有确定外饰。下一轮应把运动件收入可拆头架／喙根内，以同一 CAD 完成真正空腔和两侧轴承；不能只把显眼的罩换颜色，更不能拿本版下单打印。

下一轮[头壳包覆候选 v69](../cad/exports/goose_r2_head_wrap_v69_visual_closed_manifest.json)把外突侧颊收进一个圆角白色头壳，前下方直接留出橙色上喙插入区和两侧下喙运动槽。[闭嘴近景](../images/r2_head_wrap_v69_closed_detail_candidate.png)、[张嘴近景](../images/r2_head_wrap_v69_open_detail_candidate.png)、[整机侧视](../images/r2_head_wrap_v69_closed_side_candidate.png)与[斜视](../images/r2_head_wrap_v69_closed_three_quarter_candidate.png)来自同一参数；[闭嘴视觉 STEP](../cad/exports/goose_r2_head_wrap_v69_visual_closed_candidate.step)及[张嘴视觉 STEP](../cad/exports/goose_r2_head_wrap_v69_visual_open_candidate.step)仅供审形。[张嘴清单](../cad/exports/goose_r2_head_wrap_v69_visual_open_manifest.json)保留同版来源。

[v69 实体包络记录](../evidence/r2_head_wrap_gross_package_v69.json)显示：厂商尺寸的 XL330 本体和 33 个假定带路截面没有穿出按 `2.7 mm` 壁厚内缩的头壳；九个理想嘴姿中，**头壳—固定上喙、头壳—运动下喙、上下橙壳、两侧运动立耳—头壳**的 CAD 布尔交集均为 `0 mm³`，立耳桥与下喙保持实体连接。这纠正了前一版闭嘴时头壳与下喙约 `547 mm³` 的实物干涉。该检查仍未放入真正的中空承力架、舵盘、带轮、轴承、张紧器、紧固件、可打印分壳和线束，33 点带路也不是连续制造扫掠；不能据此宣布嘴部可装配或 50 g／拖拽能力通过。

v69 的头嘴大轮廓比外突大颊罩接近用户指定的 R2 尖嘴，但头壳仍偏方，闭嘴侧面可见连接杆，嘴根盖片与相机座的层次仍不够像参考图；整机的颈腿包覆、翼门及鞋底也未获得外观验收。清单继续保持 `appearance_review_pass=false`。当前 MuJoCo／Jolt 物理证据属于旧外形；重新评审质量惯量后才可用于 v69，不移植旧版成功结论。

在继续对照参考图时发现 v69 黑色相机面板与固定上喙约 `814.86 mm³` 实体重叠。后续 [v72 闭嘴视觉清单](../cad/exports/goose_r2_head_wrap_v72_visual_closed_manifest.json)将面板底边抬起、厚度略增，使其与镜头环的视觉实体相接，且与固定上喙留出约 `3.43 mm` 的 CAD 最近距离；头罩圆角增至 `40 mm`，底缘局部下延约 `2 mm` 以保留内藏带路空间。[v72 实体复核](../evidence/r2_head_wrap_gross_package_v72.json)记录了旧面板干涉、当前面板间隙、头罩与固定上喙／运动下喙以及两侧立耳在九个理想姿态的布尔交集：所列避让对象均为 `0 mm³`，保守带路的 33 个截面仍落在 `2.7 mm` 假设壳壁内。这只是必要几何检查，不能推断连续运动、真实公差或强度通过。

[v72 闭嘴近景](../images/r2_head_wrap_v72_closed_detail_candidate.png)、[平行张嘴近景](../images/r2_head_wrap_v72_open_detail_candidate.png)、[站姿侧视](../images/r2_head_wrap_v72_closed_side_candidate.png)、[站姿斜视](../images/r2_head_wrap_v72_closed_three_quarter_candidate.png)、[闭嘴视觉 STEP](../cad/exports/goose_r2_head_wrap_v72_visual_closed_candidate.step)和[张嘴视觉 STEP](../cad/exports/goose_r2_head_wrap_v72_visual_open_candidate.step)保留为前一版比较候选；[张嘴清单](../cad/exports/goose_r2_head_wrap_v72_visual_open_manifest.json)可查同一生成来源。该版同时压低翼门凸缘和鞋底叠层。头部比 v69 圆润，但颈杆转接、嘴根可见连杆、机身表面和鞋面仍未贴近指定参考，`appearance_review_pass=false`；头壳及面板是实心视觉件，不能打印装配或下单。高髋、外扩髋和长腿尚未纳入 v72 尺寸，仍按[坐姿权衡](seated_pickup_layout_trade.md)保留候选身份。

v72 在指定的离地 `15 mm`、前方 `240 mm` 低位姿态下出现新障碍：[闭嘴／张嘴的同版 41 点路径](../evidence/r2_head_wrap_v72_sit90_x240_z15_open.json)中，头罩距机身最小采样间隙仅 `1.47 mm`，全张下喙距地仅 `1.61 mm`。因此只通过站姿机构避让不足以证明坐姿叼取。更前方、更高的姿态有空间，但 v72 在 `110 mm` 下蹲、嘴尖 `(320,25) mm`、头俯 `50°` 时，[名义全开下喙仅离地 `0.34 mm`](../evidence/r2_head_wrap_v72_sit110_x320_z25_open.json)，仍未满足 `2 mm` 的纯几何初筛门槛。

当前 [v73 闭嘴视觉 STEP](../cad/exports/goose_r2_slim_bill_v73_visual_closed_candidate.step)和[张嘴视觉 STEP](../cad/exports/goose_r2_slim_bill_v73_visual_open_candidate.step)仅将下喙外壳向内收薄：夹持垫一侧的上缘保留，外侧下缘最多抬约 `4 mm`。[闭嘴近景](../images/r2_slim_bill_v73_closed_detail_candidate.png)、[张嘴近景](../images/r2_slim_bill_v73_open_detail_candidate.png)和[站姿斜视](../images/r2_slim_bill_v73_closed_three_quarter_candidate.png)显示尖嘴更轻薄；[闭嘴清单](../cad/exports/goose_r2_slim_bill_v73_visual_closed_manifest.json)和[张嘴清单](../cad/exports/goose_r2_slim_bill_v73_visual_open_manifest.json)保存同版参数与生成来源。[九姿态实体与粗包络](../evidence/r2_slim_bill_gross_package_v73.json)仍显示被检查的头壳／嘴壳／连杆避让对不互穿、下喙桥保持连接，电机盒和假定带路不穿出内缩壳。但削薄后的壳体强度、打印层向、软垫固定与真正抓拖力未验证；这不是可以下单的嘴部 CAD。

### 同版坐姿必要复查

上喙内侧改形会改变嘴尖基准和薄壳质量，旧版坐姿物理证据不可直接继承。新[20 点可达图](../evidence/seated_workspace_r2_nonintersecting_bill_v55.json)在 `x=240–320 mm`、嘴尖 `z=15/25/40/55 mm` 的固定折腿姿态中通过 `17/20` 个视觉壳间隙样点。[15 mm 姿态与 21 点路径](../evidence/exterior_sit_sweep_r2_nonintersecting_bill_v55_x280_z15.json)所需下颈／上颈相对俯仰约 `60.7°／47.8°`，嘴壳最低处约 `12.14 mm`。在新视觉壳薄壁质量估算约 `4.035 kg` 下，[50 g 等效力双脚静力初筛](../evidence/foot_only_equilibrium_r2_nonintersecting_bill_v55_x280_z15_50g.json)需要候选限力的约 `0.946` 倍；带固定双脚前馈的[2 秒 MuJoCo 保持](../evidence/physics_sit_r2_nonintersecting_bill_v55_x280_z15_50g_proxy.json)中，两脚接触约 `99.9%` 时间、嘴无地面接触，过渡后未触短时力矩上限。它施加的是**无物体的嘴尖外力**，嘴部电机／2:1 传动尚未成为同版真实接触模型，不能证明夹起、起身或拖拽。

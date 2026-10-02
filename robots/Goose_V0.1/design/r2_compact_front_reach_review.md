# 小机箱与前颈够地候选：几何、预留空间和低位负载初筛

设计方向继续以[用户指定的 B／R2 尖嘴图](concepts/r2_pointed_beak_closed_reference.jpg)为外观基线。Goose 借鉴 MicroDuck 的紧凑躯体，但要多出可弯鹅颈、真正夹持／拖拽和更灵活的双腿。这里把[上一版 310 × 190 × 180 mm 视觉机箱](r2_compact_silhouette_review.md)只沿前后方向缩短 `30 mm`；其余头、尖嘴、颈段、腿、鞋保持相同，避免把外形和运动学改动混成一项。**本候选未通过外观验收，视觉 STEP 不是可装配或可打印整机。**

| 对照 | 310 mm 机箱 | 280 mm 候选 | 可作出的判断 |
| --- | ---: | ---: | --- |
| 视觉机箱长×宽×高 | 310×190×180 mm | 280×190×180 mm | 更接近小机身与较长颈的比例；双侧翼门曲面仍需重画 |
| 15 个坐姿目标的几何初筛通过数 | [10/15](../evidence/seated_workspace_r2_silhouette_v51.json) | [13/15](../evidence/seated_workspace_r2_compact_front_v53.json) | 头壳后缘与机箱有更多空间；仅采样一条站姿到目标的关节插值 |
| 内部器件预留盒的最小名义内表面余量 | [15.13 mm](../evidence/body_reservations_r2_silhouette_v51.json) | [15.13 mm](../evidence/body_reservations_r2_compact_front_v53.json) | 最紧处仍由 IMU 侧向位置控制；已扣 `2.4 mm` 壁厚和 `0.3 mm` 配合余量，但未设计真实中空壳和支架 |
| 1.6 mm 假设 PETG、升级髋俯仰／膝、XM430 踝俯仰条件质量 | 4.101 kg | 4.038 kg | 仅薄壳面积估算与零件预留质量，不是实测质量 |

[站姿侧视](../images/r2_compact_front_reach_v53_side_candidate.png)、[斜视](../images/r2_compact_front_reach_v53_three_quarter_candidate.png)、[25 mm 嘴尖坐姿](../images/r2_compact_front_reach_v53_seated_side_candidate.png)、[同源视觉 STEP](../cad/exports/goose_r2_compact_front_reach_v53_visual_candidate.step)和[参数／原图哈希清单](../cad/exports/goose_r2_compact_front_reach_v53_visual_candidate_manifest.json)可直接对照。缩短机箱让腿、颈和嘴在画面中更突出；不过原图的机身大面、抽象翼门、颈腿外饰和低矮鞋尚未达到复刻质量。仍保留 `appearance_review_pass=false`。现行 `robot_spec.json` 与旧 RC2 可编辑 CAD 是**另一版 16 轴工程候选**，未被本视觉试验悄悄覆盖。

## 坐低后前颈工作范围

双腿平足折低 `90 mm`、机箱前俯 `20°`、头部最终向下 `60°` 的固定姿态下，对嘴尖前向 `x=240、260、280、300、320 mm`，高于地面 `z=25、40、55 mm` 的 15 个目标逐一求解。短机箱额外让 `(260,25)`、`(320,25)`、`(240,55) mm` 三点通过 `21` 点的视觉壳体／机箱／地面间隙初筛；这证明**缩壳有可量化的够地空间收益**，并非新增一个颈关节。所有目标都仍需嘴内接触姿态、颈部实体转轴／电机、线束和腿部自碰撞复核。

在 `(280,25) mm` 目标，[单点及路径记录](../evidence/exterior_sit_sweep_r2_compact_front_v53_x280_z25.json)求得下颈／上颈相对俯仰约 `54.9°／47.2°`、头部相对俯仰约 `−62.1°`。采样中下颈／机箱最小间隙 `14.07 mm`、头壳／机箱 `30.67 mm`，机箱最低处 `84.52 mm`，喙壳最低处约 `22.5 mm`。这条路径只是直线角度插值；没有装配公差、腿杆互碰、下喙全开扫掠或实际受控下蹲。这里“前半段更自由”的设计要求具体指**在不碰壳、不拉扯线束的条件下保留这片工作空间**，暂不增加颈轴数。

## 低位负载代理的严格边界

在上述简化模型里，`x=280 mm`、嘴尖高度 `25 mm` 和 `15 mm` 两个目标分别有[静力筛查](../evidence/foot_only_equilibrium_r2_compact_front_v53_x280_z25_50g.json)、[静力筛查](../evidence/foot_only_equilibrium_r2_compact_front_v53_x280_z15_50g.json)，需候选限力的 `0.946／0.949` 倍。加双脚静力前馈后，各做 `2 s` MuJoCo [25 mm](../evidence/physics_sit_r2_compact_front_v53_x280_z25_50g_proxy.json)与[15 mm](../evidence/physics_sit_r2_compact_front_v53_x280_z15_50g_proxy.json)保持：双脚同时触地约 `99.9%`、喙与地面接触为零、过渡后执行器无触限；15 mm 目标最终嘴尖约 `14.1 mm`。施加的是嘴尖向下 `0.4905 N` 外力，不含物体、摩擦夹持、下喙动作或负载起身。

更低的 `10 mm` 目标虽然[静力解可行](../evidence/foot_only_equilibrium_r2_compact_front_v53_x280_z10_50g.json)，但[同条件动态保持失败](../evidence/physics_sit_r2_compact_front_v53_x280_z10_50g_proxy_failure.json)：嘴端约 `10.3%` 时间碰地，峰值约 `1.23 N`。因此不能把几何上靠近地面解读为可以叼起薄布边。当前较可信的初筛范围是指定物上有**约 15 mm 高的可接触特征**，而这也仅是嘴尖位置／外力代理，不是夹取合格结果。后续要在同一 280 mm 外形内用真实 R2 嘴内垫、指定样件和可控接近路径验证从地面闭嘴、保持、抬起；如需薄布边，须独立解决更低接触高度与防撞地控制。

机箱预留盒检查仅说明已有电池、电路、扬声器等轴对齐规划盒落在假设的圆角壳内；通用线束预留盒本来与电池和计算板的盒相交，不代表三件真能同占空间。壳仍为实心视觉件，门铰链、抽取方向、支撑肋、颈根／髋电机、插头转弯与散热都未排布。BOM 不因本结果放行。踝部 XM430 名义外包络虽有上一版[必要筛查](../evidence/ankle_package_screen_r2_silhouette_v51_xm430_hub.json)，鞋壳仍无电机空腔与承力构件；缩短机箱未解决脚踝制造。

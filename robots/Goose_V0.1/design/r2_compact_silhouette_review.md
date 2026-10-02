# R2 紧凑机箱轮廓：同版外形与低位动作核查

用户确认的 [B 步行鹅](concepts/history/walker_b_selected_reference.png)与[R2 收尖嘴](concepts/r2_pointed_beak_closed_reference.jpg)仍是外观基线。本候选只解决上一版头嘴前伸过多、机箱显厚、缩壳后颈根衔接过浅三个大轮廓问题；**尚未通过用户外观验收，也不是可打印装配**。

| 对照 | 前移膝轴候选 | 本候选 | 工程含义 |
| --- | ---: | ---: | --- |
| 视觉机箱 `x×y×z` | `310×190×200 mm` | `310×190×180 mm` | 仅缩小外壳；内部支架、线束和电池净空待实际排布 |
| 头嘴总成相对颈肘 | 原位置 | 后收 `25 mm` | 上颈末端同步后移，不能只移动渲染头壳 |
| 头罩比例／R2 喙长系数 | `1.15／1.20` | `1.00／1.10` | 头嘴前缘更收敛，闭嘴功能长度与载荷仍待验证 |
| 视觉整机包络 | 约 `505×268×630 mm` | 约 `467×268×612 mm` | 概念外形坐标，不是制造定尺 |

[闭嘴侧视](../images/r2_compact_silhouette_v51_side_candidate.png)、[斜视](../images/r2_compact_silhouette_v51_three_quarter_candidate.png)、[正视](../images/r2_compact_silhouette_v51_front_candidate.png)、[平行张嘴近景](../images/r2_compact_silhouette_v51_open_beak_candidate.png)和[坐姿侧视](../images/r2_compact_silhouette_v51_seated_side_candidate.png)均由同一套参数化视觉实体生成。[闭嘴 STEP](../cad/exports/goose_r2_compact_silhouette_v51_visual_candidate.step)、[张嘴 STEP](../cad/exports/goose_r2_compact_silhouette_v51_visual_open_candidate.step)及其[闭嘴清单](../cad/exports/goose_r2_compact_silhouette_v51_visual_candidate_manifest.json)、[张嘴清单](../cad/exports/goose_r2_compact_silhouette_v51_visual_open_candidate_manifest.json)可复查源码与原图哈希。机箱减高后，颈头总成也下移 `10 mm`，使颈根重新接上机箱顶面。两套 STEP 都是相交的视觉实体；没有中空承力架、真实翼门铰链、R2 可装配四杆、线束或打印分件。

与原图直接对比，本版机箱和头嘴的比例比前移膝轴版收敛，但白色颈腿壳仍像直杆，鞋的橙白黑叠层过厚，翼门是硬边矩形，机身表面也未达到原图的连续圆润感。因此 `appearance_review_pass=false`；不能因为外包尺寸和颜色相近就称为外观复刻。后续外观工作应先修这些大面与接缝，同时保留关节、镜头、嘴内接触和检修净空，不优先做羽毛线条或焊点细节。

另做了[较低鞋壳的侧视对照](../images/r2_low_shoe_rejected_side.png)，把黑底、橙层和白壳总高压低约 `5–6 mm`，并让翼门贴近机箱；[生成清单](../cad/exports/goose_r2_low_shoe_rejected_manifest.json)保留参数。视觉上更轻，但[踝电机本体盒筛查](../evidence/ankle_package_screen_r2_silhouette_v52.json)显示俯仰电机顶部超出白鞋壳约 `28.75 mm`，侧倾电机约 `12.75 mm`；本版现有鞋壳的[对应超出](../evidence/ankle_package_screen_r2_silhouette_v51.json)已分别达 `23.25／7.25 mm`。两者都没有可装配踝罩、输出盘或线束；进一步压低鞋壳在现行电机布局下使包装更难，故不将低鞋对照升级为工程候选。

## 同版低位证据与边界

机箱下降 `90 mm`、前俯 `20°`、嘴尖瞄准 `(x=280,z=40) mm` 时，颈下段／上段相对俯仰约 `47.1°／47.2°`、头部相对俯仰约 `−54.3°`。[端点及 21 点站姿到低位路径的网格采样](../evidence/exterior_sit_sweep_r2_silhouette_v51_x280.json)得到下颈与机箱至少 `14.36 mm`、头壳与机箱至少 `25.81 mm`，机箱最低点 `81.1 mm`，嘴壳最低点约 `37.5 mm`。这是**一条直线关节插值的必要几何筛查**；没有腿杆互碰、装配公差、线束、连续扫掠或动态坐下结论。

在 `1.6 mm` PETG 薄壳、假设升级的髋俯仰／膝／踝俯仰电机和简化双脚矩形接触下，初始候选总质量约 `4.267 kg`。[双脚静力解](../evidence/foot_only_equilibrium_r2_silhouette_v51_x280_unloaded.json)需要初筛限力的 `0.909` 倍；嘴尖向下 `0.4905 N` 的[50 g 等效外力](../evidence/foot_only_equilibrium_r2_silhouette_v51_x280_50g.json)需要 `0.951` 倍。两项均只作必要静力条件；真实结构质量和连续额定未计完。

最初以统一 `kp=24、kd=1.1` 保持低姿态时，[头部控制诊断](../evidence/physics_seated_reach_r2_silhouette_v51_x280_head_trace.json)显示头关节在 1 kHz 离散步间交替摆动，`0.5 s` 后约一半的命令触及短时限力，故本候选被加严判据否决。将同一简化模型的速度反馈减到 `kd=0.25` 后，[无物体试验](../evidence/physics_seated_reach_r2_silhouette_v51_x280_kd0p25.json)在 `2 s` 内双脚同时触地约 `99.9%` 时间、嘴无地面反力、过渡后无执行器触限。再在嘴尖施加 `0.4905 N` 向下外力和相应力矩，[50 g 负载代理试验](../evidence/physics_seated_reach_r2_silhouette_v51_x280_50g_proxy.json)也通过相同低位保持判据，嘴尖最后约在 `(279.4,39.4) mm`。

负载代理是**无质量、无夹持摩擦的外加力**，不是被 R2 嘴夹住的物体；不能证明叼起、起身、移动拖拽或自主任务。较低反馈增益也没有在站姿、单脚或跨引擎系统上验证。此版尚无真实零件包络、承力 CAD、连续扭矩和温升、全程下蹲控制、可采购 BOM，因此制造与采购继续不放行。后续 UnitySim2Sim、BevySim2Sim 仍沿引擎无关 SI 契约接入，不为当前 Jolt 模型改变动作接口。

### 踝电机尺寸纠错与较小电机分支

上述 `4.267 kg` 物理候选把踝俯仰设为 XM540，而最初鞋壳包络检查只按 XM430 计算，这是不可沿用的证据。[按 XM540 真尺寸复核](../evidence/ankle_package_screen_r2_silhouette_v51_xm540_hub.json)发现电机本体进入现有鞋底约 `7.25 mm`，且超出黑色踝罩的名义径向／侧向包络，**此布置被否决**。不得因它的姿态试验通过就把 XM540 写入采购表。

重新按 XM430 踝俯仰建立同版模型后，条件质量约 `4.101 kg`；[50 g 等效力静力解](../evidence/foot_only_equilibrium_r2_silhouette_v51_x280_ankle_xm430_50g.json)仍为初筛限力的 `0.951` 倍，[2 秒负载代理试验](../evidence/physics_seated_reach_r2_silhouette_v51_x280_ankle_xm430_50g_proxy.json)双脚接触约 `99.9%` 时间、嘴无地面反力且过渡后无驱动触限。[XM430 本体与黑色踝罩盒筛查](../evidence/ankle_package_screen_r2_silhouette_v51_xm430_hub.json)中，电机底部在黑鞋底上方约 `2.25 mm`，露出白鞋壳部分名义落在黑罩外轮廓内，但径向余量仅 `2.36 mm`、侧向每边 `4 mm`。这是**值得深化的尺寸必要条件**，远非可装配通过：黑罩现为实心视觉圆盘，壳壁、输出盘、惰轮、轴承、螺钉、线束和另一台踝侧倾电机都未排入实际空腔。较小踝电机在站姿、单脚、走路与拖拽中的连续能力也没有验证。

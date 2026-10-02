# R2 缩壳鹅：短鞋与前移膝轴的外观／承重对照

用户要求 Goose 借鉴 MicroDuck 的紧凑机箱，但具备更灵活的腿脚、长颈和真正可用的 R2 尖嘴；同时强调先对齐原 B／R2 外观，再审力学。此页记录两个仍**未通过外观和制造放行**的同版候选，不把视觉 STEP 当打印件。

| 候选 | 只改变的外形变量 | 同版入口 | 判断 |
| --- | --- | --- | --- |
| 短鞋 | 在上一版 50 mm 后掌基础上，把鞋尖边缘收回 40 mm | [侧视](../images/r2_compact_shoe_side_candidate.png)、[斜视](../images/r2_compact_shoe_three_quarter_candidate.png)、[脚底范围](../evidence/exterior_support_screen_r2_compact_shoe.json) | 长鞋带来的“滑雪板”比例减轻；黑底最低 1 mm 顶点给出的前后范围由约 `−63.62～163.62 mm` 变为 `−63.62～123.62 mm`。静态几何仍包住条件重心，但前方动态余量变小。 |
| 前移膝轴 | 保留短鞋、R2 嘴、机身和踝轴，把膝轴从 `x=−65 mm` 移到 `−35 mm` | [站立侧视](../images/r2_forward_knee_side_candidate.png)、[斜视](../images/r2_forward_knee_three_quarter_candidate.png)、[正视](../images/r2_forward_knee_front_candidate.png)、[张嘴细节](../images/r2_forward_knee_open_beak_candidate.png)、[闭嘴 STEP](../cad/exports/goose_r2_forward_knee_visual_candidate.step)、[张嘴 STEP](../cad/exports/goose_r2_forward_knee_visual_open_candidate.step)、[清单](../cad/exports/goose_r2_forward_knee_visual_candidate_manifest.json) | 腿从过分后折变得更直，膝部受力改善；腿线与原图是否足够像鹅、是否具备真实关节包装，仍未通过。 |

前移膝轴版沿用 `310 × 190 × 200 mm` 视觉机箱、双腿六轴物理假设和 R2 平行开嘴。站立外观仍是有尖嘴、长颈、抽象翼门的机械草模，头罩、颈壳和鞋壳的曲面与接缝离用户参考图有差距。生成清单保持 `appearance_review_pass=false`。`STEP` 是相交的视觉实体集合，无中空安装、承力框架、真实门铰链、线束通道或打印分件。

## 坐姿必须同时过几何与双脚承重

[较近目标的坐姿侧视](../images/r2_forward_knee_seated_reach_x280_side_candidate.png)和[斜视](../images/r2_forward_knee_seated_reach_x280_three_quarter_candidate.png)把机身降低 `90 mm`、前俯 `20°`，嘴尖放到 `(x=280,z=40) mm`，鞋底保持水平。[采样几何](../evidence/exterior_seated_reach_r2_forward_knee_x280_tip40.json)给出下颈／上颈／头壳对机身的最小间隙约 `23.13／75.23／13.90 mm`，机箱最低点约 `72.22 mm`。上段颈关节相对俯仰约 `47.2°`，具体执行器行程与线束弯曲均未验证。再伸远至 `x=300 mm` 时，[间隙](../evidence/exterior_seated_reach_r2_forward_knee_x300_tip40.json)增至约 `19.98／90.16／31.03 mm`，却增加腿部承载力矩。这些都是端点网格采样，不是全行程扫掠。

更靠近脚的 `(x=210,z=40) mm` 目标曾在简化物理里被双脚稳定保持 2 秒，但[实际外形筛查](../evidence/exterior_seated_reach_r2_forward_knee_x210_tip40.json)发现头壳进入机身约 `39.87 mm`；该结果已被明确否决。物理判据现在要求下颈、上颈、头壳都不穿机身，避免把这个伪成功当成抓握空间。有效目标仍使整只嘴向下约 `60°`，嘴内接触垫对不同物品的切入角和拖拽转姿尚未验证。

对同一六轴腿模型，用双脚矩形鞋底的八个接触角点承重，并排除嘴和机箱撑地；在 `1.6 mm` 统一 PETG 薄壳质量假设和现行短时初筛电机限力下，[静力对照](../evidence/foot_only_equilibrium_r2_compact_shoe.json)与[前移膝轴版](../evidence/foot_only_equilibrium_r2_forward_knee.json)的最小归一化力矩比例为：

| 嘴尖前方坐标 | 原膝轴 `x=−65 mm` | 前移膝轴 `x=−35 mm` |
| --- | ---: | ---: |
| `x=210 mm` | `0.950` | `0.843`，但头壳自碰，禁止采用 |
| `x=300 mm` | `1.066` | `0.959`，几何端点通过但余量很薄 |

把指定 `50 g` 物体等效为嘴尖向下 `0.4905 N` 的**简化外力**，[同模型静力扫描](../evidence/foot_only_equilibrium_r2_forward_knee_50g_sweep.json)在 `x=270／280／290／300 mm` 分别需要初筛限力的 `0.963／0.977／0.990／1.004` 倍。`x=270 mm` 时[头壳仅有约 `5.8 mm` 采样间隙](../evidence/exterior_seated_reach_r2_forward_knee_x270_tip40.json)，公差与运动扫掠风险太大；`x=280 mm` 是本轮比 `x=300 mm` 更值得深化的折中点，**不是已经放行的抓取点**。在 `x=300 mm` 处，更薄的 `1.2 mm` 外饰假设给出 `0.895`；若额外补计 `0.25／0.50 kg` 尚未设计的机箱承力件，则分别回到 `0.950／1.006`，见[轻壳加 0.25 kg](../evidence/foot_only_equilibrium_r2_forward_knee_50g_wall1p2_extra0p25.json)和[加 0.50 kg](../evidence/foot_only_equilibrium_r2_forward_knee_50g_wall1p2_extra0p5.json)。所以**不能靠把未知结构质量写成轻壳来放行 50 g 拾取**；必须先做真实承力 CAD、质量账本和连续扭矩／温升核查。等效外力不代表嘴已夹住自由物体。

用双脚静力解作关节前馈、再叠加位置反馈，[无物体的 2 秒低姿态试验](../evidence/physics_seated_reach_r2_forward_knee_x280_tip40_ff.json)使嘴尖最后位于约 `(279.5,39.7) mm`，两脚与地面同时接触约 `99.9%` 时间，嘴地接触为 `0`，采样壳体间隙通过。无物体的[静力比例](../evidence/foot_only_equilibrium_r2_forward_knee_x280_unloaded.json)为 `0.934`。这证明在**该简化质量、接触、电机短时限力和控制假设下**，较低姿态不必靠嘴撑地；不证明夹物、起身、连续工作或实物稳定性。`50 g` 结果仅为另一个静力外力筛查，不是这次动态试验的负载。

[同版六轴腿试验](../evidence/physics_stance_trial_r2_forward_knee_six_axis.json)的三组单脚卸载仍失败。把髋侧倾也升级为较重的 XM540 后，20° 侧移的重心仅刚进入支撑足内，右脚仍不离地；增加至 25–30° 并改变抬脚幅度或释放摆动腿侧倾，见[较大侧移](../evidence/physics_single_support_r2_forward_knee_25_30_lift2.json)和[释放摆动腿](../evidence/physics_single_support_r2_forward_knee_release_25_30_lift1.json)，出现短暂离地却不能稳定保持、不摔倒。**没有可验收的单脚支撑或步行策略；仅换大电机没有闭合控制。**

下一轮先解决两个主问题：在用户指定的鹅轮廓内，增加颈前段可用的俯仰行程，同时把有效嘴内接触区、机身全程扫掠、执行器和线束包络一同设计，让坐下后的嘴能以适合夹物的角度够地；并建立可重复的双脚→单脚→移动夹拖轨迹和足底力反馈。视觉外饰的小缝线及电路板焊点优化继续延后。此候选仍禁止采购或批量打印。

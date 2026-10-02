# Goose R2 尖嘴外形的脚型与物理可行性复核

本页比较同一尖嘴外形下三种脚型，并明确区分视觉外形、条件质量估算和实际 MuJoCo 动力学。原 B／R2 参考仍是外观基线；[后掌候选侧视](../images/r2_heel_study_side.png)、[斜视](../images/r2_heel_study_three_quarter.png)、[视觉 STEP](../cad/exports/goose_r2_heel_study.step)和[生成清单](../cad/exports/goose_r2_heel_study_manifest.json)可供复核，**均不是制造或外观验收通过的版本**。

用户指出的布局问题属实。早期草模髋部在躯干中心后约 85 mm，腿看起来挂在机身后方。前移腿部安装基准 85 mm 后，髋部与躯干视觉中心同为 `x=-10 mm`。此时踝点 `x=0 mm`，原脚后缘仅约 `x=-14 mm`、前缘 `x=164 mm`，踝点过于贴近脚跟。三种脚型共用同一上身和腿轴坐标，以下范围来自黑色脚底网格最低 1 mm 的顶点，而非实测橡胶接触压强：[脚型几何核查](../evidence/exterior_support_screen_v35.json)、[整体后移 25 mm](../evidence/exterior_support_screen_v36_footback.json)、[仅加长后掌 50 mm](../evidence/exterior_support_screen_v36_heel.json)。

| 候选 | 双脚前后几何接触范围 | 脚踝到后缘／前缘 | 判读 |
| --- | --- | --- | --- |
| 原脚位 v35 | `−14～164 mm` | 约 `14／164 mm` | 后方余量过小，脚踝明显偏后 |
| 整脚后移 25 mm | `−39～139 mm` | 约 `39／139 mm` | 改善脚跟余量，但损失 25 mm 前方接触范围 |
| 后掌延长 50 mm，脚尖不动 | `−64～164 mm` | 约 `64／164 mm` | 两端几何余量同时保留；暂作下一轮候选，尚需摆腿净空和打印质量实测 |

即使双脚范围包含重心，单脚期仍需让整机重心从中线向支撑脚至少横移约 `43 mm`，再加控制裕量。这个数是接触网格的必要条件，**不是行走可行性证明**。后掌更长也可能在摆腿时擦地；没有步态试验前不能把它冻结为最终脚型。

[条件质量复核](../evidence/exterior_mass_screen_v36_heel.json)用旧候选的准确电机 SKU 厂商质量、[电子件预留](../hardware/component_envelopes.json)和视觉壳面按统一 `1.2／1.6／2.0／2.4 mm` PETG 壁厚乘密度估算；相交的外饰面、实际填充、金属支架和电机包装均尚未精确拆分。按 `1.6 mm` 情形，估计质量 `4.08 kg`，静止站姿投影重心约 `x=10 mm`，后掌版的双脚前后边界余量至少约 `74 mm`；这只说明双脚静态投影不在边界外，不保证关节有力或能迈步。将躯干前俯 `40°`、长颈折向 `x=300 mm` 地面目标的外观姿态，估算每侧髋关节需约 `1.49 N·m` 的等分静态重力矩，超过旧 XM430 的 `0.82 N·m` 初筛值。该姿态的下颈外饰还侵入机身约 `2 mm`；[低头几何筛查](../evidence/exterior_ground_reach_screen_v36_heel.json)只采样网格顶点，实际安全净空需要更大。

[独立 MuJoCo 候选](../evidence/physics_stance_trial_v36_nominal_detailed.json)加入自由机身、左右脚底与地面摩擦、各腿髋／膝／踝、颈部关节及按条件质量生成的惯量，按现有限力运行：名义站姿约 `0.69 s` 失稳，低头姿态约 `0.24 s` 失稳。相同几何把所有关节限力临时放大 `2.5` 倍，[站姿可维持 `2 s`](../evidence/physics_stance_trial_v36_torque_2p5_detailed.json)，低头仍约 `0.35 s` 失稳；放大 `5` 倍虽短时未倒，[喙尖已偏离目标并穿过地面](../evidence/physics_stance_trial_v36_torque_5_detailed.json)，不算完成拾取。大力矩对照只用来定位问题，不是电机选型，也没给出连续温升证明。名义站姿的膝关节控制长期触限，说明仅升级髋部不足以闭合方案。

不让躯干前倾、而将同一两段颈部折到地面，数学上有一组视觉解；下颈外饰却进入原机身约 `36 mm`。若选择这条路线，需设计颈根大角度扫掠通道，同时迁移内部器件和结构框架，再验证全程自碰撞、线束、关节角度与承力。该姿态的每侧髋部估算静态重力矩约 `0.76 N·m`，贴近旧 XM430 初筛上限，缺少步行和接触扰动余量；不能仅通过削壳宣称落地。长颈、躯干高度、膝位置和电机能力需要联立优化。

当前判定：保留低矮一体化后掌作为外观候选；**否决现有腿部驱动与低头轨迹的工程放行**。在真实零件包络和质量表闭合后，先做颈根避让与膝部力臂方案，再以同一版本模型验证站立、单脚、触地拾取和移动拖拽；PPO 只能在物理模型与控制限力合理时补充控制可行性，不能替代结构或连续力矩验证。已有 PPO 站立冒烟训练只是诊断，未形成步行策略。

进一步按[MicroDuck Max Pro 基线](microduck_max_pro_baseline.md)复核，旧 5 轴腿没有实现用户要求的腿脚自由度升级；其官方模型的踝点位于足底前后接触范围内，且站姿前后重心几乎压在踝轴上。Goose 下一版须比较每腿 5 轴与增加踝侧倾后的 6 轴，连同脚底形状、单脚换重心及新增电机质量一起求解。原脚型候选和旧 16 轴控制接口不能直接升级为通过版。

[DGX Spark 的一次 RSL PPO 诊断](../../../experiments/Goose_V0.1/r2_stance_dgx_nominal_20260928/metadata.json)在旧低限力候选上训练 61,440 环境步；12 次独立 4 秒站姿回放为 0 次通过，说明该短实验没有弥补模型缺口，不是 Goose 最终策略。[髋俯仰和膝换 XM540 的同增益对照](../evidence/physics_stance_trial_v36_xm540_hip_knee_kp40.json)虽站立 2 秒，低头仍约 0.37 秒失稳。两者都只用于定位结构/控制问题，不能替代制造包络、连续扭矩和真实夹拖验证。

## R2 比例修正与第六腿轴初筛（2026-09-28）

针对用户确定的尖嘴参考，后续视觉草模把头壳放大至原草模的 `1.15` 倍、喙长改成 `1.20` 倍，保持髋部前移和 50 mm 后掌。[当前侧视](../images/r2_proportion_side_candidate.png)、[斜视](../images/r2_proportion_three_quarter_candidate.png)、[张嘴](../images/r2_proportion_open_beak_candidate.png)与[视觉 STEP／清单](../cad/exports/goose_r2_proportion_visual_candidate_manifest.json)可复查；外观仍未过关。此版[脚底筛查](../evidence/exterior_support_screen_r2_proportion.json)给出单脚时重心至少横移 `42.88 mm` 的必要几何条件；[条件质量](../evidence/exterior_mass_screen_r2_proportion.json)约 `4.121 kg`，低头等分髋部静态重力矩约 `1.549 N·m`，均非实物量测。[新几何低头筛查](../evidence/exterior_ground_reach_screen_r2_proportion.json)只有约 `3.29 mm` 的采样最小颈根间隙，远不足以作为运动包络验收。

在同一新外形的简化 MuJoCo 接触模型中，[原电机限力](../evidence/physics_stance_trial_r2_proportion_nominal.json)名义站立约 `0.671 s` 跌倒。把左右髋俯仰与膝换成 XM540 后，[五轴腿对照](../evidence/physics_stance_trial_r2_proportion_xm540.json)以 `4.453 kg` 的条件质量站立 `2 s` 未倒，低头仍约 `0.358 s` 跌倒。加入左右踝侧倾 XM430 后，模型成为**每腿六轴的诊断候选**，质量约 `4.617 kg`；它尚未接入旧 RC2 的 CAD、BOM、训练协议或跨引擎模型，不能称为已交付的 18 轴 Goose。

[第六轴短时试验](../evidence/physics_stance_trial_r2_proportion_ankle_roll_single_support.json)使用同一条件模型及 `kp=40, kd=2`、关节 PD 和初筛扭矩上限。双脚着地时，两髋侧倾 `−14.32°`、两踝补偿 `+14.32°`，整机重心向左移约 `50.9 mm`，足底基本平贴，2 秒未倒；锁住踝侧倾的对照约 `1.815 s` 跌倒。这是第六轴的**局部收益**，不是可行走证明。接着按三组侧移角抬右脚：`14.32°` 方案右脚全程仍触地，未完成卸载；`17.19°` 和 `20.05°` 方案出现短暂离地，但分别约 `1.952 s`、`1.644 s` 侧翻。三组均未通过单脚支撑。该试验只有矩形脚底、近似惯量和开环关节目标，没有压力反馈、零力矩点、真实电机连续温升或实体夹拖；调 PPO 不能替这些输入缺口背书。

[踝部电机本体盒初筛](../evidence/ankle_roll_package_screen_r2_proportion.json)把俯仰轴留在后方、侧倾轴放入鞋内前方，两个 XM430 本体盒名义分开 `16.75 mm`，但侧倾电机顶面比现有白鞋壳高 `7.25 mm`，需新空腔和罩盖；输出盘、惰轮、轴承、线束、螺钉及全行程扫掠尚无可装配结论。**工程判断：保留六轴腿为值得继续的 Max Pro 候选，不冻结为最终自由度。下一步先在不破坏 B/R2 外形的前提下闭合支撑脚负载、单脚控制和实体踝脚包装；低头拾取另需重设计颈根避让与躯干姿态。**

## 较紧凑的 R2 整机比例：踝轴包装修正后仍未放行

[新外观比例](exterior_review.md)将高颈草模约 `788 mm` 的视觉高度降至约 `629 mm`，机身和 R2 收尖嘴尺寸不变。第一次直接压低全腿时，[踝部本体筛查](../evidence/ankle_roll_package_screen_r2_profile.json)发现踝俯仰 XM430 本体进入脚底约 `7.95 mm`，所以该压缩法被否决。随后保留踝轴 `z=51 mm`、缩短膝髋之间与膝踝之间的竖向跨度，形成[现行外观候选](../cad/exports/goose_r2_ankle_clearance_visual_candidate_manifest.json)；[新本体盒筛查](../evidence/ankle_roll_package_screen_r2_ankle_clearance.json)中俯仰电机底部高于橡胶鞋底顶面约 `2.25 mm`，侧倾电机本体与俯仰电机本体名义相隔 `16.75 mm`。但两台电机分别高出白鞋壳约 `23.25/7.25 mm`，还没有真实空腔、盖板、支架、惰轮与线束，**仍不是可装配的脚**。

[同版足底筛查](../evidence/exterior_support_screen_r2_ankle_clearance.json)的前后接触范围不变，单脚几何上仍至少要求横移 `42.88 mm`。[1.6 mm PETG 条件质量](../evidence/exterior_mass_screen_r2_ankle_clearance.json)约 `4.023 kg`，站姿重心高度约 `267.63 mm`，比高颈候选的约 `328 mm` 低；目标低头姿态的每侧等分髋部静态重力矩仍约 `1.396 N·m`，高于旧 `0.82 N·m` 初筛值。[低头网格筛查](../evidence/exterior_ground_reach_screen_r2_ankle_clearance.json)显示口尖可到地面目标，但下颈外饰与机身采样穿入约 `5.13 mm`。这些都是条件估算，不能当打印质量或实际连续扭矩。

[自由机身 MuJoCo 短试验](../evidence/physics_stance_trial_r2_ankle_clearance_six_axis.json)计入较重的双髋俯仰／双膝 XM540 和两台新增踝侧倾 XM430，条件总质量约 `4.519 kg`。名义站姿维持 2 秒；预设低头约 `0.344 s` 跌倒。双脚侧移时，即使有踝侧倾补偿，重心只移动约 `38.3 mm`，小于接触几何所需的 `42.88 mm`；三组侧移后抬右脚的诊断中，右脚始终接地，均未达到单脚支撑。因此这版降低重心、避免电机进入脚底，却**仍未证明第六轴实现 MicroDuck Max Pro 的行动能力升级**。真实电机连续额定、侧移控制、承力鞋壳、完整低头碰撞、移动拾取与拖拽都尚待闭合；旧 16 轴 RC2 的策略和接口不能直接移用。

为区分髋侧倾限力与控制轨迹问题，又在**同一外形、接触和 PD 命令**下将两侧髋侧倾也临时按 XM540 的质量与 `2.12 N·m` 初筛限力计算。[限力对照](../evidence/physics_stance_trial_r2_ankle_clearance_hip_roll_torque.json)条件质量增至约 `4.685 kg`；三组单脚试验仍未让右脚稳定离地，低头约 `0.345 s` 跌倒。即使髋侧倾的触限明显下降，踝与脚底接触、躯干回滚和开环姿态目标仍限制卸载。**不能据此前的触限率直接断言“换大髋电机就能走”，也不能据此否定踝侧倾的潜在价值。**下一次应先在完整关节包装模型中加入支撑脚压力/姿态反馈、验证可卸载的单脚轨迹，再决定第六轴和执行器组合；PPO 应在这套可解释的物理基线上训练与独立回放。

## MicroDuck Max Pro 的缩壳／坐姿候选

用户新增的方向是缩小机箱、让颈前段更能活动、双腿折低也能叼取地面物体。[同版外形](exterior_review.md)把视觉机箱从 `350 × 205 × 230 mm` 收至 `310 × 190 × 200 mm`，不改变 R2 尖嘴和高踝轴。[双脚几何范围](../evidence/exterior_support_screen_r2_compact_body.json)仍是前后 `−63.62～163.62 mm`，单脚仍需至少 `42.88 mm` 侧移。按相同 `1.6 mm` PETG 壁厚估计，[条件质量](../evidence/exterior_mass_screen_r2_compact_body.json)从上一候选 `4.023 kg` 降到 `3.811 kg`；这仅是视觉薄壳面积账本，机内支架、铰链、布线及真实打印质量尚未闭合。

双腿保持鞋底水平、机身降低 `90 mm`、前俯 `20°` 的[坐姿几何筛查](../evidence/exterior_seated_reach_r2_compact_body_90_20.json)给出髋／膝／踝俯仰约 `+4.76°/−63.30°/+38.54°`；嘴尖 `z≈20 mm` 时下颈与缩壳的采样间隙 `14.84 mm`、机箱最低点 `72.22 mm`。嘴尖改到 `z≈40 mm` 时，[间隙约 `19.98 mm`](../evidence/exterior_seated_reach_r2_compact_body_tip40.json)。两组都没有完成全行程自碰、真实电机安装、嘴内夹物或受力验证；图上的 60° 向下嘴角也偏“啄地”，不是已经验收的拖拽接近姿态。

在独立 MuJoCo 候选中，用 XM540 假设的双髋俯仰／双膝／双踝俯仰及 XM430 踝侧倾，质量约 `4.473 kg`。[六轴腿同版短试验](../evidence/physics_stance_trial_r2_compact_body_six_axis.json)站姿保持 `2 s`，但三组单脚抬脚均为 `0` 次干净单脚支撑；所谓“低头未跌倒”靠的是嘴端胶囊与地面接触约 `97.4%` 时间、峰值法向反力约 `23.61 N`，不能算拾取。单独的[坐姿嘴尖 40 mm 试验](../evidence/physics_seated_reach_r2_compact_body_tip40.json)中两脚仍接触地面，但嘴端接触地面约 `95.1%` 时间、峰值法向反力约 `34.51 N`，最终嘴尖从目标 `40 mm` 下沉到约 `8.7 mm`；目标保持率为 `0`。额外把 PD 增益提高的[诊断](../evidence/physics_seated_reach_r2_compact_body_tip40_kp60.json)也未消除这一问题。因此缩壳＋坐姿只是**有价值的几何方向**，仍未形成不靠嘴撑地的真实夹取或更强步态。

本试验的嘴只是一条地面接触胶囊，没有 R2 上下喙夹紧、指定物、喙部顺应性或接触力反馈；静态电机上限仍是初筛，不含连续温升。下一结构迭代须先让嘴内有效夹持区以合适角度接近物体、双脚独立承重、再在坐下—夹紧—起身—拖拽整段验证。更大电机或 PPO 不能替代这个接触与支撑判据。

## 短鞋与前移膝轴的足底独立承重初筛

[同版权衡](forward_knee_trade_study.md)继续保留缩壳与高踝轴，收短鞋尖 40 mm、膝轴前移 30 mm。按相同简化质量和短时限力，嘴尖 `(x=280,z=40) mm` 的双脚静力解在无载时为限力的[约 `0.934` 倍](../evidence/foot_only_equilibrium_r2_forward_knee_x280_unloaded.json)；把 `50 g` 物体等效为向下 `0.4905 N` 外力后为[约 `0.977` 倍](../evidence/foot_only_equilibrium_r2_forward_knee_50g_sweep.json)。后一项只给必要静力条件，余量很薄；壳体、结构质量和电机连续能力尚未确定。

用无载静力解辅助关节保持的[2 秒坐姿试验](../evidence/physics_seated_reach_r2_forward_knee_x280_tip40_ff.json)中，两脚同时触地约 `99.9%` 时间、嘴触地为零，采样头壳对机身间隙约 `13.9 mm`。此结果修复了上一缩壳候选“嘴替双脚撑地”的伪成功，但只成立于这套无物体的简化接触和控制模型；没有夹紧物体、带载起身、单脚支撑或迈步。较近的 `x=210 mm` 姿态虽可被旧简化模型保持，头壳实际进入机身约 `39.9 mm`，已被几何筛查否决。三组单脚卸载及追加的大侧移测试仍失败，不能把低位保持推广为走路或拖拽能力。

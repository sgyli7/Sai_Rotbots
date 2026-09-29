# Goose 的 MicroDuck Max Pro 基线

用户定义的 Goose 是 MicroDuck 的 **Max Pro 能力版**：原机的行走机动性和嘴部抓握还不足以满足目标，Goose 才增加腿脚自由度、可弯长颈和能真正叼起、移动拖拽指定物的 R2 尖嘴。保留原 B 步行鹅、R2 收尖且可平行张开的鹅嘴外观方向。外观必须先达到用户参考图的辨识度；工程取舍不能把它改成另一只比例失真的鸭子。MicroDuck 提供经过实机工作的系统和模型方法，**其尺寸、现成策略和电机余量不能直接视为 Goose 的验证结果**。

对原外观草模做了单一可回退的 R2 嘴长对照：[侧视](../images/r2_pointed_max_pro_side_candidate.png)、[斜视](../images/r2_pointed_max_pro_three_quarter_candidate.png)、[张嘴细节](../images/r2_pointed_max_pro_open_detail_candidate.png)、[视觉 STEP](../cad/exports/goose_r2_pointed_max_pro_visual_candidate.step)及[闭嘴生成清单](../cad/exports/goose_r2_pointed_max_pro_visual_candidate_manifest.json)／[张嘴清单](../cad/exports/goose_r2_pointed_max_pro_visual_open_candidate_manifest.json)。它只把原短嘴从铰点向前拉长 1.6 倍，供 B/R2 多视角轮廓比较；仍保留草模其他比例和质量缺口，**不代表用户外观验收、R2 平行机构装配或制造放行**。

本次量测使用 Pollen Robotics [MicroDuck RL 固定提交 `5946fd9`](https://github.com/pollen-robotics/microduck_rl/tree/5946fd9cdbc58956424420153e51975af3b30d77) 的 `scene_walk.xml`、`robot_walk.xml` 和网格，运行端对照 [MicroDuck 固定提交 `bc41fb5`](https://github.com/pollen-robotics/microduck/tree/bc41fb5c9a9b39894669c1e022e375cf83800382)；可复算的 [几何与质量对照](../evidence/microduck_baseline_comparison.json)由[量测脚本](../../../scripts/diagnostics/check_goose_microduck_baseline.py)生成。上游资料没有复制进 Goose 交付包。旧资料中的 MicroDuck 模型与方案说明仍保留，参见[来源审查](primary_sources_review.md)。

| 核查项 | MicroDuck 已有能力或模型事实 | Goose 的增量与判断 |
| --- | --- | --- |
| 腿脚 | 每腿髋偏航、髋侧倾、髋俯仰、膝俯仰、踝俯仰 **5 轴**。运行端 15 台电机，其中嘴部独立，PPO 输出其余 14 轴。 | 旧 RC2 **仍是每腿 5 轴**，没有实现用户希望的腿脚自由度升级。下一结构候选增加左右**踝侧倾各 1 轴**，即每腿 6 轴；检验单脚支撑、侧向重心转移、脚掌平贴及叼/拖受侧向扰动的收益。独立脚趾或复杂后掌只在任务证据要求时添加。 |
| 颈头和嘴 | 已有颈俯仰、头俯仰/偏航/侧倾 4 轴，另有独立嘴部电机与开合控制；不是只会摆头的空壳。 | Goose 需要更长且可弯折的鹅颈、R2 尖嘴单电机平行夹持、50 g 夹取和拖拽力路径。头颈总 5 轴仍是候选；4 轴方案与 5 轴方案要按地面可达、视野和负载比较，不靠轴数多少定输赢。 |
| 质量和尺度 | 官方 RL README 描述约 25 cm、800 g；实际 MJCF 惯量质量合计 **0.737 kg**。STAND 关键帧的重心约 `(0.6, 0, 141.7) mm`，嘴尖高约 `224.5 mm`。 | **v36 后掌草模**假设 1.6 mm PETG 壳体时约 **4.08 kg**，重心高约 **324 mm**，分别是 MicroDuck 的 **5.53 倍质量**和 **2.29 倍重心高度**。这个对照否决“原控制器/电机直接放大可用”的推断；4.08 kg 也只是条件估算，并非锁定目标。新加长嘴视觉版还没有重新做质量与动力学估算。 |
| 脚踝与脚底 | STAND 关键帧脚踝几乎与全机重心同一前后坐标；最低 2 mm 网格点所给脚踝后/前几何余量约 **17/31 mm**。 | 当前 Goose 后掌候选约 **64/164 mm**，前后比例仍比 MicroDuck 偏向长脚尖。脚掌后移与后掌延长需同时考察摆腿扫掠、接触面积与外观；仅静态双脚投影通过不足以证明走得稳。 |
| 训练/运行 | 官方 [RL 说明](https://github.com/pollen-robotics/microduck_rl/blob/5946fd9cdbc58956424420153e51975af3b30d77/README.md)列出 50 Hz PPO/ONNX、实机运行、BAM XL330 电压/摩擦模型、背隙和电池/延时随机化、步行/起身/地面接近等独立任务。 | 借其**方法**：准确执行器模型与实机控制周期、统一观测/动作契约、分任务策略切换、严格独立回放、质量/重心/摩擦/电压扰动。Goose 电机和整机尺度不同，须重新标定执行器与策略，不能导入 MicroDuck 权重冒充可行走。跨引擎接收器仍走中立 SI 契约，Godot 先验证，Unity/Bevy 保留同等适配条件。 |
| 地面拾取 | [GroundPick 源码](https://github.com/pollen-robotics/microduck_rl/blob/5946fd9cdbc58956424420153e51975af3b30d77/src/mjlab_microduck/tasks/microduck_ground_pick_env_cfg.py)让口尖**接近地面而避免撞地**，再回到站姿；明确奖励双脚接触及脚掌平贴。 | 很适合作为 Goose 的“接近—保持姿态—回站”任务结构，但它不包含真实物体接触夹紧、提起、边走边拖的完整闭环。Goose 要另测抓取接触、喙部受力、单/双脚换相与移动牵引。 |

GroundPick 源码另采样口端 `10–40 g` 虚拟重量，却把施力函数登记为 `weight=0.0` 的奖励。当前本机 `mjlab` 的 `RewardManager.compute()` 遇到零权重项直接 `continue`，该施力函数不会运行；**不能引用这段配置宣称 MicroDuck 已验证负载拾取**。即使以后修正施力，口端向下外力也不等于真实夹持、物体惯量和拖拽接触。

当前 16 轴 RC2 与 78 cm 量级外观草模均不冻结为 Max Pro 结构。下一版先对照用户 B/R2 图确定外轮廓，再在同一可检查 CAD/MJCF 里比较 **10 腿轴原型**与**12 腿轴踝侧倾原型**；后者若保留 5 轴颈头和 1 轴嘴，总计为 **18 主动轴候选**。[现有脚型几何筛查](../evidence/exterior_support_screen_v36_heel.json)给出单脚支撑时重心至少侧移约 43 mm 的必要条件；若暂用 324 mm 重心高度的刚体近似，相当于约 `atan(43/324)=7.6°` 的侧倾。髋侧倾能把机身移向支撑脚，踝侧倾可补偿足底滚转以保持脚掌平贴；确切关节角、扭矩与步态仍须在完整模型里求解。新增轴必须在动作试验中改善单脚脚掌平贴、侧向承重或受力拾取/拖拽，且其电机与线束能装入不破坏外观的腿脚。若两轴只增加重量和成本，不能因为“Max Pro”名称而强行保留。既有 16 轴模型、BOM、53/10/16 维接口仍标为 **RC2 历史候选**；18 轴必须创建新的版本和动作契约，不能暗改旧模型或让旧策略混用。

现有 [R2 脚型与物理试验](stance_layout_review.md)已显示旧驱动限力的站姿和低头失败。在相同 `kp=40, kd=2` 诊断控制增益下，把髋俯仰与膝的候选电机都改成更重的 XM540（条件整机质量增至 4.412 kg）后，[短时 MuJoCo 对照](../evidence/physics_stance_trial_v36_xm540_hip_knee_kp40.json)在 2 秒站姿没有跌倒，但低头仍约 `0.37 s` 失稳，且没有连续温升、脚踝升级或夹取接触；这说明“只换大电机”也不解决目标动作。此前 [DGX Spark PPO 诊断](../../../experiments/Goose_V0.1/r2_stance_dgx_nominal_20260928/metadata.json)对旧低力矩候选训练 61,440 环境步，12 次独立 4 秒站姿回放均失败；这只能否决该短训练结果，不能证明 PPO 路线或 Goose 方案本身不可行。

更新的[同一外形六轴腿试验](stance_layout_review.md)已把左右踝侧倾放入物理候选，并计入新增电机质量。它在双脚侧移时有足底平贴收益，但三组单脚换重心／抬脚试验均失败；[踝部包装](../evidence/ankle_roll_package_screen_r2_proportion.json)也只有电机本体的必要包络检查。这正是 Max Pro 的工程验收分界：**关节多两个不自动等于行动能力更强**。保留六轴方案继续优化，但不能把现阶段试验称为行走或抓拖能力升级成功。

用户进一步明确，Goose 可以借鉴 MicroDuck 较小的机箱，让颈前段有更大活动范围，目标是**双腿折低时仍能从地面叼取**。新[紧凑机身同版外形](exterior_review.md)已把机箱从视觉草模的 `350 × 205 × 230 mm` 缩到 `310 × 190 × 200 mm`，并保持长颈、R2 收尖嘴、双足和抽象翼门。它验证了缩壳＋坐姿的几何收益，但[接触试验](../evidence/physics_seated_reach_r2_compact_body_tip40.json)发现嘴端承受大量地面反力，尚未完成不靠嘴支撑的夹物姿态。后续要比较颈前段活动范围、嘴内接触角、坐下／起身控制与腿部实际卸载，不能仅凭更小机箱或更多轴宣称 Max Pro 能力已实现。

后续[短鞋、前移膝轴与颈部够地对照](forward_knee_trade_study.md)在更完整的足底承重筛查下，找到一个不让嘴撑地的**无物体**低位保持姿态；头壳与机身仍只有约 `13.9 mm` 端点采样间隙，嘴向下约 `60°`，静力和短时动力学结果都不能替代真实夹物。重电机版简化整机约 `4.36 kg`，远大于 MicroDuck 上游模型的 `0.737 kg`；收小外壳没有把质量与控制问题缩回原机尺度。颈前段所需更大俯仰行程必须与接触角、承力和线束一起设计，而不是直接复用 MicroDuck 的电机或地面接近策略。

最新[280 mm 视觉机箱与前颈够地对照](r2_compact_front_reach_review.md)把“小机身”变成了可复查的工作区差异：同一坐姿、同一目标网格的壳体避让从 10/15 提高到 13/15；嘴尖 15 mm 高时短时外力代理不靠嘴撑地，10 mm 高时却发生嘴端碰地。它支持继续沿紧凑机身和前颈活动空间设计，**不**证明已能叼起贴地的薄物、背载起身或步行。新视觉候选质量估算仍约 `4.038 kg`，继续远高于 MicroDuck；原机电机和策略不得直接复用。

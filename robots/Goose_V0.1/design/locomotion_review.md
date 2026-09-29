# RC2 双足控制审查与步态验收

当前目标是室内平整硬地面的前进、后退、转向、停止，再叠加 50 g 持物和约 2 N 牵引；静态站立不能替代行走。所有策略回放都保留自由机身、真实足地接触和电机力矩上限。训练奖励只用于搜索策略，不能单凭奖励放行。

| 候选 | 实际变更 | 独立结果 |
| --- | --- | --- |
| `goose_rc2_v1` | 训练从直腿 `home` 起步，策略目标也以 `home` 为中心；动作最大 ±0.30 rad，达不到已验证站姿膝角 0.70 rad。 | [100 轮回放](../evidence/walk_policy_100iter_rc2.json)四项都在约 2 秒内跌倒；[直腿原位静止](../evidence/stand_home_failure_rc2.json)本身失败。已废弃。 |
| `goose_rc2_v2` | 训练起姿和动作中心统一为中立文件的 `standing`；原腿部位置增益 5 N·m/rad 不变。 | [200 轮回放](../evidence/walk_policy_200iter_v2_rc2.json)四项仍倒，脚未有效离地。已废弃。 |
| `goose_rc2_v3` | 保持 53/10/16 维观测/策略/执行器定义，腿部位置增益初筛为 15 N·m/rad；策略动作仍以 `standing` 为中心，世界/机体坐标与 SI 单位不变。 | 早期[MuJoCo 站立记录](../evidence/stand_neutral_policy_mode_v3_rc2.json)沿用了每 1 ms 重算力矩的评估器，[Godot/Jolt](../evidence/godot_jolt_standing_v3_policy_mode_rc2.json)则按 5 ms 接收；不能把两份旧记录当同周期通过。200 轮训练用了 MuJoCo 内部 `qfrc_bias`；[把旧策略仅作诊断接到 v4 中立接收器](../evidence/walk_policy_v3_on_v4_receiver_rc2.json)时四项均约 1 秒跌倒。版本护栏会阻止正式混接；此试验不能作为跨引擎策略交付。 |
| `goose_rc2_v4` | 训练与运行共用中立刚体重力前馈，腿部位置/速度增益 15/0.30。 | [200 轮独立回放](../evidence/walk_policy_200iter_v4_rc2.json)四项均在 0.94–1.22 秒失稳。复查发现早期[MuJoCo 站立记录](../evidence/stand_neutral_continuous_torque_v4_rc2.json)每 1 ms 重算力矩，不能证明约定的 5 ms 模式；[修正后的 5 ms 站立试验](../evidence/stand_neutral_policy_mode_v4_rc2.json)失败。[Godot/Jolt v4 站立](../evidence/godot_jolt_standing_rc2.json)通过也不能掩盖这项 MuJoCo 失稳。已废弃。 |
| `goose_rc2_v5` | 保留 SI、53/10/16、20 ms 策略与 5 ms 力矩周期，把腿部速度阻尼由 0.30 降到 0.10；版本护栏阻止旧策略混入。 | [MuJoCo 真实 5 ms 站立](../evidence/stand_neutral_policy_mode_v5_rc2.json)与[Godot/Jolt 同模式站立](../evidence/godot_jolt_standing_v5_rc2.json)各自由站立 4 秒通过；[MuJoCo 零动作 8 秒](../evidence/stand_neutral_policy_mode_v5_8s_rc2.json)也通过。但[200 轮原策略回放](../evidence/walk_policy_200iter_v5_rc2.json)四项在 0.98–1.34 秒跌倒，[Jolt 同一候选的静止策略回放](../evidence/godot_jolt_policy_v5_diagnostic_rc2.json)也失稳；[仅作诊断的 0.25 倍动作](../evidence/walk_policy_v5_scaled_diagnostic_rc2.json)可站 8 秒，却无抬脚、有效位移或正确转向。步态仍未通过。 |
| `goose_rc2_v5` 低探索对照 | 模型、控制、奖励和 51,200 环境步不变；初始探索标准差 0.22→0.05，策略输出层从零动作开始。 | 训练期跌倒 877→255，但[MuJoCo 独立四项回放](../evidence/walk_policy_calm_init_v5_200_rc2.json)仍在 2.78–4.16 秒跌倒，均无有效双脚离地；改善存活时间尚不足以交付步态。[Jolt 同策略 4 秒静止诊断](../evidence/godot_jolt_policy_calm_init_v5_200_diagnostic_rc2.json)没有摔倒，但站姿偏差 8.15°、最大机身倾角 8.88°、根部位移 2.34 cm，超出站姿判据，也没有检验行走。[试验源与配置](../../../experiments/Goose_V0.1/rc2_walk_calm_init_v5_200/README.md)留档。 |

独立[回放工具](../../../scripts/evaluation/evaluate_goose_walk.py)设定静止漂移、前后位移、转向、倾角和双脚真实离地/接触切换判据；只看位移可能把滑脚误判为步行。它从 ONNX、策略元数据、模型和规格哈希绑定输入；策略只接收 53 维传感/指令观测，世界位姿与接触仅用于评分。当前命令和阈值是 RC2 工程诊断门槛，仍需完整负载步行及 Godot/Jolt 同任务回放。

v4 的主要失效已由[同模型控制周期/阻尼对照](../evidence/torque_cadence_diagnosis_rc2.json)定位：每 1 ms 更新、阻尼 0.30 站立 4 秒；每 5 ms 更新、阻尼 0.30 在 1.047 秒摔倒；每 5 ms 更新、阻尼 0.10 恢复 4 秒站立。初筛还发现 0.05–0.20 可站立，v5 取 0.10 并重新复测两引擎。v5 新问题不同：稳定的零动作基础上，策略原输出破坏平衡；把输出缩小四倍只剩原地站立。后续须先解决策略稳定动作与速度/转向指令响应，再做真实双脚抬离、持物与移动拖拽训练；不能无限追加轮数或用动作缩放冒充步态交付。任何再改控制增益、动作中心或反馈类型都要更新契约版本与策略来源，再复测两引擎的正常站立。

[固定种子的随机动作探针](../evidence/policy_exploration_probe_rc2.json)显示：标准差 0.03/0.05 的未训练动作在该样例存活 8 秒，0.10/0.22 分别在 3.12/1.42 秒跌倒；原 RSL 配置的探索标准差正是 0.22。这只是一组初始姿态和随机序列，不能推成通用安全阈值。后续低探索对照确实减少跌倒，却仍没有命令响应与有效步态；下一轮应审查动作空间、可观测速度、足底接触和训练课程，而不是再以训练奖励或存活时间替代独立回放。

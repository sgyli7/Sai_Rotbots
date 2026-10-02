# RC2 低探索、零动作起步的 v5 步态对照（失败样本）

与 `rc2_walk_neutral_v5_200` 使用相同模型、规格、SI 控制契约、奖励和 51,200 环境步；本试验把初始 Gaussian 动作标准差从 0.22 降为 0.05，并把策略输出层初始化为零。检查点、ONNX、元数据和 runner 配置来自同一次 200 轮训练；元数据保存修改后的源码哈希、初始化参数和策略哈希。

[固定种子探索探针](../../../robots/Goose_V0.1/evidence/policy_exploration_probe_rc2.json)只是选择该对照的局部依据，不是鲁棒安全阈值。训练期失败次数由原 v5 的 877 降为 255，但[MuJoCo 独立自由机身回放](../../../robots/Goose_V0.1/evidence/walk_policy_calm_init_v5_200_rc2.json)静止、前进、后退和左转仍分别在 2.80、2.92、2.78 和 4.16 秒跌倒，四项都没有双脚真实离地。[Godot/Jolt 同策略静止诊断](../../../robots/Goose_V0.1/evidence/godot_jolt_policy_calm_init_v5_200_diagnostic_rc2.json)虽未摔倒，具名站姿判据仍失败；这不是跨引擎步行验收。初始前进指令的动作变化量也很小；尚未学到可验收的速度响应。不能部署或拿训练奖励替代步行验收。

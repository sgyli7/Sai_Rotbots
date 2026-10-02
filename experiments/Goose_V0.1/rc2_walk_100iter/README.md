# RC2 旧控制契约步态试验（保留失败样本）

本目录保存 `goose_rc2_v1` 的 100 轮 RSL PPO 训练检查点、ONNX 策略、元数据与配置。8 个环境、每轮 32 步，共 25,600 个环境步；模型 SHA-256 `07d4209a5a7b9322a04b9cdb62694a69cf35c97716c262909d21f039599c4cb0`。策略只作失败复现，**不得部署**。

[独立回放](../../../robots/Goose_V0.1/evidence/walk_policy_100iter_rc2.json)的静止、前进、后退、左转四项均在约 1.5–1.94 秒跌倒，没有交替离地。随后确认旧环境从未通过站立测试的 `home` 姿态重置，旧动作目标范围无法达到已验证的膝关节站姿角度；[直腿姿态失败记录](../../../robots/Goose_V0.1/evidence/stand_home_failure_rc2.json)保留。后续控制契约升级到 `goose_rc2_v2`，以中立文件的具名 `standing` 作为动作目标基准，并重新测试 Godot/Jolt 站立；此目录不是新版本策略。

# Goose neutral transfer：Unity / Bevy 适配验证事实与清单

核查日期：2026-09-28。范围：已有 SI 导出、传感/力矩协议，以及未来 Unity / PhysX 和 Bevy / Rapier 接收器的验证条件。本轮只读取源码、官方文档与官方发布源码包；未启动 Unity/Bevy，未实现接收器，未修改模型、控制接口或其他项目。

**当前 Goose 的 Unity 和 Bevy 适配器均未实现、未验证，不能声称已兼容。** 此页下方哈希和行号是调查当时的快照；当前中立导出 SHA-256 为 `55481d54d22f4a2cb2be3c1526e3723da9cb5e743423bab7721a86dda8ab4cc3`，已补上具名任务点、相机、执行器速度边界、供所有后端共用的站立与地面叼取两个初始姿态，以及独立的 20 ms 策略 / 5 ms 扭矩周期，并去掉 `godot_adapter`/`future_adapters` 后端标注字段。现行 `goose_rc2_v5` 将腿部策略目标明确为“具名站姿角度＋0.30 rad × 动作”，并将腿部阻尼按真实 5 ms 周期修正；53/10/16 维数和 SI 单位没有改变。状态和哈希以重新生成的 [rigid_transfer.json](../models/full/rigid_transfer.json) 为准，Jolt 的私有质量尺度只在其适配器中。源码见 [导出入口](../../../scripts/models/export_goose_transfer.py)。

## 1. 已有输入基线

以下是本次读取 `models/full/rigid_transfer.json` 的快照。以后验证应重新记录哈希与统计，不能把本表当作未来导出包的固定值。

| 项目 | 已有值 / 源码依据 |
| --- | --- |
| 机器人 / schema | `Goose_V0.1`、`rc2`、`sai_rigid_transfer_v1` |
| 单位 / 坐标 / 四元数 | m、kg、s、rad、N·m；`x_forward_y_left_z_up`；`wxyz` |
| 步长 | 物理 `.001 s`，控制 `.02 s`，即每 20 个物理步一个控制周期；[导出:90](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/scripts/models/export_goose_transfer.py:90)、[控制:8](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/src/sai_agent/goose/control.py:8) |
| 结构 | 21 个刚体、20 个 hinge/slide 关节、1 个 `point_closure`；自由根不导出为固定关节，[导出:43](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/scripts/models/export_goose_transfer.py:43) |
| 观测 / 策略动作 / 力矩消息 | 53 / 10 / 16；10 个腿部动作，16 个有序编码器与执行关节，颈嘴独立控制；[控制:48](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/src/sai_agent/goose/control.py:48) |
| 被动嘴机构 | `passive_jaw_pin`、`passive_follower`、`passive_pad_compression`、`passive_pad_pitch`，加 `beak_loop` 闭环。不是 20 维策略动作 |
| 闭环 | `lower_jaw` 局部点 `[0,0,.018]` 与 `upper_crank` 局部点 `[.025,0,0]` 重合，`free_relative_rotation=true`；[导出:75](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/scripts/models/export_goose_transfer.py:75) |
| 惯量 | 每刚体质量、局部 COM、主惯量三个值、主轴局部四元数、home COM 与主轴世界姿态；不是仅提供源刚体坐标系对角惯量，[导出:33](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/scripts/models/export_goose_transfer.py:33) |
| 当前 armature | 20 个关节均为 0。以后出现非零值必须支持并验证，或显式拒绝；不能偷偷加到子体对角惯量 |

快照 SHA256：`rigid_transfer.json = d3075ecb53cad29efbe079630a4cfd993b35f52bfb755bf1d19566f78434970f`；包内 `model_sha256 = 7d0cce9eccd9b43d1b9fcdf2190ebdeb2e0916f907f48b1b742824debda2a59b`，`source_spec_sha256 = 7c4e8946a8bda5b1ae703b68aee89ee1d4c2c5ba465c4a57212bcbce40e119a6`。

已有 Godot 接收器采用局部 `MASS_SCALE=100`、COM 主轴刚体坐标、hinge 限位符号转换、等反作用力矩，以及滑动关节锚点施力。这些是该适配器的实现，不是 Unity/Rapier 的 API 约定，也不是跨后端通过证明；见 [goose_adapter.gd:4](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/integrations/godot/goose_robot/goose_adapter.gd:4)、[关节:100](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/integrations/godot/goose_robot/goose_adapter.gd:100)、[施力:217](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/integrations/godot/goose_robot/goose_adapter.gd:217)。

## 2. 接收端版本与物理路线必须先标明

本机 Unity 项目记录的是团结 `2022.3.62t14 / 1.10.2`，`org.mujoco` 固定到官方仓库 commit `13827e9ee56f097f57acf69ae52b078f9839682d`。其已存在的 MicroDuck 主路线使用 native MuJoCo，PhysX/ArticulationBody 为比较路线；见 [ProjectVersion.txt](/home/ethan/Projects/Sai_Lab/Unity_Sim2Sim/TuanjieProject/ProjectSettings/ProjectVersion.txt:1)、[manifest.json](/home/ethan/Projects/Sai_Lab/Unity_Sim2Sim/TuanjieProject/Packages/manifest.json:5)、[该项目运行路线](/home/ethan/Projects/Sai_Lab/Unity_Sim2Sim/README.md:12)。这只是本地工程事实，不是 Goose 接入结果。

因此未来 Unity 报告必须分别注明「Unity 渲染 + native MuJoCo」与「Unity + PhysX」。前者即使运行成功，也不能计作独立 PhysX 的 Sim2Sim 验证。本文件的 Unity 物理 API 依据是官方 **2022.3** 文档；团结分支的实际行为仍待在固定二进制上验证，不假定与上游所有细节一致。

Bevy 本地项目尚无 Cargo 工程，文档计划采用 Bevy `=0.19.1` 与 `bevy_rapier3d =0.36.0`；见 [实现起点](/home/ethan/Projects/Sai_Lab/Bevy_Sim2Sim/docs/implementation_plan.md:23)。本轮独立读取官方发布包，确认绑定的 `Cargo.toml:193–209` 使用 Bevy `0.19.0` 兼容范围、Rapier **`=0.35.0-glamx0.2`**；以 [0.36.0 发布清单](https://docs.rs/crate/bevy_rapier3d/0.36.0/source/Cargo.toml) 为准，不能用 Rapier 主线或其他版本源码替代实际绑定。

本轮读取的 [bevy_rapier3d 0.36.0 官方包](https://static.crates.io/crates/bevy_rapier3d/bevy_rapier3d-0.36.0.crate) SHA256 为 `20d17a43103d304271514b8fc955969ddfb8eb9e4d470d4e5dd1bbc03903ab50`；[Rapier 0.35.0-glamx0.2 官方包](https://static.crates.io/crates/rapier3d/rapier3d-0.35.0-glamx0.2.crate) 为 `d9961dfc6cabf508c2db7bc7a73b9d82800de898ccaed0bbaab58290c9620fc0`。源码只在内存解包读取，未安装或复制入工程。

## 3. 一手 API / 源码事实

### SI、坐标、全惯量

| 主题 | Unity 2022.3 事实 | Bevy / 发布 Rapier 事实 |
| --- | --- | --- |
| 力矩与时钟 | `Rigidbody.AddTorque(..., ForceMode.Force)` 输入为世界坐标 N·m，下一次物理积分应用；Acceleration、Impulse、VelocityChange 语义不同。`fixedDeltaTime` 是受游戏 timeScale 影响的秒数。[AddTorque](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Rigidbody.AddTorque.html)、[fixedDeltaTime](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Time-fixedDeltaTime.html) | `ExternalForce` 持续作用于每个物理步，不是一次性冲量；发布 `rigid_body.rs:310–341` 明确该语义。Rapier `integration_parameters.rs:219–232` 的 `length_unit` 是每米对应的世界单位数，并缩放内部容差；不是自动转换 SI 数据的接收器。[ExternalForce 源码](https://docs.rs/bevy_rapier3d/0.36.0/src/bevy_rapier3d/dynamics/rigid_body.rs.html#310-341)、[积分参数](https://rapier.rs/docs/user_guides/rust/integration_parameters/) |
| 方向约定 | 官方明确为左手坐标，+X 向右、+Y 向上、+Z 向前。[旋转与方向](https://docs.unity3d.com/2022.3/Documentation/Manual/QuaternionAndEulerRotationsInUnity.html) | Bevy `Transform::right/up/forward` 分别为局部 +X/+Y/−Z；v0.19.1 `transform.rs:290–325`。[固定版本源码](https://github.com/bevyengine/bevy/blob/v0.19.1/crates/bevy_transform/src/components/transform.rs#L290-L325) |
| COM / 主惯量 | Rigidbody 的 `centerOfMass` 相对 Transform 位置和旋转，**不包含 Transform scale**；`inertiaTensor` 是在 COM、经过 `inertiaTensorRotation` 旋转的主轴系中的对角值。未显式设置时，碰撞体会自动决定它们。[COM](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Rigidbody-centerOfMass.html)、[惯量](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Rigidbody-inertiaTensor.html) | `MassProperties` 包括局部 COM、mass、principal inertia、principal inertia local frame。`AdditionalMassProperties` 与附属碰撞体贡献**相加**，不是覆盖；应回读最终质量属性。[MassProperties](https://docs.rs/bevy_rapier3d/0.36.0/bevy_rapier3d/dynamics/struct.MassProperties.html)、[AdditionalMassProperties](https://docs.rs/bevy_rapier3d/0.36.0/bevy_rapier3d/dynamics/enum.AdditionalMassProperties.html) |
| 作用点 | `AddForceAtPosition` 的 force 和 position 都是世界坐标，产生线力及相对 COM 的力矩。[API](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Rigidbody.AddForceAtPosition.html) | `ExternalForce::at_point(force, point, center_of_mass)` 使用世界坐标；发布源码 `rigid_body.rs:327–340` 计算 `(point−COM) × force`。[源码](https://docs.rs/bevy_rapier3d/0.36.0/src/bevy_rapier3d/dynamics/rigid_body.rs.html#327-340) |

由方向约定推导的验证要求：接收器应单独记录 neutral→engine 的正交变换，并验证位置、重力、姿态、IMU 和关节轴往返一致。若变换含反射，不能把角速度、力矩和四元数当普通位置向量直接置换；轴向量与三角形绕序的奇偶性必须通过探针检查。这里不选定 Unity/Bevy 的转换矩阵，也未实测正方向。

惯量比较应重建同一 COM、同一坐标系下的完整矩阵 `I = R_principal · diag(I_principal) · R_principalᵀ`，再比较转换后的完整矩阵。COM 到模型原点的平移不等于可以丢弃主轴旋转。该式是基于已导出字段的验证推导；碰撞体追加、自动重算、层级 scale 或只取对角线均需被回读检查发现。

### 关节、闭环、相邻碰撞

| 主题 | 一手事实与未来限制 |
| --- | --- |
| Unity hinge / articulation | Hinge 围绕所设 anchor/axis 运动；`JointLimits.min` 的角度单位为**度**。Articulation revolute 是父 anchor 的 **X 轴**；`jointPosition` 角量为 rad，而 `ArticulationDrive.lowerLimit` 角量为度。API 能表明单位/轴，不能单凭这些资料判定当前父子选取、home 零点与力矩符号。[Hinge](https://docs.unity3d.com/2022.3/Documentation/Manual/class-HingeJoint.html)、[JointLimits.min](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/JointLimits-min.html)、[ArticulationBody](https://docs.unity3d.com/2022.3/Documentation/Manual/class-ArticulationBody.html)、[jointPosition](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/ArticulationBody-jointPosition.html)、[drive limit](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/ArticulationDrive-lowerLimit.html) |
| Rapier hinge / slider | GenericJoint 的主轴是 frame **X**，local axis / anchor 分别相对两个刚体；绑定 `generic_joint.rs:52–139`。发布 Rapier `generic_joint.rs:38–49`：revolute 只放开 AngX；prismatic 只放开 LinX，锁三转动。`RevoluteJoint::angle` 是 frame1⁻¹·frame2 的 X 旋转、范围 [−π,π]，`revolute_joint.rs:92–107`；角目标文档注明 rad。home 偏移、绕回与限位映射仍需实际探针，不能复制 Godot 的 hinge 限位取负规则。[GenericJoint](https://docs.rs/bevy_rapier3d/0.36.0/bevy_rapier3d/dynamics/struct.GenericJoint.html)、[PrismaticJoint](https://docs.rs/bevy_rapier3d/0.36.0/bevy_rapier3d/dynamics/struct.PrismaticJoint.html)、[发布 Rapier 关节源码](https://docs.rs/crate/rapier3d/0.35.0-glamx0.2/source/src/dynamics/joint/revolute_joint.rs) |
| Unity 点闭环 | Articulation 是逻辑**树**，树关系自身不能增加嘴部跨树边。ConfigurableJoint 可独立将三个平移 Locked、三个转动 Free，以表达点约束所需自由度；这是 API 的候选表示，不是已完成的 Goose 闭环方案。`connectedArticulationBody` API 的存在也不能证明团结版本支持任意 articulation link↔link 闭环组合；选中的组合必须单独运行验证，不支持则明确失败。[articulation tree](https://docs.unity3d.com/2022.3/Documentation/Manual/physics-articulations.html)、[ConfigurableJointMotion](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/ConfigurableJointMotion.html)、[connectedArticulationBody](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Joint-connectedArticulationBody.html) |
| Rapier 点闭环 | `MultibodyJointSet::insert` 返回 Option；同 multibody 再插入或第二体已有父 link 时返回 None，发布 `multibody_joint_set.rs:123–164`。官方说明可以用额外 impulse constraint 闭环；SphericalJoint 只锁三平移，未启用 angular limits/motors 时保留相对转动，绑定 `spherical_joint.rs:23–26`、Rapier `generic_joint.rs:44–53`。组件存在不代表该 Goose 闭环已经装入或数值通过。[闭环说明](https://rapier.rs/docs/user_guides/rust/joint_constraints/)、[发布 Multibody 源码](https://docs.rs/crate/rapier3d/0.35.0-glamx0.2/source/src/dynamics/joint/multibody_joint/multibody_joint_set.rs)、[SphericalJoint](https://docs.rs/bevy_rapier3d/0.36.0/bevy_rapier3d/dynamics/struct.SphericalJoint.html) |
| 相邻碰撞排除 | Unity `Physics.IgnoreCollision` 是 collider-pair 排除，保存场景不会持久保存该状态；必须在加载/重置后重新核对。Rapier `GenericJoint.contacts_enabled` 只管关节两端的碰撞，不能代表包内任意 body-pair 排除。两端各有多个碰撞体时需覆盖所有对应 pair。[IgnoreCollision](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Physics.IgnoreCollision.html)、[Rapier attached-body contacts](https://docs.rs/bevy_rapier3d/0.36.0/bevy_rapier3d/dynamics/struct.GenericJoint.html#method.contacts_enabled) |

Goose 当前无限位被动铰链可能有 `range=[0,0]`；接收器必须读取 `limited`，不能把这个数组当成焊死要求。被动压缩关节以 m、N/m、N·s/m 工作，被动角弹性以 rad、N·m/rad、N·m·s/rad 工作；这是 hinge/slide 分类型解释现有 SI 字段的要求，不能统一当“角度＋力矩”。

自由根内部执行器的验证要求来自已有导出，[adapter_requirements:93](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/scripts/models/export_goose_transfer.py:93)：若用刚体外部力矩表示关节执行器，应在父子体施加等大反向力矩；不能只驱动子体或额外固定 torso。若使用物理后端的关节广义力 API，则应通过无重力、无外接触的自由根动量探针证明反作用被包含，不能再重复加一套外力矩。

### 调度事实

Unity `Physics.Simulate` 不会调用 `FixedUpdate`；渲染帧率 delta 不适合作为固定物理步长。Bevy 绑定把同步、积分、回写分成 `SyncBackend → StepSimulation → Writeback`；`ExternalForce` 组件回写与直接写 Rapier 状态的顺序不同，重复上传会改变力矩。官方依据：[Unity Simulate](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Physics.Simulate.html)、[PhysicsSet](https://docs.rs/bevy_rapier3d/0.36.0/bevy_rapier3d/plugin/enum.PhysicsSet.html)。

绑定发布源码 `plugin/configuration.rs:15–60` 中 `TimestepMode::Fixed { dt, substeps }` 每次 tick 推进 dt、每子步 dt/substeps，默认却为 Variable、上限 1/60 s。仅设置 Bevy Fixed 时钟或 substeps 数不能证明已按 Goose `.001 s` 积分。源码依据：[0.36.0 configuration.rs](https://docs.rs/crate/bevy_rapier3d/0.36.0/source/src/plugin/configuration.rs)。

## 4. 未来逐项验证清单

以下各项 **Unity / Bevy 均未执行**。API 研究完成不改变这项状态；本表是后续检查范围，不选定实现架构或新增验收阈值。

| 编号 | 必须验证的条件 | 应保存的证据 |
| --- | --- | --- |
| B01 输入完整性 | 按 robot_id/schema/hash 加载 neutral 包；21 体、20 关节、1 闭环逐名对应。root 自由；所有局部 body/geom/joint/site 坐标经同一 source→engine 规则转换，具名 `standing` 与 `ground_side_grasp` 中的每体 COM/主轴和每个主动关节角应可复原。核对 world 静态几何与任务地面，不能因没有 dynamic body 而静默遗漏 | 包哈希、引擎/物理版本、名字映射、实际组件/constraint 数、姿态误差、缺失资源退出记录 |
| B02 SI / 坐标 | 长度、mass、gravity、dt、角量、force、torque、stiffness/damping 分类型正确。Godot 的质量比例与坐标矩阵不得隐式继承。若接收器内部缩放，质量/惯量/外力/内力/力矩/被动弹性全部一致且出端回到 SI | 三轴单位平移与旋转往返、gyro/gravity 符号、mesh 绕序、1 N/1 N·m 单体响应；注明变换及内部单位 |
| B03 全惯量 / COM | 逐体回读质量、COM、主惯量/主轴，与转换后的完整矩阵相符；排除 collider 密度叠加、自动重算与层级 scale。固定模型原点和 COM 主轴体的两种表示均需正确重建源 frame | 每体 SI mass、COM、完整 3×3 tensor 差异与世界 COM；非对齐主轴测试 |
| B04 hinge / slider | 父 A / 子 B、双方 local frame、home 零点、q 与 qdot 正方向、上下限一致。实际加正负力矩/线力并核对 motion。无限位关节不误锁；slide 锁三转动。角度 degree/rad 转换只发生在相应 API 边界 | 每个命名关节 home、正负扰动、非对称上下限结果；无重力单关节探针及 q/qd 轨迹 |
| B05 嘴部闭环 / 被动件 | 装入两局部点的三平移约束，保留相对转动；所有被动 hinge/slide、压缩/角弹性、阻尼和 spring_reference 保留。真实闭环限制产生运动，不能改成动画跟随、焊死或丢弃 follower | 开闭嘴全过程、点残差、各被动 q、受载压缩及卸载轨迹；插入失败/unsupported 的诊断 |
| B06 内力 / 接触 | 自由根等反作用，无外接触时核动量；压缩/弹簧线力使用实际锚点，速度包含该点的 `ω×r`，不是仅 COM 速度差。相邻与显式 body-pair 排除逐项生效；摩擦/接触近似明确记录，避免双重原生 damping 或 motor | 父子反作用、锚点力矩、非 COM 施力、排除 pair、接触位置/穿透/冲量与收敛结果 |
| B07 53 / 10 / 16 | 53 维严格按既有字段与缩放拼接；只含 IMU、编码器、command、上次腿部 action、phase。10 个腿动作使用 `action_joint_names`；力矩消息仍为 16 个 `encoder_joint_names`，含独立颈嘴控制；不借用 MicroDuck/Sai001 的维度或数组顺序 | 同一输入逐元素观测/目标/力矩对照、打乱名字顺序反例、模型与 policy metadata/hash 不一致反例 |
| B08 时序 / watchdog | physics dt=.001、策略决策 dt=.02、扭矩更新 dt=.005；同一扭矩周期内 gyro/q/qd 对齐，策略输出每四个扭矩周期更新一次。明确仿真时间与墙钟；控制帧单调、每份 torque 的 seq/time 对应，过期停止。逐步清空/重建应聚合的力，避免 Rapier 持续力累加或多套力矩重复应用 | step/策略/扭矩计数、暂停/掉帧/延迟/重复/乱序/重置测试、最后有效命令与停止原因；离屏与可见模式对照 |
| B09 显式失败 | 未知 schema/constraint/geometry、无效惯量/非零未支持 armature、坏名字/维度、非有限数、过大 torque、坏时钟、缺失资源或闭环插入失败均拒绝；不能静默改静态、跳过约束或退化几何后仍报 pass | 故障输入、明确错误、非零退出/失败结果、未继续用旧 torque 的证据 |

B07 的字段切片已存在：[control.py](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/src/sai_agent/goose/control.py)；gyro 3×.25、gravity 3、command 3、q−home 16、qd 16×.05、previous leg action 10、sin/cos phase 2。当前共同控制器的腿目标是 `standing + .3·clip(action,−1,1)`，[runtime.py](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/src/sai_agent/goose/runtime.py)，与训练起姿使用同一中立文件。`q−home` 仍是观测字段，不等于动作目标也以旧 home 为中心。策略/扭矩接收器按 v5 的 `neutral_rigid_gravity` 在每个 5 ms 扭矩周期算重力前馈，不读取 MuJoCo 专有偏置力；离线 MuJoCo 评估也必须按 5 ms 更新，不能用每个 1 ms 积分步的控制结果冒充策略模式。未来每个接收器必须验证这两种姿态参考和力矩来源不会混用。

B08/B09 应保留已有边界的含义：[协议](../../../src/sai_agent/goose/protocol.py)要求合同、SI、名字顺序、有限数据、gravity 单位范数和非负合法 seq/time；[共享控制器](../../../src/sai_agent/goose/runtime.py)拒绝旧/乱序帧和超过 `.08 s` 的传感时间间隔；扭矩消息默认有效期 `.06 s`、最大 `.1 s`，回显传感 seq/time 且检查力矩边界。现 [Godot 适配器](../../../integrations/godot/goose_robot/goose_adapter.gd)另有 `.5 s` 墙钟响应等待，并在仿真时间超过 action expiry 时退出。墙钟停顿与仿真帧间隔是两件事，不能只测其中一个。

## 5. 放行边界与仍未验证之处

目前只有导出数据和 API 事实；没有 Unity/Bevy Goose 的加载、单关节、自由根、闭环、控制器联通或任务回放证据。团结分支关节闭环组合、具体坐标/限位符号、发布 Rapier 的小尺度接触/闭环误差，以及实际调度次序仍需 B01–B09 探针。

未来最小证据应包括：固定版本与输入哈希、实际质量/惯量/结构回读、单关节和被动闭环探针、完整自由根控制回放、协议故障注入。每份结果必须注明作用范围；加载/站立成功不自动代表行走、拾取、拖拽或策略效果通过。阈值与任务放行条件留待对应验证方案，不在本研究中改定。

当前 `sai_rigid_transfer_v1` 只表达刚体、hinge/slide 和点闭环，未包含柔性布、视觉目标定位或任务场景的完整转换。未来若需要这些能力，必须另查相应真实资产与后端能力，不能把当前导出成功称为已支持。

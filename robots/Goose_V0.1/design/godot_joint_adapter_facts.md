# Godot 4.7.2 / vendored Jolt 关节适配事实

核查日期：2026-09-28。范围：官方 Godot **4.7.2.stable.official.ed1daf0bf**、其 vendored Jolt、PhysicsServer3D API。只用于 neutral SI 全身适配器的实现依据；没有修改主模型、控制契约或 Sai_Lab。

## 版本与证据来源

- 本机 `/home/ethan/.local/bin/godot --version` 返回 `4.7.2.stable.official.ed1daf0bf`。
- 源码固定提交为 [`ed1daf0bf001b61586d9930840f2f1394092c079`](https://github.com/godotengine/godot/tree/ed1daf0bf001b61586d9930840f2f1394092c079)，其中 [`version.py`](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/version.py) 记录 4.7.2 / stable。
- 本机原始源码压缩包：`/home/ethan/Projects/TempWorktree/Sai_Lab/legacy-godot/work/game60-upstream/godot-ed1daf0bf001b61586d9930840f2f1394092c079.tar.gz`，核算 SHA256 为 `e607e9985e1c201bc9cdc1aec8a120f0c3f53b9603f1f828e2b748534a2471ef`。只读取它，把少量审查文件放在本工作树 `.scratch/goose_joint_adapter_facts/sources/`。
- 同目录的既有 extracted engine source 带旧 armature 修改，hinge / joint / body / Jolt HingeConstraint 等文件与上述压缩包不同。**下文行号均对应固定官方压缩包，而不是那份修改副本。** 官方 4.7 文档只作补充，具体符号以固定版本源码和原版二进制探针为准。

## 1. Hinge：局部 frame Z，API 限位与 B 相对 A 右手角反向

`joint_make_hinge` 将传入的 A/B 局部 frame 直接交给 Jolt joint；scene node 的配置代码也用 body global transform 的逆变换计算局部 frame。frame 属于 **body origin 的局部坐标**，不是 world 或 COM 坐标。适配器不应先自行减 COM；Jolt bridge 会缩放局部 anchor、减 shape COM，再转成 LocalToBodyCOM。依据：[server 第 1353–1368 行](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/modules/jolt_physics/jolt_physics_server_3d.cpp#L1353-L1368)、[scene hinge 第 100–115 行](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/scene/3d/physics/joints/hinge_joint_3d.cpp#L100-L115)、[frame 转换第 45–66 行](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/modules/jolt_physics/joints/jolt_joint_3d.cpp#L45-L66)。

Hinge 轴取 frame **Z**，normal / 零角参考取 frame **X**，A 对应 Jolt body1、B 对应 body2。X normals 在 world 对齐时为零角。依据：[Godot hinge 第 60–83 行](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/modules/jolt_physics/joints/jolt_hinge_joint_3d.cpp#L60-L83)、[vendored HingeConstraint.h 第 30–46 行](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/thirdparty/jolt_physics/Jolt/Physics/Constraints/HingeConstraint.h#L30-L46)。

为说明符号，本文用 `q` 表示 **B joint frame 相对 A joint frame，绕 A frame +Z 的右手角**。这是数学标记，不是修改项目控制契约。轴已对齐时，用 world frame 的 `x_A/x_B/z_A`：

```text
q = atan2(z_A · (x_A × x_B), x_A · x_B)
q_dot = z_A · (omega_B - omega_A)
```

Jolt 的当前角计算是 body2 相对 body1 的有符号转角；Godot bridge 却把 motor target speed 取负，并把 A 参考 frame 旋转 `-midpoint`，随后使用对称 Jolt limits。由此推导且经探针确认：

```text
想要 q ∈ [q_min, q_max]：
    Godot HINGE_JOINT_LIMIT_LOWER = -q_max
    Godot HINGE_JOINT_LIMIT_UPPER = -q_min
    HINGE_JOINT_FLAG_USE_LIMIT = true
想要内建 motor 目标 q_dot：Godot motor target velocity = -q_dot
```

依据：[Jolt GetCurrentAngle 第 129–134 行](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/thirdparty/jolt_physics/Jolt/Physics/Constraints/HingeConstraint.cpp#L129-L134)、[Godot motor 第 118–125 行及 limit 第 392–410 行](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/modules/jolt_physics/joints/jolt_hinge_joint_3d.cpp#L118-L125)。limit midpoint 转换同文件 [第 392–410 行](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/modules/jolt_physics/joints/jolt_hinge_joint_3d.cpp#L392-L410)。

手动施加物理 torque 使用 world 向量的正常右手方向，**不应再套内建 motor 的取负**。若 adapter 用另一种 q 定义或交换 A/B，必须重新对应符号。本文只核双 body、无缩放、相同初始 joint frame；省略 body 接 world 时还可能由 Jolt `joint_world_node` 设置交换 A/B，源码见 [joint 第 122–129 行](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/modules/jolt_physics/joints/jolt_joint_3d.cpp#L122-L129)。

## 2. Slider：frame X，B−A 正位移，锁定三轴相对旋转

Slider 轴为 frame **X**，normal 为 frame **Z**。vendored Jolt 同时求解两轴横向位置约束和全相对旋转约束；它不是允许绕滑动轴旋转的 cylindrical joint。Godot 的 slider angular-limit 参数在 Jolt 下不被采用，修改非零值会警告。依据：[Godot slider 第 70–82 行](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/modules/jolt_physics/joints/jolt_slider_joint_3d.cpp#L70-L82)、[Jolt 第 257–266、309–313 行](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/thirdparty/jolt_physics/Jolt/Physics/Constraints/SliderConstraint.cpp#L257-L266)、[Godot 忽略 angular limits 第 310–318 行](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/modules/jolt_physics/joints/jolt_slider_joint_3d.cpp#L310-L318)。

以 world anchor `p_A/p_B` 和 A frame world +X `x_A` 定义 `s = x_A · (p_B - p_A)`，**Godot lower/upper 直接对应 `[s_min,s_max]`，不用 hinge 的符号反转**。Jolt 当前位移明确计算 B anchor 减 A anchor再投影；Godot 的负 midpoint linear shift 最终把 A anchor 移到 midpoint。依据：[Jolt GetCurrentPosition 第 174–180 行](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/thirdparty/jolt_physics/Jolt/Physics/Constraints/SliderConstraint.cpp#L174-L180)、[Godot rebuild 第 505–523 行](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/modules/jolt_physics/joints/jolt_slider_joint_3d.cpp#L505-L523)。源码里的 slider motor speed 不取负（[第 129–135 行](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/modules/jolt_physics/joints/jolt_slider_joint_3d.cpp#L129-L135)）；此次没有运行 slider 内建 motor 探针。

## 3. Pin：只保持连接点重合，不锁相对朝向

Godot Pin 使用 Jolt `PointConstraint`，约束两个 anchor 的三维位置重合，不添加角度锁定；相对转动保持自由。该自由度并不意味着偏心 anchor 的约束力不会产生力矩。依据：[官方 PinJoint3D 文档](https://docs.godotengine.org/en/4.7/classes/class_pinjoint3d.html)、[Godot pin 第 47–58 行](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/modules/jolt_physics/joints/jolt_pin_joint_3d.cpp#L47-L58)、[vendored PointConstraint 第 90–121 行](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/thirdparty/jolt_physics/Jolt/Physics/Constraints/PointConstraint.cpp#L90-L121)。不能把 Pin 当作 weld、hinge 或完整平面闭环约束。探针只实测了 COM 处 pin 的 Z 旋转自由度；其余转动自由度的结论来自源码。

## 4. 相邻 body 的 collision exception

`joint_disable_collisions_between_bodies(joint, true)` 在 Jolt 实现中给 **A→B 和 B→A** 都添加 body exception；false 分别移除。对于不通过同一个 joint 连接、但物理模型要求排除的 body pair，可显式调用 `body_add_collision_exception(A,B)` 和反向调用，保持清单明确。Jolt 接触判断检查两侧 exception，任意一侧存在即排除该对；这种排除不会自动扩展到全部祖先/后代。依据：[server 第 1570–1574 行](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/modules/jolt_physics/jolt_physics_server_3d.cpp#L1570-L1574)、[joint 第 206–220 行](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/modules/jolt_physics/joints/jolt_joint_3d.cpp#L206-L220)、[body 第 1320–1321 行](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/modules/jolt_physics/objects/jolt_body_3d.cpp#L1320-L1321)。

应在建模/重建时配置 pair 清单，不在每个 physics tick 重复添加。实现直接 `push_back`/`erase`，没有调用方所有权标记或此处的去重分支；joint flag 与手动 exception 应协调生命周期。依据：[body 第 1018–1031 行](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/modules/jolt_physics/objects/jolt_body_3d.cpp#L1018-L1031)。探针只核 true/false 各一次的 exception 列表变化；没有进行多调用方或重建后清理测试。PhysicsServer3D 的 `body_get_collision_exceptions` 是 C++ 接口，未绑定为此版本 GDScript 方法；本次用 `PhysicsBody3D.get_collision_exceptions()` 查询。

## 5. 自由根的手动关节 torque 必须带等反作用

`body_apply_torque` / `RigidBody3D.apply_torque` 只向指定 body 累积外力矩，**不会自动给另一个 body 补电机反作用**。Jolt 原生角度 motor/constraint 求解则对 body1 减、body2 加角冲量。依据：[Godot body 第 935–944 行](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/modules/jolt_physics/objects/jolt_body_3d.cpp#L935-L944)、[vendored AngleConstraintPart 第 39–54 行](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/thirdparty/jolt_physics/Jolt/Physics/Constraints/ConstraintPart/AngleConstraintPart.h#L39-L54)。

因此，若用手动 torque 表示 A/B 之间的内部执行器，并以本页 q 定义驱动 B，应在同一物理步施加 `tau_B = +tau * axis_world`、`tau_A = -tau_B`。只给 B 加力矩等于向整机注入外力矩；自由基座下不能用静态根试验掩盖该差别。这是上述 API 语义与内部执行器动量守恒的实现推论，不是 Goose 控制律选择。固定环境/静态 A 能吸收反作用，不能证明自由根正确。

## 6. 线性弹簧与压缩力：记录 attachment point

官方 `body_apply_force` 的 `position` 是 **相对 body origin、用 world 轴表达的偏移向量**。不能传 world 绝对点，也不能把局部偏移原样当 world 偏移。若 world attachment 为 `p`，应传 `p - body_world_origin`。`apply_central_force` 仅加 COM 力，刻意不产生转动。依据：[官方 PhysicsServer3D force 文档](https://docs.godotengine.org/en/4.7/classes/class_physicsserver3d.html#class-physicsserver3d-method-body-apply-force)、[Godot body 第 887–906 行](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/modules/jolt_physics/objects/jolt_body_3d.cpp#L887-L906)。

Jolt positioned force 同时累积 COM 力和 `(p - COM) × F` 力矩，依据 [Body.inl 第 127–130 行](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/thirdparty/jolt_physics/Jolt/Physics/Body/Body.inl#L127-L130)。因此两端 attachment 的内部弹簧/压缩力应在各自 attachment 点施加等反向力，按实际几何计算力矩；只有明确等价于 COM 作用或另补相同力矩时，才能用 central force。对移动/旋转 body，每步重新转 attachment 到 world；阻尼若使用端点速度，应包含 `omega × (p - COM)`，不能无条件用两个 COM 线速度代替。后两点是几何/刚体运动学推论，本轮没有检验 Goose 弹簧参数或闭环受力。

## 7. 本机隔离探针与未验证项

探针脚本与原始结果只放 `.scratch`：[probe.gd](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/.scratch/goose_joint_adapter_facts/probe/probe.gd)、[result.json](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/.scratch/goose_joint_adapter_facts/probe/result.json)。运行的是原版上述二进制：

```text
godot --headless --path .scratch/goose_joint_adapter_facts/probe --fixed-fps 120 --quit-after 300
```

结果记录 physics engine `Jolt Physics`；120 Hz，240 回调/2 s，重力 0、碰撞 mask/layer 0、1 kg、对角惯量 `[1,1,1] kg·m²`。这些是人工双体测试条件，不是 Goose 物理参数。

| 测项 | 本次实测 |
|---|---|
| Hinge API lower=-0.2、upper=+0.7，给 B +Z / −Z torque | 终点 q 分别 `+0.20000493`、`−0.70000424 rad`；符合反向 limit 映射 |
| Hinge API motor target +0.5 rad/s，无 limit | B omegaZ=`−0.5 rad/s`，q=`−0.99583383 rad` |
| Slider 同样 lower/upper，给 B ±X force，并同时给 +Z torque | s=`+0.70000172` / `−0.20000458 m`；相对 Z 转角和 omegaZ 为 0 |
| COM 处 Pin，给 B +Z torque | anchor 位移为 0，omegaZ=`1.99166512 rad/s`；允许转动 |
| 自由双体 hinge，±0.25 N·m 等反向 torque | omegaA/B=`−/+0.49791628`；等惯量总角动量 Z=`0` |
| 同一个自由双体，只给 B +0.25 N·m | omegaA=`0`、omegaB=`+0.49791628`；总角动量非零 |
| +Y 1 N，world +X 1 m 的 origin 偏移点 / COM | 前者 omegaZ=`1.99166512`，后者 omegaZ=`0` |
| joint collision disable true / false，各一次 | 两侧 exception 数量分别 `1/1` → `0/0`；本次没有打开碰撞做接触对照 |

初次探针因调用未绑定的 GDScript exception 查询函数而解析失败；Godot 仍返回进程码 0。修正为 node 查询后运行产生完整 result.json，没有脚本错误。结果验收不能只看 Godot 退出码。

**未验证**：旋转/偏心/缩放任意组合的 frame 映射，超过 ±π 的连续角 unwrap，省略 A/B 的 world-node 行为、slider 内建 motor、Pin 全三轴逐项探针、多个 collision exception 所有者/重建生命周期、全身闭环/接触/被动物理稳定性及 Goose 控制响应。源码给出的自由度与 API 符号不是这些项目的通过记录。

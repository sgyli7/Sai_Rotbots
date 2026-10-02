# Goose_V0.1 工程候选 rc2

本页记录 **RC2 历史候选**的设计决策与验收边界，不取代交接包历史。具体尺寸、轴向和硬件型号以该候选[规格](../configs/robot_spec.json)为准；生成物须核其规格哈希。用户已否决 RC2 外观；后续 [MicroDuck Max Pro 基线](microduck_max_pro_baseline.md)提出每腿 6 轴的 18 主动轴新候选，但尚未改写此历史规格。**不能按本页下单全套或直接打印装配。**

## 目标与外形

双足、长颈、橙色扁嘴、白色圆润躯干和宽脚共同构成游戏鹅目标；动作表达包括探头、歪头、回望、停顿与鹅叫。嘴的叼起与拖拽都是首版核心能力。两侧是随外壳曲率形成的手动翼形检修门，表面保持简约，不描写实羽毛，也没有翅膀执行器。视觉比例和动作节奏参考 [goose.game](https://goose.game/)；概念图不提供工程尺寸。当前真实 CAD [外形核查](exterior_review.md)未通过，外观与可落地性仍须在同版模型上同时成立。

当前方案每腿 5 轴、颈头 5 轴、嘴 1 轴，共 **16 个主动轴**。颈两段 135/220 mm，第二段缩短以给地面接近和抬升留下关节行程。使用 12 × XM430-W350-T、2 × XM540-W270-T、2 × XC330-M288-T；两种电压的 TTL 总线分开供电与通信。R2 嘴维持一台 XC330 驱动的平行四杆下喙和固定上喙。电机堵转值的 20% 仅为初筛扭矩，不是连续热额定。

相对交接包的 7R/18 轴研究方案，RC2 暂去掉独立的颈部轴向扭转与头部偏航。颈根偏航承担左右看，中段/头部俯仰承担探头与低头，头滚转保留歪头和侧向叼取；这样减少远端电机重量、颈内线束扭转和检修复杂度。已做预设姿态的地面可达与相机设计视野检查，但尚无连续动作、真实线束和自主目标跟踪验证，**16 轴仍是工程候选，不是已证明 7R 两轴永远多余**。若指定任务要求机身不动而头部独立偏航或颈部改变弯折平面，须带物体/视野/负载证据重新比较，不静默恢复或删除轴。

## 任务边界与已有证据

首版指定物包括 50 g 小块、杆和环；拖拽覆盖布边、空拖鞋、轻篮/箱和带轮小车，初设持续牵引 2 N、停止阈值 4 N。环境是室内平整硬地面。遥控和指定物标记自主共用具名行为；任意物识别与自由探索延后。相机视觉不能读取仿真物体真值；真值只用于评分。

同版模型的 [MuJoCo 4 秒站立](../evidence/stand_ground_rc2.json)、[50 g 接触夹取与释放](../evidence/grasp_50g_rc2.json) 和 [0.3 kg 样块短距牵引](../evidence/drag_short_pull_rc2.json) 单项通过；牵引样块移动约 76 mm，地面切向力中位数约 2.23 N。夹取与拖拽都从预设姿态开始，机身与样件自由，仅靠接触传力；它们没有验证边走边拖或视觉自主接近。[合成图像定位](../evidence/vision_pixels_check.json)也不能等同真实相机任务。负载步行、跨引擎完整任务以及真实硬件未放行。

## 跨仿真约束

现行 `goose_rc2_v5` 明确 10 个腿部动作以具名站姿为中心、每单位 0.30 rad；53 维观测仍用规格中 `home` 作为关节偏差零点，两个参考值不得混用。训练和运行均按 5 ms 扭矩周期使用中立刚体重力前馈，不让策略依赖 MuJoCo 专有的整机偏置力。[v4 200 轮步态失败](../evidence/walk_policy_200iter_v4_rc2.json)后发现旧站姿测试错误地每 1 ms 更新力矩；在真正 5 ms 周期下腿部速度阻尼 0.30 失稳，v5 调整为 0.10。物理模型与几何未变；[v5 200 轮策略](../evidence/walk_policy_200iter_v5_rc2.json)也未通过独立行走验收，不能部署。

[MJCF](../models/full/robot.xml) 与 [中立 SI 刚体数据](../models/full/rigid_transfer.json) 定义同一模型：具名身体/关节、完整质量惯量、局部与世界坐标、碰撞几何、闭环、被动关节、相机、任务点以及分开的正常站立/地面侧叼姿态。策略周期 20 ms，扭矩更新周期 5 ms；控制器输入为编码器、陀螺与重力方向，输出为有时效的 SI 扭矩。Jolt 的质量尺度和坐标变换只在 Godot 适配器内；UnitySim2Sim 与 BevySim2Sim 后续也从中立文件及同一版本控制契约实现，不继承 Jolt 的私有单位。逐项验收条件见 [后端一致性核查](backend_conformance_facts.md)。[MuJoCo v5](../evidence/stand_neutral_policy_mode_v5_rc2.json)与[Godot/Jolt v5](../evidence/godot_jolt_standing_v5_rc2.json)在同一正常站姿与真实 5 ms 扭矩周期下各自由站立 4 秒通过，无额外双脚支撑补偿；Jolt 根部漂移约 2.95 mm、最大倾角约 1.53°、最大关节误差约 1.87°、闭环残差约 0.0015 mm。此前[旧 1 ms MuJoCo 站立记录](../evidence/stand_neutral_continuous_torque_v4_rc2.json)与[修正后的 v4 失败](../evidence/stand_neutral_policy_mode_v4_rc2.json)均保留；[侧叼姿态站立失败](../evidence/godot_jolt_ground_grasp_stance_failure_rc2.json)提示接触叼取任务仍须独立验收。Unity/Bevy 尚未实现，不能写成已通过。

## 制造与采购门槛

[CAD 清单](../cad/exports/cad_manifest.json) 含每件 BREP/STEP/STL、质量、材料及哈希；整机 STEP 是设计交换件。[121 件实体从原位至地面侧叼的三姿态精确布尔核查](../evidence/part_clearance_sampled_rc2.json)与[具名站姿核查](../evidence/part_clearance_standing_rc2.json)均无大于 1 mm³ 的穿插，[电机包络](../evidence/motor_clearance_check.json)和[头罩设计视野](../evidence/camera_clearance_check.json)也通过。抽样通过尚不证明连续全行程、螺钉牙深、线束弯折、打印层向强度或实物热性能。原交接工作簿保留历史；[现行 BOM](../hardware/goose_rc2_bom.xlsx) 已把白/橙/黑 PETG、黑 TPU 和条件性 PAHT-CF 试料列入材料预算，但仍为工作清单，须按 [包装与附件扣重](procurement_packaging_facts.md) 核查并获得人民币含税报价。现已能核到的 ROBOTIS 全球公开价小计为 US$4,631.80（只含电机、接口与候选后支承，未含其他件、税运及中国报价）；它已占用相当多的“几万人民币”心理预算，成本必须再做方案比较。电池、急停、分支保险和 USB 防反灌都要按 [电源核查](power_bus_facts.md) 的未闭合项处理。打印机建议与官方材料条件见 [打印机核查](printer_selection.md)。

工程放行需要：无关键装配干涉的结构源与加工输出、现行 BOM 与接线/装配顺序、具名硬件接口、可加载训练模型、自由接触叼取和拖拽/移动任务、MuJoCo↔Godot/Jolt 一致性及 Sai_Lab 训练入口。用户另设实际打印、装配、扭矩温升和带载行走的实测门槛。焊点优化、装饰分缝和轻量拓扑可后续雕琢；不能把供电安全或关键动作缺口列为装饰性延期。

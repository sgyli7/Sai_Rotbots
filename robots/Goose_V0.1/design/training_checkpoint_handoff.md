# Sai_Lab：460件训练参数检查点

交接版本 `goose_one_piece_head_training_checkpoint_si_v1`，源装配SHA256 `1a05dc55c66f96bee59f8cdb50d2f15942fdcf201e91c8d2e72140ba30be25de`。这是当前一体头壳版，整机名义条件质量 **10.430762603kg**、18主动轴。先交付同版结构和训练入口；完整制造、电气及三四阶段仍未完成，体型和执行器仍可能因未关闭的工程问题修改。后续变更必须新建模型版本和策略目录，不能默默沿用本版策略。

## 开始使用

解压交付ZIP，进入包根目录，Python3.12：

```bash
python -m pip install -r requirements.txt
PYTHONPATH=src python scripts/diagnostics/check_goose_training_checkpoint.py --steps 10 --output artifacts/entry.json
```

先读[实际入口检查](../evidence/training_checkpoint_entry.json)。`stance_smoke_pass=true`才允许使用包内PPO入口；否则先解决记录中的碰撞/动力学问题，入口会拒绝启动。训练输出必须是新目录，不覆盖已有实验：

```bash
python -m pip install -r requirements_train.txt
PYTHONPATH=src python scripts/training/train_goose_checkpoint.py --output artifacts/first_run --iterations 2 --envs 1 --horizon 4 --device cpu
```

本轮零优化器更新、不交付策略。[RSL初始化](../evidence/training_checkpoint_rsl_initialization.json)确认网络65输入／18输出；初始化时的契约随后仅改了验收元数据，全部物理和接口参数保持，见[最终化核对](../evidence/training_checkpoint_validation_finalization.json)。PPO脚本仅是明确的消费入口；此版本没有重新执行PPO。CPU MuJoCo负责物理；`--device cuda`只改变网络设备，并非GPU物理。Sai_Lab的大规模GPU环境需要按契约接入。

## 交付参数和同源资料

| 内容 | 同版文件与约定 |
|---|---|
| 有碰撞MJCF／URDF | [MJCF](../models/training_checkpoint/robot.xml)、[URDF](../models/training_checkpoint/robot.urdf)；完整资源随包，相对链接检查 |
| 中立SI契约 | [contract](../configs/training_checkpoint_contract.json)；右手X前Y左Z上，m/kg/s/rad/Nm，四元数wxyz |
| 质量与惯量 | [19体闭合静力表](../hardware/one_piece_head_service_body_parameters.csv)、[运行时契约](../configs/training_checkpoint_contract.json)；运行时21体嘴部拆分后再分出12个脚垫，总质量守恒，33体 |
| 轴顺序／接口 | [18轴CSV](../configs/training_reference_joints.csv)；65观测、18动作，按名字获取qpos/dof地址，禁止把自由根/被动轴当主动轴 |
| 软脚底 | 每脚6个被动压缩垫，行程1.5mm、典型TPU模型约23kN/m和2Ns/m；不是硬鞋底，也不代表复杂地形已经通过 |
| 时序 | 物理0.1ms、力矩5ms、策略20ms；微小脚垫不能随意改成1ms或人为增重来消除不稳定 |
| 嘴部机构 | 2个被动坐标：qin=qjaw、qcoupler=−qjaw；嘴部实际电机驱动input rotor。URDF mimic需要各后端主动实现；不能按显示关节错接执行器 |
| CAD与外观 | [460件装配quad源](../cad/source/one_piece_head_service_fixture/assembly_scene.json)、[单件头壳STEP](../cad/exports/one_piece_head_service/head_integral_print_shell.step)、[STL](../cad/exports/one_piece_head_service/head_integral_print_shell.stl)；全quad是CAD派生采样，并非艺术细分控制笼 |
| 实际渲染 | [Cream](../images/microduck_color_blocking_one_piece_head_service/cream.png)、[Graphite](../images/microduck_color_blocking_one_piece_head_service/graphite.png)、[Lavender](../images/microduck_color_blocking_one_piece_head_service/lavender.png)、[Sky](../images/microduck_color_blocking_one_piece_head_service/sky.png) |
| 采购与增量 | [执行器表](../hardware/stage_two_actuator_bom.csv)、[基础候选BOM](../hardware/mechanical_candidate_bom.csv)、电源/计算板/相机/机壳固定增量及[单件头壳增量](../hardware/one_piece_head_service_bom.xlsx)；未确认项不算可直接下单 |

运行时显示使用每件最多10000三角面的源派生减面网格，便于仿真；完整quad源与实际精细渲染随包保留。显示LOD与三角碰撞网格属于引擎输入，不改变CAD源quad、质量或完整惯量。质量包含先前线束/电源等设计预留，不把显示几何体积冒充全部实物质量。

原有形状仅在源几何哈希一致时重用CoACD碰撞；新增凹件使用5mm局部表面凸簇，必要时先减到40000三角面。局部退化簇使用最小50μm厚保守包络，逐簇记录；不能把这些近似宣称为1mm精度，更不能合并空心叉架成实心胶囊。模型保留全部460件的碰撞覆盖登记及12个软垫。连续真实CAD净空仍以原生实体检查为准。

## 验证边界与后续顺序

当前一体壳原生实体有效、打印网格闭合；10个有限头部姿态、33个保留核心的有限平移样本没有已检接触。同源嘴尖20N及中部50N两组各63静力筛查通过。核心平移没有包含相机/夹嘴连杆/工具/线束；这些不是完整装配或连续扫掠通过。

实际[闭合姿态尺寸记录](../evidence/training_checkpoint_geometry.json)由完整460件quad源计算。当前入口验证：0.2秒、10个策略步，初始自碰撞候选0、求解器警告0，65/18接口和名义质量核对通过。

本包把实际同版模型加载、完整惯量/轴位/方向核对、65/18接口以及短时物理检查保存在证据中。短时通过只允许初始训练探索，不代表学会站走、转弯、坐下拾取或拖日用品。各腿包含hip yaw/roll/pitch与膝、踝pitch/roll；转向自由度具备，但转向能力仍待动态验证。

尚未关闭的主要工程项：完整安装/工具/线束与翼门固定、真实供应商部分无效CAD接触、USB-CAN-A实际尺寸预留、AK48电压及回馈/看门狗、供电保护/独立急停和实物热/载荷。采购信息由本工程继续核实。请Sai_Lab先接入名义站立和低幅动作，随后加扰动/转向，再展开步行及地面夹拖；后者需要同版任务和碰撞复核。

MuJoCo、Godot/Jolt、Unity、Bevy共同消费相同SI质量、轴序、全惯量、力矩上限、软脚底及嘴部被动约束。URDF不足以表达弹簧/求解器/接触时序的项目由中立契约明确补充。本轮没有宣称跨引擎数值一致性已通过，不能为了Jolt覆写其他后端的契约。

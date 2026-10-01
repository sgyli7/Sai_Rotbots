# 整机机械与物理检查点 — 喙骨架和轴向保持合入

**第三、第四阶段仍未完成；制造、采购、训练硬冻结和最终外观均未放行。** 本页对应314件机械候选。2026-09-30 17:55:02 UTC的三小时时间盒已经超时，后续进展不改变未按时完成的记录。[轴系合入前检查点](mechanical_checkpoint_pre_bill_retention.md)保留292件版本的说明；[更早检查点](mechanical_checkpoint_pre_native_head.md)同样保留。

## 当前同版交付

条件裸机质量 **10.3423457 kg**，**18个主动轴、65维观察、18维动作**。主轴、身体、腿脚轮廓和控制接口没有变；本次加入原生金属喙骨架、上下空心喙壳、轴承压盖、轴向间隔套、后卡簧和前端止挡螺钉，并为其切出真实安装窗口。

| 资料 | 内容和边界 |
|---|---|
| [质量与静力台账](../evidence/body_bay_mechanical_parameters.json) | 闭嘴状态19个主要刚体，逐体质量、重心、完整惯量和设计力矩；条件质量不是实物称重 |
| [中立SI契约](../configs/mechanical_reference_contract.json)、[逐体CSV](../configs/mechanical_reference_bodies.csv)、[关节CSV](../configs/mechanical_reference_joints.csv) | 18个主动轴和2个嘴传动从动坐标；后端共同坐标，不依赖Jolt专有接口 |
| [参考MJCF](../models/mechanical_reference/robot.xml)、[URDF](../models/mechanical_reference/robot.urdf) | 21个刚体，nq=27/nv=26/nu=18；从动曲柄与连杆实际拆分，参考模型不提供完整碰撞 |
| [接触MJCF](../models/mechanical_physics/robot.xml)、[URDF](../models/mechanical_physics/robot.urdf)、[接触契约](../configs/mechanical_physics_contract.json) | 33个移动刚体、10,911个独立凸体；nq=39/nv=38/nu=18，另有12个理想弹性脚垫坐标 |
| [实际装配](../cad/source/mechanical_preview/scene.json)、[Blender源](../cad/source/mechanical_preview/quad_assembly.blend) | 314件，5,076,268个源四边面；运行和STL三角化不改变编辑源；工程实体以BREP/STEP为准 |
| [候选BOM](../hardware/mechanical_candidate_bom.csv)、[紧固件表](../hardware/mechanical_candidate_fasteners.csv)、[清单](../hardware/mechanical_candidate_bom_manifest.json) | 338行候选零件、101组紧固件；记账一致不代表SKU、材料、加工和报价已经采购放行 |
| [当前四色实渲染](microduck_color_blocking_314_parts.md) | 同一314件装配的Cream、Graphite、Lavender、Sky；待用户审美验收，不是制造最终外观 |
| [安装一致性报告](../evidence/mechanical_bill_retention_installation.json) | 30件有效原生增量逐件核对CAD/源/装配/质量/重心/完整惯量；8件旧对应件已替换，没有重复计重 |

旧`images/mechanical_preview`斜视和头部近景、292件四色图保留历史，不作为当前314件外观证据。当前四图全部核对相同场文件、零件源、顶点、quad和位置指纹；只是涂装和近似显示法线变化，涂层质量尚未冻结。

## 质量变更和训练版本

[合入前基线](../evidence/mechanical_bill_retention_baseline.json)保存原292件场文件身份、被替换件及旧逐体参数。当前净增 **62.9315g**；头部内部结构预留 **80g**完整保留，没有用已建件抵扣未建相机、连接和布线。

- `head_roll`闭嘴静力刚体：0.6629173 → 0.6740555kg，增加约1.68%，局部重心移动约1.193mm。
- `beak_hinge`闭嘴静力刚体：0.06717435 → 0.11896770kg，增加约77.10%，局部重心移动约2.104mm。

总质量只增加约0.61%不代表旧逐体训练区间依然有效。Sai_Lab必须使用新的明确模型版本；第一、第二阶段和292件历史模型不得沿用当前验证结论。本版可作为限定装配/坐标/接触检查候选，不能宣称大结构、质量和预算已硬冻结。

## 实际轴向保持结构

[27件原生锁固套件](../cad/exports/jaw_retention/manifest.json)提供BREP、STEP、STL和quad源。8mm输出轴保持76mm长度，轴承位置不变；轴承处为圆轴颈，D扁位仅在骨架及输出臂传矩段。后端采用7.6mm直径、0.9mm宽卡簧槽，前端为M4端面螺钉和止挡垫片。五段11OD/8.1ID间隔套区分轴承内圈与外圈载荷路径，名义端隙0.15mm。

前后外圈压盖各用三颗M3x8螺钉，实际建出攻丝底孔、垫片、螺钉头及5.5mm名义啮合。前盖切出曲柄活动区；后盖和壳体切出间隔套与工具通路。卡簧按任何转角的保守包络检查，不靠指定卡簧姿态获得净空。详细轴承挡肩/倒角、配合公差、垫片选配、螺纹预紧及承载强度仍未放行。

各独立CAD清单中的`installed:false`保留其生成时的候选状态；后续合入事实以[安装报告](../evidence/mechanical_bill_retention_installation.json)为准，不改写原生成记录。[显式替换配置](../configs/mechanical_native_replacements.json)防止旧框架和新框架同时出现。

## 有限验证结果

| 检查 | 当前结果 | 边界 |
|---|---|---|
| [静力](../evidence/body_bay_mechanical_parameters.json) | 63/63指定接触和连续设计力矩工况，含质量扰动、50g等效载荷和±2N | 非冲击/疲劳/实测热额定或步行证明 |
| [参考一致性](../evidence/mechanical_reference_validation.json) | 39个FK工况及逐体质量/重心/全惯量通过 | 非全运动范围干涉证明 |
| [新轴系原生配合](../evidence/jaw_retention_native_fit.json) | 23/23张合点，47件限定集合、937对实体；不相关干涉为零，7处名义螺纹交叠单独量化 | 离散采样，非连续扫掠、完整头部或强度验收 |
| [锁固quad源](../evidence/jaw_retention_quad_gate.json) | 27件、560,034个四边面；闭合、绕序、源身份及原生体积/重心误差通过 | 工程实体细分显示源，非全部制造工艺证明 |
| [Blender身份](../evidence/mechanical_blend_identity.json) | 当前314件、5,076,268个quad与源身份/位置一致 | 非所有零件已可制造 |
| [接触与站立](../evidence/mechanical_physics_rejection.json) | 7/7指定自碰撞姿态；限连续力矩、自由根PD站立1秒，最大倾斜约1.824°，零数值警告/力矩裁剪/垫底碰撞 | 非行走、转向、复杂地面或长期稳定 |
| [低位路径](../evidence/mechanical_ground_reach_path.json) | 82/82全模型几何采样；下蹲70mm后夹持点约[200.0,0,24.2]mm | 非动态坐下、地面拾取或严格连续扫掠 |
| [原碰撞部位CAD复核](../evidence/mechanical_low_reach_native_pair.json) | 原头部支架对两片前机壳，82/82零实体交集 | 仅该零件对，非全机原生检查 |
| [50g保持/受拉](../evidence/mechanical_50g_hold_pull.json) | 预置自由物体保持0.75秒，后段2N拉力；头部坐标系滑移检查通过 | 摩擦假设0.65；非地面拾取、真实垫连接、日用品拖拽或带物行走 |
| [四色版本核对](../evidence/microduck_color_blocking_314_parts_pixel_validation.json) | 四图同场、同源、同相机，279个源网格哈希核对 | 非实物色号、最终制造外观或用户审美通过 |

[移动传动质量误差](../evidence/mechanical_native_linkage_static_bound.json)以七个任务姿态×161个张嘴点核算，整机重心变化上限约0.004563mm、颈部重力修正约0.000323N·m，仍在已有条件余量内。23项机构、质量和运行测试通过；没有扩大PPO训练。

新的喙实体以各自native STL进行凸分解，记录与CAD的体积/重心误差；空心零件保持多个独立凸体，没有合并成堵住安装空隙的包络。接触模型使用MuJoCo3.10.0、0.1ms时间步，脚垫与摩擦仍为理想材料假设；有限成功不消除真实材料和控制误差。

## 历史失败和载荷筛查

本次保留[首次螺钉堆叠失败](../evidence/jaw_retention_first_stack_failure.json)、[扩大套件首次干涉](../evidence/jaw_retention_expanded_first_failure.json)、[切壳断开实体失败](../evidence/jaw_retention_shell_cut_first_failure.json)及[替换映射/后口余料失败](../evidence/jaw_retention_installation_map_failure.json)。修正对应实体、切除真实安装余料并恢复替换映射；没有静默删除小实体、过滤不相关碰撞或把中断结果称为全通过。

[早期喙梁承力初筛](../evidence/native_bill_load_screen.json)仍限于当时喙板薄截面和理想边界：56.25N等效力下上/下板名义应力50.65/75.75MPa，理想挠度0.498/0.317mm；理想连杆销力约406N。新的上喙安装耳局部避让已变化，该旧报告不验证新耳根、D扁位、轴槽、螺纹、轴承座、压盖或夹持垫连接。旧[头部支承](../evidence/head_load_path_fit.json)、[嘴传动](../evidence/beak_native_linkage_fit.json)及独立喙骨架检查保存为历史局部证据，不充当314件完整头部放行。

## 剩余主线与退出条件

新增[24件可更换夹持组件及12件框架紧固候选](grip_cassette_candidate.md)：含外壳的67实体/1,308配对与新增固定紧固件的79实体/870配对均通过23个张合位置；源quad、名义螺纹接触及实际维护槽分别核对。四处螺钉穿壳和原生开孔异常的失败保留。两套增量合入预估净增15.51g、可能344件/10.3578562kg；逐体质量、重心、全惯量与接触参考点变更已列明。因实际材料/强度、完整工具路径及整机接触任务仍未通过，保持独立，没有改变当前314件运行模型或四图；不能用预估数替代已安装版本。

1. **完整实际承力与装配。** 夹持垫与金属骨架/薄壳的连接、相机安装、翼门铰链锁止、壳连接、线束通道和完整紧固件仍未闭合；关键轴、耳根、轴承座、盖和螺纹须有载荷/工艺依据。装饰性微调可延期，真实承力连接不能以仿真刚体粘连代替。
2. **供电与回馈保护。** [供电检查点](../hardware/power_release_checkpoint.md)和[原厂手册适用范围](../hardware/ak_manual_applicability_audit.json)仍有效：选定AK48驱动的持续电压/回馈窗口、6S满电下过冲、电阻/保险/断开与散热布线未放行；供应商问题没有发送。
3. **新版实际硬件控制。** [CAN布局](../hardware/stage_three_can_layout.json)为17个CAN轴加独立TTL头部伺服候选。旧16轴Dynamixel程序不覆盖这版硬件；真实协议档案、急停、超时断线和限流实现及验收未完成。
4. **整机任务与后端。** 当前真实行走、转向、地面拾取、日用品/小车拖拽及指定物自主未验证；Godot、Unity、Bevy均须落实并检查本版传动/弹性脚垫。中立契约和URDF mimic不意味着所有引擎自动实现。
5. **最终制造外观与预算。** 实体/电子版1:1须建立在实际制造装配上；当前四图仅为同版候选配色。完整材料、SKU、工艺和中国报价未冻结，保护件及未完成连接仍可能改变质量或包络。

上述事项仍需实际产物和验证，不能把本检查点或任一有限测试替代第三、第四阶段退出条件。

## 复现

工作分支`codex/goose-stage-three-four`。从仓库根执行以下入口；需要build123d/OCP、NumPy、trimesh、MuJoCo，重建碰撞另需CoACD。当前quad源来自实际场文件，四色渲染入口见[配色文档](microduck_color_blocking_314_parts.md)。

```bash
PYTHONPATH=src python scripts/diagnostics/check_goose_bill_retention_installation.py
PYTHONPATH=src python scripts/diagnostics/check_goose_mechanical_reference.py
PYTHONPATH=src python scripts/diagnostics/check_goose_mechanical_physics.py
PYTHONPATH=src python scripts/diagnostics/check_goose_ground_reach_path.py
PYTHONPATH=src python scripts/diagnostics/check_goose_low_reach_native.py
PYTHONPATH=src python scripts/diagnostics/check_goose_grip_hold_candidate.py
PYTHONPATH=src python -m pytest -q tests/test_goose_native_linkage.py tests/test_goose_stage_one.py tests/test_goose_mass_properties.py
```

重建和原生实体核查入口见同名`scripts/cad`、`scripts/models`、`scripts/diagnostics`脚本。几何、归属、质量或接触改变后，必须重建同版并重新验证；原图、原文档、采购表和关键失败证据继续保留。

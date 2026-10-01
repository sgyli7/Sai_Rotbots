# 整机机械与物理检查点

**当前为344件候选、10.3578562kg条件裸机质量、18主动轴。第三、第四阶段和最终制造外观均未完成，不能宣告训练硬冻结。** 本检查点把24件实际夹持组件和12件上喙/框架紧固件合入同版源、质量/全惯量、MJCF/URDF、碰撞模型和四色图；并揭示真实垫面与旧低位代理点的差别。原三小时时间盒已超时，原截止时间保留，没有重置。

当前源与检查哈希见[机器可读检查点](../evidence/mechanical_integration_checkpoint.json)。[314件合入前检查点](mechanical_checkpoint_pre_grip_installation.md)、[不可变基线](../evidence/mechanical_grip_installation_baseline.json)和Git提交`209d5d89afef58b2ee274c3e0ecb5f5bc3945103`保留完整历史。不能将314件或更早版本的任务、参数和图片混入本版。

后续独立[前端夹取及连续动作](tip_grip_checkpoint.md)候选替换六件、净增1.673g，取得站立到地面夹取、约73.7mm抬升保持、放回和回站的有限功能结果；颈根6次控制指令仍被连续上限截断，未完整放行。它没有回写本页默认装配、质量或四色图，不能混合两版证据。

后续独立[相机安装与任务视野](camera_installation_checkpoint.md)修正旧单板占位，保留当前夹嘴轴承固定头架并生成承力架、开孔面罩和色环，相对被替换件净增约3.762g。现有夹取动作中的样件被上嘴遮挡，指定物自主必须包含观察定位环节。相机候选尚未安装，本页344件模型、参数及四图保持原版本；未将局部空间检查当作完整装配或自主任务通过。

## 同版交付

| 入口 | 当前内容 | 放行边界 |
|---|---|---|
| [参数台账](../evidence/body_bay_mechanical_parameters.json) | 19个闭嘴静力刚体、18轴；257件原生重建件，约3.2855kg | 条件密度/硬件包络及显式预留；非最终称重 |
| [实际装配源](../cad/source/mechanical_preview/scene.json) / [Blender](../cad/source/mechanical_preview/quad_assembly.blend) | 344显示件、5,766,994个源quad | CAD工程表面显示细分；非全部制造连接已闭合 |
| [参考MJCF](../models/mechanical_reference/robot.xml) / [URDF](../models/mechanical_reference/robot.urdf) / [SI契约](../configs/mechanical_reference_contract.json) | 21刚体，包含两个真实移动传动件；逐体质量、重心和完整惯量 | 无碰撞，不能作为行走任务模型 |
| [接触MJCF](../models/mechanical_physics/robot.xml) / [URDF](../models/mechanical_physics/robot.urdf) / [SI契约](../configs/mechanical_physics_contract.json) | 11,232个独立凸体，12被动脚垫，33运动刚体；nq39/nv38/nu18 | 碰撞与材料假设候选；18动作/65观察维持，其他引擎仍须实际适配 |
| [BOM](../hardware/mechanical_candidate_bom.csv) / [紧固件](../hardware/mechanical_candidate_fasteners.csv) / [提取核查](../hardware/mechanical_candidate_bom_manifest.json) | 368行候选BOM、101组台账紧固记录，数量/质量/哈希提取通过 | 部分SKU、工艺、额定和采购价未定，不是可直接下单清单 |
| [四色图](microduck_color_blocking_344_parts.md) | Cream、Graphite、Lavender、Sky，同版实际Blender渲染 | 待用户审美验收；非实物色号或最终1:1制造外观 |

## 增量及参数变更

[36件安装报告](../evidence/mechanical_grip_installation.json)逐件核对BREP/STEP/STL/NPZ、场文件归属、质量、重心及完整惯量，确认六个旧对应件不再出现。净增**15.5105g**，80g头部结构预留完整保留；未用新增零件抵扣尚未完成的相机、线束和壳连接。

- `head_roll`闭嘴静力刚体：0.6740555 → 0.6846111kg，增加1.566%，局部重心移1.047mm。
- `beak_hinge`闭嘴静力刚体：0.1189677 → 0.1239225kg，增加4.165%，局部重心移0.996mm。
- [真实接触参考](../configs/mechanical_grip_reference.json)从原生X240mm移至X220mm；旧点超出新垫最前缘X238.7mm。闭嘴原生平面Z553mm，装配刚性基准抬升3.7mm。

[夹持组件说明](grip_cassette_candidate.md)给出承托板、M2.5沉头紧固、TPU垫和M3固定堆叠。各CAD清单的`installed:false`保留生成时状态，后续合入事实以安装报告为准。名义几何通过不验证TPU卡头插入、撕裂/蠕变、真实摩擦、螺钉预紧、防松、工具路径或强度。

## 有限验证及实际失败

| 检查 | 当前结果 | 证明范围 |
|---|---|---|
| [静力](../evidence/body_bay_mechanical_parameters.json) | 63/63，含质量扰动、50g静力载荷和±2N | 非冲击、疲劳、热额定或步行证明 |
| [参考一致性](../evidence/mechanical_reference_validation.json) | 39个FK工况、21刚体质量/重心/全惯量通过 | 非全行程净空证明 |
| [夹持组件原生配合](../evidence/grip_cassette_native_fit.json) | 67实体/1,308配对，23/23位置，零未决 | 399直接查询和287明确标记的构造/历史上界分别记录；不假称内核修好或连续全机放行 |
| [固定紧固件配合](../evidence/bill_mount_fasteners_native_fit.json) | 79实体/870新增配对，23/23位置 | 名义螺纹单独量化，非预紧与强度验证 |
| [Blender身份](../evidence/mechanical_blend_identity.json) | 344件及全部5,766,994quad匹配源与位置 | 非所有制造装配可用 |
| [接触/站立](../evidence/mechanical_physics_rejection.json) | 7/7指定姿态；自由根限力矩PD站立1秒，最大倾斜约1.897°，零警告、裁剪及脚垫底碰 | 非行走、转向、复杂地面或长期稳定 |
| [现有低位路径](../evidence/mechanical_ground_reach_path.json) | 82/82离散几何采样，真实参考约[194.7,0,43.5]mm | 旧24.2mm代理描述不适用于新垫；尚未拾取地面物体 |
| [原碰撞零件CAD复核](../evidence/mechanical_low_reach_native_pair.json) | 原头部支架对两片前机壳，82/82 | 仅这组零件，不覆盖全部姿态配对 |
| [50g接触保持/受拉](../evidence/mechanical_50g_hold_pull.json) | 初始零物体穿插；真实两垫接触，保持0.75秒、后段2N拉力通过 | 物体预置在张开的嘴内；非地面拾取、日用品拖拽或带物行走 |
| [15mm地面目标筛选](../evidence/mechanical_grip_ground_pose_screen.json) | 36组有限候选完成；15组IK/静力可行，但均有地面或机身碰撞候选，0组通过完整有限筛查 | 静力和可达性不能替代实体空间；[两组原生喙壳/地面复核](../evidence/mechanical_grip_ground_floor_native.json)确认实际交叠；不宣称全局不可达 |
| [四色身份](../evidence/microduck_color_blocking_344_parts_pixel_validation.json) | 同源、同镜头、311个外部网格哈希匹配；旧图保持 | 非用户审美通过或制造放行 |

[传动移动质量界](../evidence/mechanical_native_linkage_static_bound.json)为七姿态×23张合位置，共161点；整机重心移动约0.00456mm、最大名义颈部重力修正约0.000323N·m，仍在已有扰动余量内。[23项机构/质量/运行测试](../evidence/mechanical_grip_installation_tests.json)通过，其中四项直接加载当前机构/接触模型，其余检查历史兼容和通用质量计算；没有追加PPO训练。

## 下一段主线与完整退出条件

1. **实际地面拾取空间和任务。** 先处理真实垫面、喙端、头颈姿态与地面的关系，给出有限结构/动作替代及原生复核。不能把升高物品、固定根或预置物体成功写成地面拾取。转向、行走、日用品/小车拖拽和指定物自主也仍需同版任务证明。
2. **完整承力与装配。** 相机实际包络/安装、翼门铰链锁止、壳连接、线束和完整五金未闭合；关键耳根、轴、轴槽、轴承座、盖和螺纹仍须工艺/载荷依据。旧薄板理想应力筛查不验证新增螺母座或这些局部结构。
3. **电气与硬件控制。** [供电检查点](../hardware/power_release_checkpoint.md)与[手册适用范围](../hardware/ak_manual_applicability_audit.json)保持：AK48连续电压/回馈上限、满电过冲、制动电阻、保护定值和热布线未放行。[当前18轴通信检查点](../hardware/current_hybrid_control_checkpoint.md)新增实际USB串口封包、V3协议、17CAN+独立TTL调度、被动采集和软件故障测试；当前设备的物理档案、独立急停、驱动器自身超时和实际限流仍未确认，供应商问题未发送。
4. **跨引擎和复现。** 中立SI本体保持，优先MuJoCo↔Godot/Jolt；URDF mimic或12被动脚垫数据不表示Godot、Unity、Bevy自动实现。须实际适配和回归，不为了Jolt改变其他引擎的物理契约。
5. **最终制造外观与采购预算。** 四色图仍是候选装配，缺失的壳连接/护罩/布线及涂装质量没有冻结。实体/电子版1:1、可采购SKU和全机预算须完成后再验收。

保留[布尔诊断](../evidence/grip_cassette_boolean_diagnosis.json)、[螺钉穿壳失败](../evidence/bill_mount_fasteners_shell_first_failure.json)和[异常开孔失败](../evidence/grip_cassette_shell_repeat_failure.json)。没有静默删小实体、把超时当零、放松不相关碰撞或替换失败记录。

## 复现

工作分支`codex/goose-stage-three-four`。以下检查使用当前同版文件；重建次序为参数→场文件→参考模型→碰撞分解→接触模型。依赖build123d/OCP、NumPy、trimesh、MuJoCo，碰撞重建另需CoACD。四图入口和源身份见配色文档。

```bash
PYTHONPATH=src python scripts/diagnostics/check_goose_grip_installation.py
PYTHONPATH=src python scripts/diagnostics/check_goose_mechanical_reference.py
PYTHONPATH=src python scripts/diagnostics/check_goose_mechanical_physics.py
PYTHONPATH=src python scripts/diagnostics/check_goose_ground_reach_path.py
PYTHONPATH=src python scripts/diagnostics/check_goose_low_reach_native.py
PYTHONPATH=src python scripts/diagnostics/check_goose_grip_hold_candidate.py
PYTHONPATH=src python scripts/diagnostics/screen_goose_grip_ground_poses.py
PYTHONPATH=src python scripts/diagnostics/check_goose_grip_ground_floor.py
PYTHONPATH=src python -m pytest -q tests/test_goose_native_linkage.py tests/test_goose_stage_one.py tests/test_goose_mass_properties.py
```

旧`check_goose_bill_retention_installation.py`和独立夹持参数预估针对安装前历史版本，不用于当前整机闸门。几何、归属、质量或接触变更后重新生成同版证据；原资料、采购表、旧模型和关键失败继续保留。

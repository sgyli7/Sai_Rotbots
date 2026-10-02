# 可更换夹持组件原生候选

**24件夹持组件与12件固定紧固候选已合入当前344件整机、质量/惯量、运行模型和四色图；制造和训练仍未放行。** 当前条件质量10.3578562kg，入口见[整机检查点](mechanical_integration_checkpoint.md)与[36件实际安装核对](../evidence/mechanical_grip_installation.json)。生成时清单保持原始`installed:false`；安装前状态见[314件检查点](mechanical_checkpoint_pre_grip_installation.md)。

## 解决的连接缺口

旧夹持垫为显示网格，没有完成与新喙骨架的承托/紧固。此候选用3mm上承托板和2mm下承托板，将软垫背面接到金属骨架；承托板长60mm、最大宽24mm，前端收窄，与旧42mm宽软垫代理不同。

每侧四颗M2.5沉头螺钉和四颗螺母。上侧名义M2.5x12，下侧M2.5x10；2mm螺母名义全高啮合，末端分别伸出1.2/1.3mm。金属骨架增加实际平面螺母座，喙壳开出承托板/软垫和安装口，没有把螺钉浮放在斜板面上。

软垫采用明确的85A TPU材料/密度假设，接触层上1.2mm、下1.3mm，每侧四个蘑菇卡头进入金属孔及背面避让。4.4mm卡头通过2.7mm孔需要弹性变形，**装配应变、撕裂、蠕变、摩擦和耐久未验证**；不是已可用的实物卡扣。拆下软垫后才能维护沉头螺钉。闭嘴接触平面仍为原生设计坐标Z=553mm；整机安装时还须应用同一坐标基准变换。

新增[12件固定上喙/框架紧固候选](../cad/exports/bill_mount_fasteners/manifest.json)：四处M3x12螺钉、0.5mm垫片和2.4mm螺母，各有1.1mm名义伸出量，连接已有的4mm框架与4mm固定耳板，不锁死活动下喙。该候选质量6.068g，独立于24件夹持组件，已一起合入当前候选整机。橙色上喙壳的两处连续维护槽覆盖完整螺钉头、垫片及内侧螺母，并延伸至外壁，避免留下0.26mm悬空薄条。工具路径、供应规格、预紧防松和耳根强度仍未放行。

## 文件与验证

- [原生清单](../cad/exports/grip_cassettes/manifest.json)：24件BREP/STEP/STL和闭合quad源，条件套件质量129.956g；清单逐件给出路径、哈希、密度、重心及全惯量。另记录实际减去的空腔和实际增加的金属座BREP，控制体不算实体零件、BOM或质量。
- [quad一致性](../evidence/grip_cassette_quad_gate.json)：24件、3,458,358个四边面；源身份、绕序、闭合及原生体积/重心比较通过。[固定螺钉quad核查](../evidence/bill_mount_fasteners_quad_gate.json)为12件、20,400面。工程交换验证不等于制造和装配放行。
- [机械核心原生核查](../evidence/grip_cassette_core_native_fit.json)：63个原生实体、22个增量件、1,133对限定配对，23/23张合点通过；8处名义螺纹接触单独量化，不计为净空。该范围明确排除四片头/喙壳，不能替代壳体核查。
- [完整集合核查](../evidence/grip_cassette_native_fit.json)：67个原生实体、1,308对限定配对，23/23张合点通过，耗时67.18秒，零未决配对；没有排除四片外壳。399次直接原生公共体积查询与287次明确标注的构造/历史范围继承核查分别记录；8处名义螺纹接触单独量化。
- [固定螺钉集合核查](../evidence/bill_mount_fasteners_native_fit.json)：79实体、870对新增紧固件配对，23/23张合点通过，耗时15.09秒；4处名义螺纹接触单独量化，12处壳体空腔包含核查。结合夹持组件核查覆盖两组增量，但不称为全机或连续干涉证明。
- [安装前参数预估](../evidence/grip_cassette_parameter_delta_pre_install.json)保留314→344的预测与原哈希；后续[实际安装核对](../evidence/mechanical_grip_installation.json)确认净增15.5105g、80g预留不扣减及逐体惯量一致。`head_roll`质量增1.566%、重心移1.047mm，`beak_hinge`质量增4.165%、重心移0.996mm；当前参考、接触模型和四色图使用同版344件。

**夹持参考点已更新。** 新垫最前缘为原生X238.7mm，旧X240mm超出接触面。[当前参考](../configs/mechanical_grip_reference.json)采用内部X220mm；新50g预置物保持/受拉已核查实际两垫接触与初始零穿插，但不证明地面拾取。真实参考在原低位姿态高43.5mm；[36组15mm目标筛查](../evidence/mechanical_grip_ground_pose_screen.json)没有可用组合，不能沿用旧24.2mm代理描述或宣布完整拾取成功。

首次开槽使上喙壳底分为三个实体。[失败记录](../evidence/grip_cassette_shell_first_failure.json)保存实际体积、边界、失败源与输入。当前改为真正的连续后部安装口，不选取最大实体来掩盖分离。下喙窗口同时覆盖整个软垫接触层，防止只切承托板而保留上方屋面材料。[首轮原生检查未完成](../evidence/grip_cassette_first_native_run_incomplete.json)和[首次有界检查](../evidence/grip_cassette_first_fit_incomplete.json)继续保留。

当前构造核查不靠把超时改为零：零件完全处在实际减去的空腔内时，测量原生`零件－空腔`的剩余体积；仅减料修改继承旧配对时，核对原报告的全部源哈希、原零件身份、配对范围和采样角度，并逐一检查新增金属座。继承报告给出的≤0.01mm³上界与直接公共体积分别标注，不虚写为精确零。原生布尔内核仍存在慢查询，不宣称内核已经修好。

另外增加每个负体七个内部见证点的采样拒绝检查，以抓住原生布尔错误添加材料的已见问题；这是采样检查，不是连续几何正确性证明。五项通用CSG测试及源变化/失败姿态拒绝测试覆盖这一边界。

[首次实际框架螺钉/壳体干涉](../evidence/bill_mount_fasteners_shell_first_failure.json)保存四处真实交叠及四处未决螺母配对；[圆形维护口异常](../evidence/grip_cassette_shell_repeat_failure.json)保存原生实体增为两个的失败。诊断还观察到额外实体在原本为空的孔中心包含材料，故没有选择最大实体或发布圆形口版本。当前用真实连续槽口并延伸至外壁完成重建。

[布尔诊断记录](../evidence/grip_cassette_boolean_diagnosis.json)列出最小复现、对照、独立进程与OBB单项实验，以及额外实体/悬空薄条的观察。失败实体的完整字节没有全部保存，记录不假称逐字节复现或全域证明；保留已有构造配方与输入身份。

关键局部强度、实际软垫材料/卡扣、螺钉/螺母供应规格、预紧防松和完整工具路径仍未闭合。已通过的是限定名义几何核查，不是这些工程退出条件。

## 复现

```bash
PYTHONPATH=src python scripts/cad/build_goose_grip_cassettes.py
PYTHONPATH=src python scripts/cad/build_goose_bill_mount_fasteners.py
PYTHONPATH=src python scripts/diagnostics/check_goose_native_increment_meshes.py --manifest robots/Goose_V0.1/cad/exports/grip_cassettes/manifest.json --output robots/Goose_V0.1/evidence/grip_cassette_quad_gate.json
PYTHONPATH=src python scripts/diagnostics/check_goose_grip_cassettes.py --scope mechanical_core --wall-time 90 --pair-timeout 3
PYTHONPATH=src python scripts/diagnostics/check_goose_grip_cassettes.py --scope full --wall-time 120 --pair-timeout 3
PYTHONPATH=src python scripts/diagnostics/check_goose_bill_mount_fasteners.py
PYTHONPATH=src python scripts/diagnostics/check_goose_native_increment_meshes.py --manifest robots/Goose_V0.1/cad/exports/bill_mount_fasteners/manifest.json --output robots/Goose_V0.1/evidence/bill_mount_fasteners_quad_gate.json
PYTHONPATH=src python scripts/diagnostics/check_goose_grip_installation.py
PYTHONPATH=src python -m pytest -q tests/test_native_csg_clearance.py tests/test_goose_native_fit_inheritance.py tests/test_goose_native_interference.py
```

原生布尔调用使用独立Linux fork进程实施单对时间盒，任何超时、进程异常和未测试配对保留为未决；非最优原生包围盒只用于保守初筛，最终已查询配对仍取OCCT实体公共体积。以上不是PPO实验；后续同版整机回归及其证明边界见整机检查点。旧独立参数预估脚本仅针对安装前数据，不能在当前台账上重复当作预测入口。

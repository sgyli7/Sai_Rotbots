# Gorilla G18 肩—上臂完整候选封存：A/B 均拒绝

本轮完成两种整组肩 pitch→roll→yaw→上臂→肘→既有前臂/腕/掌的有限几何候选。所有原111可见甲中立顶点/面保留0 mm；实际同尺度四视仍明显外露、错位，因此没有外观 fit。旧腿足是历史占位，不匹配用户最新下半身图，不推定整机接触、载荷、质量或姿态通过。

入口是 `a/scene.json.gz`、`b/scene.json.gz`、各自 `producer_source.py`、`assembly.brep` / `assembly_si.step`。`physical_interface_load_path_contract.json` 含完整52候选树、精确world axes/ports、184个实际rest transforms。`function_mass_retirement_inventory.json` 列全34退休自制ID、80新增件、6×10完整原驱动成员、条件净料COM/完整I和参考质量；不能按前缀删除OEM功能。

| 结论范围 | A | B |
|---|---:|---:|
| whole source parts | 2576 | 2576 |
| 新原生资源拒绝 | 3 | 4 |
| 新自建条件钢 CAD 质量 kg | 127.494626 | 130.855848 |
| 新原生合法范围对应 CAD 质量 kg | 84.021058 | 65.649408 |
| 被拒绝 native 对应 CAD 规划质量 kg，不能进 fixedknown | 43.473567 | 65.206440 |
| 新增12独立SKF参考质量 kg，另计一次 | 13.8 | 13.8 |
| 中立混合/有限标签 positive pairs | 723 / 36 | 589 / 4 |
| 主承力 CAD 根：pitch/roll/upperarm/forearm（各侧） | 1 / 2 / 2 / 1 | 2 / 3 / 1 / 2 |
| 实际旧甲 fit / service / connection acceptance | 拒绝 | 拒绝 |

B的4个 finite-label pair中3个涉及原生错误源，只能作诊断；唯一两件新源均合法的 keeper×upperarm 实材交为右侧3.0486839305 cm³。不能将4项全部称真实材料交，也不能据数量下降称通过。A合法新料仍有92.3659219082 cm³ elbow parent/child交和多处keepers。CAD实材根与内闭腔表面不同：这里根来自实际OCC分体，不是默认split/fixnormals所得，所有几何根和错误source原样保留。

B保留完整gear/motor/brake/encoder/controller/inputcoupler/cooling case及两ports/connector；原4 G13 fixed支承不退休。主pitch轴归AA3候选XZ(-.13,2.29)，原70 mm错轴明确纠正；roll、yaw、elbow整组rest位姿与下游负载壳同时变更。借用catalogue质量只是未qualified范围，内部races/rotor等刚体划分不已知，不能将whole OEM stock的均匀实体I用为真正SI。

`rigid_pose_report.json` 是恒材料中立+4有界姿态，完整轴树、q和body T均可加载，root shift为0，不每pose重造孔。`complete_service_park_report.json` 每侧3完整功能组、每组9个拆卸样本；已拆件实际停车、不隐藏，B roll9/9、yaw5/9、elbow9/9均失败。初装/可拆轴承杯/紧固释放未认证。PCD、轴承压力中心、真实keeper槽/配合、线程预紧/焊接、持续热/驱动/管线全为红线。

质量口径：A/B自制料是实际CAD净量，原生坏source的料量只能作为未通过规划假设。原34旧件有规划范围106.052/110.964/122.553 kg，但不是合格材料替代credit。包括新件/184保留变换/原G13功能的局部规划范围A429.020/454.587/504.667、B432.381/457.948/508.029 kg，既不是全机数，也不是资源合法已知总量；OEM净质量、混合owner分配/惯量、流体/管线/初装未知不能当0。verified mass credit明确0。A保留变换件的旧COM/I未更新，禁止用；B作刚变换但仍无重新SI资格。

STEP独立单位回读：各自source world SI米；显式×1000到OCC写出，STEP声明METRE，再mm→m回读，实际bounds最大差约9.99e-8 m。各piece独立OCC tag、CAD/native体积库存最大相对弦误差0.07138%，只是身份，不关闭材料/接合/运动资格。

最终receiverB只读delta：一次绑定 `bound_final_receiver_body.json.gz` =7102db0e…；2537-34+80=2583件，184整组成员逐ID更新。新增/移动肩臂×body新几何中立query 0 pair；这是限定局部增量，未跑整个新组合mixed/动作，A/B既有失败仍保。receiver PC270打开bore的partial seat/washer、预紧/重力剪力连接未知不豁免；没有给共同装配放行。

已实际查看B `bare_four_view.png`、`original_armor_four_view.png` 和 `literal_source_sections.png`；前两张为实际三角源同尺度投影、后者为literal plane intersections，不是艺术效果。新关节壳/完整功能在原肩外明显突出，cutout导致load-path分根，不能靠再补小桥或微倒角覆盖。下一宏观应先统一完整串联各固定/输出安装区域及真实下游空间，保宽厚设计体积和不可删除功能，而非再次从gross组件布尔挖断宽壳。本轮不产第三种几何，也不做FE/SIMP。

来源保留：A/B初版producer和source未改；A首静态报告原bytes `first_static_gate_report_before_full_pass.json` 与旧checker `check_codesign_before_fixed_body_fallback.py` 保留，fixed-body FK fallback后结果另留当前文件。inventory曾在端口axis整数归一处失败，原producer `write_inventory_before_axis_dtype_fix.py` 及A/B已写出的inventory-before bytes原样保留；仅修分析脚本float dtype重跑，不修改几何。`report.json`逐项producer hash↔真实路径，`manifest.json`冻结当前全部输出身份。

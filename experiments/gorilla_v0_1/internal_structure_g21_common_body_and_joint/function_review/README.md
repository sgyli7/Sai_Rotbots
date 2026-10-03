# G21 独立完整功能与来源范围审查

读取两份3003件实际body、两份110件三轴native、接口/源库存合同，逐exact row/member核查。结果在 `functional_scope_review.json`；422条逐项证据在 `422_source_member_partition.json`。未修改旧源、几何、质量合同或碰撞规则，没有FE/GPU/Git。

**422不是422个缺失零件。** A/B均422条的成员全部仍present，和当前能源退休ID的交集为0。720能源确实替换旧480及HV/LV共用功能，但它没有减少这422条。三轴native同body的exact ID交集为0；body的6个新关节保护框是空间候选，不能称实际肩已装入。

| 旧422来源范围 | rows | 质量量/范围未知 | 范围已知、COM/完整I未qualified | 当前处理 |
|---|---:|---:|---:|---|
| F1旧腿缸/保持/复合脚brace/guard | 314 | 26 | 288 | 全源明确旧下肢仅历史占位。隔离出新body共同布局，不要求沿旧16腿缸/轴位补齐；新腿工程须重新完整分配 |
| F1旧腰pitch双缸/保持 | 34 | 4 | 30 | 当前仍保留历史函数。不能让不存在tree的barrel/rod owner冒充已接新腰；整组替换接口待定 |
| G13旧肩有限结构及OEM功能 | 58 | 0 | 58 | 三轴native未integrate，因此是待替换历史context，不是已删除/已物理替换 |
| G18旧roll/yaw外轴承 | 8 | 0 | 8 | 新三轴有相应轴族功能提案；具体member退休和真实支承split须在共同集成后声明 |
| G18 elbow外轴承 | 4 | 0 | 4 | 三轴不含肘。仍是当前上肢需要的内/外圈split与真实载荷接口 |
| 蓝前臂甲＋gold marker | 4 | 0 | 4 | native owner left/right_forearm不在当前树。marker明确attached_surface_part指wrap；只需实际外壳挂接/body归属，不缺一个新驱动总成 |
| 合计 | 422 | 30 | 392 | dynamic owner/split均旧源未闭，不作为一个无限扩散的“全部物理未知”数字 |

分类使用F1实际 `motion_interface_id`、`physical_assembly_id` 与接口的base/output、旧source family、native attached_surface和当前tree。只作函数来源隔离，**没有**把barrel owner按名称改成base body，也没有把某bearing gross的整质量分配给输入/输出。原四缺缸造成保持源 `finite_cylinder_mount_owner_present=false`；这证明旧方案不完整，不冻结新腿必须采用同四个位置。

例：`f1_left_hip_rod_material` 的native body是left_hip_rod_link，但另有mass_owner_body=left_thigh及motion_interface_id=left_hip；F1接口声明base left_hip_roll_carrier/output left_thigh。这可以关联历史负载功能，不能证明同体刚性。`f1_left_fold_holding__lhdv33_21_core_reference` 明确无finite cylinder mount owner。`g13_left_CSG65_complete_reference` 的mixed_OEM_input_output_unknown不因新目录2A或owner重命名得到split。`left_forearm_gold_marker` 直接附着 `left_blue_forearm_wrap`，而wrap仍未接新proximal/distal forearm树。

新body预算可继续：cage有限单件114.2395kg；能源A/B上界103.7092/104.1098kg，各720颗count已知而实际cell lower/nominal mass未知(max70g为上界)。这些是当前真实来源的条件库存，不是整机净重；还要分别保留新增25个custom function envelope的质量范围与热/电资格，6个joint保护框则明确nonadditive未知。旧314腿不会阻止新body节点/thermal/pack共同几何，但会阻止全身净M/COM/I及步行能力放行。

三轴native A/B各65个finite-flag件、45个protected/reference件。有限候选已有连续core receiver、两级transfer shell、三套output carrier、stepped input shaft、rotor holder、TIM及48个CS安装bolt；它们不能因几何生成就称装配成功。OEM CS/FS/WG9件、stator/rotor6件和12bearing保持完整参照；三套brake、feedback、driver、water ports/hose、power loop各只有完整功能保护占位，真实保持力/热/气隙/细接头/服务路径仍未完成。A条件组件库存177.704–193.124kg，B95.124–110.544kg，包含自身receiver，且仅实际**左**三轴；不能镜像乘2再加body cage，而不拆共享core函数。output螺栓/keys/keeper/brackets/threads、水fill等额外项仍null＋非零声明。

新接口合同和旧body tree不一致。B pitch新pivot[-.04,.515,2.405]，旧[-.13,.56,2.29]；新yaw为CSG50/ratio80，旧G19 load探针较小CSG40/ratio100。A/B当前body都选B保护合同，旧tree和肩部native却未重挂，必须在实际新下游FK与质量分配后重算负载；不得把G19八轴重力数直接转作新B额定。初始register的output中心还被actual_installation_delta修订，审查绑定最终interfaces/scene，不复用早期中心数。

body cage源码有200×80/5mm闭口rails、两端横梁、肩节点plate、腰实体桥和X轴环形法兰；不是空的细杆框。腰环centre[.238,0,1.91]与旧torso roll轴line只有几何同轴候选；仍缺实际OEM输出端面/PCD、固定与moving材料分离、螺接反力/预载和真实支承图。肩合同X=.115也不是连接证据：节点plate源码X=.118±.006m，合同平面位于其有限厚度内，需定义真实配合面/空间/紧固，而不是只接同坐标名称。新joint receiver在X=.111实际材料截面有数值，无法代替这些端面连接函数。

优先下一接口工作：①明确body/cage共享receiver与左右三轴完整exact退休/保留成员及真实bolted ports；②将新pivot/轴/gear ratio带到完整肘腕手FK，分开input rotor、bearing圈、brake fixed/moving与静态自重owner；③新腰固定→输出→cage端面的有限接合和反力图；④将brake/driver/encoder/water/线束protected预算落实为完整功能候选。采购缺型可为黄，未约束压力/母线/保持/热/支承为红。历史314腿、已知质量未知COM、input/output拆分以及真正无量的30条须分别记账；不会让“422”阻塞可复核的body条件设计。

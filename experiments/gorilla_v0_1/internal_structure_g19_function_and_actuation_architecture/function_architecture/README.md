# G19 完整功能分配与两路线比较

只读受控G18 B源 `9873e9db2a6a5c20d9466216577c69a6c7afcab9c2db4ce22b88b4181c40e694`。2583实际source IDs分到229可审查源包和14任务族，2247质量行、45非加性service/fluid记录按原成员一次对账，无漏ID或退休动作；合计质量/COM/惯量依然null。表的功能标签由源ID、类别和既有完整驱动成员表建立，属于待审功能分配，不是制造BOM、刚体资格或稳定ABI。AABB只给源stock边界，不证明可用腔。

**先解完整功能，而不是第三次修旧壳。** 需求是双足、双手真实操作和自主复杂任务/Bevy原生物理；当前源、研究方案与用户要求分栏。G18实际每手8个旧compact-drive stock；每手5远置驱动是已研究的候选，用户没有冻结驱动数量。三轴腕功能保留。8→5或其他欠驱动/差动方案，须先证明对掌、抓放、工具控制自由度、真实力传递、反馈/保持、跨腕腱路和完整安装替代，才可退休旧ID。不能按数量比例减质量。新下半身尚未工程重建，旧14主缸native/4缺缸/额外brace与18阀数量都不是下一整机硬合同。

| 真正要一起分配的范围 | G18源条件质量口径 | 本轮处理 |
|---|---|---|
| 18保持＋18电控主阀库存 | 184.623/213.059/246.008kg，完整自有安装参照 | 36套逐ID、owner、功能和共享条件；不继承数量必需、不直接减阀数/guard |
| 六套肩roll/yaw/elbow完整驱动 | 76.569/84.901/101.302kg | 60gear/motor/brake/feedback/controller/cooling/ports/connector成员保持；不把裸gear或motor评级当联合关节 |
| 两肩pitch参考/支承/输出遗留＋新载体 | 多个真实source包；坏新料和mixed moving owner仍未知 | 集成轴承/外支承是否重复必须按六维载荷、pressure-centre和接口证明，不自动删12SKF或原四固定支承 |
| 电芯、四pack辅助和全局HV/LV | 480×70g仅33.6kg上界；nominal未知 | source包不零计，不替代持续能量/SOC/热与新路由证明 |

## 阀组：共享功能的边界

`valve_function_allocation.json`列全18保持和18方向阀现有成员，每项有真实source owner与所需证据。共用供压、回油、过滤/传感、控制通信或安装manifold可以比较；独立反向计量、近缸保持、pilot释放/回压、补油、热膨胀与故障隔离不能因共泵就消失。保持模块中的模板P/T别名实际代表F1/F2工作线，不是永久tank端；方向阀spool中位泄漏不能替代缸侧保持。

旧13hyd-DOF/18主缸只是一种布局。两个缸驱动一个机械DOF时，一套主阀是否足够，要由新几何的length Jacobian、各腔cap/annulus流量、正负负载、力分配、同步/feedback、pilot和故障行为共同证明；不同DOF要同时异压/异速运动时，单spool共享并不自然成立。局部守压还要涵盖爆管、供压丢失、阀卡滞/泄漏与安全停止需求，目录“closed/zero-leak”不构成机器人安全认证。主阀和保持core数量最后跟新真实执行器拓扑走，不锁中央柜、不把每个完整模板当不可减安装下限，也不给任意减重百分比。

已有厂家参照支持宏观边界：LHDV33-21 bare twin3.5kg、setting420bar与family load350bar分别；preset≥1.2×实际最大load、return≤10bar；D/E25/16Lmin有压降/调谐条件。Parker D1FB C/OBE complete core2.9kg、222×46×125mm，P/A/B350bar而T210bar，18–30V/max2A、20Lmin参照为每metering-edge5bar。F1完整安装模板约holding5.350–6.704kg、directional4.907–6.963kg，是列出的安装设计范围，不是不可减下限或制造上限。原E2a五姿态max4.069/12.208Lmin@.1/.3rad/s仅历史工作点，不迁移到新下腿或G19。实际load不是204bar供压，持续热、震荡、密封、pressureproof与loss-power行为仍红。

## 电源：先定义重叠，而非删柜减重

四个present ID都在原账中各计一次：`ds_hv_distribution`与`g16_HV_contactors_fuse_precharge_disconnect_current`（mid3.5+4kg），`ds_low_voltage_converter`与`g16_LV_converter`（mid1.3+1.2kg）。这是功能边界重叠候选，不是重复ID/ghost；不能直接删除。

可比较一套明确main HV PDU＋每pack局部BMS/fuse，与main＋选择性branch保护/有证冗余两路。须交预充/DC-link、主接触器、隔离监测、电流/故障清除、回馈/残能、pack与branch职责。现g16柜未证明覆盖ds的isolation/DC-link。LV可比较一套完整多rail转换系统，或critical autonomy/control与pump/fan/valve auxiliary分区；24V名称不覆盖12V EWP80与实际compute/encoder rails。冗余需独立feed、backfeed隔离、故障选择性及维持安全停止的时长/能量，两个盒子不自动证明可用性。

`hv_lv_function_reconciliation.json`逐项列源职能与这两种分配的证据门。旧四ID均保留，只有新完整source、ports/rails/连接、热/故障与操作域已证明覆盖，才精确退休并计一次新库存。无需先冻结母线，不均分转子/轴承圈，也不借少算未知owner获得较轻方案。

## 两个整组路线，先选再落实

`architecture_candidate_comparison.json`比较：

1. **直接串联的一体承载关节/壳。** 宽厚反力墙、输出支承、gear/motor/brake/feedback/drive/cooling与服务共同设计，保OEM真实A输出/B固定/WG输入及完整stock；自造框/支承可重分配，不把旧粗墙永久锁定或裁掉OEM。
2. **近端集中驱动＋真实远置传动。** 近端放完整驱动/控制/热，局部支承、输出载荷和必要holding仍保；shaft/belt/tendon/液路等路线需先选并有有限力/速/刚度/摩擦/热/运动跨越和断链行为范围，不能一根示意线或动画替代。增大的躯干热、服务、线路/机构质量也计入。

两路用相同任务和reach、25kg每手条件probe与50kg敏感性比较（不是用户payload评级）；同source owner/6D载荷/速度/温度/周期/母线/回馈/油水与rotor air、能量/SOC和实际四视/服务空间。gear Tr/Tav/repeated/peak与motor Tc/Ts不能跨工作点拼成持续能力。普通35°C环境radiator不会使源20°C安装面额定自动成立。未知自造模块先保红，可信机械/热范围闭合后的采购缺口才黄。若两案仍要匿名缩OEM、断主载荷路径或无证删除功能，回架构而非第三局部patch；拓扑优化等真实载荷/接口/空域明确后再用。

## 文件与复现

- `source_id_owner_task_registry.json.gz`：全部真实ID、source owner、质量行scope、任务/源包、reference/material/fluid及未映射状态。行质量是原完整组的范围，不能复制给每个member。
- `function_buckets.json`、`macro_function_families.json`：229源包→14任务族层级与精确成员、共享/退休证据；数值子集非整机。
- `source_reconciliation.json`：2583/2247/45一次对账，退休清单空。
- `existing_primary_reference_conditions.json`：只读取旧一手记录，保URL/版本/条件/未知；不联网采购。旧CSG50/65轴向B+J误读不继承，G18当前几何另以源绑定。

复现两入口：`.venv/bin/python .scratch/gorilla_internal_g19_function_architecture/build_function_allocation.py`，然后同目录 `write_architecture_options.py`。二者仅读受控源/既有研究，输出仅本目录。此分支不给新geometry、FE/GPU或整机/ABI采用；根负责最后路线和物理取舍。

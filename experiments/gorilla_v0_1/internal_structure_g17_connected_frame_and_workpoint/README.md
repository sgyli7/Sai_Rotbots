# Gorilla G17：连续宽厚主架与完整工作点

本轮形成了连续自有主架、完整肩三轴候选和同任务的冷却/能量核算。**完整安装、承力、稳定SI与审美仍未通过；两宏观候选均不采用。** 壮硕轮廓提供真实三维材料分配体积，不能以细杆、装饰镂空或文件有效性代替骨架。后续拓扑优化须保留真实接口、全部器件和功能空域，在同载荷/功能范围下比较完整结构的质量、刚度与强度。

| 实际进展 | 同版证据 | 对整机的限制 |
|---|---|---|
| 主架与两肩锚实际连续 | [A/B布局报告](body_layout/README.md)；原自造锚被新净材料包含，CAD合法1实体，native1材料根，净质量95.705637kg（ρ7850假设） | 不额外再计两锚30kg；不是减重、焊接/疲劳、支承或吨级资格。两锚仍各侵入CSG65完整参考法兰84.009315cm³，OEM真实安装/内部材料未闭合 |
| 完整功能真实摆位 | B2530件，480芯、18方向阀及保持/控制、完整S1五热包/六风机、两完整低温150泵均保留 | B24处包内材料交：壳接管孔、冷板接管净料连接、安装螺栓孔各8；包3与泵组完整安装/护罩参考交7.6235cm³。当前泵前露188mm、包前露47mm及后散热63mm是实际可见面采样下界，不能推论AA3全局不可容纳 |
| 肩pitch→roll→yaw宽厚承力壳 | [完整串联候选与源身份](serial_shoulder/README.md)；B54新增网格资源合法，逐体CAD/完整惯量和新轴FK均可复查 | 自制钢CAD140.389753kg/native140.343604kg为曲线离散差；8个参考轴承质量另9.2kg，不能由密度填实推OEM惯量。完整局部功能范围319.250–340.723kg、旧carrier减重credit0；原上臂接口、原甲和拆卸均拒绝 |
| 合回整机的独立拒绝诊断 | [root完整静态组合](serial_shoulder/bound_root_independent_serial_and_joint.json)：按22退休ID、28移动驱动和54新增件组合2562件，保111原甲及完整系统组 | 新/动件×全部present件297混合正体积对，明确有限材料22对；含roll→yaw壳×上臂各61.397cm³、yaw输出×上臂75.083cm³及螺栓/挡圈。计算域和外部检修空域排除，OEM参考和原甲分别分类，无owner豁免。未测unchanged×unchanged、全身动作或连续接触 |
| 联合压力/热/储能 | [最终v3工作点](thermal_workpoint/README.md)、[精确算式源](thermal_workpoint/joint_workpoint_v3.json) | 单150在59L/min压头不足；双150冷态曲线、NPSHr与第二级连续壳压未知。共享转子风路尚未真实建立；35°C环境/200V峰值入口51.43–53.33°C超188公开50°C条件。480芯保10%储能余量的任务时间预算25.90–26.87min，30min未通过 |

原甲保留仅证明来源，实际[肩部原甲四视](serial_shoulder/b/original_armor_context_four_view.png)清楚显示宽桥穿出，包装拒绝。当前[全身四视](body_layout/b/native_whole_four_view.png)、[躯干剖面](body_layout/b/actual_sections.png)、[肩部实际剖面](serial_shoulder/b/literal_native_sections.png)均为实际同源几何诊断。外部腿脚设计仍由用户指定的「Gorilla 设计」推进，本轮未并行改稿。冷板断面图只是参数图，不是新CAD或效果图。

源身份：主躯A `ce5ad4d0…`、B `52eb6bb5…`；肩A `7b0a11c3…`、B `e15b691b…`；热v3 `c43cf234…`。完整SHA、逐版producer、CAD/STEP、实际图和失败保存在[快照清单](snapshot_manifest.json)。142项主架身份/积分与273项串联FK/公式复核只覆盖所列范围；不能以检查数量宣布物理通过。原native网格、解析CAD和完整OEM参考范围分别保留，没有静默修源。

历史缺口明确保留：肩A首分析producer原字节缺失；root在最终补明确未知/范围之前生成的初步报告字节未保存，原producer可按已有SHA恢复，初步manifest与缺口记录在`root_review/before_final_scope_audit/`。当前最终报告是独立重算，未冒称历史报告原件。首版范围分类与各次撤回的热假设仍保留，均不增加几何改善轮次。

精选168原文件映射、190来源/输出身份核对；相同字节复用已有受控副本。下载PDF/网页原文、日志和缓存排除，来源收据/参数/哈希保留。CAD/大JSON无损gzip、脚本`.py.txt`均注明编码。恢复到独立空目录：

```bash
python experiments/gorilla_v0_1/internal_structure_g17_connected_frame_and_workpoint/restore_snapshot.py.txt --destination /absolute/empty/destination
```

这只恢复精选原字节，不承诺缺失的历史源、下载原文、完整生成链或物理结果重现。默认模型、catalog、ABI、策略与GPU均未改变。

下一G18按整组收束：肩座—三轴—上臂的完整轴位/材料/安装共同重建；真实模块布局和自有安装孔/冷板连接；真实风液路与运行电压/任务预算比较。每项最多两宏观候选，保留宽厚三维域，先关闭装配与同工作点能力障碍，再对同源负载做骨架优化。可见包装变化需实际最小同源四视与用户审美判断。当前唯一状态见[当前决定](../../../robots/gorilla_v0_1/design/current_decisions.md)，后续稳定SI与复杂Bevy目标继续。

# G22 实际共同装配与下一设计入口

本轮把真实双肩三轴总成装入共同身体源，建立主架安装候选和导体／绝缘路由原型。**共同安装仍失败，首检查点、整机物理与审美未放行。** 新下半身仍在修订，不冻结尺寸或轴位。

| 成果 | 证据与范围 |
|---|---|
| 实际双肩与身体组合 | [共同源](root_assembly/scene.json.gz)、[组成裁决](root_assembly/integration_decision.md)、[独立复核](composition_review/report.md)；几何接续成立，真实输出转接和腰输出仍缺 |
| 主架、双接收座、紧固候选 | [原生／CAD与报告](core_connection/README.md)；固定连接存在材料交叠，组件质量不等于净装配质量 |
| 一端子、两感知线路原型 | [真实路由与检查](typed_routes/README.md)；自身导体和介质有限检查成立，完整19电位网络、电气与热资格未闭 |
| 共同空间检查 | [安装检查](common_installation_review/README.md)、[线路安装](route_installation_review/README.md)；主架与换热器／泵冲突，线路穿进气管；未知旧网格查询保持未知 |
| 同源拆壳与运动学 | [实际四视图](root_assembly/actual_common_neutral_cutaway_four_view.png)、[载荷与镜像范围](root_assembly/kinematics_payload_and_mirror_parameters.json)；仅几何FK与手点载荷公式检查，不是抓握、自由根或驱动能力 |

共同源 SHA `3190ec7d03019ed2d74a5f812b85a15f93d7f03104f98235e5107986e7f1a50b`。图像、源、生产器与报告分别绑定身份。初版右臂翻转错误及纠正均保留；64个右侧件携带旧左侧CAD质量元数据，当前不用于右侧质量惯量。整机质量、COM、完整惯量和稳定SI仍未知。

下一G23共同设计：完整肩传动重新朝向并建立真实宽闭口转接；完整180芯模块落实19网络和冷板／BMS／维护；比较一体闭口主架与真实分体节点，并与热系统共同安排。最多两种宏观候选，局部失败后回整机取舍；原稿审美约束和复杂Bevy终点保留。

保存身份见 [snapshot_manifest.json](snapshot_manifest.json)。137个所选原文件已在隔离目录按哈希恢复，63个JSON解析、41个生产器AST解析；一份原始语法错误版本按失败记录保留，见[恢复检查](restoration_validation.json)。这只验证保存与有限数据结构，不声称全生产器重放或物理通过。公开出版物、下载和运行缓存排除；复用的旧受控依赖须一并保留。

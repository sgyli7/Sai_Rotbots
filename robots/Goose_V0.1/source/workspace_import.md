# Goose_V0.1 本地导入与上下文恢复

日期：2026-09-28。范围：导入交接资料、恢复设计上下文、核对文件和本地引用。

## 实际落盘位置

- 原始附件：[goose_v0_1_workspace_handoff.zip](../../Goose/goose_v0_1_workspace_handoff.zip)，保留原位置和原字节。
- 唯一机器人导航：[README](../README.md)。保留包内 `robots/Goose_V0.1/` 布局及历史文件名，版本名沿用交接资料；本次未登记可运行机器人。该导航后来随 RC2 工程工作更新；[交接时的机器人 README](robot_readme_handoff.md)另存供追溯，原字节仍在附件 ZIP 中。
- 交接包根 README：[workspace_handoff_readme.md](workspace_handoff_readme.md)。为保留仓库根 README，将其归档到此处，仅调整两处导航链接。
- 附带复算脚本：[goose_beak_r2_kinematics.py](../../../scripts/diagnostics/goose_beak_r2_kinematics.py)。
- 文件映射、哈希及本次检查结果：[workspace_import_check.json](../evidence/workspace_import_check.json)。

包内关于“尚未写入用户电脑”的表述记录的是打包时状态；本记录确认资料已导入当前 Sai_Rotbots 工作区。
以下“导入时”数字是 2026-09-28 初次导入快照，不代表后续 RC2 工程文件没有变化。交接文档、历史记录与表格仍保留；机器人 README 后来更新为现行导航，其交接时全文已另存。

## 已恢复的设计基线

依据 [conversation_handoff.md](../design/conversation_handoff.md)、
[kinematic_review.md](../design/kinematic_review.md)、[beak_r2.md](../design/beak_r2.md)、
[walker_structure.md](../design/walker_structure.md) 和 [当前工作簿](../hardware/walker_r2_bom.xlsx)：

- 已选 B 双足步行鹅，白色躯干、长颈、橙嘴、机械双腿与宽脚；A/C 轮式方案留作历史。
- 当前嘴部 R2 为固定上喙、平行四边形下喙、单 XL330 与约 2:1 传动候选，夹持面位于嘴内；旧 XC330 直驱铰接嘴单独归档。
- 理想几何输入为摆杆 25 mm、固定与活动支点间距 14 mm、参考摆角 ±40°；参考行程约 32.139 mm、中途前移约 5.849 mm，30 mm 净开口仍是装配标定目标。
- 双腿 10、颈头 7、嘴部 1，共 18 个候选主动轴；关节布局、器件分配与负载尚未冻结。首阶段为 50 g 指定物试验，100 g 留待后续。
- 不恢复轮式方案、Cargo、额外手臂或嘴下外挂夹爪；旧图中的高度、质量、载荷与续航数值没有成为工程规格。
- 工程状态仍为设计候选和理想运动学核对，尚无制造 CAD、全行程三维装配验证或实机验收。后续详细迭代从头嘴真实零件包络开始。

阅读顺序：交接记录 → 本次机构复核 → 嘴部 R2 与采购工作簿 → 整机背景。
[离线图片库](../design/concepts/index.html) 和 [资产索引](asset_index.md) 同时保留当前图与历史资料。

## 完整性与本地引用

交接包 59 个文件全部导入：17 份 Markdown、23 张图片、1 份 HTML 图片库、
3 份 JSON、6 份 CSV、4 个 Excel 工作簿、4 个历史原始 ZIP 和 1 份复算脚本。
其中 58 个文件字节不变，另 1 个为上述归档后修复导航链接的交接包根 README。
包内资产清单的 54 条记录全部通过 SHA-256 和大小核对。

检查范围包括本次导入 Markdown/HTML 与仓库根 README 的本地链接和图片引用，
图片解码、Excel ZIP/XML 完整性、工作表列表、CSV 列数以及历史原始 ZIP 的完整性。
本次共核对 216 处本地链接和图片引用，缺失目标为 0；23 张图片全部通过解码检查。
Excel 中没有实际超链接关系；当前工作簿保留 9 个工作表及原公式。
复算脚本使用原默认参数运行，输出与包内 JSON 记录一致，仅复现已有理想运动学结果。
外部网址、报价、库存及器件规格本轮不重新核验，继续按资料中的历史来源理解。

采购来源列有 20 处旧导出路径文字，分布在当前/历史采购 CSV 和当前/历史 R2 工作簿中；
它们是来源说明，不是可点击的本地超链接。本次保留原表和原公式，用以下映射接续：

| 原来源文字 | 当前文档 | 原文归档 |
| --- | --- | --- |
| `docs/Goose_Beak_R2.md §4.2` | [嘴部 R2，第 4.2 节](../design/beak_r2.md) | [原 R2 文档](../design/history/beak_parallel_r2/goose_v0.1_walker_beak_r2_docs_goose_beak_r2.md) |
| `docs/Goose_Beak_R2.md §6` | [嘴部 R2，第 6 节](../design/beak_r2.md) | [原 R2 文档](../design/history/beak_parallel_r2/goose_v0.1_walker_beak_r2_docs_goose_beak_r2.md) |
| `docs/Goose_Beak_R2.md §8` | [嘴部 R2，第 8 节](../design/beak_r2.md) | [原 R2 文档](../design/history/beak_parallel_r2/goose_v0.1_walker_beak_r2_docs_goose_beak_r2.md) |

可从源包对应行或单元格追溯：CSV 物料 B03/B05/B07/B09/B12；
Excel 的“嘴部R2采购”页 K9/K11/K13/K15/K18。工作簿中的仓库根相对 README 提示，
以及相对于 `hardware/` 的机构复核和用户原图路径，也已确认文件存在。

本次未修改机器人登记、打包清单、模型、控制或训练参数；未启动制造、采购或 GitHub 提交。

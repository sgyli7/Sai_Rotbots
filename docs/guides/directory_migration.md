# 目录迁移记录

迁移日期：2026-09-27。迁移前提交：`8a36c439ed1c1fe83e8f768ed42ff85b824181d4`。

本次按机器人归档资料、共享公共能力，共移动 334 个文件。
机器人 ID、默认 001、`sai_agent` 导入、`sai-agent` 命令与策略选择名称保留。
规则正文见[工程规范](../../sai_robots_engineering_rules.md)。

## 新旧路径

| 原目录 | 新目录 |
|---|---|
| `models` | `robots/Sai_Agent_001/models` |
| `policies` | `shared/policies` |
| `configs` | `shared/configs` |
| `experiments/stair_profiles` | `experiments/Sai_Agent_001/stair_profiles` |

逐个文件的例外映射见 [directory_migration.json](directory_migration.json)。
定位历史路径时，先查 `file_moves` 的完整匹配，再替换 `directory_moves` 的最长目录前缀。
旧提交、版本固定的外部接入仍使用其原布局；新版本调用者应使用 `model_root(robot_id)`
定位模型，不再拼接根目录 `models/`。

- 001 专属文档归入其 `design/`，真实图像归入其 `images/`，概念图归入 `design/concepts/`。
- 002 变更记录归入 `design/`，BREP 输入归入 `cad/source/`，STEP/STL 和导出报告归入 `cad/exports/`。
- 历史运行、机器人与引擎结果归入 001 的 `evidence/`；安装、CI 与发布证据归入 `docs/releases/evidence/`；共用后端/性能检查归入 `docs/validation/evidence/`。
- 命令脚本按模型、CAD、训练、评估、诊断用途归类；现有诊断回放与测试样本保持原名称。
- 新训练运行默认输出 `artifacts/<robot_id>/<run_id>/`，历史台账里的旧输出地址不改写。

交付 ONNX 对应的 `flat-v1.pt` 训练检查点归入 `experiments/Sai_Agent_001/flat_v1/`，
作为精选复现输入保留，运行 wheel 不携带训练检查点。

## 历史记录与资产

模型、网格、策略、CAD、建模输入、历史验证 JSON 与实验台账按移动前 SHA-256 核对。
这些历史文件的内容和内部哈希不改写；源码、实时文档、资源登记和打包引用更新到新路径。
实验 `stair_profiles` 中的早期 `descent60` 与交付策略的 `descent60` 哈希不同，分别保留。
`ascent60` 的实验快照与交付副本虽相同，仍保留其复现角色，不在本次整理中去重。
001 完整可编辑 CAD 未随原仓库交付，此次不补造源文件；002 的 STEP 只覆盖变更壳体和垫片。

## 验证

- 自动测试：13 项通过，覆盖原控制契约、机器人变体、源码/包资源定位、Godot 资产导出和默认 ID。
- 资产与历史记录：541 个模型、CAD、建模输入、策略、JSON/JSONL 文件的迁移前后 SHA-256 一致；独立审查另核对图像等共 553 个资产/记录文件，字节一致。
- 平地回归：001、002 各 8/8 项完整关节 MuJoCo 控制检查通过。
- 安装包：运行 wheel 构建并在全新环境安装，506 个条目；包含的资源逐项与源码比对一致，无 CAD、设计、图片、实验、历史证据或训练检查点。
- 包内资源：两个机器人的完整/显示/精简模型、默认与两种显式实验策略、货物控制器均加载成功。
- Godot 启动：源码和安装包中的 001/002 共四次一秒 W 输入检查通过，各记录 51 个采样；安装包 001 使用省略 `--robot` 的默认入口。
- 文档与脚本：本地 Markdown 链接、全部 Python 源码语法、评估与模型处理的可用命令入口检查通过。
- 独立审查：无阻塞问题；旧证据文本路径和迁移文件数量两处文档问题已修正。

此次启动检查使用本机已有 Godot `4.7.stable.official.5b4e0cb0f`，不是原文档中的 4.7.2；
它验证资源导入、启动和基本步进，不替代原有完整 Godot 性能/阶梯/货物验收。
GPU 训练、GPU 数值回放、CAD 布尔重建和 Unity 编辑器没有在此次目录迁移中重跑。
历史仿真验收与制造资料限制保持原有含义。
原评估脚本会生成完整关节训练模型；本次 002 检查产生的额外模型已清理，未新增到交付资源。

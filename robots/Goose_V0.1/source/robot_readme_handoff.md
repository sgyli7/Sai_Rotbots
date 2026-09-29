# 交接时机器人 README（历史快照）

此页从原始 ZIP 提取；仅为迁入 `source/` 给相对链接加 `../`。当前工程入口见 [README](../README.md)；精确原字节见 [原始附件](../../Goose/goose_v0_1_workspace_handoff.zip)。

---

# Goose_V0.1 / Walker — 工作区入口

**当前版本：嘴部R2平行机构；本次补图已复核。**
本目录包含实体图片、结构说明、采购表和聊天决策交接，不依赖其他聊天的临时文件链接。
日期：2026-09-28。工程状态：设计候选与理想运动学核对，尚无制造CAD/实机验收。

![当前配套设计板](../design/concepts/beak_r2_review_board.png)

## 从这里继续
| 入口 | 内容 |
|---|---|
| [聊天设计交接](../design/conversation_handoff.md) | 用户目标、已选/否决方向、嘴部版本变化和下一阶段范围 |
| [嘴部R2说明](../design/beak_r2.md) | 当前机构、尺寸预算、夹持面、材料与测试计划 |
| [新增机构图复核](../design/kinematic_review.md) | 固定件连接、四点定义、32.14mm参考行程、5.85mm扫动和30mm止挡计算 |
| [整体结构](../design/walker_structure.md) | 既有身体、颈腿、内部组件与嘴部的关联 |
| [采购工作簿](../hardware/walker_r2_bom.xlsx) | 整机/嘴部/加工/来源/参数及新增“R2机构复核”页，共9页 |
| [嘴部采购CSV](../hardware/beak_r2_purchase.csv) · [打印件CSV](../hardware/beak_r2_print_parts.csv) | 与当前继承R2明细一致，便于Agent读取 |
| [离线图片资料库](../design/concepts/index.html) | 当前效果图、用户原图和找回的历史图，点图可看原尺寸 |
| [全部资料索引](../source/asset_index.md) | 历史文档、表格、图片和原始包的具体文件位置 |
| [理想运动计算记录](../evidence/beak_r2_kinematic_check.json) | 仅数值检查，不是实机验收 |

阅读优先级：本次机构复核 → 嘴部R2说明/工作簿 → 整机背景 → 效果图。
历史目录只用于溯源；原始ZIP保留原字节，展开历史文档仅修复了本地相对链接。

## 核心基线
- B步行鹅；保留身体、双腿、宽脚、长颈、头壳和相机相对关系。
- 固定上喙＋平行四边形下喙；嘴本身夹取，单台XL330＋约2:1传动为R2样测候选。
- AB=DC=25mm；AD=BC=14mm；±40°算例给出32.139mm行程及5.849mm中途前移；30mm仍为净开口目标。
- 旧XC330直驱铰接嘴单独归档，不混用其支架、BOM或开口公式。
- 不恢复轮式方案、Cargo或嘴下外挂夹爪；不把旧图的尺寸/载荷/续航当规格。

## 本地接续
将本包的`robots/Goose_V0.1/`与`scripts/diagnostics/goose_beak_r2_kinematics.py`合并到已有Sai_Rotbots工作区。
先读取仓库根`sai_robots_engineering_rules.md`。遇到同名文件先比较内容，保留用户现有更改；
已有机器人登记ID时以仓库实际登记为准。资料导入不需要伪造可运行模型或擅自修改默认机器人。

运行复算（仓库根）：
```sh
python scripts/diagnostics/goose_beak_r2_kinematics.py
```

这份包尚未自动写入用户电脑、切换客户端模式或提交GitHub。
实际制造前需完成真实零件包络、全行程干涉、视野与台架测试。

# Gorilla F1 独立最终审计（只读）

F1 两个冻结布局均仍拒绝。发现并确认原系统库存包含 **142 条已从实际 native 场景移除的 E2 结构历史质量行，650.329499798 kg**；它们所有 union `member_ids` 都缺失，不能保留为现存结构或与外计 F1 结构相加。修正仅写本审计目录，原 F1 冻结场景与账不改。现存旧上躯干 **77.937223578 kg** 是另一类问题：其 native 实体仍在，肩支承功能未被 F1 660 mm torso 完整替代，因此保留为不兼容功能挑战，不能作为删除质量的理由。

## 绑定范围

- F1 structure `structure_scene.json`: `90b62e0135a724fb9cb7df9909d58f3b618d40f6f5be922b516e1d83ca073ee6`；interface `f95096a90fa7bff442a94a22a2fe59c4406fe86d6e822fd212d809dbee64b12d`；checks `9dfb183cd43fe5c295bf272733949d097f963c23c4ef7bccc8344634fb05a984`。
- F1 system layout 1 `db4a91f1c715f17bb3bbf53dc9bcb11285b799fa51413b10fccc9aa6bfd2aa1a`；layout 2 `a295a21b6fbc3f72eca172a7b683c1b2886a4ebb6c84af9c9d60258d4ced5311`；spec `cc1cc87b760eabb3158d5e850eec8f5f0b0aead0aa8299b63aebdf5fb10c3a96`。系统作者确认两套均未采用，冻结后不再写入。
- 没有重新做整机碰撞、静力、热资格或器件检索。审计只确认实际材料、目录/假设质量账、变换与替换关系；安装及逐体惯量未接受。

## 材料与姿态独立复算

对 375 件 × 5 姿态独立扇形三角化，以局部原点的有符号四面体体积与一阶矩复算；闭边、正体积、面序、owner/union group 相同，并以正行列式刚体拟合检查。全部通过这些几何一致性条件。303 件指定密度材料形成 134 个有限材料 union；中立体积/质心独立复算净钢 **772.655734962755 kg**，与原 float32 Boolean 账差 `−5.68e−13 kg`。58 条参考组件范围 **107.693 / 123.213 / 154.013 kg**；它们按目录/声明范围计量，不从包络体积猜质量。

独立重新 Boolean 五姿态的最大体积差 **4.755928259e−9 m³**（7850 kg/m³ 下约 0.0373 g），是重复 float32 union/变换数值敏感性；上游更小误差来自直接刚体变换中立 union，两个口径分开报告。不是材料在姿态中变化的证据。

`structure_receipt.json` 是早先结构阶段收据，其 `system_final_audit_pending=true` 仅记录当时阶段；本报告和后续系统收据已完成冻结系统核查。

## 真实实体分量修正

旧 checks 的 24 组是 `trimesh.split` 封闭表面岛诊断，不能直接称 24 组材料断链。复核使用 `manifold3d.Manifold(Mesh64(...))`、Add union 与 `decompose()`。该 API 按拓扑分离边界，封闭内空腔可产生负体积分量；因此保留全部符号，不 `fix_normals` 翻正。将每个负空腔通过完整体积包含相交分配给最小含它的正外边界，再统计材料实体。

134 组中 **23 组有多个真实材料实体，总计 182 个正外实体**，无未归属负腔。`waist_pitch_carrier` 原 2 表面岛实际是 **1 材料实体 + 1 封闭内空腔**。空心立方壳、贯通空心环、两个分离空壳、空腔内另一个实体回归分别得到 1/1/2/2 材料实体；内腔不计第二个实体。净 Mesh64 钢质量 **772.655711702049 kg**，比原 float32 账低 **0.000023261 kg**。最大 signed 体积守恒误差 **1.301042607e−18 m³**；容差 `1e−10 m³`，腔体包含误差阈值 `max(1e−10 m³, |V_void|×1e−8)`。逐组计数/腔体/质量/质心在 `solid_components_receipt.json`。

这一修正不会证明焊接、支承、销/轴连接强度或力流闭合；不同 material group 没有跨 body 合并。23 组多实体仍需真实连接说明。API 语义来自本机 docstring 和 [Manifold 原始实现](https://github.com/elalish/manifold/blob/master/src/manifold.cpp)。

## 系统质量账修正

两布局各 1794 native parts / 1485 system+retained rows。逐行查实际 `part_name/id`；union 行逐成员查 `member_ids`，不能只看移除名单是否含聚合行名。1342 行实体成员全在；143 行全不在，无 mixed。143 中 **142 是旧 E2 结构历史库存**；唯一另一个是明确的 **30 L 全局油库存**，是有意 metadata 库存，保留。现存旧上躯干挑战亦保留。

| 范围（两布局相同，kg） | low | nominal | high |
|---|---:|---:|---:|
| 移除的历史 E2 幽灵库存 | 650.329500 | 650.329500 | 650.329500 |
| 修正后现存 retained context，除 36 新模板与全局油 | 750.800190 | 899.686922 | 1127.964447 |
| 36 新保持/主阀模板 dry | 184.622676 | 213.058911 | 246.008299 |
| 全局 30 L 油一次 | 24.600000 | 25.500000 | 26.400000 |
| 上三项现存系统库存 | 960.022866 | 1138.245833 | 1400.372745 |
| 外计 F1 结构片段（134 material groups+58 refs） | 880.348735 | 895.868735 | 926.668735 |
| 上述已列现存候选库存之和 | **1840.371601** | **2034.114568** | **2327.041480** |

最后一行 **不是兼容完整机器人质量范围**，更不是减重成功：4 缺失缸、未装接口、重新走管/电源、OEM 内腔/部件分体、肩支承与旧/新 torso 兼容性等仍缺，不能给它们 0 kg。正负质量变化只是纠正已移除历史实体；未来完整所需质量未被这个表上界约束。逐行 presence 分类及被移除历史行保存在 `present_mass_receipt.json`。COM 只有已知行位置的库存加权诊断，30 L 油库存位置未知被明确排除，不能叫全机 COM；任何原张量仍为代理，不是逐体 SI 资格。

## 替换、实际硬件和模板

- 375 件冻结 F1 structure 原生值在两 system layouts 全部一致，系统质量行没有重复加入 structure 件，外计账匹配。四 cooling cases 各一实体；旧四完整袖壳不再出现，不能将旧 port/hose 残留等同完整旧 case。
- 右 hip yaw 的 gear/motor/brake/encoder/controller/connector 六件，新的 native 与外计 reference rows 各一次，旧 `e2_ds_right_hip_yaw_*` aliases 零次。76 same-stock aliases、68 oldbank、18 oldholding、119 old oil material、16 old oil spatial inventory 全部已移除；它们的聚合历史 E2 mass rows 是上述幽灵错误的不同层级，已单独纠正。
- 五改液压轴的 **20 条原 brake/encoder/controller/connector** 仍有 native 与质量行，未把未替代电子制动功能删成零。
- 111 原甲顶点/面原值与 E2a 一致；四 main contact pads 亦一致，角色 `contact_surface_candidate`。`left_composite_forepad_upper_edge` / `right_composite_forepad_upper_edge` 在 E2a、F1 native 与 F1 row 都已不存在，**没有额外 F1 删除 credit**。
- 实际 finite barrel+rod 只有 **14 缸**；left/right fold 与 ankle 共 **4 缺缸**。zero-eye 缺口为 fold 11.5555 mm/侧、ankle 22.6666 mm/侧。18 套保持模块仍按实际库存计，4 个缺缸 owner 的模块不能称已安装；14 个存在 barrel link 也只是接口候选，安装未放行。
- 对 holding/directional 各 lower/nominal/upper 六源模板独立四面体复算有限附加材料，OEM core 用目录质量（LHDV33-21 3.5 kg、D1FB C doublecoil+OBE 2.9 kg），没有 `density×OEM box`。holding dry **5.350162 /5.987120 /6.704331 kg**，directional **4.906653 /5.849486 /6.962796 kg**。最大模板总质量复算误差约 `1.08e−10 kg`。
- 36 实例的 648 个 native 子件完全由源模板矩阵变换（最大顶点变换误差 0），OEM core 各一次，有限材料逐件一次；最大单件质量误差 `8.83e−11 kg`、质心误差 `3.86e−12 m`。范围是自建安装件尺寸敏感性，不是经厂家认证的完整模块上下界。holding 全包络 nominal **257×147×109 mm** 大于旧 **180×100×110 mm** 安装窗口，不能拿窗口当 fit。
- 有 77 个原可视细节/标记/屏幕/格栅等 native 件没有直接质量 ID，属于旧显示/功能包络与质量映射的未闭合边界；不从外观猜材质，也不将每个 UI 面当独立实物质量。新 F1 有限模板不存在未映射质量件。这进一步限制“完整整机质量”表述。

## 油水与接口边界

30 L 油一次计入 **24.6/25.5/26.4 kg**；18 holding+18 directional 外部已知 void **0.516280637 L** 与 108 段直线最短 hose void **6.422094059 L** 是库存分配，未再次加质量。OEM 未知内腔、实际缸腔、油箱余量、运动软管拓扑和弯曲半径未闭合；不能按 30 L 自动认定填充满足。

冷却库存 16 行对应 **12.481996329 L**，与源分体净水账三档质量逐行合计差 0，未再次计入新模块油 void。新壳/能源/泵位置变化后空间有效性、供回接头及跨关节路径仍明确未通过，不能把保留的 fluid inventory 当真实已路由液体。压力/流量/温升/电源持续资格未在本次审计中改判。

## 可复现入口

在 repo root 执行（仅输出本目录）：

```bash
.venv/bin/python .scratch/gorilla_internal_f1_audit/audit_structure.py
.venv/bin/python .scratch/gorilla_internal_f1_audit/correct_solid_components.py
.venv/bin/python .scratch/gorilla_internal_f1_audit/audit_system_templates.py
.venv/bin/python .scratch/gorilla_internal_f1_audit/classify_present_mass.py
.venv/bin/python .scratch/gorilla_internal_f1_audit/audit_replacement_details.py
```

输入/输出 SHA 与脚本、最终范围及不接受项由本目录 `manifest.json` / `final_receipt.json` 绑定。未复制 OEM 版权 PDF/CAD，未修改任何上游冻结文件。

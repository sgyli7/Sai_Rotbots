# Gorilla G1 腰部完整安装链：两次有界候选，均拒绝

本目录仅保存腰部 yaw → pitch → roll → 连续肩反力桥的临时候选。没有修改 AA3/C15 原 111 片外甲、F1、canonical、索引或 Git。没有全机重绘、采购选定、GPU、SI/制造/强度/审美放行。两次实际安装失败后停止几何修改，返回宏观路线。

## 文件身份与完整功能

- `candidate_a_scene.json`：首套，SHA `6c232af1301971772407f44351b89df3863b95087562d968666b06debb6a63d7`；原 producer 的确切冻结字节是 `build_candidate_a.py.txt`，原嵌入路径在该候选生成时为 `build_waist_chain.py`。
- `scene.json`：第二套 B，SHA `f1efdc21d3c8fddb4b90318210a07463c30174f8fa566feabe2529cc8f75bf1a`；实际 producer 是 `build_waist_chain.py`。
- B 共 32 个独立 ID：两套各十项旋转驱动功能、两套完整有限缸体/杆、四根眼销、四个净反力材料体。gear、motor、brake、encoder、controller 和 connector 保留完整参照尺寸及质量范围；其内材/旋转件拆惯量没有伪造。
- `parameters_and_interfaces.json`、`pitch_J_flow_and_force_screen.json`、A/B resource/mass/pose 记录和 `rejection_and_connection_receipt.json` 绑定各自源；`manifest.json` 提供全部文件和外部只读依赖哈希。

原厂安装身份已由本次独立来源确认：图纸 A 小 PCD 面是 output flange / inner race / FS 输出；B 大 PCD 是 fixed case / CS；B 中心为 WG input。整套源按这一身份重新构建，未只改旧堆栈标签。CSG65 保完整 123.5 mm，CSG50 保完整 98 mm，未叠加 F2 guessed races。输出安装面分别为 yaw Z=1.526 m、roll X=-0.025 m/Z=2.05 m；真实 bearing 参考面为 yaw Z=1.5035 m、roll X=-0.043 m。

唯一安装原始文档在 `../gorilla_internal_g1_oem_installation/csg_csf_gear_units.pdf`，官方 https://www.harmonicdrive.net/_hd/content/documents1/CSG-CSF_GearUnits.pdf ，SHA `517160deff3bc6272980fef807212d29ee2301ce819b4388df540fcd3ce7d97b`。p33、36–37 的身份/孔距可用于探索；50 case 14 孔与 generic 12 孔容量表冲突、OEM 内部惯量、预紧/安装强度和持续热仍未知。不能把 Mc 倾覆值当驱动额定。

## 两次实际拒绝与范围

A 的 pitch J 在 ±25° 内过零，宏观机构拒绝；其全球旋转后分段 union 的两个 barrel 原生产源出现低于 1e-10 m³ 的闭面小体，资源契约失败。保留原源和诊断，不通过检查器翻面修复。

B 先做 121 点眼位/行程纸面核查，再以共同 local Z 构建完整 barrel/rod，最后一次整刚变换。B 的 32 个 native 源均通过 signed containment/闭面/唯一 ID 资源契约；没有 `fix_normals`、`split`、`compose` 或诊断修复。资源正确仍不等于可安装。

| B 真实采样姿态 | 不同 owner 真材料冲突 | 原甲材料冲突 |
|---|---:|---:|
| neutral | 11 | 30 |
| pitch -25° | 14 | 35 |
| pitch +25° | 11 | 32 |
| roll +10° | 11 | 32 |
| yaw +15° | 11 | 33 |

最大自身冲突为 yaw input coupling 穿 pelvis 固定反力板 **26.282 cm³**。中立其余十对是左右 cylinder barrel/rod 与 A/B 销、yaw/pitch carrier 的实体交叠。眼孔只从环 primitive 扣除，随后 union 的 sleeve/rod collar 又占入孔内；必须在下一整组 producer 对完整眼结构建立真实贯通加工孔。缸体通道同时与两个独立 carrier 未闭合，不能仅改眼位后称装配通过。

最大原甲冲突为 yaw fork 与 `ivory_rear_pelvis_cartridge` **86.611 cm³**；其后是左右 thigh wrap 约 60.68/60.65 cm³，以及两缸与 rear pelvis band 约 59.73/58.91 cm³。完整逐对记录与 owner 分组见 receipt。由于自身安装先失败，这些不是“AA3 必须整体改形”的证据，本轮外甲修改为 **0 mm**。

四个净反力材料体本身各为一个连续材料分量。yaw owner 净 union 的三个分量是连续叉壳和两根有配合间隙的 A 销，不能误报为叉梁三段断开；B 销与 carrier 材料 union 并不替代真实机械保留/配合证据。被动 pitch 轴/衬套明确独立有间隙，接触、摩擦、轴向保持未知。roll 输出至肩桥有限材料连续，但 flange 螺栓和完整上臂固定反力安装未验，不能删旧上身质量并宣称已整机替换。

最终检查器同时保持缸 A-B 轴与实际随 parent 移动的眼销轴；纠正早版“最小方向旋转”在 yaw 时引入的虚假缸体绕轴旋转，A/B 已重跑。五个动作点不是连续扫掠合格，全部 reference envelope 交叠单列，OEM stock 不当真材料。其余全身结构/硬件没有纳入本腰部范围。

## 模块质量、液压粗算与下一整组路线

B 干态模块有限净钢材料 **306.376 kg**，完整组件参照功能合计 **40.653 / 43.313 / 48.513 kg**；新模块总范围 **347.029 / 349.689 / 354.889 kg**。范围排除原甲、完整臂腿、旧上身、油/阀/管路和 root 的 880.424 kg 外部上身负载。此源为拒绝候选；这不是合格整机净重。A 的 311.922–319.782 kg 仅为资源失败诊断。

B 双 pitch 缸 bore/rod=50/25 mm，假设压力 21 MPa；±25° 下 J=0.089128–0.200488 m/rad，完整眼长 0.487288–0.616269 m，stroke=0.148981 m，zero-eye=0.477288 m。在 qdot=.5 rad/s 敏感性下双缸峰值 cap/annulus 流量约 **23.619/17.715 L/min**，理想 21 MPa×Q 为 **8.267 kW**。对 root 1.59 kN·m 外部上身敏感性，理想低 J annulus 压力约 6.057 MPa；没有计算损耗/冲击/保持/热额定，不生成能力评级。两条 actual cap/rod port 坐标已给，分支 `g1_pitch_distributed_branch_two_cylinders`；没有画出阀/holding/新管路，也没有沿用旧油线接通或重复加油质量。

下一轮先联合闭合 fixed case 反力板的 input 贯通、完整眼加工孔与整对缸体扫掠通道，再评估剩余原甲冲突。若完整液压 pitch 在规定范围仍无法容纳，比较**完整旋转 pitch** 安装链作为宏观替代，不再本轮补第三眼位；目录两组能力不能直接相加，OEM 总包络不缩。

质量改进应比较真实净截面与明确未焊 6082 挤压/机加螺接载荷壳。root 的理想材料截面粗算仅指明下一宏观窗口，不在这版悄改 7850 kg/m³ 密度，也不把铝典型 E/屈服直接作焊接/铸件/孔联接强度证明。保持 AA3 原审美，只有自身安装闭合后仍存在明确物理冲突，才提出最小壳变化及同源四视供用户审美接受。

## 真实视觉与复现

`bare_chain_native_four_view.png` 与 `with_original_armor_native_four_view.png` 已实际打开查看。相同 226.229508 px/m，显示完整新腰模块及未改的原111甲；不显示其余全身结构，侧面空白和断开的外甲反映此限定范围。它们是 native 三角诊断投影，不是新概念设计/最终制造/审美权威。

只读检查与图生成：

```bash
.venv/bin/python .scratch/gorilla_internal_g1_waist_chain/check_waist_chain.py .scratch/gorilla_internal_g1_waist_chain/candidate_a_scene.json
.venv/bin/python .scratch/gorilla_internal_g1_waist_chain/check_waist_chain.py .scratch/gorilla_internal_g1_waist_chain/scene.json
.venv/bin/python .scratch/gorilla_internal_g1_waist_chain/render_four_views.py
```

A producer 冻结映射、B 当前 producer、资源 validator 与输入源都在 manifest；不要直接运行 A 冻结文件去覆盖 B。installation/physics/stable SI/aesthetic 均为 false。

# Gorilla F2 单侧四缸：压力、杆与销独立宏观粗筛

21 MPa 理想腔压粗筛已完成；冻结A/B源有 fix_normals() 将封闭内腔翻正的绕向错误，原体积/质量/连通及Boolean证据未接受。此筛查只按实际顶点量取及声明尺寸做解析假设，未称源native为合法材料实体。本报告不改变 F2 几何/装配拒绝状态，也不构成连续驱动、完整强度、疲劳、导向或真实接触资格。仅使用本轮四缸实际源，没有把旧 E2a LP 或外部六维 wrench norm 当成缸眼/销真实载荷。

## 同版输入与实际尺寸

闭腔语义诊断只引用上游 `/home/ethan/Projects/Sai_Rotbots/.scratch/gorilla_internal_f2_lower_module/closed_cavity_receipt.json` SHA `ead9bd0fc6d2312cb24d9f4cad2660cde6a32b2246afa43bf50ca664a00449e2`；不在本压力分支重算修正实体/质量或碰撞。
- A：`/home/ethan/Projects/Sai_Rotbots/.scratch/gorilla_internal_f2_lower_module/a/module_scene.json` SHA `2d1b6d06e30c199355d6c86742ebf21641be791c1290f2aafb94e43ef2c521e8`；checks SHA `33c203fa19660ea96206cd3772374806d4348367ca3bc5819a62655190138359`，source/checks绑定匹配=True；源metadata标记四缸几何包=4。源几何/物理 accepted=false；绕向/闭腔拒绝独立保留，旧质量与连通计数不作为有效材料证据。碰撞/装配亦未关。
- B：`/home/ethan/Projects/Sai_Rotbots/.scratch/gorilla_internal_f2_lower_module/b/module_scene.json` SHA `7adcfa17ec342f46eadce874999da4e35b3f0a480d72176e2c03cbb050a87814`；checks SHA `3a0807548355db07b597ea9b2fd15ec38d1bf3981129ae606ba3387bf45b5d6e`，source/checks绑定匹配=True；源metadata标记四缸几何包=4。源几何/物理 accepted=false；绕向/闭腔拒绝独立保留，旧质量与连通计数不作为有效材料证据。碰撞/装配亦未关。

四缸相同 bore63 / rod30 / barrel wall5 mm；rear/front cap20 mm、piston20 mm、seal空间20 mm是有限自建源尺寸，并非厂家额定总成。每端按 native 顶点测得尺寸（不是合法实体资格）：pin Ø40×106 mm、eye Ø76/孔Ø42×轴宽44 mm、fork两片厚14 mm、反力中心±32 mm（跨距64 mm）；实际内/外fork接触位置使反力跨距可取50/64/78 mm敏感性。销孔径向1 mm、眼与各fork面3 mm间隙是当前真实几何，尚不是合格轴套/配合/接触。

| layout/缸 | stroke mm | 最短/最长眼距 mm | 自建额外固定空心段 mm | source φ30段长度 mm（union前） |
|---|---:|---:|---:|---:|
| A/left_fold | 53.186 | 271.978/305.164 | 38.792 | 133.186 |
| A/left_ankle | 44.583 | 518.786/543.369 | 294.203 | 124.583 |
| A/left_foot_roll_pair_0 | 50.036 | 260.171/290.207 | 30.135 | 130.036 |
| A/left_foot_roll_pair_1 | 50.036 | 260.171/290.207 | 30.135 | 130.036 |
| B/left_fold | 66.282 | 268.560/314.841 | 22.278 | 146.282 |
| B/left_ankle | 37.905 | 475.105/493.011 | 257.200 | 117.905 |
| B/left_foot_roll_pair_0 | 50.036 | 260.171/290.207 | 30.135 | 130.036 |
| B/left_foot_roll_pair_1 | 50.036 | 260.171/290.207 | 30.135 | 130.036 |

φ30段在 union 前包括与大径 piston 重叠10 mm；它不是完整自由屈曲长度。长踝缸眼距主要来自固定空心载体段，不应当成543 mm裸露活塞杆。

## 21 MPa 力与厚壁筒

`Ac=πD²/4, Ar=πd²/4, Aa=Ac−Ar`；`F_extend=pcap Ac−prod Aa`，`F_retract=prod Aa−pcap Ac`。使用理想毛力，不乘0.9等效率系数降低压力证明载荷。实际摩擦/惯性/重力/配压未由这些式子闭合。

| 加压腔/另一腔 MPa | 伸出净力 kN | 回缩净力 kN |
|---|---:|---:|
| 21/0 | 65.462 | 50.618 |
| 21/1 | 63.052 | 47.501 |
| 21/2 | 60.641 | 44.384 |
| 21/5 | 53.410 | 35.032 |
| 21/21 | 14.844 | -14.844 |

两腔同21 MPa时回缩方向净力为负，显示不能把供压直接称负载压力或双向额定力。21 MPa是本次腔压工况，不是已证明的最大腔压：保持阀设定、返回背压、压缩负载与shock可改变实际腔压；必须独立限制。四缸不能因单缸静力值就声明同速、同压或任务共同可达。

Lamé 直筒假设：`a=D/2, b=a+wall, po=0`；`A=(pi a²−po b²)/(b²−a²)`, `B=(pi−po)a²b²/(b²−a²)`；`σr=A−B/r²`, `σθ=A+B/r²`, `σz=A`（理想闭端轴力）。von Mises由三主应力差计算；不是薄壁公式。

四缸理想直筒内壁 `σθ=143.572`, `σr=-21.000`, `σz=61.286` MPa，最大 `σVM=142.524` MPa。这个σz=A闭端状态不是滑动piston/gland总成已证明的轴向路径；相同径向/环向、假设轴向0或−A时内壁VM分别155.142/187.981 MPa，仅载荷路径敏感性，非真实上下界。端盖板弯曲、前gland、螺纹/密封槽/端口、焊缝、整体轴向压缩/弯曲与应力集中不在该直筒Lamé中；不能凭此放行20 mm端盖或整缸。

## 杆压缩与理想Euler范围

φ30实心毛截面推压应力 **92.610 MPa**，回拉 **71.610 MPa**。旧自研 `355 MPa` 假设下毛屈服力约 `250.935 kN`，是条件标尺，不是实材资格。

`I=πd⁴/64`, `Pcr=π²EI/(K L)²`，`E=210 GPa`、K=.7/1/2是端约束敏感性。各源φ30段和整个眼距假想均匀φ30杆分别算，不把后者当真实组合缸屈曲模型。短段理想Euler应力往往超过假设355 MPa，弹性Euler适用条件本身不满足。

| layout/缸（最长眼距当均匀φ30） | K=1 ideal kN | K=2 ideal kN | K=2/21MPa推力 |
|---|---:|---:|---:|
| A/left_fold | 884.927 | 221.232 | 3.380 |
| A/left_ankle | 279.116 | 69.779 | 1.066 |
| A/left_foot_roll_pair_0 | 978.493 | 244.623 | 3.737 |
| A/left_foot_roll_pair_1 | 978.493 | 244.623 | 3.737 |
| B/left_fold | 831.363 | 207.841 | 3.175 |
| B/left_ankle | 339.048 | 84.762 | 1.295 |
| B/left_foot_roll_pair_0 | 978.493 | 244.623 | 3.737 |
| B/left_foot_roll_pair_1 | 978.493 | 244.623 | 3.737 |

A踝缸K=2假想均匀φ30模型仅为推力1.066倍，提示端约束/组合刚度敏感；**既不能据此称真实屈曲失败，也不能称通过**。真实barrel/sleeve/rod变截面、piston/gland导向长度及承压、端眼转动、偏心、间隙、连接与侧向力尚未形成屈曲模型。

## 实际跨度销粗筛

梁假设沿销轴：眼居中w=44 mm总载F，两fork反力各F/2。以64 mm反力中心跨距，均匀眼分布 `Mmax=F(2L−w)/8`；居中眼点载 `Mmax=FL/4`；`Z=πdp³/32`, `σb=M/Z`, 双剪平均`τ=F/(2πdp²/4)`、圆截面最大剪切`4τ/3`。弯曲最大纤维与剪切最大点不同；`sqrt(σb²+3τmax²)`只是非同点保守包络，不是真实销某点VM。短粗销的三维接触/剪切变形不由梁模型证明。

| 21MPa推力；64mm反力中心 | 弯应力 MPa | 非同点弯剪VM包络 MPa |
|---|---:|---:|
| centered_uniform_eye_load_point_reaction_centers | 109.396 | 124.842 |
| centered_point_eye_load_point_reaction_centers | 166.698 | 177.219 |

双剪平均 `26.047 MPa`、圆截面剪切峰值 `34.729 MPa`；实际fork接触位置50/64/78 mm与眼分布/点载组合在JSON逐项列出，其粗弯应力范围 `72.930–203.163 MPa`，最大非同点包络 `211.881 MPa`。另一敏感模型把眼点载放在轴向边缘±22 mm，反力失衡；不假称均匀接触。

64mm中心支承下，眼平均投影承压 `37.194 MPa`、每fork `58.448 MPa`；gross净ligament仅作尺寸标尺。孔边应力集中、眼/叉撕裂、bushing/Hertz、销肩槽、轴向留置、弯扭组合、焊缝与循环疲劳未证。两端压力载荷逐端独立列出，并非实际任务wrench分配。

## 材料与关闭条件

唯一新增一手材料标尺为 [Ovako 42CrMo4](https://steelnavigator.ovako.com/steel-grades/42crmo4/)（2026-02-03版；2026-10-02核实）。其中6082是Ovako厂家42CrMo4 M钢材系列代码，绝非EN AW-6082铝；该+QT圆棒表列25<40 mm的Rel≥750 MPa、40<100 mm的Rel≥650 MPa，典型E210 GPa。原棒有效截面/热处理与证书决定适用性；40 mm成品边界不能自动取750 MPa，较大原棒车成40 mm亦不能继承小截面值。来源是材料尺度，不是本项目选材或销证书；没有登录/下载PDF。事实记录在material_source.json。

- 压力边界：给出所有实际腔的保持/冲击/背压上限及同工况力分配，端口、盖、gland、密封与连接承压另核；不能将21 MPa母线替代load/preset压力。
- 杆/缸：明确实际端约束、变截面组合刚度、piston/gland导向及偏心接触，才可确定有效长度/屈曲与侧载；当前Euler敏感性没有这一资格。
- 销/眼/叉：明确真实轴套与配合、承载接触/反力作用位置、留置、连接/焊缝与实际材料强度；用真实A/B压力眼反力而非六维norm核弯剪/承压/撕裂，再针对任务循环关闭疲劳。
- 材料：明确grade/+QT工艺、ruling stock尺寸及成品证书；旧S355/355MPa是假设。成品销热处理、原材/成品取样方向与证书未知；42CrMo4强度不能无证填入本体。
- 模块装配与力链：先关闭当前原甲/不同body真实干涉、恒材料和连接诊断；本粗筛不替代几何通过，更不证明上游膝、末端arch接口或整机任务能力。

## 复现

```bash
.venv/bin/python .scratch/gorilla_internal_f2_pressure_pin_screen/screen_pressure_pin.py --layouts a b --output final_screen.json
.venv/bin/python .scratch/gorilla_internal_f2_pressure_pin_screen/make_report.py
```

原生端点/眼/叉/销实测、return pressure、Lamé主应力、Euler适用标记、分布/点载销以及实际源SHA均在final_screen.json。manifest绑定同版输入与输出；仅本ignored目录写入。

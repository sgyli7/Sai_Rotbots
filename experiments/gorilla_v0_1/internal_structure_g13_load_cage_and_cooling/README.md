# Gorilla G13：宽截面承力笼架、肩干湿分区与同源载荷

壮硕体积用于宽厚三维承力和完整模块共同设计。实际主躯B、独立肩A及主躯A负载粗核已封存；**三者是不同源的研究候选，尚未整合或放行安装、强度、持续热、审美与稳定SI。** 宽厚墙/肋不是永久锁死的拓扑优化禁改域，也不以整体塞满钢料作为目标。

## 主躯承力与真实库存

[主躯报告](load_cage_colayout/README.md)绑定B源`299582c9…`、3038成员/1173新质量行。200×90mm闭口纵梁/横梁、4mm起始壁和5mm颈节点连接同版两旧肩锚座；最后B腰法兰扩大形成真实净材连接。钢净104.537820kg包含两旧anchor一次，不能与未含anchor的G12框197.552kg直接比较减重。旧墙厚和钢材不是最终取舍。真实器件扣除后的局部截面不保证仍为理想完整闭口梁。

**测量范围纠正：**冻结子报告中“含64.255993kg旧anchors”用了解析OCC范围；实际布尔输入是两份native，每份32.096532kg，合64.193063kg。[root更正](root_review/scope_corrections.json)保留原字节，未改写历史报告。A初始8component诊断数的是2正边界/6负腔，不能称8材料根；独立负腔实体探针没有真体积交，A腰法兰独立失败保留。最终B严格nesting是1外材料根/4负闭腔；所有原孔腔保留。

root由原三角[独立积分](root_review/b_frame_moment_review.json)核体积0.013316920m³、条件钢COM/fullI及边度/方向；[实际STEP回读](root_review/b_actual_step_readback.json)确认1solid/5shell、默认mm换算后相对体积误差8.79e−13、bounds约1e−10m。它们支持身份/单位和源资源，不证明焊接、腰支承或强度。

完整480实际尺寸电芯分成4个20×6模块，每颗最大70g预算，不是已量得真实电芯净质量。完整能源/保护/安装/冷板等51.388–64.428kg；80s6p最低7.44kWh仍只是参考能量，母线、绝缘、回馈、端电压/放电与持续冷却未知。安装与TIM已形成接面，但螺纹预紧和接触热阻未关闭。30L油/12.482L水各全球一次，统一暂归torso；容器工作液位/回流/膨胀/动态分布仍未闭。4个新大风机/芯仅尺寸或自有安装预算，不继承完整原厂芯额定。

限定所有new-new/new-vs-all旧成员筛查1976正体积对，含原甲41/独立肩6/new-new142/其余1787；没有retained-retained或运动。**不能与G12的317限定范围比较进退。** 水箱碰泵1.68L、笼架碰HX568.9cm³、油碰甲473.8cm³、腰adapter236.6/gear192.6cm³等仍拒绝，未知不按owner豁免。[真实四视](load_cage_colayout/b/native_four_view.png)、[剖面](load_cage_colayout/b/actual_sections.png)已查看，只是内部诊断，不是新美术采用图。

## 完整肩干湿分区

[肩A报告](shoulder_cooling_zones/README.md)绑定`2a6126f4…`，190实际成员、完整115mm齿轮和66mm电机、同轴及支承/制动/反馈。66mm导热套、40mm湿冷却段与干安装collar真实分区。限定资源/中立±30有限材料交、水域材料交和分阶段拆卸采样关闭；每侧125.494mL水腔连续，边界逐面微探针支持几何覆盖。

初装端盖R26.1mm不足以装入R105mm stator/套；分组拆出不能证明初次装配。真实可拆cover、螺纹/预紧/工具/托持、OEM保护参考及连续Tn/热流仍开放。40/66湿覆盖、全长TIM和轴向热传播仅条件粗算，不继承参考690W为安装能力。8个小曲面接头native/CAD体积差0.397–0.434%超旧0.25%比较；[root独立190件核](root_review/a_native_inventory_review.json)也明确失败，不自动放宽。全部四视、wet/dry与最终1um避顶点[轴向剖面](shoulder_cooling_zones/a/cooling_section_axial_YX_Z2290p001.png)已查看，旧精确顶点面诊断保留。

**肩A尚未替换主躯B中的G11独立126件及旧anchor。** 各自局部通过不继承为同版整机通过，G14须明确替换/合并而不能叠加。

## 负载、材料与优化边界

[负载报告](loads_and_materials/README.md)只属于主躯A`9c5b1f1f…`，65独立算术检查支持成员/六维守恒与理想截面，不属于B。按同633旧干子集逐完整member退休37行，不扣没有在其内的77.937kg旧桥；两native anchors从肩库存扣一次。A条件功能库存745.225/840.987/994.204kg，非整机/完整上躯。源owner条件名义腰833.804kg、Fz−8.180kN/My−2.473kNm；另列全油箱归torso条件，不能继承至最终B或搬运能力。

实际接口X=.115两肩及腰源面绑定六维合同提案。载荷/支承、动力、自重分摊、夹持和接触仍有条件，不将刚体gauge当真实固定支承，不继承旧踝42组。未切200×90×4理想梁各分半、最大重力×1.5的约21.925MPa只是截面粗核；真实stock孔、节点和局部截面/剪扭/屈曲/疲劳没有通过。

实取[SSAB hollow handbook](https://www.ssab.com/-/media/files/en/infra/news-and-articles/ssab-domex-tube-structural-hollow-sections-en-1993-handbook.pdf)和[Hydro6082技术资料](https://www.hydro.com/globalassets/08-about-hydro/hydro-worldwide/austria/nenzing/alloy-data-sheets/hydro-en-aw-6082.pdf)。同截面铝比钢质量约0.345、EI约1/3；同外截面匹配两方向EI可能更重或无解。宽厚域应增加有效I并重分配墙/肋，而不是只换ρ、照鸟骨图片挖孔或承诺减重百分比。材料产品/temper/焊热影响与制造资格分开，当前没有新FE/SIMP。

## 保存与整机下一步

[清单](snapshot_manifest.json)保存105精选原字节/109冻结身份检查；保留A、Bbefore_interface、最终B、原CAD失败、肩原失败和独立审计。[恢复入口](restore_snapshot.py.txt)仅写独立空目录。G13负载报告引用的A producer在B期间已更新；精确旧producer在a/build_cage.py保留并以历史绑定alias记录，不改旧SHA或覆盖新版。原下载/日志/依赖及冗余图排除，计算仍需先前受控输入与隔离CAD运行时。

G14重新共同安排完整换热器/双风机/密封风道、能源/泵阀/油水与腰接面，整合完整G13肩，保持原审美；另做真实可拆壳初装以及原厂完整热部件/库存范围。各最多两宏观，07:25UTC肩/热首源、07:40硬收；07:30主躯首源、07:45硬收；root07:45–08:05至少20%整合。不继承自有180mm芯安装预算为Boyd完整芯，也不冻结旧油水stock。腿脚外形等用户通知，无GPU。稳定SI、真实双足双手和复杂Bevy仍是目标。

# G12 共同布局：A/B两候选封存，B拒绝放行

最终诊断源为`b/scene.json.gz`（6bcdbd91…）：2538parts，667新质量row；A原源87d27071…保存在`a/`，没有第三布局。111原甲逐值不变、G11 B128肩件逐值不变，未恢复旧103肩core。旧Victron形状/10.24kWh及旧77.937kg上躯桥仅待替历史，不能从本次结果抵扣成已闭合整机质量。

4×120颗P45B maxØ21.55×70.15mm、轴X、12×10格、pitch22.5mm实画480颗；最小径向间隙0.95mm。4×20s6p只是条件电路，最低参考能量7.44kWh，maxcell质量预算33.6kg，不是实际逐芯质量/完整pack持续额定。4完整pack的enclosure/separators/insulation/busbar/coldplate/20sBMS&fuse/sensors/mount/connector/vent全保；HV接触器/预充/断开/current测量和LVconverter独立画出。电路走线、绝缘、回馈、火灾泄压、端电压与原23驱动母线匹配均未通过。200..336V仅条件区间，未继承母线。

完整能源设计库存55.511/60.671/68.551kg（含源maxcell预算），上值超过原48.2..67.4kg设计余量1.151kg，据实保留。4完整功能AABB各10.112L（含细小vent/安装凸出，非净材料），合40.448L；124×282×237mm enclosure外stock合33.150L。不能用旧planning19.65..33.50L声称实装已够；各小附加实际空间单列。service在拆壳后复用，不永久扣除框架。

两泵各完整7功能的原生profile未缩：主stack沿X布置，filter与inverter分置，支承/LC6Lmin条件/电功率与新油水路线红线未关闭。原阀、hold、电驱、换热、fan、duct、compute、screen、网络与线管仍保留；移动后的旧管线仅invalid历史context，没有假称端口接通或省掉功能。screen/111外甲未裁。

油30L、水12.481996L每全局库存只计一次（25.5+12.481996kg条件ρ预算）。两oil箱内腔共33.781L、两water箱12.728448L，静态几何容量足；实际pipe/chamber/coldplate void、气室、膨胀与运动体分配尚未闭合，不能把全库存既灌满tank又加在管路。四global inventory几何只是库存放置诊断，不是已连通运行填充。

宽厚主躯为真实净钢baseline：A200.264kg；B197.552kg、25.165886L、1solid。前后X8mm、侧Y10.2mm、Z端8mm是坐标内偏置，非均匀法向壁厚；另有8mm跨肩web与实际腰neck/flange。没有把旧6mm壁锁成不可删实体，不再扣全部518legacygross/service；当前仅pack housing与实pump/新tank reference留空。baseline没有经过强度/优化，材料/焊缝/疲劳/制造证书未知。

B CAD BRep有效，SI STEP声明METRE；raw错误MM声明仅被显式改单位token、坐标未缩放。默认MM reader真正回读后÷1e9体积得到25.165886L，rel1.32e−13。667新资源在既有signed-material合同下通过（包括原始边/空腔），仅是这667件资源，不替111甲/128OEM/整机资格。

有限筛查仅覆盖667新physical/reference相互＋111原甲＋128肩，**未筛全部2538件**。共317正体积pair：175对原甲、24肩、118新新；NoError仅数值查询，无修源或负腔翻转。原甲/OEM的fan-triangle查询不等完整源资源认证。所有行与范围在`b/finite_overlap_rows.json`，没有静默排除。

最重实际不足：

- 腰下油库存各约308.7cm³进入原蓝腿甲，水库存各约144.9cm³进入原格栅socket；有限箱体自身也需安装空间。容量足不代表容纳成立。
- 新frame与左右fixed motorcase各64.211cm³实材交；与protectedQTL210 profile各195.956cm³，不可猜OEM空孔取消；holder各41.143cm³。与闭anchor各216.397cm³可能属于拟同材同parent焊接搭接，但必须显式整体union/连接设计再算，当前没有当作合格mate或独立总质量。
- frame与主白甲约104.182cm³、hoodside116.692/104.128cm³查询交；G11条件开口closure不是内腔保证。可见甲0mm保持，当前layout失败，未靠改壳盖过去。
- 新packfastener/connector库存穿frame约18.657cm³/上pack；vent与connector约1.239cm³/pack。polymer隔板/端绝缘亦有小同材搭接，库存叠体未装配union；不能按同body把所有交叫接触。
- mount bars距case1mm未落实连接；coldplate到cell端至少10.925mm的真实热接触链未建，channel是未接端口闭空腔。480芯/功能库存存在不能替代持续热条件。

因此B是同源可检查的拒绝候选，不是连通已安装承力整机。没有第三修孔/補桥/FEM/SIMP/采购/GPU/Git；根线程决定下一架构。新库存301.390/306.670/314.710kg仅frame+新能源/流体/容器等，不含原甲/128肩/保留旧系统，严禁当whole mass/COM/I。入口可继续真实布局、原生资源/空间/轴反力，不能直接当载荷qualified优化输入。

复现B：`.venv/bin/python .scratch/gorilla_internal_g12_torso_system_colayout/build_colayout.py --layout-b`；只读核：同目录`audit_colayout.py`；最后`finalize_colayout.py`。A原producer文本只是历史归档，不在a路径直接运行（其相对root以原执行路径为准）。

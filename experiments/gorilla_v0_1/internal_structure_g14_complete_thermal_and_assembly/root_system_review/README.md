# G14 整机功能、库存与冲突范围的独立复核

只读G14 body候选，不改CAD、外甲或已冻结热报告。A实源`75670984…`与3472对positive rows/audit哈希一致。B在第一次读取时actual source已经`a6a45796…`，其3082对仍来自`5139be5f…`旧源；该初读结果保存为`b_unbound_overlap_review.json`，不能绑定改正后B源或用作A/B改善证据。07:52:40确认body freeze已存在，实际scene/audit/overlap均绑定`a6a45796…`，随后仅一次重读最终B并重新计数。早期unbound旧结果保留，未用于最终对比。

## 同源A的三类计数

| 诊断类别 | positive pairs | 意义 |
|---|---:|---|
| 有限材料几何交叠 | 1444 | 740同declared body、704异body；同owner不代表允许实体穿插。只有几何证据，不代替严格全源材料资格、实际装配/承力/强度。 |
| 完整器件/窗口/服务/未知scope包络障碍 | 1886 | 不从计数中豁免；gross包络交还不能自动当真实材料，但仍阻止声称安装已闭。 |
| 全局库存或已画fluid region待分配 | 142 | 全局箱液体代理与硬件相交不直接当刚体撞击；实际管/腔分配及实体排他仍必须解决，不能靠“只是水油”放行。 |

三类互斥合计3472。全部case仍无整机物理资格。`a_top5_direct_boolean_receipt.json`对下表5对重新直接读源坐标/面，逐polygon作确定fan三角化（未fix normals/删件/修源），原Mesh64 kernel均NoError，Boolean值复现；不是严格全部边界/包含/装配审核。

| A新布局首5有限材料障碍 | 交叠cm³ | 具体含义 |
|---|---:|---|
| 新双前plenum×连续暖白躯干甲 | 44.805 | 实际duct材料侵入原甲；隐藏内皮/路由未闭，不能据此要求整体改外观。 |
| 新笼架×旧右EMRAX空气duct | 41.327 | 新笼架与保留旧风道共同占材；旧风道是否退休/改造须显式方案。 |
| 新笼架×旧左EMRAX空气duct | 41.327 | 同上，旧LC电机仍需空气循环的功能不能静默删掉。 |
| 新油箱壳×waist pitch barrel1 | 41.041 | 壳与独立移动缸材料相交，不能当油库存代理豁免。 |
| 新油箱壳×waist pitch barrel0 | 41.041 | 同上，机构与箱体分区需要共同重排。 |

全场最大的有限材料问题另是两行完整方向阀guard之间126.577 cm³/对，前5见JSON。各21件完整阀组都保留，但3行bank的130 mm中心距不足以避开现204 mm级完整guard；不能通过减去guard或按相同body接受。其余最大包络包括单背屏与旧C15屏形reserve1167.677 cm³、阀核心与hip gear447.444 cm³、背屏与原甲277.248 cm³；这些仍是对应scope障碍。

## 替代、移动和质量范围

A3106件无重复native ID；1306个proposed-retired ID均不在actual scene。1179 new mass rows均有actual member且无同ID重复。它们包含参考器件、自定安装材料和全局fluid，不是整机净重，也不能继承ghost650 kg旧union行。四pack各120颗，480原颗粒与完整辅助功能保留；cell70 g是最大预算，不是实称质量或真实额定。

原5件油水HX从G13到A不是同一刚体移动：主体中心由[.220,0,1.925]到[−.250,0,1.960]；四原hollow ports也各自归到[−.250,0,1.960]。原138 mm两侧横距/172 mm油口竖距/210 mm水口横距被压成0；主体和管口不是“已完整搬好”。A的热分区、实际接口不能靠保留旧route宣称接通。B当前geometry的group correction虽已解决共同平移，但必须用同SHA重新算整机pairs。

完整主core只有1件584×305×64 stock；2件172×172×51完整fanbody和guard真实另列。fan mass1/2.5/4 kg为自定预算，原厂质量仍未核。旧两`e_*_supplement_rear_core`、10条旧sealed ducts，以及`e_coolant_pump_complete_reserve`仍在scene，未列为本次退休；它们不能既当history又在active mass/clearance里暗算。需要给active/reference-only/完整功能替代关系，不能默认旧泵就是第二热路泵。

屏模块`ds_back_screen`有完整电子模块质量1/1.7/2.7 kg；C15 `rear_control_screen_module_envelope`明确无物理质量，是同设计功能的形状reserve。两者不能计成两个屏，也不能将其包络交直接判两个真实屏碰撞。B已给alias字段；仍需真实统一布局并接回原蓝背屏/玻璃/UI安装。

18×21件directional组与18×15件holding组均存在；四缺缸的holding/实际安装位置仍unknown，保留功能不代表悬空件已装好。移到bank的阀body字段仍有旧limb owner，`route_owner_support_unknown`已标，不能据位置或名字补造固定支承。

## 第二热路与液体不能由预算盒冒充

`g14_hot_secondary_complete_function_budget`是13.6 L、6/12/22 kg自定整盒，声明hotcore/fan/guard/plenum/pump/controller/mount/valves/fittings。没有独立native pump/degas/保护调节/冷却液隔离接管/服务port，UA、扬程和库存不闭；不能自动认作已经实现R2热路线。完整oil-waterHX虽然有两流体不相交的原腔，真实新接口与串并流、串污染故障保护仍未闭。

全局oil25.5 kg与water12.482 kg在new rows分别一次（合计37.982），两个肩`bounded_water_region`是全局stock内分配alias，不能再加0.264 kg；source又有ρ1050混合液与全局ρ1000的差别，配方尚未统一。global fluid boxes未代表实际tank operating fill/外管路同时装液；它们的142对/或后续B对不能“删除库存后得到通过”。

与冻结G14热报告一致：一芯whole airflow用双fan合计16 m³/min一次；纯水H166只做最大公开温度筛查。8.010–8.991 kW总热不等于一芯合格，分离lowT3.885–4.866和油4.125 kW仍缺真实压降、NPSHr、mixing/temperature及secondary UA；0.65/0.8 kW auxiliary是否含fan/pump未闭，不凭空抵消或重复添加。

结论是下一次共同布局的具体输入，不能证明AA3必须改形，不能宣称新主躯、完整能力或复杂Bevy任务已经验收。

## 最终同源B补充（07:53）

最终B3108件：有限材料几何1360对、包络1673对、库存37对，合计3070；不是旧3082对。源/audit/rows同SHA，HX5件已共同刚体平移。该修正没有关闭其他材料、旧功能替代、NPSHr或热问题。

- `g14_water_reservoir_shell` × `e2_dual_fluid_HX_material`：77.466 cm³。
- `g14_side_exhaust_sealed_return_-1` × `e2_oil_P_18port_header`：46.305 cm³。
- `g14_side_exhaust_sealed_return_1` × `e2_oil_P_18port_header`：46.305 cm³。
- `g14_cage_anchor_output_adapter_net_material` × `e2_dual_fluid_HX_material`：43.894 cm³。
- `g14_cage_anchor_output_adapter_net_material` × `e_right_original_to_emrax_air`：41.327 cm³。

这些B值来自最终producer同源rows的独立分类；A/B各自首5均再直接读对应源完成Boolean复算，未将局部复算冒充全部严格源或全机资格。

body最终仍绑定G13 shoulder_A `2a6126f4…`；没有采用另目录G14肩初始装配B的新可拆壳，不能继承它的安装结论。

# Gorilla G12：真实格栅与两条条件热路

先保AA3可见外表面0mm。本轮核原生开口、同工况风机/换热器资料与热量守恒，比较前全量与前低温＋secondary两条热路；没有新热路CAD、CFD、物理或安装放行。

## G11面积错误更正与实际几何

G11把 `.scratch/gorilla_internal_g_root_macro/flow_heat_screen.json` 中液压缸 `inlet_area_m2=0.0031172453105244723`（63mm缸cap面积）误作前格栅面积。G11的双口面积0.00623449、68/113m/s与free-area敏感结论拒绝，旧冻结文件保留。**G11功率、能量、480芯及热量账本不因此改变。** 同源文件真正空气gross字段是 `two_throats_gross_projected_area_upper_bound_m2=0.04590089236`；它来自两black_well全顶点AABB，不是净开口。

原C15 `appearance_c_scene.json` SHA `7a1e49f4…`，每侧黑喉内圈0..7顶点的YZ投影0.01945156m²；原11根louver的真实投影并裁到内圈，合计遮挡0.00333553m²。每侧剩0.01611602、双侧 **0.03223205m²**。没有再凭空乘一个“50%自由率”。滤网、guard、密封、非平面口的法向流通及周围真实遮挡未核。

黑喉沿−X延长72mm，前口随Z改变X，不能把allvertices X宽141mm当正交72mm管长。旧turning_plenum候选内75×121.58×235.70mm，侧矩形口约0.0176773m²/侧；rear wall在+X投影中可见是转向候选，不是外部排气。原facet的z2.150截面和ROI已实看：`native_intake_roi_and_section.png`。整个旧转角/体内出口没有证明密封、连续接到core和外界，也没有用AABB宣布freecavity。

## 同一工况的一手参考

- [ebm-papst官方DC目录2025-08](https://www.ebmpapst.com/content/dam/ebm-papst/products/compact-fans/axial-compact-fans/DC_axial_compact_fans_catalog.pdf)，printed138/139、PDF121/122。同一Ø172×51mm族的G24V曲线，表中622/760/861m³h工况分别215/215/193.7W；压力约475±30/350±25/190±25Pa是图读值，保留误差。H48V也单独核。没有把零静压152W/932m³h拼成高背压额定；guard、装入效应、完整质量仍未知，不能缩成旧90mm fan。
- Boyd4320同族：[规格](https://info.boydcorp.com/hubfs/Thermal/Liquid-Cooling/Boyd-Stainless-Steel-Tube-Fin-Heat-Exchangers.pdf)、[热性能](https://info.boydcorp.com/hubfs/Thermal/Liquid-Cooling/Boyd-4320-Heat-Exchanger-Graph-Metric.pdf)、[空气压降](https://info.boydcorp.com/hubfs/Thermal/Liquid-Cooling/HX_4320_Graph_AirSide.jpg)、[液侧压降](https://info.boydcorp.com/hubfs/Thermal/Liquid-Cooling/HX_4320_Graph_LiquidSide.jpg)。各图已实看，参数读数保留误差。每件干6.4kg、净液.844L。公开热曲线是 `Q/(Tin_water−Tin_air)`，**不是UA**；仅同一完整core与对应水/风量可比较，不能转给原35×90×195mm盒。完整尺寸/安装面仍缺，本轮没有假画已装配参照。

## 两宏观路线的约束

热量先用G11 A名义7.711kW、B敏感12.759kW；480芯典型R替代总η损失时A峰值 **8.010–8.991kW**，不叠加。G11辅助.65/.8kW已含fan/水泵/compute等假设；实际两fan约.43kW若不能在辅助账本中分摊，需要重算功率和热，不能无声额外计或漏计。

| 同工况筛查 | 双口风量m³/s | 净投影平均m/s | 同族fan与剩余未知风阻 | 两同族4320、各7.5Lmin，ambient25°C |
|---|---:|---:|---|---|
| A前全量，空气升15K | .4262 | 13.22 | G约338.5±25Pa；扣core与图误差后未知入口/弯/出口K须≤2.71，H≤3.13 | 需水入口54.0、混合出口46.6°C，仅条件比较 |
| A480典型R低压，升15K | .4970 | 15.42 | G/H只约100/109Pa；K余量约.36/.41，没有证据旧转角能做到 | 水约56.5→47.9°C；风阻先成为挑战 |
| B前全量，升15K | .7053 | 21.88 | 每fan1269.6m³h超过两参照零压风量；拒绝这个fan pair | 超出公开thermal airflow图，不外推 |
| B前全量，升25K | .4232 | 13.13 | 气侧接近A，但不能只提高空气温升就过 | 水73.2→60.9°C超过现EMRAX LC入口≤50°C条件 |
| 前低温3kW，升15K | .1658 | 5.15 | 风量在公开曲线低流量区，但功率表没有夹住此点；实际PWM/工况功率未知 | 水45.8→42.9°C，coldplate/内部温差尚未合格 |

阻力按 `ΔPcore(Q)+ΣK_i ρ(Q/A_i)²/2`，各真实截面必须分别计；表中K仅统一到净投影的条件总预算，不是测得的C15阻力。双侧0.032232m²投影开口、75mm转角及core/fan均要重建连续密封和渐扩，不继承旧air ducts connected。

**路线1：前双格栅承担全量。** 保见面，重建隐藏渐扩与较大完整core/fan，pull fan后由独立密封侧/背出口排到外界。油经完整油水HX，与电机水套、四battery冷板、compute/驱动冷板在有明确泵、阀平衡、脱气和维护的水路汇合。A名义有条件热头；480低压典型R的风阻余量很小，现有旧转向不通过。不能据两来源未装配就宣称前面必须扩大。

**路线2：前格栅承担低温电机/电池/compute，侧背或髋secondary承担较高温油侧。** 前3kW只是初分配问题：A剩4.711、B剩9.759kW；A480低压cell热可能使前低温负担超过3kW，必须按真实热源重分。secondary保完整油水HX、高温水环、泵/膨胀脱气、core/fan、进排风与供电，压力侧隔离，不把21MPa油直接送到低压水core。建议下一CAD预留secondary face .04–.10m²、core深.04–.08m、fan/plenum/guard深.08–.18m作为**设计问题范围**；自身UA、尺寸和整机fit未证，液体/功能件未知不零计。可先使用原隐藏空间，但若要新可见开口，必须出具体候选四视给用户，而非本轮擅自采用。

ambient25°C是计算条件。在35°C，前3kW同族参考出口会上移到约52.9°C，已超旧电机水入口50°C条件；需要重做热域/流量/完整core或明确环境运行域。12.482L水约52.17kJ/K，只能存热：持续3kW亏欠会升温约3.45K/min，不能当稳态散热器。

## 完整功能、管路和下一出口

JSON保留原热路实际29件（core/fan/8air ducts、pump/reservoir/fill、14水管等，按真实源字段计）及九完整energy/pump/HX/compute/screen组的原成员/质量/owner，全部是旧context且未接通。旧两个35mmcore、25mm90mmfan不是永久约束，也未被缩放成官方件。

同族两core并联各7.5Lmin，共15Lmin；现两EMRAX LC最小分支共12Lmin已占大部分流量。电池、compute、油水HX还需真实串/并分配、温差、压降和水泵PQ；不能把都“6Lmin”写进串联却给每件相同冷入口。旧6mm半径是占位外径，不证明内径；假设8–10mm内径、每支7.5Lmin，速度约2.49–1.59m/s，直管、弯头与同族水core压降还需相加。油/水库存分开一次计，液体不能当承力实体。

下一共同布局先核路线2或真正更完整路线1：实际每热源端口和body owner→真实液管/接头/软动圈→泵/脱气/HX→core/fan→进排气，给pressure/UA/功率与质量空间账本，并与主躯/肩/电池同版材料、运动和工具排他域共同检查。没有完整尺寸和实际端口时只保unknown；外形变化的必要性目前未被证明。

`arithmetic_verification.json`独立核39项SI守恒、净投影与同源身份，0数值失败、0源hash变化。它只核计算，不关闭pressure/UA/装配红线。

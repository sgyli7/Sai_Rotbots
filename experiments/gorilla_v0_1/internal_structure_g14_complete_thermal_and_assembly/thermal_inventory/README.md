# Gorilla G14 完整散热功能与液体库存（条件设计输入）

此轮读取冻结G13 B `299582c9…`，补齐一整块4320的制造商尺寸参照与水泵曲线。它不重做机身、不改变原甲、不认可G13当前安装；G13整装碰撞失败仍保留。根线程决定下次共同布局。本目录最多比较两条热路线，不把器件来源核实、粗温度筛查、安装通过和持续热能力混为一项。

## 完整器件与接口

- **4320**：历史制造商Lytron目录printed51明确584×305×64 mm（含直管，未加旧Caravel风机），主body图线510×277 mm，直管OD12.7 mm、伸出53 mm、竖直间隔48 mm、下管离底板129 mm。原图全plate/body投影0.178120/0.141270 m²仅gross上界，未给净翅片开口。管的depth datum、完整装配孔坐标和现版公差仍待核。2003目录是制造商原始出版物的镜像，不能称当前正式CAD。[原始尺寸目录](https://theelectrostore.com/content/datasheets/Lytron_2003_catalog_heatexchangers_45-51.pdf)
- 当前Boyd2019 BC2019.7资料给4320G10干质量6.4 kg、水腔0.844 L、316L水路与铜翅片。测试压力不等于机器人工作压力。热图给的是`Q/(入水温−入风温)`，不是UA；不移植到G13旧180 mm安装预算。[当前系列资料](https://info.boydcorp.com/hubfs/Thermal/Liquid-Cooling/Boyd-Stainless-Steel-Tube-Fin-Heat-Exchangers.pdf)，[4320热图](https://info.boydcorp.com/hubfs/Thermal/Liquid-Cooling/Boyd-4320-Heat-Exchanger-Graph-Metric.pdf)
- **172风机**：catalog printed139完整body Ø171.5±0.5×50.8±0.3 mm，安装圆162 mm、孔4.3 mm；172×51是外形参照。guard、插头/引线、支架、密封板和工具空间另保留。原压力图ISO5801A无guard，不能套到装完护网/弯风室的流量。风机质量未闭合，未当0 kg。[完整DC目录](https://www.ebmpapst.com/content/dam/ebm-papst/products/compact-fans/axial-compact-fans/DC_axial_compact_fans_catalog.pdf)
- **冷却水泵参考EWP80 alloy #8109**：官方2023目录p11给35 mm双barb、前body127 mm、出水端到轴94.56 mm、轴向105.43 mm；因安装耳整体datum未完整读出，用140×170×120 mm明确自定保守stock，不伪称精确OEM包。裸泵1.025 kg（目录同时印2.03 lb，与g字段矛盾留档）；12 V/最大16 V，最大电流7.5 A@13 V不是指定工况功耗。p6曲线20/40/60 L/min约43.7/34.5/23.5 kPa（读图±2 kPa，曲线电压条件未写）。控制、35 mm到各支路缩接、支架、保险线束及NPSHr另缺；没有供应选定。[制造商目录](https://daviescraig.com.au/media/2576/1688618225.CatalogueV8Small6-July-2023.pdf)

`reference_stock_package_scene.json`提供可编辑局部SI外包络：完整core、两完整fan body、非零适配/guard/connector/双前plenum/后排风与工具带。所有stock明确不是OEM实体材料或安装CAD，不能拿其filled box当实际净金属碰撞。整机的实际摆位由body作者另做。没有将历史250 mm Caravel孔位当172风机直装。

## 两条热路线

G11A30分钟设计问题的480-cell典型R热**替换**原ηtotal电池损耗后，另计实端到母线ηDC=.98的0.389416 kW，原ηtotal电池项不重复保留。总峰热8.010–8.991 kW；油路4.125 kW，低温电机/传动/电池/计算及辅助分摊3.885–4.866 kW。新fan/pump功耗是否已在0.65 kW aux中分配未闭，不能再重复加入，也不能当全覆盖。B是高并发敏感性12.759 kW（油6.750），不是480-cell完成60分钟额定。

| 路线 | 完整功能 | 条件筛查与缺口 |
|---|---|---|
| R1 共用低温水路/一完整芯 | 两EMRAX、所有rotary、四pack、compute/功率板及油水HX；一完整4320+双前入/双fan/后排 | 最高公开点H166 W/K、入水15.1 L/min、整芯总风16 m³/min时，25°C环境要使回水≤50°C仅约4.928 kW；35°C仅2.957 kW。8–9 kW全部低温散掉在此域失败。没有因失败要求AA3外形扩大。 |
| R2 低温主路＋热油独立水路 | 前入口支持一完整4320低温主路；油回流经真实oil-waterHX接独立hot-water pump/secondary exchanger/脱气与保护 | A低温3.885–4.866 kW在25°C最高公开点存在条件讨论域，35°C不足。hot-water Tin70/环境25时secondary需H约91.7–150 W/K；油水HX还需UA/LMTD、压力与污染隔离核查。副芯可用第二完整4320参照或声明未知定制完整芯；不能拿未定180 mm盒继承额定。 |

上述50°C是EMRAX数据条件入口界。QTL等65/15.3 Nm热额定的20°C mount、battery可接受cell/水温、接触热阻、hot-water实际温度均未验证，不能把50°C统一当全机器件许可。两fan的合计流量只在一芯热图上使用一次；没有“每fan各用一整芯曲线”的翻倍。最大公开点未证明两风机在现有plenum/guard压降后还能达到。Boyd热图与本温度公式使用纯水热容率`QL/min/60×4180 W/K`（ρ≈1000 kg/m³），只保留公开纯水参考；G13/G14肩腔粗算另有ρ1050、cp3700的混合液假设，而body全局water库存仍ρ1000。这三者不是已选同种冷却液。配方/温度物性、质量、压降和H曲线修正尚未统一，不能把此纯水H166直接给乙二醇或真实肩支路使用。

现有27目标的59 L/min来自旧custom分配：18rotary共36、EMRAX12、HX6、compute1、power2、四旧pack2。这些分配不是额定且可以重新设计，但不能只保EMRAX12便说所有功能已冷却。新一芯串入整59 L/min时资料缺压力/热图（液压压降图最高约11.36 L/min，热图最高15.1），不外推。将core另设支泵/旁路要真正列新增泵、混水/温升与保护，不能暗中接成已通。

G13新肩4 mm两个流口在旧3.3 L/min假设下流速约4.377 m/s、动压9.58 kPa；仅两口各K1–4的自定敏感项就是19.2–76.6 kPa，尚未计弯头/水套。EWP80参考在完整59流量附近只有约24 kPa，不能宣称旧分支一泵可供。`pump_pipe_pressure_sensitivity`记录不同ID的Darcy+K粗算；实际K、分配阀、芯体/水套/滤器压降及扬程工作点仍红。

## 库存从空间派生

原E2实际源有64水管段中心线71.491 m、119油管段75.089 m，已把每段ID/长度/圆管体积列入机器JSON。它们是旧路径输入，不代表新G13已连接。冷却水原生union合计12.482 L（包含原器件/旧reservoir），油外部union12.640 L、油水HX水腔0.9239/油腔0.8883 L。新四pack通道实画仅0.009869 L；不能拿旧pack旧水腔继续累加。

新完整支路线预算保留长距离drive supply/return的45–72 m，加trunk/pack/compute/hot-HX等，ID与长度敏感推得管液**1.847–8.589 L**；这是待新同源路径替代的空间预算，不是已连管道或全水库存。再加Ncore×0.844、实际HX水腔、四pack小腔、真实电机水套/泵/阀/compute容积及脱气装液，才得Vfill。未知腔体不零计。水膨胀1–4%、气腔20–35%仅设计敏感假设，实际水/乙二醇、冷热压力与吸入口净正压未闭；不能把此范围认证为材料事实。

F1十四实缸的rod×stroke最大装液摆量合计0.977589 L；缺四缸另有0.130764 L数学候选量，实际腔体未知。每缸cap/annular扫掠也保留，dead chamber/活塞/装配姿态不能靠扫掠量补全。油总量应为实际外部线/阀/缸/油水HX加工作tank fill。工作fill需覆盖吸入口、行程摆量、回油脱气、accumulator和倾斜/温升；45–60 L/min回流、1–3 s自定脱气敏感缓冲0.75–3 L，不能当已证所需停留时间。

G13油箱内30.369 L、水箱内12.955 L只是几何容积，30/12.482 L是once全系统代理。不能既让整库存都在tank又加外部fluid。按旧E2外部油12.640分配，30 L总库存仅剩tank17.360 L；新分配还会变。原生流体代理未构成实际液路装液/NPSH证据。报告没有偷偷删30 L，也没有把它作为永久最低箱体。

## 下一次真实共同设计出口

先选主低温+hot分区，按新肩口与所有drive水套定支路，再给真实headers、冷板、泵扬程、吸入口/脱气、完整4320端口及sealed plenum/后排风；重新计算每段流体库存与热/压降，并核装配/维护/外甲交。新增副芯的尺寸/质量/UA仍缺，不能通过“定制”黄线绕过。G14不放行持续热、完整整机质量、驱动额定或AA3审美。

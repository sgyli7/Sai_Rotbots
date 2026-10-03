# F 双向保持与紧凑电控模块来源核查

当前18个自建保持块的实际已列质量范围101.887946/113.208829/135.850594kg；这是现有净钢体布局，尚无完整压力/保持额定。**113kg不是双向保持功能的物理必需下限；也不能直接将现有库存改为某个目录合计。** 本报告不选定采购，不修改冻结模型。

|真实完整阀芯＋双向block参照|质量|正式图纸包络/条件|流量与压力分别记|
|---|---:|---|---|
|LHK22G-21|0.85kg|98×49×60mm，包括40mm spring及最大19mm调整投影；不含外接头/安装支承|20L/min；family load≤320bar，setting≤400bar，高压弹簧201–400bar|
|LHK33G-21|2.4kg|125×65×80mm，不含外接头/支承|60L/min；family load≤320bar，本型号setting≤360bar|

[LHK官方D7100 02-2025/1.0](https://productfinder.hawe.com/downloads/D7100-en.pdf)，页1/4/9/10/15/33/56。-21为载荷方向改变的双阀，双方可独立设定；0.1kg是裸安装kit，不能冒充0.85kg整阀块。厂家限定LHK用于不易振荡的工况；双缸机器人适用未知。预设应高于最大负载压力，控制/回压受回路影响；串联阀片泄漏可能累积pilot压力而造成creep，主阀中位泄压行为必须匹配。-21不等于另含shock或所有失效保护。

[LHDV官方D7770 08-2024/1.0](https://productfinder.hawe.com/downloads/D7770-en.pdf)，页1/4/7/9/10/16/27/38：LHDV33-21完整twin3.5kg，有特殊减振；-21WD3.6kg为不同功能。family setting≤420/load≤350bar；D/E码25/16L/min、setting50–350bar、允许return10bar；额定最大流量fully-open仍可有50bar压降。当前版本要求preset≥1.2×最大负载压力，不能继承2014版1.1。图p27主长175、宽88、body高70+topbolt10mm，左调整凸出未给全尺寸；未得到exact完整AABB。无权由减振/零泄漏描述推出机器人安全保持或稳定。

[LHT官方D7918 05-2025/1.1](https://productfinder.hawe.com/downloads/D7918-en.pdf)，页6/9/17/26：LHT21P-26为2.5kg双路manifold件，图示99.5×90×59.5mm，另10mm螺栓进入baseplate；外baseplate/油道/接头质量未含。建议flow≤28L/min。LHT同样有不易振荡的适用限制，不能作为更适合机器人振荡的证明。

作为拒绝参照，[EDM-VB官方RE18301-43/02.2016](https://www.hydraforce.com/globalassets/2.-products/product-pdf-override-files/re18301-43.pdf)的1.2kg包含铝block＋两阀，40L/min、pmax250bar，要求preset≥1.3×最大load。若**真实最大load**为204bar，所需265.2bar超过此参照；204bar供压不能自动代入最大load。其mating/base/支承也需另计。

## 同版本实际五姿态流量

绑定E2a scene6039922d…和五姿态statics；独立从真实A/B、parent/output transform与关节轴算J，再由相对旋转求q，仅选限位内允许瞬时±方向；18缸×5姿态全部q在给定范围。Q=area×|J·qdot|，供回使用真实缸径/杆径。不引用旧宏观眼点，不调用root LP/evaluator。每格为五姿态允许方向内max供/max回，L/min；两项可能来自不同瞬时方向，不可拼成一条轨迹。

|缸|0.1rad/s|0.3rad/s|
|---|---:|---:|
|waist_pitch_pair_0|3.7811/3.7811|11.3434/11.3434|
|waist_pitch_pair_1|3.7811/3.7811|11.3434/11.3434|
|left_hip_roll_pair_0|3.1233/3.1233|9.3699/9.3699|
|left_hip_roll_pair_1|3.2911/3.2911|9.8733/9.8733|
|left_foot_roll_pair_0|1.3666/1.3666|4.0998/4.0998|
|left_foot_roll_pair_1|1.3960/1.3960|4.1879/4.1879|
|left_hip|1.1746/1.1746|3.5238/3.5238|
|left_knee|4.0693/3.4163|12.2080/10.2490|
|left_fold|1.5826/1.5826|4.7478/4.7478|
|left_ankle|2.4503/2.4503|7.3510/7.3510|
|right_hip_roll_pair_0|3.1233/3.1233|9.3699/9.3699|
|right_hip_roll_pair_1|3.2911/3.2911|9.8733/9.8733|
|right_foot_roll_pair_0|1.3666/1.3666|4.0998/4.0998|
|right_foot_roll_pair_1|1.3960/1.3960|4.1879/4.1879|
|right_hip|1.1746/1.1746|3.5238/3.5238|
|right_knee|4.0693/3.4163|12.2080/10.2490|
|right_fold|1.5826/1.5826|4.7478/4.7478|
|right_ankle|2.4503/2.4503|7.3510/7.3510|

最大单port4.069336/12.208009L/min，流量数值均低于LHK22的20及LHDV-E的16目录参照。只是这些姿态的瞬时流量条件；不是contact兼容运动、全路径最大值、负载压力合格或同时可达速度。主泵总流量、真实载荷正负功、减振/阀控速度、爆管失压动作、回压及补油仍红。保持失去pilot的正常闭合机理不构成所有失效都安全的认证；污染/座损/控制泄漏/缸内泄漏/支承损坏必须另审。

## 完整库存候选范围与损耗

18个LHK22目录block为15.3kg，18个LHDV33-21为63kg；均非含安装的整机最终库存。`flow_and_installation.json`另列自建有限体积：每模块4钢接头shell（OD24–32/ID8–10/L25–35mm）、一个4–6mm折弯支架和2颗有限M6包络。按7850kg/m³真实净体积，加项0.455271–1.202042kg；LHK22 core＋这些金属库存为1.305271–2.052042kg/模块，18份23.494887–36.936755kg。这是**不含未知密封/真实螺纹/安装面强度/保护外壳/反馈附加的条件材料参照**，不是完整module上界或最终30kg总量。LHDV G1/2的接头支架也不能沿用小口径最小值。未取得完整OEM CAD；原厂dimensioned图可供root重建标尺，真实装配和油库存需重新布置且仅计一次。

油侧损耗应分实际segment算Δp_bar·Q_Lmin/600kW；counterbalance降低负载时的背压、全开参考压降、directional metering和主泵余流分别处理，不能按所有流量×204bar烧掉或把参考全开压降当每个task定值。安装preset、各腔实际loadbar与T/returnbar分开，双缸配力、热/惯性压力和面积比仍未闭合。

## 电控主阀补充（保留原阀数）

[Parker官方D1FB MSG11-3500/UK，25.03.2024](https://www.parker.com/content/dam/Parker-com/Literature/Industrial-Systems-Division-Europe/Catalogues/Industrial-Valves-UK/03/D1FB-UK.pdf)，页3-4/5/6/7/12/13：C型为完整双线圈4/3阀；OBE包括驱动，2.9kg、222×46×125mm。P/A/B≤350bar、T≤210bar；OBE18–30V/max2A，100ED但coil可150°C。20L/min规格在**每metering edge5bar**，非在零压降；非对称缸流量还要核functional curves。matingconnector明确另配、质量未公开，baseplate/四螺栓/接头/电缆安装/隔热不能删。不是保持阀，中位spool泄漏和故障断电需完整回路解释。这里没有用2.2kg外置驱动版尺寸拼成2.9kgOBE总成。

此源无长手柄但保manual override功能。18阀或13共享阀的选择未做；本任务没有减少阀数。30V×2A=60W为供电上限乘积参照，不是测得持续发热；OBE局部供电和封闭机体热条件仍未知。

## 文件和复现

下载PDF仅在ignored cache，未确认再分发许可，不入Git。三个HAWE源原字节SHA见sources.json。Parker与EDM官方PDF可浏览核查，直接cache分别403，raw hash为null；Bosch扩展源原链接cache404，已停止扩展，未绕权限/注册，也不合成资料。

复现：`.venv/bin/python .scratch/gorilla_internal_f_holding_sources/compute_flow_and_installation.py`；sources.json逐源URL/version/page/hash；flow_and_installation.json保留90组逐缸姿态与全部允许方向，manifest.json绑定全部输入/输出。未进行选型、真实装配放行或采购。

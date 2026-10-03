# Gorilla G17 热/液体联合工作点（有界候选）

最终算式源为 `joint_workpoint_v3.json`（SHA c43cf2342734b9161b3a09f0ca80c61b1d4acc620ce3cfca008b81a9b49fb207）。`build_joint_workpoint_v1.py` → `extend_joint_workpoint_v2.py` → `finalize_joint_workpoint_v3.py` 保留每版源；`verify_joint_workpoint_independent.py` 不导入 producer，9项独立算式/来源检查通过。数据与图仅为同一候选的参数诊断；不是连续能力、安装、整机物理或审美放行。Root 决定下一整组路线。

## 直接影响整机的门禁

- **单150压头不足。** 59 L/min、四0707并联各14.75，公开暖芯图26–34kPa，再串188支路20kPa、实际规格ID10软管、短ID32主管及自定过滤分配余量，乐观模型也约59.67kPa，大于单150图读38.84kPa。候选A拒绝该同工况。
- **双150未放行。** 同流串联参考77.68kPa。35°C冷液敏感：平滑湍流假设67.47–84.55kPa，层流假设96.42–122.42kPa；实际芯体流态、冷泵曲线、NPSHr、第二级壳/吸入许可未公开。不能把两条图相加当符合物理。实际body低液面Z2.20135、stage0参考中心Z2.355，有153.65mm吸高。条件NPSHa7.48–12.10m并不等于NPSH通过。第二级33.21–65.21kPa(g)吸压；500kPa爆破压力不能代替连续壳压许可。
- **未建真实转子风路。** 候选共享两低温芯风道，各6.5m³/min。原30min问题峰值每个188轴输出7.5kW：每路3经转子、3.5旁路后复合过芯；高并发每个13.125kW：5.25经转子、1.25旁路。同一风量只计一次，实际body未画分流/护网/风道/平衡及独立排风。源172风机6314/2TDH4P24V的622m³/h、475Pa、215W点按理论相似缩至6.5m³/min得到186.74Pa/53W，**不是公开新PWM额定**。保留六风机总1290W供电上限，未给电池节能credit。四芯都挤过原前口的压力敏感失败不证明外甲必须改；需要前双格栅与后/侧真实封道/排风分配。
- **200V峰值入口超源条件。** 同任务损失守恒，35°C环境、50°C物性ROM与未核冷H，A低温入口288V约48.17–49.69°C，200V约51.43–53.33°C；高并发200V约68.05–72.01°C。188公開50°C入口条件无法因此放行。平均/自定热容量不代替持续峰、器件温度及450s阶段验证。50°C冷液校正仍是未知液侧热阻份额的ROM，不是保证下限。
- **30min储能不足。** 480颗80s6p最小7.44kWh、SOC75%、原任务占空、六风机/三泵公开电输入上限和其余0.5kW条件aux，A需要7.475–7.757kWh，未含额外保留余量。10%余量时间界25.90–26.87min；提出25min作为可继续设计的问题，尚非runtime额定。若30min必须，低电压上限加10%余量需至少8.619kWh；80s7p560颗≥8.68kWh仅是下一完整pack研究入口，当前body仍480，不能零计额外BMS/保护/冷板/空间。

## 同工况与完整功能范围

| 项目 | 本轮参数与来源范围 | 尚需闭合 |
|---|---|---|
| 低温流量 | 18自制冷板×2 + 2台188×6 + 4pack×2 + compute3 =59 L/min；4芯并联14.75/只 | 自制流量不是OEM最小；每支实际管长/压降、阀平衡和最大分支 |
| 热回路 | 完整0714整芯13m³/min、10L/min，图读H约153W/K；A峰热供/回约57.21/64.25°C | 这是71.1°C EGW图的条件延用，50°C校正/HX真实UA/压差仍红 |
| 电输入 | 四low+二hot完整172风机上限1.29kW；低2×150=.26kW、热80=.0975kW；其余0.5kW | 12V泵/24V风机与200–336V母线的变换、实际输入P/Q、保护/回馈 |
| 热分摊 | 原A低液平均2.80–3.22/峰4.17–5.32kW，热液平均1.858/峰4.2225kW；B低液平均5.60–7.41/峰7.97–11.24，热平均4.398/峰6.8475 | 原motor+inverterη=.9只是任务假设；LC转子约1/3仅适用于电机损失，v3把motorη.92–.96与ηinverter=.9/ηmotor分开且总热守恒 |
| 电机/TIM | QTL输入13.73–16.48Nm对1236Nm输出，在同铜耗模型31–44W；1570Nm重力敏感50–72W | 20°C安装面额定不能沿用；实际RMS、转速铁耗、制动/停机及齿轮持续边界 |
| 自制冷板 | 独立QTL尺寸参数：内D221/外D239、69mm轴向；32条3×3mm半圆并联通道、1mm肋/3mm壁、8mm自制端口 | 不是当前肩源、不是OEM缩芯；热边界Nu2–3.61、曲率/入口/汇流/TIM/压力疲劳未知；QTR小冷板未建 |

既有完整五热包、六风机、三泵、两脱气容器、过滤/旁通/调压/控制/换流保护、油水隔离HX、冷板与维护占位以G16逐功能库存保留。stock不等于已经接通。自制通道断面图是参数图，不是新CAD或外观权威。所用Darcy方形层流公式为独立解析模型；新3mm/Re132–196不在所缓存论文244–974µm/Re230–6500实验范围内。Nu不是已选真实热边界的保证值。现有OEM端口不改；8mm只用于未来自制接口。

## 当前body与液体占位

只读body `.../gorilla_internal_g17_connected_cage_layout/b/scene.json.gz` SHA52eb6bb53bb84cfacf24fbe4f2f4f4e35b4a97d4cef90729fc3ff9f0382c2756，2530件已锁几何；两150各140×190×120及30mm间隔/ID32连接、完整270mm堆栈是reference安装stock，不是压力许可。

实际油箱净容量10.716264L/工作7L；低脱气容器2.352504/工作1.2L，热1.741464/工作0.8L。新实际routes尚未建。G16旧工作fill2.608/4.108/6.608对应的global油范围不能套到当前7L；保原外部proxy10.151/12.248/15.046则总油17.151/19.248/22.046L，2/4/6%热胀与20/27.5/35%热气腔所需容量9.179/10.717/12.804L。中值欠0.875mL只作条件敏感，不能把理想容量当精确制造容差；高值明确不足。14实缸+4缺缸/实际行程回油/去气/斜姿态吸口仍红。

冷却液原route/device候选proxy为12.084/14.317/17.550L，含脱气工作2L各一次；它不是当前新routes实际需求，也不是12.482L常数额定。换成新冷板/泵管后必须按旧功能exact退休、新腔体及管长逐项重算。DOW50vol%典型物性、历史ES50/50试液、body水库存ρ1000不是已选同配方，质量与热曲线不能悄合并。

## 来源与复现

[EMRAX官方V1.6](https://emrax.com/wp-content/uploads/2025/03/EMRAX_Users_Manual_v1.6.pdf) printed17/18公开188流量6–11L/min、20kPa@6、80mL、入口≤2bar(g)、ID10软管、LC转子空气条件；文件版本修订26/04/2024，官网路径2025/03。

[Davies Craig官方2023目录](https://daviescraig.com.au/media/2576/1688618225.CatalogueV8Small6-July-2023.pdf) p6/7公开150整泵曲线、12V#8160、最大10A@13V、爆破500kPa；[官方串联FAQ](https://daviescraig.com.au/blog/davies-craig-electric-water-pumps-common-questions-answered)仅说明另一115示例能串联，不是150冷态/NPSHr/第二级壳资格。

[ebm-papst官方目录](https://www.ebmpapst.com/content/dam/ebm-papst/products/compact-fans/axial-compact-fans/DC_axial_compact_fans_catalog.pdf) 与[官方相似定律FAQ](https://www.ebmpapst.com/us/en/support/faq.html) 分别提供原全尺寸风机曲线和理论缩速关系。guardless源条件与新封道不同。

历史制造商ES目录镜像、DOW手册镜像、QTL/QTR官方缓存与原哈希沿G16保留；不是现版公差CAD。新增微流道原论文缓存来自大学作者页面，TLS链验证失败后重试关闭TLS，receipt显式记录，不能称已验证原出版商认证。另热关联式原论文PDF403失败保留记录；没有借失败下载捏造精确OEM能力。所有原源/Git/外甲/G16冻结均未改。

执行顺序：`capture_locked_body_v1.py`、`build_joint_workpoint_v1.py`、`extend_joint_workpoint_v2.py`、`finalize_joint_workpoint_v3.py`、`verify_joint_workpoint_independent.py`、`draw_parameter_section.py`。复現需要原source exact字节；旧版本保持历史不得覆盖，执行输出应写单独重放目录再对照。

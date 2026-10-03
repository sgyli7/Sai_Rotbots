Gorilla G19：完整肩臂驱动架构与差异化电气入口

本轮只比较两个完整架构，不生成第三个 G18 壳体，也不修改任何已冻结源。A 为官方组件集＋自制共同承力壳，B 为完整近端驱动库＋跨串联关节的远置传动。两者均未选定、未完成新 CAD 装配，无法给出全机质量/COM/I或持续能力。AA3上半身可见面变化为0，宽厚闭口承力原则保留；隐藏壳结构允许下一版重建，可见改形要同源提出供审美审查。下半身仍为历史占位，不对应新版原画。

源是G18根组合 `9873e9db2a6a5c20d9466216577c69a6c7afcab9c2db4ce22b88b4181c40e694`、功能重力账 `23990d4f78d7324f66fa26d9f3b7e4e9bdd781dbee812ec380ed815b1b406de9`。2247条完整功能质量行按真实候选轴树取后代；8轴中立6D复算误差0，组合FK与原G18实际52body变换比较误差0（实际匹配数见function_scope）。422项owner未映射另列，已选非法/未知质量不当0；已知数值含COM代理，不能成为总需求上下界。组合工况本身也来自几何已拒绝的诊断，不称可执行动作。

首表 `first_comparison.md` / `first_issue/` 保存原字节。`requirements.json` 为当前源轴、两种姿态、各轴low/nom/high已知6D、手任务力/力矩六维系数和0/25/50/100kg条件敏感性；原动作域/SI未更改。`function_scope_contract.json` 保留200条当前肩臂功能行和准确member IDs，本轮退休ID为空、质量credit为0。嵌套roll/yaw/elbow重力不可再加到pitch子树；两手→腰查询只汇两pitch子树一次，不含固定躯干/OEM未分配项。

| 架构 | 输入/输出和真实反力链 | 同功能完整预算 | 当前主要门禁 |
|---|---|---|---|
| A 一体共同承力壳 | torso宽节点→CS固定壳/输入双支承→motor/WG→FS输出；外部载荷走输出双支承和宽闭口输出承壳，再完整串接roll/yaw/upperarm/elbow。齿轮传转矩，不能让WG/FS吃外部弯矩。 | 基线官方8组件32.6kg＋完整8电机21.278kg；16个输出轴承参考18.4kg另计。6–8mm条件钢外环＋两端环板有限材料预算77.16–100.92kg，未含功能孔/真实节点/支承/预紧/密封/工具，不是新CAD质量；完整总计null。无嵌套轴向预算pitch264.5mm、其他214mm。 | 支承排列/真实CS/FS配合和安装、壳与下一DOF的有限连通、轴承压力中心、gear循环额定、冷却和初装/卸载维护全未关闭。 |
| B 近端驱动＋远传 | torso宽节点接完整motor/gear/brake/driver/cooling库；pitch直接远传，roll跨pitch转接，yaw跨pitch+roll，elbow跨pitch+roll+yaw。每个输出保独立支承、输出encoder/负载保持及宽闭口上臂承壳。 | 8完整2UH箱＋8电机116.478kg，只有齿箱外接圆柱gross28.425L；移动不是删质量。远传轴/带、差动/转接、张紧、防护、局部输出保持/支承尚无合格完整质量，故总计null。 | 必须建立真实耦合矩阵、关节运动中的传动路径/扫掠、刚度/预紧/反力、驱动库与全部机电模块共布；不能以根库服务容易称全臂服务通过。 |

[CSG50组件集](https://www.harmonicdrive.net/products/component-sets/cup-type/csg-2a/csg-50-100-2a-gr)为Ø170×64mm/3.2kg，[CSG65组件集](https://www.harmonicdrive.net/products/component-sets/cup-type/csg-2a/csg-65-100-2a-gr)为Ø215×83mm/6.7kg，均为真实产品，未切小旧2UH。保持成套CS/FS/WG；完整质量和内部惯量不能随意拆给固定/转动owner。官方[组件安装指南](https://www.harmonicdrive.net/_hd/content/documents1/CSG-CSF_Component.pdf)要求输入、输出各有双轴承隔离径向/轴向外力、轴向固定、相应预紧，并核WG轴向力/CS同轴度/FS动态净隙。不能继承2UH集成轴承Mc。自制壳是可定制范围，尺寸、材料和支承寿命仍需原生验证。

B的75mm节圆下，示例组合+50kg右pitch有约10.21kN张力差；紧松边预紧会改变轴载，不能把张力差当实际轴反力。自身有限管材敏感性见`architecture_comparison.json`，包括真实截面、密度、长度、扭转角；没有将花键/CV/轴承/差动忽略后给总质量。应按[官方同步带设计方法](https://www.gates.com/content/dam/documents-library/catalogs/powergrip-gt3-drive-design-manual-en.pdf)确定服务因子、齿数/啮合、带宽、张紧、轴载；具体系列额定未知。各父级运动进入`q=H(theta,parentq)`与虚功`tau_motor=H^T tau_joint`，恒长直线跨多轴并非完整传动。

电机/比率必须差异化。下面是下一原生完整总成可选输入，不能从已知重力直接选型通过：

| 轴 | 架构A的官方候选 | 架构B的完整候选处理 | 还需关闭 |
|---|---|---|---|
| pitch | CSG65-100-2A＋完整QTR160-34Z；保留QTL210-65N/ratio100或80作高Ke反例 | 现完整CSG65-2UH保持；若改QTR34Z须新完整输入支承/adapter/制动/冷却/driver，不裁箱；近端传动损失另加 | QTR较小电机的真实持续/瞬态和未知质量动态需求；不能以N→Z描述为QTL换绕组。 |
| roll | CSG50-100-2A＋QTR160-34Z；ratio80只是速度/扭矩参考 | 完整CSG50-2UH＋QTR34Z/真实远传和支承 | 50kg组合已知力矩较高，80比L10参考裕量更低；耦合/动载未知。 |
| yaw | CSG40-100-2A＋QTR160-17Z为真实较小组件候选，完整自制支承/壳仍要建 | 主B可保完整CSG50-2UH并采用QTR17Z；另换40组件必须把整自制库壳/支承算全，不能推裸组件为工业箱 | 345Nm目录L10只是参考；实际任务yaw力/碰撞/惯性不同于重力。 |
| elbow | CSG50-100-2A＋QTR160-34Z | 完整CSG50-2UH＋QTR34Z/整上臂远传及输出保持 | ratio80的已知组合+50kg右elbow已为L10参考1.09倍，故不优先；100比仍无动态/热资格。 |

[CSG40-100官方](https://www.harmonicdrive.net/products/component-sets/cup-type/csg-2a/csg-40-100-2a-gr)为1.7kg、L10参考345Nm，标准图Ø135×53mm（WG另一方向57.2mm需明确配置）。65/50的[80比官方](https://www.harmonicdrive.net/products/component-sets/cup-type/csg-2a/csg-65-80-2a-gr)、[50-80官方](https://www.harmonicdrive.net/products/component-sets/cup-type/csg-2a/csg-50-80-2a-gr)L10分别969/484Nm，不是100比的1236/611。目录L10、平均和峰值不同，不能简单当静态硬限或持续输出证明。

[QTR官方表](https://www.tecnotion.com/wp-content/uploads/2022/05/Torque_Brochure_EN_2-5.pdf)明确QTR16034Z为Tc15.3Nm/Kt0.93/Ke56V每krpm/Ic16.4Arms/1.613kg；yaw候选17Z为Tc4.2/Kt0.31/Ke19/Ic13.4/0.665kg。QTR34的N/Z同尺寸，而pitch由QTL改QTR是另一个完整尺寸型号。当前[QTL210数据](https://www.tecnotion.com/wp-content/uploads/2025/11/QTL210_Specsheet_EN_2.4.pdf)只列N，未查得可直接用的QTL低Ke标准绕组，不创建虚构Z。仅官方转子极惯量可引用，整电机/减速器fullI未知。

`winding_ratio_voltage.json`提供6480个限定筛查：两姿态、8轴不同候选、三质量标记、0/50/100kg、η.6/.75/.9、180/200/268/302.4/336V。用100°C电阻、真实电极对数和ωL、10%电压余量，稳态id=0电机驱动支路；再生/保持摩擦、弱磁、铁耗/PWM、温度及器件±10%未资格化。机械速度、目录平均输入速度亦不能从“电压上限”直接继承。

组合已知中值＋50kg/手、η.75时：右pitch QTL N100需要410.6V才能到0.5rad/s；电压模型在180/200/268/302.4/336V的上限分别0.210/0.235/0.321/0.364/0.406rad/s。N80须335.0V；302.4V只有0.449，336V点0.502并不代表全SOC能力。QTR34Z100同条件需要65.6V、10.97Arms，180V电压模型仍能覆盖0.5，但持续/动态/温度/原始配合未通过。原QTR电压上限325Vdc，336V需完整PWM脉冲/绝缘/夹钳回馈处理；root候选72s raw180–302.4V只消除该名义超额，不证明22.6V裕量足够或制动回馈能处理。没有更改任务推荐速度、母线或默认ABI。两个图均是计算数据图，不是新的外观/CAD效果。

冷源不能沿用QTL大板。`low_Ke_cooling_budget.json`：右pitch较小QTR34Z在上述已知条件的100°C电阻铜损约201.14W，另有铁/转子/摩擦/PWM未计。条件Rth(coil→vendor mounting surface)=0.17K/W、coil100°C时，假设其他热为0，安装面最多65.81°C；若其他热50/150W则57.31/40.31°C。局部水40°C时，实际安装面→水总Rth必须≤0.12829K/W；另热50W后≤0.06891，不能把0.17全算给冷却系统。如果局部水60°C、另热50W，此常数Rth假设已经负预算。

QTR实际OD160/H34.5mm整圆柱面积上界0.01734m²，并非已确认有效传热面。TIM0.1mm、k1/3/6和接触25/50/100%仅自设一维敏感，未选择材料；必须实际量测mount→套/壁→水、孔位隔离、流量/压损和最热点。选用差异化8电机，已知重力+50kg/.5rad/s条件铜损约533.26W；η.75齿箱电机驱动热敏感487.11W，合计约1.020kW只是该部分，未含全系统/动载/422未知和远传损失。这不是散热设计通过。

完成下一步的最小入口是A中的一个完整真实组件式pitch/roll单元：固定/输出壳和双支承→全电机/WG/传动安装→制动/encoder/driver→独立隔离水路→全件初装与卸载检修，再接下一DOF。使用本轮actual8轴、手6D系数及未知项，选定任务/速度/加速度和真实质量后才决定比率和绕组。B必须先用两轴真实转接/差动验证耦合、预紧、支承、刚度、效率与装卸，不能先移走8电机就扣重。原失效片材/细桥不能因换SKU隐去；承力壳有限连续与宽厚拓扑设计域需由真实CAD和接口重新建立，未装配不能做FE/SIMP替代验证。

本輪没做采购/FE/PPO/GPU/Git，未改旧源、下半身或外部聊天。工具缺matplotlib后用系统Python＋Pillow绘制纯数值图，失败源保留，没有修形/AI补图。官方绘图PDF和原册仅放ignored scratch，未宣称OEM许可或入库。Gates下载403/404保留于下载receipt，未冒充本地已下载。

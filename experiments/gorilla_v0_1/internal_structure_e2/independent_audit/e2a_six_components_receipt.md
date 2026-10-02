# E2a 右髋六件实际补齐只读 receipt

**六件库存漏项已实际补齐；安装几何仍有显著正体积冲突。** 绑定新scene `6039922d1ab479346dd590745b78d5e176a8ecf6a039bc734cfbfeed686516f6`，原5a9a与冻结system/structure/upper未修改。本检查只写独立审计目录。

1585 native parts /1111质量行：只增加 gear、motor、brake、encoder、controller、wire_coolant_connector 六件，所有旧native对象和旧质量row完全一致。六件顶点逐项等于左源件Y反射，faces逐项逆绕序，包络尺寸和质量范围相同；part/body owner/row均为pelvis，各closed、positive、winding consistent且只计一次。六件真实三角面独立COM最大残差 4.35e-14m，均匀proxy tensor最大残差 6.77e-14kg·m²；完整转子/输出体分体惯量仍不合格。

实际增重28.420000000000073/29.750000000000227/32.34999999999491kg，与六row独立求和残差不超过5.1e−12kg。新整机已列范围1744.314628644/1920.831576192/2205.829532015kg。各row独立重组的中值COM为[-0.035131948474,0.000291569746,1.478514843557]m；旧142个材料union几何与row均未改，原独立neutral材料复算仍适用。

限定安装筛查覆盖**这六新件对111原甲＋18个明确case/bridge/mount/adapter目标（共129）**，29对AABB进入真实manifold Boolean，10positive，0unknown。并额外核六件自身两两交集。其范围不是全机/全姿态/全部水油路已筛。

|主要实际native包络交集|cm³|
|---|---:|
|gear × 右蓝后肩边甲|30.5891|
|gear × 右白hood窗口侧边|38.2207|
|motor × 右蓝后肩边甲|2.0232|
|motor × 右白hood窗口侧边|4.4582|
|controller × 右白hood窗口侧边|25.0072|
|gear × moving输出adapter|34.4605|
|gear × fixed前annular mount|62.7244|
|controller × motor冷却case|5.6000|
|controller × continuous gear bridge|0.4571|

另gear×continuous白torso甲有0.000939cm³微小交集，单列为近几何容差诊断，不用该微小数替代上述显著冲突。六件内部gear/controller147.000cm³、gear/connector110.250cm³、motor/controller57.024cm³。

gear/motor属于来源尺寸重建的完整component solid envelope，不是厂商完整安装孔/支承/输出法兰CAD；与mount/adapter的实体重叠仍需真实接口几何闭合，不任意扣体积。控制器与连接模块也不得因同parent或OEM包络重叠就删质量/隐藏。显著原甲冲突成立于当前实际候选native几何，库存修复不等于fit通过，更不代表驱动、热、接触或承载通过。

复现：`.venv/bin/python .scratch/gorilla_internal_e2_audit/check_e2a_six_components.py`。机器可读每件尺寸/质量/owner、全部target与Boolean pair见 `e2a_six_components_audit.json`；源和输出hash见 `manifest.json`。

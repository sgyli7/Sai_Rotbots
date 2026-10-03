# Gorilla G17 串联肩总成：有界失败候选封存

B 源 `b/scene.json.gz` 是 271 件局部肩/旧框架/上臂接口上下文，另一次只读绑定新的 G17B 连续躯干；没有生成第三种几何。实际 B 钢路径为闭口 6 mm 壁、有限轴套/轴承座、宽过渡壳。新 pitch→roll→yaw 三轴树、原 A 输出/B 固定身份、完整115 mm gear/66 mm motor与roll/yaw的gear/motor/brake/encoder/controller/connector均在源中。

B 54 个新增对象的严格 signed native gate 通过；46 个自制有限金属件净质量 140.389753 kg。八个新增 SKF32212目录参考另计9.2 kg；原pitch四个目录参考4.6 kg保留。全部列出的局部完整功能规划范围319.250399/326.638639/340.723239 kg，不是全机质量或全部资源有效的已知项，不提供OEM内部均布惯量。旧22个候选替代件的规划范围70.584462/73.858989/81.585306 kg只用于对照；四旧carrier26.596829 kg及其他任何旧件均没有减重credit。各自制件和组合的真实CAD COM/fullI见 `b/own_finite_CAD_mass_COM_I.json`。

限定局部中立及pitch20°/roll15°/yaw20°/combined姿态：新自制实际材料交0；protected参考交仍34/58/52/34/64对。与新的95.7056 kg躯干frame五姿态查询仅有左右CSG65 gross×固定锚各84.009315 cm³（10条重复姿态），不是整机2530件装配合格。两个真正下游上臂接口分别75.083417/75.083384 cm³材料交，不能以同owner认定焊接。111原甲有104对交，最大新pitch桥×白肩约138.84 cm³。九组原位完整主功能成员没有新增冲突，泵filter/inverter辅助另核0；未筛全机其余功能。

四个实际停车拆卸：每侧roll沿X+0.35 m、yaw沿[-0.12, ±0.40,0]，前序移除件保留于真实停车位置且对侧对象不消失。每项12/21采样失败，最大roll39.288863/yaw304.007509 cm³。完整初装、可拆轴承杯/keeper/thread释放与工具托持仍未知，不声称服务通过。

`b/native_four_view.png` 是实际三角几何裸图；`b/original_armor_context_four_view.png` 原111甲同尺度叠图；`b/literal_native_sections.png`/JSON 为原生真实剖面，均已实际查看。宽闭口桥明显穿肩可见原甲，外观及包装拒绝；没有改原甲或把工业gross冲突归因AA3必须改形。

原 G13 A 接面多边形对比完全相同，原固定件所有原字段逐值保留。实际17个历史接口作为datum范围保存；新body实际plane查询须用body作者同版映射，不能继承旧face编号。Pitch线XZ −0.13/2.29相对旧Z2.36显式下降70mm；B完整roll/yaw模块Y向外65mm。所有负载、接触分担、回馈热、真实关节内件、压力中心/preload/螺纹/焊接和稳定SI均未核验，旧G15/旧G13载荷数值未移植。

生产来源逐项见 `producer_history_receipt.json`。A geometry producer1bb761与B444869原字节分别在a/b `producer_source.py`。B首门禁116683匹配 `check_source_before_parking_revision.py`；后续分析4818a匹配 `check_serial_assembly.py`。A第一分析producer5d2e1a原字节缺失，原第一报告及原始surface-island解释保留，不以现在脚本补造历史。原surface decompose连通说法已经由signed nesting材料分量解释纠正，不改变任何源。

可读/可合成入口：native `b/scene.json.gz`、新body原字节绑定副本、`b/joint_interfaces.json`、`b/actual_interface_contract.json`和summary精确22替代ID。集成必须从body场景移除旧pitch/roll carriers、旧DS自己的loadshell/outputadapters/carrierplates及旧两G13输出，保全部OEM功能件、机电辅助及上臂；不要叠加两个躯干context或两套G13原件。此替换只用于保存拒绝候选，不授予质量/接合/新SI资格。

下一步应回整体肩空间和真实拆装界面：保完整功能，决定宽承壳/可拆座/真实上臂面与新body域共同组织；不能第三次只挖孔移动bolt刷局部0交。全部冻结为工程失败证据。

## 根线程整组复核范围补充（未改几何）

根线程保留bodyB2530件，按22项替代名单退休旧件、加入28完整移动功能件和54新件，组合2562件。实际新/动件×all为297混合正体积对，其中22对明确有限材料；包括roll→yaw承件×原上臂各61.397 cm³、×近端前臂1.397 cm³、yaw输出×上臂75.083 cm³及多处keepers/bolts。完整组合仍拒绝；271件局部姿态0交绝不能泛化为整机0交。独立receipt原字节已保存为 `bound_root_independent_serial_and_joint.json`，其来源和哈希见summary。旧local summary/README/manifest字节另存before，不回填历史。CAD140.389753kg与signed native140.343604kg差约0.033%是圆面离散差，不是质量降低。肩末端与上臂/前臂需要整体接口架构处理，绝不再开第三CAD补丁。

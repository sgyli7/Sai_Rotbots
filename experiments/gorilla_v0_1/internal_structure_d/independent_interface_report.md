# Gorilla canonical D 腿—脚接口只读复核

本轮重新读取当前canonical整机、腿、脚源，使用actual triangles与Manifold材料布尔；未继承旧.scratch脚报告。输入快照与确切SHA在report.json。未改受控几何。

按中立脚neutral_locked与4组canonical腿T检查；另列整机neutral baseline，它与neutral T重复，不能算作额外独立姿态。所有腿姿态已root-z aligned，无二次平移。执行器fixed/rod采用各pose端点解算world mesh，未用重力body字段错误转动。

阈值：正材料相交>1e-10m³；AABB仅1e-9m预筛。密度明确的候选金属进入材料union，参考轴承包络单独列出。union只避免重复计算交体积，不证明焊接、刚接或额定载荷。

|姿态|侧|真材料对|参考包络对|父材料∩root脚净cm³|父材料∩踝子输出净cm³|
|---|---|---:|---:|---:|---:|
|main_neutral_baseline|left|7|6|75.740886|5.974053|
|main_neutral_baseline|right|7|6|75.740886|5.974052|
|neutral|left|7|6|75.740886|5.974053|
|neutral|right|7|6|75.740886|5.974052|
|crouch|left|7|6|75.714311|4.862191|
|crouch|right|7|6|75.714311|4.862193|
|forward_manipulation|left|7|6|75.714310|4.862193|
|forward_manipulation|right|7|6|75.714311|4.862193|
|deep_crouch_rejection_probe|left|7|6|75.732383|3.893976|
|deep_crouch_rejection_probe|right|7|6|75.732383|3.893977|

中立实际材料交点（逐件、未用参考轴承当材料）：
- left_ankle_fixed_bearing_housing_0 → isd_continuous_main_arch：27.977787 cm³；bounds=[[-0.14265038073062897, 0.3659999966621399, 0.20499999821186066], [-0.02500000037252903, 0.3840000033378601, 0.25932076573371887]]
- left_ankle_fixed_bearing_housing_1 → isd_forefoot_brace0_fixed：17.472425 cm³；bounds=[[-0.05881712585687637, 0.5709999799728394, 0.2136300951242447], [0.0025115807075053453, 0.5889999866485596, 0.27340060472488403]]
- left_ankle_fixed_bearing_housing_1 → isd_continuous_main_arch：16.912398 cm³；bounds=[[-0.14265038073062897, 0.5709999799728394, 0.20499999821186066], [-0.02500000037252903, 0.5889999866485596, 0.25932076573371887]]
- left_ankle_fixed_bearing_housing_0 → isd_heel_brace0_fixed_pin：6.390401 cm³；bounds=[[-0.12200000137090683, 0.3659999966621399, 0.21799999475479126], [-0.09801331907510757, 0.3840000033378601, 0.24074462056159973]]
- left_ankle_fixed_bearing_housing_1 → isd_heel_brace1_fixed_pin：6.390401 cm³；bounds=[[-0.12200000137090683, 0.5709999799728394, 0.21799999475479126], [-0.09801331907510757, 0.5889999866485596, 0.24074462056159973]]
- left_ankle_fixed_bearing_housing_1 → isd_heel_brace1_fixed：2.996652 cm³；bounds=[[-0.13971824944019318, 0.5830000042915344, 0.20731070637702942], [-0.08238177001476288, 0.5889999866485596, 0.2531565725803375]]
- left_ankle_fixed_bearing_housing_0 → isd_heel_brace0_fixed：0.010859 cm³；bounds=[[-0.13971824944019318, 0.382999986410141, 0.2286268025636673], [-0.13173983991146088, 0.3840000033378601, 0.23899336159229279]]
- right_ankle_fixed_bearing_housing_0 → isd_right_continuous_main_arch：27.977787 cm³；bounds=[[-0.14265038073062897, -0.3840000033378601, 0.20499999821186066], [-0.02500000037252903, -0.3659999966621399, 0.25932076573371887]]
- right_ankle_fixed_bearing_housing_1 → isd_right_forefoot_brace0_fixed：17.472424 cm³；bounds=[[-0.05881712585687637, -0.5889999866485596, 0.2136300951242447], [0.0025115807075053453, -0.5709999799728394, 0.27340060472488403]]
- right_ankle_fixed_bearing_housing_1 → isd_right_continuous_main_arch：16.912398 cm³；bounds=[[-0.14265038073062897, -0.5889999866485596, 0.20499999821186066], [-0.02500000037252903, -0.5709999799728394, 0.25932076573371887]]
- right_ankle_fixed_bearing_housing_0 → isd_right_heel_brace0_fixed_pin：6.390401 cm³；bounds=[[-0.12200000137090683, -0.3840000033378601, 0.21799999475479126], [-0.09801331907510757, -0.3659999966621399, 0.24074462056159973]]
- right_ankle_fixed_bearing_housing_1 → isd_right_heel_brace1_fixed_pin：6.390401 cm³；bounds=[[-0.12200000137090683, -0.5889999866485596, 0.21799999475479126], [-0.09801331907510757, -0.5709999799728394, 0.24074462056159973]]
- right_ankle_fixed_bearing_housing_1 → isd_right_heel_brace1_fixed：2.996652 cm³；bounds=[[-0.13971824944019318, -0.5889999866485596, 0.20731070637702942], [-0.08238177001476288, -0.5830000042915344, 0.2531565725803375]]
- right_ankle_fixed_bearing_housing_0 → isd_right_heel_brace0_fixed：0.010859 cm³；bounds=[[-0.13971824944019318, -0.3840000033378601, 0.2286268025636673], [-0.13173983991146088, -0.382999986410141, 0.23899336159229279]]

主源与canonical组件mesh逐值一致：True；参与件WT/绕序/正体积均成立=True。布尔未解项=0。

**当前候选拒绝。** 固定踝父件与脚承件的正材料相交必须解决；这不是轴承接触许可，更不是AA3必须改形的证据。轴座、脚承件及完整传动包的内部重排仍待判断，未给外壳改形必需性结论。

本轮未检查前掌/后跟卸载折叠，未推断吨载、疲劳、销配合、轴承能力或整机行走；材料union不得替代真实机械连接证明。

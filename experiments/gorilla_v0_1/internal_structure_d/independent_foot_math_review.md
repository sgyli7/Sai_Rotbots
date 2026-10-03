独立复核于 2026-10-02 18:29:40 UTC 收束，15 分钟时间盒内。只读取实际 foot/leg/whole scene 与代码；只运行隔离 LP 算例、脚局部有限材料布尔和 32 个端点长度差分，未调用整机 evaluator，未构建全模型。JSON 保留全部配对、相交体积/界限、算例和哈希；任何结果均非 physical passed。

**已修项。** 根将 heel shaft 轴向长度 0.326→0.368 m。当前中心 y=0.5，轴覆盖 [0.316,0.684] m，两 24 mm 轴承包络为 [0.358,0.382] 和 [0.658,0.682] m，已恢复完整轴向覆盖。仅证明包络覆盖，未证明配合/滚动额定/轴强度。

**仍需处理的真实材料红线。** 用当前 source native 顶点/面重建有限实体，manifold 正体积交叠阈值 1e-10 m³；不是 AABB 相交。只直接计算左脚，右脚实体为 builder 明示镜像。

| 姿态/配对 | 正体积相交 m³ | 范围 |
|---|---:|---|
| neutral fore tray / fixed main arch | 1.4349384e-5 | 实际条件钢材料 |
| neutral heel tray / fixed main arch | 2.0846891e-5 | 实际条件钢材料 |
| neutral heel tray / fixed brace 0、1 | 每条 6.4430537e-6 | 不同运动组材料 |
| fold fore tray / fixed brace 0、1 | 每条约 1.082700e-6 | 新增折叠碰撞 |
| fold heel tray / fixed brace 0、1 | 每条约 5.914290e-6 | 折叠仍相交 |

neutral 左侧共 5 对，fold 7 对；每姿态还有一对 heel bearing 参考包络与 tray 相交，须区分其未选型包络与真实轴承内部材料。上述其余项足以否定当前各运动组已具备间隙。builder 39–40、49、55–56、74、110–112 行的实际材料构造有待根修正，reviewer 未改脚。

保留 C15 原甲壳/内皮的实体核对：neutral 11 处、fold 10 处左侧正体积相交。例 neutral fore brace1 plunger/left_ivory_artwork_sloping_toe = 1.2070489e-5 m³；heel brace0 fixed/left_composite_high_heel_shell = 1.3660034e-5 m³。fold 额外撞固定 ankle_front_guard。fold 的 moving armor/pads 按实际 D 新 hinge（fore x=-0.077，heel -0.131）及 -25/+25°变换，固定甲壳保持原位；旧 C15 共同 x=-0.106 的 pivot 及旧角度不能继承作此姿态已验证。没有连续 swept collision 或 mesh 自交完整证明。

**直接可修接口。** foot builder 119 行只镜像 mesh/body/name，D_metadata 的 endpoint_A/B、independent_hinge pivot 没镜像。isd_right_forefoot_brace0_fixed 实体 y∈[-0.620,-0.560]，endpoint_A 却为 [-0.055,+0.590,0.255]，其“Rebuild from transformed A/B endpoints”规则会重建在错误侧。当前 evaluator 107 行读取 leg['actuator_definitions']，所读 d016145… leg 无此字段；8 条表在 spec['actuator_definitions']，是静态可确定的 KeyError。这两个问题在最终所绑快照尚未修。

**脚拓扑与锁孔事实。** 左侧 neutral 31、fold 23 件均闭合、绕向一致、正体积；每件只有一个正材料连通分量。tray 的负体积闭合内壁是封闭空腔，不能报成 material islands。fixed arch、fore tray、heel tray 是不同 body；未发现跨两 hinge 的连续接地 sole，但前述跨 body 相交仍阻碍运动，连接刚度未证。neutral 两 brace lock stations 相隔 50 mm，实际 17 mm 贯穿孔配 16 mm 销，fold 源不含 lock-pin 实体并标 withdrawn；没有实际防脱/操作验证。

107 行销公式 A*(2剪切面)*(2销)*(355MPa/√3)/FS2 = 82419.043 N/brace，作为“假设 S355、两销理想均分、双剪切、屈服安全系数 2”的毛截面算术正确。非整体 lock/joint 额定；孔壁承压/韧带、端部眼销、管压屈、连接/焊缝及载荷均分均未知。不扩大锁销设计。

**LP 数学。** 上向法向接触 f_i≥0 且 z_i=0，外载 F、M 关于原点，接触矩为 (Σy_i f_i,−Σx_i f_i,0)，所以代码 23–24 行
Σf_i=−Fz，Σx_i f_i=My，Σy_i f_i=−Mx
正确。给定 F_j=c_j+k_j·f，27–32 行约束是 −Cneg_j*t≤F_j≤Cpos_j*t，min t≥0，符号正确；c、C 为 N，k 为无量纲。共享同一个 f 的容量存在性 LP 与逐轴分别取得自由极值后再取 min/max 不等价。

隔离独立算例：四角 (±1,±1,0)，100 N 重力在 (0.2,-0.3,1)。令 F=-50+(正x接触和)、Cpos=20/Cneg=10，解析 t=0.5；改 c=-80 得 t=2。两模型 F1=f0/Cpos20、F2=-f1/Cneg30 且重力居中，解析共同 allocation=[20,30,30,20] N，t=1；各模型自由最大可达 50 N，仍不能据此排除共同可行 allocation。所有解析值复算一致。域外加入水平 Fx=10 N 时函数仍返回 t=0/conditional feasible：函数本身未守卫 Fx/Fy/Mz 和 contact plane；当前 main 的重力载荷及 pad z=0 限制避开此例，但函数不能泛化为完整静力平衡。

**实际轴到力映射。** 用当前 spec A/B 与 leg 每姿态 T，32 个轴以独立中央差分核 dL/dq，最大误差 8.47e-11 m/rad。axis·[(B−J)×u]=u·[axis×(B−J)] 的 arm 符号正确；若 positive F 是 B 端沿 +u 的伸出力，F=−(τgravity+τcontact)/arm 正确。spec 左 4 对 A/B 与 leg.interfaces_left 完全一致。层级 thigh→middle→distal→foot→fore/heel 保留，8 腿轴的后代含其 pads；foot exact-child body 筛选符合锁定中立假设。脚 neutral fore arm +0.1292617 m、heel -0.07759943 m，因两等分 brace 使用 -τ/(2arm)，不是取绝对力臂。两 brace 等分仅矢状面假设，不能证明 roll/torsion 反力存在；endpoint-driven barrel/plunger 的 body 质量归属也没有独立闭链重力/支反力证明。

**证明适用范围。** HiGHS success 是 solver 的 optimal 报告；原始 primal residual/violation 独立证明的是给定 witness 满足条件方程。t≤1 的 witness 可证明此受限数学模型存在 allocation；t>1 的“无 allocation”不能由 primal 单独证明，尚缺 dual/gap 证书。solver 失败当前与 feasible=false 混在一起，应保留 unknown，不能作不可行证据。压力×面积与毛截面剪切都只是 hypothesis，未覆盖摩擦、背压实际变化、热/持续功率、动态、横向/yaw轴或质量区间高端。闭合 mesh 与 primal 小残差均不代表物理通过。

绑定哈希（完整字段见 JSON）：

- robots/gorilla_v0_1/cad/source/internal_structure_d_foot_scene.json: `a0b857dac4d626f7f25532d4e5d83f5402147715413d588306a425ebce0f8a05`

- scripts/evaluation/evaluate_gorilla_distributed_layout.py: `063fc4cbe5202c95a5871cad5028a847303e5869c4cb55b07b3ea72afb57f2df`

- scripts/models/build_gorilla_distributed_foot.py: `30e1cf70e8485b4ba027da3c5862f95d3db4ea3e0d8dfe8fe370b1d1a395a70d`

- experiments/gorilla_v0_1/appearance_c_round_fifteen/appearance_c_scene.json: `7a1e49f45838303ca5fd86265dc9980c10cde85ed7626424136afd3863aa5886`

新增 D full scene/leg/spec 的只读快照及 SHA 已保留于 JSON；后续根若改源，请把新 hash 与本 snapshot 分开，不继承本次未重算的结论。

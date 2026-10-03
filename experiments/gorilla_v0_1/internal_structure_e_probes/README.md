# Gorilla E 开局：串联腿、热路径与驱动约束探针

日期：2026-10-03，Asia/Chongqing。父候选为已提交的 D `52a1a240`。本目录保存实际执行过的失败分支，不是已合成的 E 整机、稳定 SI、审美改稿或能力评级。唯一当前状态仍见[当前决定](../../../robots/gorilla_v0_1/design/current_decisions.md)。AA3 外观权威、2.65 m 高和原稿比例未更改。

| 分支 | 实际输出 | 结论及范围 |
|---|---|---|
| 完整串联腿试构 | [报告](leg/report.md)、[逐对检查](leg/e_leg_checks.json)、[三视](leg/e_leg_neutral_three_view.png)、[原生源（无损压缩）](leg/e_leg_scene.json.gz) | 中立 477 件，五个姿态；旧 D 脚踝/密封套指定交集为零，但中立仍有 18 组跨 body 材料交。最大髋桥交约 84.936 cm³/侧；脚弓—后托盘约 42.311 cm³/侧。保留真实失败，不能按 body 名虚构连接 |
| 全关节热路径试构 | [报告](thermal/inventory_pressure_heat_report.md)、[路径/质量](thermal/thermal_route_spec.json)、[同尺度正侧后诊断图](thermal/native_thermal_path_orthographic.png)、[原生源（无损压缩）](thermal/thermal_route_scene.json.gz) | 189 件、32 接口、74 供回路径；40 条跨运动组软管未做定长/弯曲/运动核查。图连通不等于额定保流/换热。17 选定模块对 111 原甲仍有 34 正体积交，非全机检查 |
| 驱动需求参照 | [E0 联合参考](../internal_structure_e_constraints/README.md)、[本目录独立轴区间](drive_reference_intervals.json) | 冻结 D 的质量/接触和串联树假设；不适用于改了轴位与质量的 E 腿。独立轴极值可能来自不同反力，不能拼成全身可行分配 |

腿分支条件净金属 401.844 kg、参考组件约 99.145/108.109/124.693 kg，部分分支总计约 500.989/509.953/526.538 kg；不含甲壳、垫、上身、能源和液路。厂家组件内含接口的重复计量资格仍未知，不能把这份部分账本加到 D 总重上。热分支约 41.972/49.173/63.100 kg，明确替换 ID 下比 D 被替换项增约 27.53/31.06/37.84 kg；未与新 E 腿组成同一完整装配或动态质量合同。

补充的独立轴区间只约束冻结 D 八缸/脚撑假设与法向接触。中值中立左髋 roll 可取约 −1480 至 +3116 Nm、左足 roll 约 −3248 至 +2058 Nm，单轴最小绝对值均可为零；这些反力不能自动共同成立。E0 的 862.8/251.3 Nm 是共同参考容量下的一个 witness，不是两个轴各自不可避免的最小需求。腰 pitch 不受该脚底反力分配影响：中值前伸空载约 1915.785 Nm、100 kg 双手条件约 2680.4 Nm，另加 3 t 外压约 9220.5 Nm。目录 L10 rated 只作标尺，不是静态硬上限、完整持续驱动或温升合格证明。3 t 外压不作为搬运载荷。

原双前芯面积参照 0.0351 m²；新后芯面 0.203 m²、后排风毛开口 0.216 m²、侧进风毛开口 0.210 m²是三个不同量。30 kW、空气升温 20 K、面速 4 m/s、孔隙率 0.5–0.7 的条件预算需控制进/排风各约 0.444–0.622 m²；这是焓守恒必要条件，不是实际任务热、风机曲线或芯体 UA。原厂 20°C 安装面、油侧换热/负功回收、OEM 水腔/端口及泵压流继续未闭合。因此不据此宣称 AA3 必须改形，也不直接放大外壳。

## 复查与恢复

[冻结清单](snapshot_manifest.json)绑定文件、压缩前后的哈希和输入图；[独立复核](independent_probe_audit.json)实际检查全部姿态/热源网格、身份、列出质量、净液体、功能有向图和空气焓公式，其通过仅限这些项目。碰撞/连接、全 E 接触驱动、压力流量、持续热与审美仍未通过。

原生 JSON 使用 gzip 无损压缩，解压后的 SHA 与原分支原始 manifest 相同。脚本作为实验原文以 `.py.txt` 保存，保留原 `.scratch` 路径/输入含义，不是注册运行入口。复现先将各分支恢复至原 `.scratch/gorilla_internal_e_leg`、`.scratch/gorilla_internal_e_system`，去掉脚本最后的 `.txt`，解压对应源；不要写回已冻结 D 或本实验文件。

腿构建引用的 `.scratch/gorilla_internal_d_geometry/probe_finite_actuators.py` 可从父 D [冻结脚本](../internal_structure_d/geometry_probe_finite_actuators.py.txt)恢复（SHA 相同）。E0 输入从[冻结 E0](../internal_structure_e_constraints/)恢复到原 `.scratch/gorilla_internal_e_constraints`。然后运行 `build_e_leg.py`、`summarize_branch.py`；腿原清单保留全部输入与结果。热分支按[复现说明](thermal/reproduction.md)顺序执行；厂商 PDF 路径/页码在其 [final_manifest](thermal/final_manifest.json)，PDF 未入 Git，热源读数是保存的研究输入，不伪称自动再提取。面积语义修正保留旧新哈希链，未重跑几何。

根复核原文为 `independent_probe_audit.py.txt` 和 `drive_reference_intervals.py.txt`，在仓库根使用已记录 `.venv/bin/python`，恢复其 `.scratch` 输入后运行。新 E 质量/轴位/接触一旦变化，必须重新核算，不能沿用这些结果放行。

下一步先比较完整旋转总成与分置线性驱动的空间、自重、行程和同工作点热，再选一个整体候选。包装探索按用户授权执行；由明确冲突产生的改稿须提交同一候选同尺度四视，用户认可后才更新审美基准。

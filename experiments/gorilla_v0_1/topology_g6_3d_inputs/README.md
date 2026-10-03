# Gorilla G6 宽厚三维结构输入

用户的壮硕外形为骨架提供宽厚三维设计空间。墙、肋和过渡节点允许重新分配材料；真实轴承、缸销、止挡和安装接口，以及器件、运动、散热和检修空域必须保留。本检查点把这一原则落实到一个实际承力件及同源载荷入口，尚未完成 Gorilla 骨架优化。

选择 G4 `g4_child_load_carrier`，源 SHA `9a88efe894625e7ed3d3f15e544ead7b574382035594ab8d4b81f530fbb7b21a`。净体积 4.073506 L、条件钢质量 31.977019 kg，仅为此件原始材料基线。它是独立关节 bench 的组件，不是用户待交的新腿脚，也不是已选整机结构。

| 本轮结果 | 适用范围 |
|---|---|
| 真实三维域、接口面、42 个六维载荷已源绑定 | 原有限材料；未来可增长域仍要减去完整功能及扫掠空域 |
| 几何 tetra 网格保持体积、原边界、孔及一个材料根 | 仅几何输入验证 |
| 第一质量网格 288.49 秒后 error 2；第二几何网格严重 sliver | **拒绝结构 FEM 和优化使用**；没有删除坏单元或补洞 |
| 主工况实际表面端口节点力映射，约 1e−11 的合力／矩残差 | 任意向量 traction 是条件假设，轴承和销的真实接触未闭 |
| 独立 3D P1／scikit-fem 数值校验 | 单位立方体工具测试；不是 Gorilla 强度或减重证据 |
| 网格拒绝门禁在真实输入上执行 | 求解前退出，没有运行真实组件刚度解 |

Root 独立复核与 Agent 均拒绝当前网格。29 个极小 tetra 的存储坐标精确有理数符号均正，但浮点体积存在消去，1582 个单元 mean-ratio <0.01；几何正体积不能保证有限元数值质量。体积、边界和连通的有限符合不覆盖应力、屈曲、疲劳、接触、制造、持续驱动或整机性能。

下一主路线是从原尺寸重建合法 CAD 并分块，获得可控的三维实体网格，再接源绑定的端口。宽壁壳＋局部实体耦合作为计算成本备选，须核传力和传矩，不能把宽厚结构退回细杆。墙肋可优化，非设计接口不是全件永久锁死。外观腿脚继续等待用户指定的「Gorilla 设计」交稿。

精选入口：[三维域与网格报告](domain/domain_review.md)、[接口](domain/domain_interfaces.json)、[网格质量裁决](domain/quality_admissibility.json)、[载荷报告](load_ports/load_port_review.md)、[真实节点载荷](load_ports/tetra_case18_loads.npz)、[独立几何复核](domain/root_quality_review_snapshot.json)、[数值单元校验](root_review/unit_cube_verification.json)、[实际拒绝收据](root_review/rejected_solve_guard_receipt.json)。

原始输入按 [snapshot_manifest.json](snapshot_manifest.json) 保存：37 条原始记录、36 个不同内容文件；producer 原始字节作为 `.py.txt` 资料保存。下载的工具运行时、PyPI 缓存和许可证抓取文本不入库，许可与来源留在报告和元数据中。MeshPy wrapper 为 MIT，实际 TetGen core 许可需另按报告核实，不能视为仅 MIT。G4 依赖和工具环境不在本快照重复保存。

先按 [G4 检查点](../internal_structure_g4_joint_study/README.md) 恢复必需源，再执行 `.venv/bin/python experiments/gorilla_v0_1/topology_g6_3d_inputs/restore_snapshot.py.txt --root /home/ethan/Projects/Sai_Rotbots`。恢复会验证保存和原始哈希，并拒绝覆写变动的 scratch。独立数值工具需在 `.scratch/gorilla_topology_runtime` 隔离安装 scikit-fem 12.0.2，使用已有 NumPy／SciPy；不修改项目锁或共享机器人模型。

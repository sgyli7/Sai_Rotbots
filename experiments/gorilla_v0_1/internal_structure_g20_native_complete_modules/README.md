# Gorilla G20 实际完整模块与安装范围

G20完成两个组件关节、两个720能源布局和两个液压技术模块的真实原生/CAD探针，均未放行安装与物理。上半身沿AA3审美，新下半身仍在用户修订；本轮不采用新外形、改变稳定SI或承诺性能。下一G21按完整整数储能、共同肩/core接口和全体载荷/功热分配推进，停止第三次单模块补丁。

| 探针 | 实际结果与范围 | 源和图 |
|---|---|---|
| 组件关节B，源`cb0b31c6…` | 110件/88自建材料资源通过；21实际材料穿插、初装失败；core面X.2825不能套现X.115。条件onboard库存56.063–58.050kg，不是安装净重或完整三轴肩 | [原生源](component_joint/b/scene.json.gz)；[裸四视](component_joint/b/bare_four_view.png)；[原甲局部](component_joint/b/original_armor_context_four_view.png)；[完整报告](component_joint/report.md) |
| 能源B，源`8031a7d4…` | 四18s10p共720芯；实际单包365.75×117.575×330.8mm。305mm层距穿包络25.8mm，两列安装壳各交86.866cm³，frame/oil/PDU/compute/pump仍冲突。cell仅50.4kg上界；全能源103.110kg仅上界、low/mid未知 | [原生源](energy_module/b/scene.json.gz)；[实际拆壳四视](energy_module/b/native_cutaway_four_view.png)；[完整范围](energy_module/README.md) |
| 液压B，原源`7d7ca296…` | 65件，5材料交/9多根；HSP gross缺2mm，原C/V标签错误，补偿/辅助连接/耐压与OEM惯量未合格。条件库存13.979–15.244kg不是安装净重 | [精选自建/包络子集](root_review/hydraulic_selected_parts_b.json.gz)；[实际四视](hydraulic_module/b/native_module_four_view_b.png)；[完整报告](hydraulic_module/README.md) |

[根线程同源裁决](root_review/integration_decision.md)与[独立原生积分/完整包络/整数拓扑/选定布尔](root_review/independent_native_audit.json)区分源生成错误、实际装配红线和未证明的外壳约束。B关节自建native44.1050kg vs CAD44.1168kg，相对−0.0267%为faceted差，不称精确相等；21交叠不被同owner豁免。能源自建有限材料27.1095kg仅其子集；OEM gross和cell不由均匀密度补造COM/I，全机M/COM/fullI仍null。根线程首版按名prefix误含globalfeed的包尺寸原报告/producer保留，按source_local_ID更正范围，未改原几何。

[snapshot_manifest.json](snapshot_manifest.json)记录197精选原路径/194冻结身份检查，原producer、失败源/范围与必要自身CAD均保留。原厂发布PDF/图/STEP、direct coil NPZ与嵌入它的两原场景留本地；其来源/哈希和失败记录受控。43/63件液压精选子集明确排除两原厂三角网格，不是原场景完整字节恢复。自身按公开事实建立的包络/几何不是OEM制造CAD或额定。

[restore_snapshot.py.txt](restore_snapshot.py.txt)只恢复精选字节到独立空目录；[验证结果](selected_snapshot_verification.json)验证其身份/JSON/producer语法和当前入口，未安装或重跑完整生成、昂贵FEM/训练和电热物理。G20没有GPU、运行模型/策略/ABI变动。C15已合主干，后续内部候选继续在草稿PR5。

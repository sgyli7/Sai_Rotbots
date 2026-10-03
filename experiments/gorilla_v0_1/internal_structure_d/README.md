# Gorilla 内部 D 冻结诊断

本候选保留 AA3/C15 比例与111甲壳，形成有限缸/腿/分段脚、全机分布模块和同源回算，完整装配/审美/物理仍拒绝。当前工作只看 `robots/gorilla_v0_1/design/current_decisions.md`，本目录是阶段历史。

`snapshot_manifest.json` 绑定受控源、配置、脚本、六图/四视、真实GLB/Blend、质量/空间/流量与独立复核。stage_* 是当时导航/决定/排期/评审副本，链接按其原文件位置解释，不把副本当新的当前索引。以工作树相对路径映射原资源，后续不得覆盖本冻结文件。

`leg_original_native.json.gz` 是原108309797字节leg JSON的无损gzip（mtime=0），解压SHA256为b4e12a5be70bd90cdd38760409997bb2810a09de928a26779a59397f1021eb67。受控22MB leg source移除重复new_parts/new_frame_parts/poses，并将四姿态的刚体网格改为中立native+精确T，保留每姿态80个真实端点执行器材料；vertices/材料/质量不缩减。规范化说明在leg source normalization字段。主装配器/评估器/渲染器能从受控输入直接重建与检查，读SHA漂移会拒绝。

geometry_*/leg_*/system_* 是各子分支原报告，绑定各自时间点，特别leg_root_foot_interface_diagnostic使用临时旧脚；不能冒称当前canonical接口结论。independent_interface是当前canonical接口；independent_foot_math原review绑定metadata修复前源，实际左侧材料未改变；math_review另绑当时函数，最后非负边界残差修复/48cases由主线程同版报告给出。所有复核范围与输入hash单独保留，不能互相替代。

independent_resource分别记录strict raw-control差异和source-bound display身份：46个保留件的既有倒角属于冻结C15显示链，新1091件严格native匹配。任何资源身份通过都不等于物理或审美通过。外部原厂PDF/CAD许可未确认者留在本地忽略区，没有作为自有完整硬件或制造资料入库。

复现入口见stage_internal_structure_d_review.md；本轮215软件测试通过，48限定静力/108端点流量不代表完整关节、摩擦、动态、电热或Bevy任务验收。

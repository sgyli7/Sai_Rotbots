# Gorilla G14：完整热部件共同布局与拓扑输入

这是内部工程候选及失败证据，首检查点、审美、装配、结构、持续热、整机SI均未放行。唯一设计外观仍为[用户确认AA3](../../../robots/gorilla_v0_1/design/concepts/aa3/user_confirmed_four_view.jpg)。

完整主躯候选B源 `a6a457964e87094401d2bba69825435697d3d44ec888eef7d3386408b6580849`，3108件；一整584×305×64mm热芯、两完整172×51mm风机、480电芯及全部辅助功能已实际重排，HX五件统一刚体搬位错误已修正。A和B修正前失败源保留。[实际四视](complete_thermal_colayout/b/native_four_view.png)、[拆壳四视](complete_thermal_colayout/b/native_cutaway_four_view.png)、[剖面](complete_thermal_colayout/b/actual_sections.png)、[最终工程报告](complete_thermal_colayout/b/final_report.json)。未采用新外壳，也没有把保留旧甲等同安装成功。

实际自有钢笼架71.963kg，一正材料根和四负闭腔；A→B框架相同，不是B额外减重。根线程独立积分净体积、重心、完整惯量及实际STEP回读；接口、闭口承力截面、接合/疲劳与吨级承压尚未证明。[独立源绑定](root_review/final_frame_unchanged_source_binding.json)、[实际框架净量](root_review/b_frame_moment_review.json)。

最终3070对是changed×all保留范围的诊断，并未覆盖unchanged×unchanged或运动。主作者309对按严格有限材料角色分类；独立1360对范围另含原甲/热路的声明材料几何。不同谓词不能比较降幅，也不代表全源材料已获得资格；参见[口径说明](root_review/scope_corrections.json)。明确障碍包括阀护罩、水箱×HX、排风×油管header、框架×HX及旧风道。旧泵/副芯/风道的完整替代账、第二热路真实脱气/保护/接管和液体分配仍开放。[系统独立复核](root_system_review/README.md)。

另存的肩A/B为230件真实可拆盖初装失败候选，B源 `7e8db6e…`：每侧五类12个有限失败采样，后盖仍与壳体相交。它是旋转后的独立装配bench，不是躯干就位维护；主躯仍绑定G13肩A，不继承G14肩B结论。[肩报告](shoulder_initial_assembly/README.md)。

完整纯水参考粗算：总峰热8.010–8.991kW，单完整芯无法满足全部低温回水要求；低温主路和热油分路继续设计。新管液1.847–8.589L仅是管路空间范围，不是全水库存。配方/完整泵扬程/风机同点/副芯UA/辅助耗电仍红。根独立94项守恒、Darcy、行程和范围算术通过，不放行能力。[完整来源与物理条件](thermal_inventory/README.md)、[独立算术](root_review/thermal_arithmetic_review.json)。

用户的壮硕身体原则已经转为三维拓扑入口：[实际六剖面/域](root_topology_review/actual_sections_and_domain.png)、[域与载荷入口审查](root_topology_review/README.md)。92.048L只是缺面与完整组排除后的粗采样候选，不是可用闭腔；真正多载荷FE须重新建立当前质量/重心和接口反力。没有本轮FE/SIMP或优化强度认证。

快照保留156项原始文件映射，147个去重后存储文件约79.4MB；所有169项冻结来源身份逐项校验。CAD/大型报告压缩保存精确字节，脚本作为`.py.txt`存档；[恢复入口](restore_snapshot.py.txt)恢复至空目录后使用原路径。下载资料/运行依赖未入库。主躯A与修正前B的历史producer未单独保存，**原程序的精确生成重放不可主张**；原native数据、CAD和结果可恢复并重新只读检查。不要以当前builder冒充历史程序。[快照清单](snapshot_manifest.json)。

下一周期G15：完整热双路/液体工作库存/阀组与承力域共同布局，显式替代旧重复储备；最多两宏观候选。腿脚原画由「Gorilla 设计」推进，收到用户通知再适配；稳定SI与复杂Bevy目标持续。

# G9 实际九组共同布局探针

两套真实候选已生成。`layout_1/scene.json.gz` SHA `20bc7cb08fd522a1d9cad5b68fb4f2365ef7cb8620e0e405ce7fe751e15d2109`；`layout_2/scene.json.gz` SHA `43e05e17130da000c5821e29aef1d54f233fd6d16a6e2a4aa7da11a36883bf52`。同一实际B周边承力core，原两F1躯干壳换一件core，故1793个原生条目；四电池、两整泵、HX、compute、backscreen共33个成员整组刚性变换。其余1759完整part字典原值、111可见甲原值，未缩OEM、删功能、改容量/采购、换腿脚或造新轴。原9组之间14个positive交减少为两套各0，仅本次中立包络/材料查询，非安装或物理通过。

布局1：完整packs转90°成为后部双列双层（中心X−.23，Y±.14，Z2.12/2.47）；两完整泵竖轴（X.04，Y±.16，Z2.32）。布局2只把完整泵转横向放高肩前侧（X.165，Y±.28，Z2.435）。HX中心[.22,0,1.90]，提出pelvis承载owner；compute[.20,0,2.61]；backscreen保持原[−.386,0,2.225]，屏玻璃/UI原值。所有owner是挂接候选，不代表有安装反力路径。每组exact IDs、矩阵、实际AABB、质量范围和后移COM见placement_parameters/moved_group_mass_positions；不得把AABB当freecavity。

真实空间筛查：L1 1282 Boolean queries、423positive（core109、甲22、9组互交0）；L2 1242queries、392positive（core113、甲53、互交0）。L1新core×9组为HX有限材料324.705cm³＋两泵return-filter参考各20.561cm³；L2新core×9组7对，包括HX、整泵参考与有限mount。有限材料、参考包络、原甲、旧上下游context在space_checks逐对分列。旧肩gear Z2.36与新port Z2.29错70mm且旧123.5mm轴长错；562cm³的旧gear×core不是正确新安装的真实材料失败，不能推导AA3必须改形。没有修旧gear让它刷过。

两套都拒绝。实看whole四视和原生triangle-plane切面显示：upper rear packs及顶部前compute破出原曲面，lower packs撞现有阀bank，HX与腰颈材料相交；不是允许外置这些器件的方案。原AA3可见外表面没动，也没有利用隐藏内皮开洞取得通过。L1相较L2给出较少新core/原甲挑战，可作为root下一宏观输入，不是采用。已达两次宏观上限，不继续第三挪位。

旧`e2_upper_net_torso`按root授权保留完整source/ID/77.937kg挑战、改为reference-only pending full functional replacement，不作为新core主动实材重叠强制障碍。两实际四视不显示它，原1794全source诊断另冻结。新core通过waist环/闭口颈—周边壳/横接—双肩boss提出三个真实port；具体面与条件轴见functional_replacement_scope。旧肩固定/输出身份、紧固、载荷、完整驱动接回尚未闭，不能声称旧桥功能完全替代或把质量差当整机减重。

油/水、真实散热芯、fan、duct、全部旧native油水管与HV/24V占位都保留。已明确变换24个已知候选source接口点并列24条旧路由失效；这些不是原厂认证datum，所有新油水/电线均未重建。其余电气接头实际datum、线管弯曲/运动、pump空气辅助冷却、工具路径unknown保留，不补虚构线或油容量。30L全局油和原water库存只计一次，新的空间分配未知。90旧阀holding服务空间保留，不把非实体当质量/可安装硬件。

scene保留旧账本列为baseline reference；实际移动后COM在`moved_group_mass_positions.json`，不要把旧COM当当前位置。所有组质量范围原值，33成员体积变化最大<5e−18m³；目录包络不造OEM惯量，新core条件钢性质来自其独立CAD。缺4缸仍unknown，不零计；整机mass/COM/fullI为null，稳定SI/持续驱动/热/真实接触/审美全部false。

可复现入口：build_placements.py 1/2；check_placements.py 1/2；render_placements.py 1/2；update_route_interfaces.py。全部只能在新clone目录再运行，不能覆盖此快照。两套实际cut PNG与native四视都已打开查看、绑定本scene hash，无贴原图、AI画CAD或修源法线。最终架构、下一完整肩腰/阀/热路共同分配由root决定，双足双手自主复杂Bevy终点保留。本轮无FEM/GPU/Git/受控文件写入。

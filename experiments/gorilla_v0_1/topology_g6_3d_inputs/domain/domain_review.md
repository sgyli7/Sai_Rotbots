# Gorilla G6 实际宽厚三维输入与网格裁决

**实有几何、六维接口与真空洞输入已建立；当前四面体网格不适合结构有限元求解。** 下一步应比较宽壁壳＋局部实体混合建模与合法CAD几何分块/重网格。两路都保持三维宽厚承力域，不能把骨架降为细杆；本轮不运行FEM/拓扑优化，不改外形或旧源。

## 当前单件与可重新分配范围

选择G4 `g4_child_load_carrier`，只读scene SHA`9a88efe894625e7ed3d3f15e544ead7b574382035594ab8d4b81f530fbb7b21a`、handoff`9189d7f0…`、report`567104f3…`、root review`99e92fa8…`。源有2944节点/5912三角面，完整signed闭面、一根真实材料体，净4.0735056506L；按原条件钢ρ7850是31.977019357kg，只为该件基线，不是合格总成或减重结果。原30件模块的资源/四姿态抽样通过不等于支承、压力、上游、工具或整机资格。

其425×240×150mm闭口主箱、短journal与成对驱动fork给出了真实宽厚布局。下一三维优化允许重新分配主墙、内部肋和boss过渡；**不把全部旧粗墙或保守大盒选择器永久禁删**。真正非设计域应落在配合表面、承压面、止退/螺栓界面及明确制造缓冲：

- 两侧59.9/28.2mm journal的实际外表面与keeper/肩；轴承引用d60/D110/T29.75，实际fit、滚子压力中心和预载未知。
- 两个实际40.4mm叉孔的承压表面与足够净截面；孔的载荷半面、pin接触和力分布尚未核。
- 两个neutral compression-shoe接触面；static hold与运动解除分开，不能把它一直当支承。
- 下游实际endcap安装表面；当前只有等效6D端口，真实足部轴/法兰/螺栓未建。

`domain_interfaces.json`保存上述实际native face候选与面积，属于几何分组；centroid半径band不自动等于实际受压面。制造最低皮暂列3–6mm条件范围，未采用、未证明其扭转/屈曲能力。允许墙/肋改变时必须对最小实体/空洞、闭口扭转、压缩屈曲、节点净截面与制造工艺同时约束。

当前网格域是**原有限材料**。未来材料可增长/重分配的域应由G4实际外primitive union，减去完整驱动、其他owner实体、孔、关节连续扫掠及维修工具void后建立新版本；没有把外甲AABB或零件AABB称为自由腔。现4姿态和21次手动抽出抽样不能证明全部新增材料域无交。独立新腿脚设计未收到，轴位、包装和全机设计域不冻结。

## 同源载荷与支承边界

`same_source_6d_load_cases.json`保留全部42工况，使用源的实际child刚变换回到中立材料坐标；驱动或static-shoe、两侧journal反力、下游等效6D端口都保留并再平衡。最大净力约1.03e−11N；并非只取某个最大缸力再叠未知力矩。只含29430N外部静态压力及1.5敏感性，不含机器人/模块自重、正常移动、惯性或疲劳谱。

两种条件输入不可混用：

1. 自平衡外力研究：保留全部同版端口反力，按真实面分布/等效6D守恒映射，只用rank6积分约束移除刚体自由度；不锁整圈journal。它分析给定反力分配，实际轴承刚度/接触仍未知。
2. 配合parent研究：显式环、fit/预载、contact或声明的支承柔度，由解产生journal反力；不能同时再施加上一方案的反力。上游安装及真实contact仍需补齐。

独立load agent正在真实边界节点上构造守恒映射；本目录只准备同源接口，未施加FE载荷。轴承整圈全固定会虚增抗扭刚度，不能称真实支承。下游力矩不能丢掉或改为单点力。

## 两次实际网格尝试

本机aarch64 Python3.12隔离安装MeshPy2026.1.1，只依已有NumPy。官方cp312 Linux aarch64 wheel671048B，SHA`bfe9b35637536c4ec24bf22d945b376a34b853f7fa34a468d358209d714af906`。wrapper是MIT，实际TetGen core为AGPL3-or-later/商业双许可；未使用Triangle，其许可另有条款。本轮仅scratch研究运行时，不进入受控源码/二进制，也不改锁或GPU。[官方PyPI](https://pypi.org/project/meshpy/)、[完整多组件许可](https://github.com/inducer/meshpy/blob/main/LICENSE)

Gmsh官方4.15.2 PyPI发布只有Linux x86_64、macOS ARM/x86和Windows wheel，没有Linux aarch64 wheel；没有因此全局apt或拉大型依赖。[官方发布文件](https://pypi.org/project/gmsh/)

| 实际尝试 | 结果 | 裁决 |
|---|---|---|
| `pq1.5f`，requested maxV1e−7m³ | 288.49秒后`TetGen runtime error code 2`，没有可用网格。错误码未进一步归因；不把它当物理失败。 | 保存明确失败，未继续优化参数。 |
| `pf`，same requested maxV1e−7m³ | .60秒，2954nodes/12722tet，netV误差4.26e−16；所有5912原facet marker齐，边界5914面。无质量refinement，实际maxTetV1.02e−4m³是请求的1020倍；该模式没有落实体积限制。 | 只做几何/接口资源核查，**FE inadmissible**。 |

第二网格`geometry_tetra.npz` SHA`e0b45d8fce7013903cde7e3f1862d3387c7310c7868ee4eb5eca7f499c8795c4`，字段`points_m/tetra/boundary_faces/native_face_markers_1based`；marker=原三角面ID+1。

实查：全facet细分后面积最大误差5.20e−18m²，材料node graph一根，与native一致；主内腔、两journal孔、两叉销孔共5点无tet材料。9处原6mm顶墙射线均覆盖6mm、穿3–20tet，但三处单段达3.29–3.46mm；这只说明射线未漏墙，不能称全域均匀两层。最小tet体积1.883e−23m³，mean-ratio最小2.94e−12、1%分位.00219、中位.0316，最长边.488m，极扁sliver阻止直接结构求解。没有用质量/体积通过掩盖病态单元，也没有跨真孔补材料。检查见`geometry_mesh_checks.json`。

Root独立cross-dot浮点路径检出1个零体积、29个体积≤1e−20m³，以及1582个quality<.01。本目录det路径的0个非正体积只表示该浮点计算路径/零阈值下的结果，**不能无条件声称无近退化单元**；极小体积/sign对运算路径敏感。Root同版复核随后对29个极小tet的存储浮点坐标作精确有理数sign检查，均正，最小约2.016e−23m³；正sign仍不解决sliver病态性。原receipt保留为历史，另绑定Root复核；统一拒绝FE，不修网格或删除tiny tet刷过。

## 两条下一路线与代价

**A 宽壁壳＋局部实体混合。** 从实际主箱内外面提取经修剪中面/厚度与连续肋；journal、销叉、止挡承压和螺栓过渡保留3D实体。壳仍承膜力、弯曲和闭口扭转，不能换成杆。壳—实体耦合要同时传力/矩，并检查重复厚度、刚性耦合范围与切口载荷；新肋与厚度可重新分配。起步面积估计来自现425×240×150/6mm几何的理想中面.384588m²，不是实际截面或减重账本；5–10mm面内步长约3.8k–15.4kquad，6DOF节点估计23k–92k，另加局部实体。6DOF只是传统壳预算，具体solver可能展开成实体、需要重算内存。scikit-fem已装但本轮未确认完整3D壳/混合联接实现，不能把2D板例子当3D壳求解器。可参考CalculiX实际shell→3D展开实现，尚未安装/构建。[scikit-fem实际示例](https://scikit-fem.readthedocs.io/en/latest/listofexamples.html)、[作者shell/solid源码](https://github.com/Dhondtguido/CalculiX/blob/master/src/elements.f)

**B 合法CAD重分块/局部hex与tet。** 由当前尺寸/primitive重建明确平面、圆柱、孔与中面，不沿用为显示CSG优化的细长三角面当每个PLC约束。宽6mm墙采用可控扫掠hex/棱柱与合格过渡，boss局部tet；共享节点/一致接口或经过验证的耦合，不把子域截断面假固支。保持实际孔、闭口体积、载荷与材料边界并做新source hash。Gmsh官方也说明已有CAD通常比重参数化CAD导出的细长STL更利于质量网格；Linux ARM工具获取需要单独有界选择。[Gmsh官方t13说明](https://gmsh.info/doc/texinfo/gmsh.html#t13)

若全件均匀3D细化，仅V=4.0735L：maxTetV1e−8即至少407351tet；当理想等边tet边长3mm，V≈3.18e−9，至少约1.28Mtet。按node≈tet/5仅作规划，后者约256k节点/768k位移DOF，单次12×12单元COO triplet（8B值+两8B索引）约4.4GB，不含稀疏因式填充；实际边界密度会更高，不能当内存保证。局部规则hex/壳—实体路线可避开整个薄壁的均匀tet成本，但需实现真实转矩接口和独立基准验证。`next_route_budget.json`保存公式与未验证估计。

Root选择下一路线；优先落实一个同源完整宽厚单件的合格单元、真实端口和边界，再计算位移/应力/屈曲，不做无界全身细网格。本轮保包装不动，所有mechanical/whole_robot/appearance放行false。

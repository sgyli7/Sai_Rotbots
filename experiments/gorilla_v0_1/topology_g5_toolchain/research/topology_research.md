# Gorilla G5 CPU拓扑优化研究

先用本机CPU完成一根实际承力web的二维多工况SIMP试验，再将候选重建为真实空洞、重新网格化，以三维总成复核。目标是提高给定质量下的承载路径效率；合金屈服、扭转、座孔、止挡和联接仍须单独约束。用户提供的AI图只表达设计意向，不能作载荷或容量证据。G4及更早源保持冻结，本轮不生成新外形或CAD。

## 工具选择与安装范围

实际探测：aarch64 Linux、20逻辑CPU；项目`.venv` Python3.12.14，NumPy2.5.3、SciPy1.18.1可导入；scikit-fem、DOLFINx、PETSc、gmsh、CalculiX、FreeCAD未装。Docker可执行文件存在，daemon/权限未验证；没有调用GPU。完整记录见`runtime_probe.json`。

| 工具 | 实际用途、许可与本机可行性 | 选择 |
|---|---|---|
| NumPy/SciPy自建Q4＋SIMP | 本机已具备稀疏求解；可写可复核多载荷、密度过滤、被动域。DTU官方Python示例是教学基准，多载荷/被动域被列为扩展任务；本轮未验证下载脚本的明确再分发许可，未复制其代码。 | 首个有界CPU试验；先验证FEM与敏感度。 |
| scikit-fem12.0.2 | 原厂BSD-3-Clause；纯Python装配tri/quad/tet/hex。PyPI当前wheel为`py3-none-any`、178478字节，基础依赖仅NumPy/SciPy；本机Python版本相容。并非现成拓扑优化器。 | 后续三维线弹性复核的轻量入口；本轮未安装。 |
| zfergus/topopt | 原厂MIT；有MMA、密度过滤和多载荷示例，但作者标早期开发。真实requirements另含nlopt/cvxopt/matplotlib，其aarch64依赖组合未实装。 | 不比现有NumPy/SciPy路径更短，不作为本轮默认。 |
| DOLFINx | LGPL-3.0-or-later；官方Docker支持arm64，FEM功能广。需要额外MPI/PETSc等运行体系，也不是完整拓扑设计工具。 | 未来模型规模或接触研究需要时再评估，不拉大镜像。 |
| DTU TopOpt_in_PETSc | 官方三维规则网格并行柔顺度/体积约束代码，需PETSc/MPI/BLAS；仓库带LGPL2.1文本，但头文件另有保留权利措辞、README版本要求也有冲突，本轮未闭合全部许可/版本适用性。 | 留作大规模路线，不为了首试安装。 |

工具事实来源：[DTU Python示例](https://www.topopt.mek.dtu.dk/apps-and-software/topology-optimization-codes-written-in-python)、[scikit-fem文档](https://scikit-fem.readthedocs.io/en/latest/)、[BSD许可证](https://github.com/kinnala/scikit-fem/blob/master/LICENSE)、[PyPI](https://pypi.org/project/scikit-fem/)、[TopOpt代码与MIT许可](https://github.com/zfergus/topopt)、[其实际依赖](https://github.com/zfergus/topopt/blob/main/requirements.txt)、[DOLFINx官方安装/许可](https://github.com/FEniCS/dolfinx)、[DTU PETSc代码](https://github.com/topopt/TopOpt_in_PETSc)。下载元数据/许可和SHA见`source_manifest.json`，没有把这些库源码复制为项目实现。

下一步可以隔离安装基础scikit-fem，使用已有NumPy/SciPy，避免改项目锁文件：

```bash
uv pip install --python /home/ethan/Projects/Sai_Rotbots/.venv/bin/python \
  --target /home/ethan/Projects/Sai_Rotbots/.scratch/gorilla_internal_g5_topology_research/runtime \
  --no-deps scikit-fem==12.0.2
```

运行时显式把这个target加入`PYTHONPATH`并记录版本/许可证。上述命令是可行安装入口，未执行；不能把wheel兼容性判断写成已成功导入或已计算结果。

## 优化对象与物理边界

G4先保持宽闭口承力墙、轴承杯座/肩、短journal boss、止挡承压座、销叉、螺栓落台和连接肋为**非设计实体域**；实际cup孔、独立parent/child扫掠、油线/线束、抽销/拉拔与工具通道为**非设计空域**。先优化内部一根web或节点过渡。二维截面不能靠删除闭口扭转壁“省重”，也不能用外甲AABB充当自由内腔。

SIMP用`E(rho)=Emin+rho^p(E0-Emin)`；对每个真实载荷`K(rho)u_i=f_i`，先最小化归一化多工况柔顺度`sum(w_i C_i/Csolid_i)`，材料预算包含所有不可删实体。完整壳、轴承座和紧固件不能从基准质量中消失。此目标优先提高刚度，**不会自动保证最大应力、屈曲、接触或疲劳**；最终比较必须相同接口、载荷、制造过程与质量口径。

密度过滤半径以米定义，网格加密时不改变物理半径；过滤之后使用投影、正确传递灵敏度并保持实体/空域。简单投影不能单独保证局部网格收敛；侵蚀/中间/膨胀多域稳健设计有明确论文依据，原论文还列有2022勘误，本轮没有实现该完整稳健优化，也不将示例阈值或过滤半径称为已保证的最小壁厚。[Wang、Lazarov、Sigmund原厂论文页及勘误入口](https://orbit.dtu.dk/en/publications/on-projection-methods-convergence-and-robust-formulations-in-topo/)

`Emin/E0=1e-6`只为优化时的数值稳定，不是真实空洞材料。必须在二值化的侵蚀/中间/膨胀候选上检查每个载荷垫、轴承boss到固定支承的实际材料连通；不能把孤岛删除后沿用原计算。候选需重网格为真空洞，重新核算反力、柔顺度、应力和净质量。

先选2.5D可加工/挤压web：规定挤出方向、连续连接、最小实体/空洞、刀具与拆装可达；若以后选铸造/增材节点，另立材料、最小特征、拔模/悬垂、后加工轴承座约束。算法滤波不是工艺证明。铝或钢都须实际净截面核算，不用直接替换密度继承钢件资格。

## 本轮真实产出与下一计算

`pilot_2d_input.json`＋`prepare_benchmark.py`生成确定性的80×45 Q4节点/单元、不可删边框、三个分布载荷向量和固定DOF。这里只用G4挑战**标量**校验多工况求解器：135.856kN关节反力、91.730kN当前缸力、14.568kNm力偶分成独立案例。320×180×4mm平板与夹持边界是人为试验，不能反推真实Gorilla轴承接触或材料承载；没有FEM求解、优化图或强度结果。力偶采用实际节点垫质心距离，生成后校验净力/净矩。复现：

```bash
/home/ethan/Projects/Sai_Rotbots/.venv/bin/python \
  /home/ethan/Projects/Sai_Rotbots/.scratch/gorilla_internal_g5_topology_research/prepare_benchmark.py
```

下一runner先过Q4常应变/刚体测试、每工况平衡和求解残差、有限差分灵敏度，再跑有界多工况优化；记录全实心与同质量G4肋壳基线、各工况柔顺度、真实体积、灰区、连通、迭代和CPU时间。网格80×45→160×90保持同物理过滤尺度。当前preparer只创建输入，不冒充solver。

G4三维入口见`assembly_3d_requirements.json`。3t29430N是静态结构工况，当前B的pitch9711.9Nm/缸61.153kN只属于被拒绝旧眼位；新静态hold与正常自重移动各自重建载荷链。不能把G4分别取得的最坏分量任意相加当某一真实截面载荷。缺少真实parent/child杯座实体、O/X压力中心/预载、框架柔度/螺栓、止挡接触、缸眼和正常运动载荷谱，尚不能做可信三维优化。

下一完整模块落实后，才把真实载荷patch与支承坐标绑定同源SHA；全3D重建与独立FEM需覆盖闭口扭转、座孔局部弯曲、止挡/轴承接触、压缩屈曲与制造节点。三维应力峰还要区分点载/约束奇异性和真实过渡。优化密度不是CAD，二维试验通过不等于三维总成或实物门禁通过；本轮physical/whole_robot/appearance均false。

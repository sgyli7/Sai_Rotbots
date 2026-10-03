新增独立数学复核，2026-10-02 18:40 UTC；旧 review.md/json 保持原绑定快照，未覆盖。只 AST 提取 asymmetric_contact_lp，使用独立 resultant 及解析期望，未 import/call main evaluator，未重核几何或运行整机。

**结论。** 新 domain guard、失败 None 和 HiGHS dual certificate 的符号正确。原三个域内解析例加原 Fx 域外例全部符合期望；新增 Fy、净水平合力为零的 yaw couple、z-plane reject 及支承区外求解失败也符合期望。

| 解析例 | 解析/计算 t | conditional feasible | 独立 dual lower bound |
|---|---:|---|---:|
| offset c=-50, positive-side cap20/negative cap10 | 0.5 | true | 0.5 |
| offset c=-80, 同容量 | 2 | false | 2 |
| 两轴共享 allocation [20,30,30,20] N | 1 | true（含声明容差） | 1 |

四角坐标 (±1,±1,0)。前两例外载 100 N 重力在 (0.2,-0.3,1)，正 x 接触合力必为60N，因此两例力分别为+10/-20N；第三例两模型 F1=f0、F2=-f1，正/负容量20/30N，中点重力使 f0+f1=50N，解析 min max(f0/20,f1/30)=1。所有输出与解析值一致。详细模型、反力和各证书见 JSON。

**双证书推导。** 令 x=[f,t]≥0，objective=[0,…,0,1]，A x≤b，E x=target。若 λ≤0、r=objective−Aᵀλ−Eᵀy≥0，则对任意 primal 可行 x：
objective·x ≥ (Aᵀλ+Eᵀy)·x ≥ bᵀλ+targetᵀy。
因此代码 42–45 行的 λ、reduced cost、dual objective 与 gap 符号正确，忽略显式 lower-bound marginals 不缺项，因全部 lower bound 都是0，其 reduced costs 已覆盖。三个算例独立从 A/E/b/target 重建，λ最大≤0、reduced最小=0，eq residual≤1.78e-14，ineq/bound violation=0，primal-dual gap绝对值≤3.34e-16；与报告 reduced costs 完全一致。

当 t>1 且声明容差内有效的 dual lower bound>1，才把 capacity-constrained allocation 记false；t=2例对此给出数值下界。t≤1 的有效 primal witness可给条件存在性，不需dual才成为存在证据；objective最优性的数值证书仍有独立用途。当前边界t≈1采取1e-7容差，不能称精确数学/区间证明。

**域守卫与失败。** 26 行拒绝总Fx、Fy或Mz超过1e-7及 contact z超过1e-8。原 Fx=10N 域外例、Fy=10N、两相反水平力构成 Mz=10Nm但净Fx/Fy=0、contact z=.001m，均抛 ValueError。将重力移到 x=2m，超四角支承凸包，HiGHS报告 infeasible，函数 solver_success=false 且 conditional feasible=None；未把没有独立 infeasibility certificate 的求解失败混作容量不可行。

**仍可补的一项证书记录。** 39–40 行 primal validation验eq和A，不显式记录所有 x≥0 的 bound residual。三个算例独立验 max(0,-min(x))=0；建议把此残差纳入声明容差和输出，完整覆盖 primal 条件。此处是数值证书完整性缺口，没有证据说明当前实测解违反非负约束。

**preview读取范围。** .scratch/gorilla_d_mass_contact_preview.json 有4姿态×4=16cases，读取时16个conditional true、16个dual-valid flag、最大报告gap约2.33e-15，physics_accepted=false。其 evaluator_sha256=3df96cdd…，与本次 evaluator cd5e7027… 不同；这些只是该 preview 本身带旧hash的读取事实，不是独立复算16个新整机 LP。不能据16个True宣称manufactured assembly、3D brace sharing、动态/摩擦、连续热或完整串联载荷放行。

本次源绑定：

- evaluator SHA256: `cd5e70271a962c73168ce747823ea3af52742c3370ddc62e0dd7d07f77f8cee7`
- asymmetric_contact_lp source SHA256: `526b0fbd805d8fa7cebc56509084846fadc53dbfb350601aec5a7c502ffe53cd`
- current unchanged at finalize: `True`

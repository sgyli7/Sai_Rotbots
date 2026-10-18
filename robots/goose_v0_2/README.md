# Goose V0.2

**当前入口：[physics_v0_2_20261018_04](models/physics_v0_2_20261018_04/README.md)，14块低复杂度凸碰撞代理。** 实际MuJoCo凸包为14块、547个支持顶点、单块最多63点、1038个凸三角面；加载源网格为548顶点/1040面，二者分别统计。

04只替换碰撞代理。物理合同、执行器合同、逐项质量账和运行适配器与02逐字相同；设计总质量16.970203929 kg、23个刚体、18个控制轴、4个内部机械坐标，驱动/物理200 Hz、策略接口50 Hz。代理不参与质量计算，完整惯量、轴系、闭环和连续扭矩/速度/电源降额仍来自硬件合同。原生CAD、硬件资料和02源文件未改。

- [运行说明与唯一加载入口](models/physics_v0_2_20261018_04/README.md)
- [物理合同](models/physics_v0_2_20261018_04/physical_contract.json) · [执行器合同](models/physics_v0_2_20261018_04/actuator_contract.json) · [逐项质量账](models/physics_v0_2_20261018_04/mass_ledger.json)
- [凸块来源与机械相邻例外](models/physics_v0_2_20261018_04/collision_manifest.json) · [源身份](models/physics_v0_2_20261018_04/source_snapshot.json)
- [实际碰撞体三视](images/physics_v0_2_20261018_04/runtime_contacts_three_views.png) · [可旋转GLB](models/physics_v0_2_20261018_04/preview/runtime_contacts.glb) · [OBJ](models/physics_v0_2_20261018_04/preview/runtime_contacts.obj)
- [独立解包及硬件数据不变核对](evidence/physics_v0_2_20261018_04/independent_release_gate.json)
- [直接原生CAD夹持轮廓检查](evidence/physics_v0_2_20261018_04/independent_native_grip_contour_sealed_source.json) · [关键接触检查](evidence/physics_v0_2_20261018_04/independent_critical_contact_sealed_source.json)
- [接触参数与Sim2real标定边界](evidence/physics_v0_2_20261018_03/sim2real_contact_boundary.json) · [硬件续办](hardware/training_physics_20261018_followup.md)

真实下夹持面侧前缘在03中漏覆盖4.041mm，已作为[真实CAD拒绝用例](evidence/physics_v0_2_20261018_03/native_contact_reference_check.json)保留。04只在原下喙凸块补入已采用TPU垫的真实平面边界，其余13个OBJ与03逐字相同，不增碰撞块、不改变硬件数据。两份小原生BREP和可重放轮廓随源保存，采用身份由原生质量/COM与whole05保存面放置相互核对。

有限直接CAD复核中，下夹持轮廓在数值精度内吻合、无虚增凹口或孔区；上夹持轮廓最大缩入约0.025mm，脚底约0.524mm。上下真实夹持平面、嘴部真实物体、双脚地面、有限颈部姿态及身体–小腿/跨脚阳性检查另有记录。只有明确机械相邻的6对例外，非相邻自碰保留。原整机2.4315mm/躯干6.9954mm数值是相对02父代理的有限方向差，不能当作相对native CAD或实体的绝对误差，更不是全ROM认证。

最终04同MuJoCo3.10、固定CPU的原生步进中位值约19.8–33.3微秒；参考驱动适配器在400步检查中平均约0.184毫秒/物理步。对同一硬件291块模型，最终04碰撞查询快42.8–48.4倍。旧14的1.5倍相对成本目标未获放行，03历史对照中部分姿态慢约2倍的拒绝结果保留，04不宣称该目标已达。GPU和批量训练吞吐未测，不宣称全任务或旧版同吞吐已验证。

摩擦系数0.65与接触柔度仍是设计假设，condim3未实证滚动/扭转阻力；接触几何通过不等于真实抓持力、地面牵引或温度/磨损响应已标定。实物质量/COM/惯量、摩擦柔度、电机力矩速度与延迟仍须台架实测。后续标定若改变物理合同或接触则另发版本，不热覆盖本包。

当前按[稳定夹持、100g举起与倒退拖运验证方案](design/grasp_lift_drag_validation.md)推进硬件优化：Rotbots本聊天负责机体/低矮理货车、V0.2拖拽验证及证据决策，数据归Sai_Lab独立V0.2入口维护；既有Picking聊天负责V0.1，不再承接拖拽或购物车任务。目标是在像鹅的外观约束下提高真实可持续载重/拖拽能力，正式重载超过16.9702kg自重，低矮理货车首版按20kg有效货物载荷设计、车重另计；带轮车和无轮滑块分榜，100g举起保留基础回归。第一单[局部夹持审核](evidence/grip_100g_pilot_001/pm_review.md)与第二单[0.5–4kg前置拖运审核](evidence/ground_drag_load_002/independent_review.json)保留失败证据，尚未证明20kg或完整整机拖运；04输入未变。GPU与训练更新为零，旧长期训练和定时任务保持暂停。02的291块及03漏边版本不作为当前入口。

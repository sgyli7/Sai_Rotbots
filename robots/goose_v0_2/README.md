# Goose V0.2

**[独立训练物理包 physics_v0_2_20261018_02](models/physics_v0_2_20261018_02/)**：固定设计质量 **16.970203929 kg**，23 个刚体、18 个控制轴、4 个内部机械坐标；驱动和物理更新200 Hz，策略接口50 Hz。

本轮按用户最新要求优先交付训练物理数据。它来自实际 whole05 和明确的电气固定质量分配；任务训练、实体安装和制造仍是独立工作。运行和接触验证结论以包内 manifest 与配套验证记录为准。

- [运行说明与唯一加载入口](models/physics_v0_2_20261018_02/README.md)
- [物理合同](models/physics_v0_2_20261018_02/physical_contract.json) · [执行器合同](models/physics_v0_2_20261018_02/actuator_contract.json) · [逐项质量账](models/physics_v0_2_20261018_02/mass_ledger.json)
- [源身份索引](models/physics_v0_2_20261018_02/source_snapshot.json)
- [硬件续办入口与未完事项](hardware/training_physics_20261018_followup.md)

默认按连续设计能力限制扭矩，峰值单列且禁用；参考适配器执行速度曲线、电压降额、200 Hz目标斜坡和350 W总正机械功率预算。新脚raw8和head17装拆方案未采用，保留正确旧六件脚部机械回退及原脚底接触。包不包含任务、奖励或策略，不修改Sai Lab训练仓。

后续硬件须服从冻结的逐体质量、重心、惯量、轴系、外接触与功率合同。需要改变时另发物理版本，保留本包，不热覆盖。TangPa外观一比一、完整实体装配、热、疲劳及实测称重未因本包交付而被视为完成。

本次已按有源结构筛查恢复双髋铝材，连同正常压盖/螺钉配套净减重441.069076 g；未发布的17.411 kg基线保留为历史，不进入本次发布。

- [实际碰撞体可旋转GLB](models/physics_v0_2_20261018_02/preview/runtime_contacts.glb) · [OBJ](models/physics_v0_2_20261018_02/preview/runtime_contacts.obj)
- [实际运行碰撞体三视](images/physics_v0_2_20261018_02/runtime_contacts_three_views.png)
- [独立验收记录](evidence/physics_v0_2_20261018_02/independent_release_gate.json)

运行模型实际291碰撞叶，14是语义职责数；不宣称它仍是旧14叶。

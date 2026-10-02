# 当前装配的同版参数与运动学参考

2026-09-30。**第三、第四阶段仍未完成。此增量关闭新轴位、质量账与交换格式不同版的问题；碰撞、硬件和最终外观未放行，不能用于行走或夹拖训练。** 原来的阶段期限已经超过，本页不重新计时。

## 本次交付

- [SI 契约](../configs/body_bay_reference_contract.json)、[逐体 CSV](../configs/body_bay_reference_bodies.csv)、[关节 CSV](../configs/body_bay_reference_joints.csv)。19 个刚体、18 个主动轴，裸机条件质量 10.052499 kg，测试用 50 g 物体没有计入裸机。所有刚体的质量、重心、完整惯量直接来自[当前质量账](../evidence/body_bay_component_parameters.json)。
- [MJCF](../models/body_bay_reference/robot.xml)、[URDF](../models/body_bay_reference/robot.urdf)和对应显示资产带入当前 262 件装配。场景及几何输入逐一核验哈希；源文件仍为原生 CAD 和四边面，运行显示交换网格三角化。旧第二阶段模型、契约与关节顺序保持原样。
- [跨格式验证](../evidence/body_bay_reference_validation.json)独立解析 URDF 坐标并与编译后的 MuJoCo 比较，核对质量、局部重心及重建完整惯量。验证包含 7 个原静力任务姿态和 32 个任意根位姿/关节角，仅验证坐标计算，不将任意角度叫作可执行姿态。

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/models/build_goose_body_bay_reference.py
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/diagnostics/check_goose_body_bay_reference.py
```

根原点采用当前 SI 台账的世界零点；全机 3.7 mm 脚底基准抬高已经包含在轴位、组件和显示坐标中，不能再加一次。MJCF 使用完整源惯量的主值和主轴四元数编码，URDF 与中立 SI 数据保留完整张量。所有关节仍采用原来的轴序、SI 单位与候选驱动限值；Godot/Jolt、Unity、Bevy 的实际动力学适配并未验收。

## 使用边界

模型中全部显示几何的碰撞标志关闭，URDF 不包含碰撞节点。空心壳和带孔支架如果直接变成整块凸包，会凭空堵住内部空间；本轮不继承旧碰撞资产来掩盖新轴位变化。完整碰撞模型需要在实际承力装配收尾后生成和验证。这里没有地面接触、弹性脚底或步行控制证明，没有启动 PPO，未接入现有训练入口或默认模型登记。

当前外观仍有未完成头嘴、踝部和壳体固定零件。当前 25 组大转角装配筛查仅 8 组通过；原来的范围只是候选，连续组合运动和线束净空未通过。能加载、有一致惯量或 FK 正确均不能作为制造、动态运动或最终外观放行。

## 剩余整机交付工作

1. **机械与运动空间**：颈根、头嘴、踝部和脚底的完整承力连接；壳体固定、手动门铰链/锁止；轴承和紧固件容量；连续动作、线束和大转角碰撞。1
2. **电气**：准确驱动电压及回馈窗口；有额定依据的主保护、制动/泄能、线束和接线；器件实际容纳及连续热预算。
3. **整机交付**：完整同版碰撞模型、限定任务运动验证、最终实体装配外观与交换资料的一致性。新训练版本须另经门槛验收，不能因为本参考轴数相同而复用旧策略。

现有[原生装配检查点](body_bay_native_checkpoint.md)及失败记录继续保留。纯装饰圆角、涂装和焊点细化可后置；上述承力、供电和净空问题仍属于工程交付门槛。

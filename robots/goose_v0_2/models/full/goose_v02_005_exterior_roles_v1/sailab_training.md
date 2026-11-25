# Goose V0.2 · Source007 43 凸体训练包

站立入口实测支持 2 或 32 个并行环境。保留原 007 的 21 个刚体、18 维动作、65 维基础观测、质量惯量、关节与驱动。31 个凸网格可接触地面和物体，其余 12 个凸网格仅作用于各自的关节对。原脚底和喙部精密接触垫一并保留。

在锁定环境解包并运行。

```bash
python launch_native50.py --check-only --num-envs 32
python launch_native50.py --mode train --num-envs 32 --iterations 100000 --output artifacts/train/segment_001
python launch_native50.py --mode train --num-envs 32 --iterations 100000 --resume artifacts/train/segment_001/receipt.json --output artifacts/train/segment_002
```

本次从新训练开始。续训只接收同模型、同软件、同环境数的检查点。

| 32 环境实测 | 594 体版本 | 58 体版本 | 43 体版本 |
|---|---:|---:|---:|
| 站立环境步／秒 | 1508 | 1338 | 1343 |
| 50 mm 落地环境步／秒 | 1358 | 1230 | 1257 |

CPU 对照原版 007 的 1420 个姿态，报告中的接触深度最大差 0.451 mm。CPU 与 GPU 均检查了左右两个侧倒姿态的头壳、相应小腿和后壳支撑点。两种环境数均实际执行 PPO、存档和续训。

验收涵盖站立、50 mm 落地、重置、指定关节接触与上述支撑点。移动、完整起身、拾取与拖拽技能按各自任务验收。
记录及整机对照图见 `qualification`。

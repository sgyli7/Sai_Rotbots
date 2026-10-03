# Gorilla E2 历史包装诊断快照

这是 2026-10-02 20:25–20:40 UTC 捕获的独立包装试探，**不是 E2a 当前 master，也不是 final E2a 整机碰撞核查**。它保持旧记录的来源和适用范围，不继承后续变更的几何/质量/动作结论。

来源为结构 SHA `373a88cfdf38f98c86566d19ebec922b46acec74d90c8b60c45dec60544905b2`（587 行）、system SHA `3f7cb1734ab281ca7a8ff3bbe0051eef7302219d44a77e58ee6be2ca017668c5`（821 行）、upper SHA `c608630753397ca2596b260d755662bb5e5df527d10c968af560fe16b716e263`（15 行）。原甲来自 C15，SHA `7a1e49f45838303ca5fd86265dc9980c10cde85ed7626424136afd3863aa5886`；唯一审美权威仍是用户确认的 AA3 四视图。

精选原记录完整保留：`packaging_review.md`、`packaging_candidate_task.json`、两张同尺度真实面投影、`full_capture_screen.json`、旧名单下的 `review.json` / `independent_current_system_screen.json`、`internal_bank_probe.json`、原始输入和四个复现脚本。大 JSON 以 gzip `mtime=0` 保存，脚本原字节以 `.py.txt` 保存；它们是冻结复现输入，不作为新运行代码入口。

范围分别是 system 329 个指定对象对 111 原甲的中立交叠筛查、结构 587 行对原甲、upper 15 行对原甲。404 对记录使用较早 286 名单，416 对记录使用捕获时全部新增材料与指定保留模块；两者不能混作同一范围。平移试探在结构源出现前运行，其 new-new 筛查只含 system / upper。投影没有全部旧非承力饰件，不能作为新的审美成品或硬件验收。所有几何、物理、稳定契约和审美门禁仍为 false。

结论边界是先做 **P0 内部联合重排、外表面改量 0 mm**；P1 功能风口和 P2 局部外改须有同工作点热量/实际干涉等证据，并在同源正、侧、后、顶四视候选上获得用户审美接受，才可替换外观权威。这里的毫米阶梯是搜索预算，不是物理充分性结论。

## 恢复与复核

`snapshot_manifest.json` 记录存储文件和解压后原 SHA，`restore_map.json` 逐文件记录历史 `.scratch` 恢复路径。恢复时先核对 stored SHA，对 `gzip_mtime_0` 解压，再核对 uncompressed SHA；`.py.txt` 按 restore_destination 恢复成原 `.py` 名称。C15 输入没有重复复制，恢复映射明确引用已有 `experiments/gorilla_v0_1/appearance_c_round_fifteen/appearance_c_scene.json`，核对上述 SHA 后恢复为 `.scratch/gorilla_internal_e2_packaging/source_appearance_c_scene.json`。

只在独立复现 checkout 恢复，避免覆盖活跃 `.scratch` 候选。恢复完整映射后，原脚本中的历史绝对根和原输入路径保持历史含义；若换路径，先记录路径适配而不改变几何或校核门槛。`original_capture_manifest.json` 是原捕获 manifest 的原字节副本，保留其 `.scratch` 身份。

`restore_map.json` 的 `historical_producer_input_aliases` 还给出了分析器最初读取的上游 `.scratch/gorilla_internal_e2_system/`、`upper/`、`structure/` 路径。这些别名使用同一份存储字节，不另复制资料；如需重跑原 `analyze_packaging.py` 或保留其原读取入口，须在独立复现 checkout 同时恢复别名。尤其投影脚本会检查上游 structure 文件是否存在，不能只恢复打包目录就声称全体 1423 行复现。已有仓库 C15 / D 固定输入仍须按原捕获 manifest 的 SHA 复核。

# SaiRobots 工程目录与命名规范

本文件是工程唯一的目录与命名规范。新建、移动、重命名文件和提交 Git 前必须遵守。
采用「按机器人组织资料，公共代码与能力共享」；按需创建目录，不预建空目录。
目录的存在不代表相应硬件、制造资料或验证已经完成。

## 1. 目录与职责

```text
SaiRobots/
  sai_robots_engineering_rules.md  # 唯一规范正文
  README.md                       # 项目介绍、机器人列表、使用入口
  CHANGELOG.md
  CONTRIBUTING.md
  LICENSE
  THIRD_PARTY_NOTICES.md
  pyproject.toml
  uv.lock
  robots/
    catalog.json                  # 稳定机器人 ID 与模型路径登记
    <robot_id>/                   # 现有 Sai_Agent_001、Sai_Agent_002
      README.md                   # 本机器人的唯一资料导航
      design/                     # 需求、决策、方案、尺寸说明
        concepts/                 # 外观概念图、提示词与概念说明
      cad/
        source/                   # CAD 编辑源及作为输入的 STEP/BREP
        exports/                  # 导出的 STEP/STL、工程图、导出记录
      source/                     # 建模输入网格、NPZ、来源与导入记录
      models/                     # 可交付、可加载的仿真模型
        full/                     # 完整模型及配套网格，保留内部布局
        tasks/                    # 任务与运动学描述
      hardware/                   # BOM、电路、接线、装配资料
      configs/                    # 本机器人专用运行配置
      policies/                   # 本机器人独占的交付策略
      images/                     # 实际模型渲染、仿真截图、实物照片
      evidence/                   # 本机器人的精选验证记录
  shared/
    components/                   # 多机器人共用的零部件设计与资产
    configs/                      # 共用训练、运行配置
    policies/                     # 共用交付策略，含显式实验选项
  src/sai_agent/                  # 共享控制、仿真、运行、资源定位代码
  scripts/
    models/                       # 模型构建、转换、导出、渲染入口
    cad/                          # CAD 处理与生成入口
    training/                     # 训练、策略导出入口
    evaluation/                   # 评估入口
    diagnostics/                  # 性能、数值、回放诊断入口
  integrations/
    godot/                        # Godot 接入代码与最小示例
    unity/                        # 实际引入时创建
  experiments/
    ledger.jsonl                  # 精简实验索引与结论
    <robot_id>/<experiment_id>/    # 配置、候选策略、精选结果
  tests/                         # 自动测试
    fixtures/                     # 测试必需的输入样本
  docs/
    guides/                       # 项目级使用与维护指南
    architecture/                 # 公共架构、接口、控制协议
    research/                     # 多机器人共用调研
    releases/                     # 发布记录与发布验证
    validation/                   # 公共代码、打包、跨机器人验证
  third_party/                    # 确需随仓库保存的第三方源码
  licenses/                       # 第三方许可证原文
  artifacts/                      # 本地生成与运行产物，不入库
  .scratch/                       # AI 临时工作文件，不入库
```

根目录只保留项目入口、规范、许可证、Git/CI/格式/依赖配置及根 AI 入口。
禁止新增根目录模型、截图、实验报告、临时脚本，以及未登记的一级目录。
`models/full/` 保留 `assets/`、`visuals/`、`contacts/` 等资源包内部结构，
不为统一文件扩展名拆散模型与关联文件。

## 2. 文件归属

先确定「属于哪个机器人」，再确定「是什么资料」。
只有确实被多个机器人使用的内容才能放入 `shared/`。

| 内容 | 唯一归属 |
|---|---|
| 需求、方案、尺寸说明、设计决策 | `robots/<robot_id>/design/` |
| AI 外观概念图、提示词 | `robots/<robot_id>/design/concepts/` |
| CAD 编辑源和作为设计输入的几何文件 | `robots/<robot_id>/cad/source/` |
| CAD 导出交换文件、打印网格、工程图、导出报告 | `robots/<robot_id>/cad/exports/` |
| 生成模型所需的输入网格、NPZ、来源清单 | `robots/<robot_id>/source/` |
| MJCF、URDF、物理参数、显示与碰撞网格 | `robots/<robot_id>/models/` |
| BOM、电路、接线、装配说明 | `robots/<robot_id>/hardware/` |
| 实际模型渲染、仿真截图、实物照片 | `robots/<robot_id>/images/` |
| 专用配置、独占交付策略 | 该机器人的 `configs/`、`policies/` |
| 共用零部件、配置、交付策略 | `shared/` 对应分类 |
| 通用可导入的程序逻辑 | `src/sai_agent/` |
| 构建、训练、评估等命令入口 | `scripts/` 对应分类 |
| 候选方案、候选策略、可复现实验资料 | `experiments/<robot_id>/<experiment_id>/` |
| 精选机器人验证记录 | `robots/<robot_id>/evidence/` |
| 发布/公共验证 | `docs/releases/`、`docs/validation/`，可用 `evidence/` 子目录 |
| 日志、录像、连续检查点、临时导出 | `artifacts/<robot_id>/<run_id>/` |

- 按用途分类，不仅按扩展名分类。STEP 可以是输入或导出，JSON 可以是参数、配置或证据。
- `source/` 保存建模输入，`src/` 保存程序代码，两者不得混用。
- 机器人目录只保存数据与资料；CAD 处理等脚本统一放入 `scripts/`。
- 通用程序不得反向导入 `scripts/`。运行代码和多个脚本复用的逻辑放入 `src/sai_agent/`。
- 共享资产维护一份源文件；机器人交付必需的生成副本可保留，须记录来源与版本。
- 同一策略的跨机器人验证分别归属各机器人，不得把 001 的结果当作 002 的结果。
- CAD 和物理参数分别注明设计依据；概念图不能作为尺寸、质量或惯量依据。
- 源文件缺失时记录缺口，不补造来源，不把显示或仿真模型称为完整制造资料。
- `catalog.json` 保持稳定 ID；运行模型通过 `sai_agent.paths.model_root()` 定位。

## 3. 命名与 AI 工作

- 新增自研目录、文件主名使用英文小写 `snake_case`，例如 `cargo_shell.step`。
- 禁止空格、中文文件名，以及 `final_final`、`new2`、`backup` 等不能表达用途的名称。
- `README.md`、`LICENSE`、工具固定名称、第三方原始名称保留其要求。
- 机器人目录名必须与登记 ID 完全一致；现有 `Sai_Agent_001`、`Sai_Agent_002` 保持原样。
- 登记后的机器人 ID 不得随意改名；已发布策略名称、关节名称、模型内部标识属于兼容接口。
- 原有模型资源包内部名称、历史实验策略和历史证据名称保留，防止破坏引用和追溯。
  此例外仅适用于本次迁移保留的既有内容，新增内容仍遵守命名规则。
- 实验名使用稳定名称，例如 `stairs_012`；一次实验中的原始候选不能被下一次实验覆盖。
- 原有 `tests/fixtures/gpu-stair-contact/` 作为历史复现样本保留名称和内容。

规范正文只维护在本文件：

- Codex 的 `AGENTS.md`、Claude 的 `CLAUDE.md`、Cursor 的 `.cursor/rules/` 引用本文件，不复制正文。
- AI 配置只允许位于工程根；禁止在机器人、模型、代码目录中散落规则文件。
- AI 新建文件前必须确定归属，不能确定时先使用 `.scratch/`。
- 禁止擅自创建一级目录或 `misc/`、`others/`、`temp/` 等兜底目录。
- 每个机器人只维护一个 `README.md` 导航入口；专题文档归入分类，不重复维护相互矛盾的说明。
  项目根、独立实验或工具的 README 不属于机器人导航入口。

## 4. 实验、生成物与 Git

生成物是否入库，取决于它是否是交付或复现必需内容。

- 入库：设计源、必要建模输入、交付模型、策略与元数据、实验配置、精选成功和失败记录、必要测试样本。
- 不入库：环境依赖、引擎缓存、完整运行日志、连续检查点、临时截图、AI 抓取资料和临时评审报告。
- `experiments/` 保存可复现实验资料；`artifacts/` 保存运行中产生的大量输出。
- 交付策略可以标明 `experimental`；位置不代表正式验收通过，也不代表成为默认策略。
- 模型、策略和验证记录应关联机器人 ID、源版本或哈希、配置和运行环境。
- 不因失败删除关键记录，不覆盖已发布策略来保存新候选。
- CAD 软件、引擎安装、依赖、其他项目工作副本留在各自软件或项目位置，不复制进本仓库。
- 第三方源码保留上游布局和许可证；机器人衍生资产可随模型保存，须保留来源清单。
- 同名策略只有确认内容及用途相同后才能合并。已交付副本与实验快照可为复现分别保留。

`.gitignore` 至少覆盖 `.venv/`、Python/测试缓存、`artifacts/`、`.scratch/`、
`build/`、`dist/`、引擎缓存、本机 AI 状态；保留根共享规则入口。
二进制标记和第三方许可证的既有换行设置不得在整理时改动。

运行 wheel 使用显式包含清单，只包含机器人登记、模型、交付策略、运行配置、
适配器、许可证和代码。不得整目录包含机器人 CAD、源设计、图片、历史证据与实验。
新增机器人须同时更新登记、wheel 包含清单和源码/安装包加载验证。
源码分发可包含设计和复现资料，不等同于运行 wheel。

## 5. 移动与验收

- 整理使用独立提交；移动时同步更新程序引用、脚本导入、登记、打包、CI、文档链接。
- 不夹带机器人结构、质量、关节、控制参数或验收标准的修改。
- 历史 JSON、实验台账中的哈希和运行路径保持原始含义；用迁移说明记录新旧路径。
- 两个机器人均须从源码和安装包加载各自模型；默认 001、命令和导入保持兼容。
- 检查现有测试、模型加载、Godot 启动、策略引用、脚本入口和本地文档链接。
- 模型、网格、CAD、建模输入、策略与历史记录的哈希不变；仅调整必要路径引用。
- 发布包包含全部运行资源，排除设计源与历史产物。

本次迁移的具体路径映射与验证见 [目录迁移记录](docs/guides/directory_migration.md)。

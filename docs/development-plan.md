# 开发计划

更新日期：2026-09-20。承接历史执行记录（v0.1.1 之前 D1—D14 与 §八/§九回填，见 `docs/archive/pre-skill-product/对齐层-开发执行计划.md`）；本文件只记当前状态与后续计划。

## 已完成

- **v0.1.1（已发布推送）**：schema v0 全命令、六规则检出、双组断言 + command 检查器、demo-project 带真代码、三宿主装配、import-speckit 黄金快照；维护轮（提交 6d996a4）统一 verify 退出语义、配置校验收紧、Spec Kit 官方格式兼容、`detect --fail-on` 门禁、安装命令统一 git 直装。
- **导入边界修复（09-20）**：`##`/`###` 级 Acceptance Scenarios 标题在故事边界判断前识别，验收内容不再落入"规格概览"；新增二级/三级标题与后续故事隔离测试。
- **Skill 产品化改造（09-20）**：三技能合并为单一 `specripple` 技能（SKILL.md + run.py 自包含入口 + references + templates）；`build-skill` 构建自包含分发包（runtime 内置仓库源码与锁文件，专用缓存虚拟环境）；init 重写（内容指纹清单、旧技能迁移：未改则移除、改过则保留并报冲突）；首次接入流程（onboarding）；旧技能目录移除（原文存档 `src/specripple/legacy/`）；旧规划文档归档 `docs/archive/pre-skill-product/`。
- **安装与文档修复（09-20 复审后）**：init 重装对照上一份清单指纹——用户改过的受管文件保留并逐个报冲突，未改的才升级（新增重装保护/指纹升级/无清单未知内容三组测试）；init 随装完整 runtime（与 `build-skill` 共用 `runtime_file_plan` 装配计划，纯 init 安装无全局 CLI 也可运行，新增端到端测试）；旧技能迁移识别覆盖全部已发版本文（e49998a/6d996a4 变体注册表，原文经 `git show` 字节级提取）；修正参考文档行为错误（`index.json` 在项目根、`command` 检查器不看空 stdout）、README×2/migration 的 zip 解压路径、architecture 的 `uvx specripple` 表述，并按修正后说明真实安装验证一次（zip 顶层 `specripple/` → 复制 → run.py detect 0 findings）。
- **wheel 普通安装随装 runtime（09-20）**：wheel 以 `specripple/_runtime_src/` 包数据强包含 runtime 构建输入（pyproject/uv.lock/README），init 装配回退链扩为"源码检出 → 已装技能自带 runtime → wheel 载荷"，普通 `pip/uv pip install` 后 init 同样产出可独立运行的 runtime。验收走真实分发路径并有回归钉住（`tests/test_distribution.py`：构建 wheel → 全新 venv 安装 → init 临时业务项目 → 安装后 `run.py` 成功/门禁失败/配置错误退出码 0/1/2）。
- **v0.2.0 版本检查点（09-20）**：上述全部工作以单提交形成检查点（未推送）；新增 CHANGELOG.md，版本 0.1.1 → 0.2.0。

## 下一阶段（按优先级）

### 1. 收尾本轮（维护者动作）

全量测试（150，含真实分发路径 e2e）、真实包构建、两个实测仓回归（code-run 7/7、codex-run 43/43，退出码真值 0）与新版单技能宿主回放（`manual-tests/skill-run/`：普通项目 → init 安装 → codex exec 首次接入 → 需求变更同步到门禁全绿，日志+README 可回放）均已完成；已按维护者指示形成 v0.2.0 版本检查点提交（未推送，推送与打标签由维护者执行）。

### 2. 分发卫生（小工作量，先做）

- 三平台 CI（GitHub Actions：uv sync + pytest，Windows/Linux/macOS 矩阵）。
- LICENSE 选型与补文件（维护者决策，建议 MIT 或 Apache-2.0）。
- README/文档中声明无遥测、无网络调用（除 uv 安装依赖）。

### 3. v0.2：最小变更追踪（核心价值补强）

围绕"影响集是候选集而非结论"补：

1. 读 Git 基线与当前差异，识别哪些条目真的变了；删除条目时用旧图计算影响。
2. 最小来源映射：条目 → 代码/测试文件路径（frontmatter 或侧表），impact 输出文件路径与证据。
3. 候选三态落盘：每个候选记录"已修改 / 已检查无需修改 / 尚未确认"，不允许无解释消失。
4. PASS_TO_PASS 基线保护：断言删除、削弱、越界改动产出可审查差异。
5. 统一报告：覆盖情况 + 未解决冲突 + 测试结果 + 整体结论，区分"通过"与"证据不足"。

验收标准：在 specripple 自身迭代中使用；一个真实仓库的关键工作流全程三态可追溯。

### 4. 增量收益验证（决定后续扩张方向）

固定宿主、模型、初始仓库与用户请求，约 20 个有人工预期结果的变更，三配置对照：宿主加普通同步提示 / 宿主加流程技能 / 宿主加技能 + 完整 CLI。记录漏改、无关修改、错误通过、误报、人工纠正次数、耗时与 token。预期影响与关键验收由独立于执行 Agent 的人工评审判定。若 CLI 相比仅技能无明显减漏改，收缩为技能包 + 检查器；收益成立再加 MCP 与检索通道。

### 5. 后置项（不在当前承诺内）

MCP server（FastMCP：impact/detect/verify 三工具）、BM25+RRF 检索通道、CRR 报表、Claude Code 真机实测、更多宿主薄壳。触发条件：第 4 步收益验证成立，或有真实使用者提出接入需求。

## 论文轨（并行，另行排期）

变更传播案例、消解对话与三态记录可直接作为实验素材； 英文论文骨架待恢复后重启。

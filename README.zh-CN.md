# specripple

[English](README.md) | 简体中文

面向 AI 编程代理的"变更驱动多工件对齐"工具：你改需求，agent 列出带证据的影响集、传播编辑、与你逐题消解冲突，并用可执行验收把住完成关——而不是直接宣称"做完了"。

产品是**一个技能**；底层由零 LLM 的确定性 CLI 负责检查。

## 状态

v0.2.0（2026-09-20）：skill-first 产品——原三份技能合并为单一 `specripple` 技能，内置自包含运行时（`scripts/run.py`，无需安装 CLI）、带内容指纹清单与旧技能迁移的安装器，且每条安装路径（源码检出/技能包/wheel）都随装完整运行时，附首次接入流程。见 [docs/architecture.md](docs/architecture.md) 与 [CHANGELOG.md](CHANGELOG.md)。

## 快速开始（60 秒）

```bash
uvx --from git+https://github.com/midiexiangdeliren-crypto/specripple specripple demo
```

不发布 PyPI（维护者决策）——uv 直接从 GitHub 拉取。

## 装进你的项目

**路径 A：技能包（推荐）。** 获取自包含包（在仓库检出里跑 `specripple build-skill --out dist`，或从 GitHub release 下 zip），解压后把顶层 `specripple/` 目录复制到你项目的 `.agents/skills/specripple/`。首次使用时技能内的 `run.py` 会用 uv 自动建好缓存运行环境。然后把 `.agents/skills/specripple/references/onboarding.md` 交给宿主 Agent 跑首次接入（四选一：已配置 / 导入 Spec Kit / 普通项目最小条目化 / 只配验收）。

**路径 B：CLI + 安装器。**

```bash
uv tool install git+https://github.com/midiexiangdeliren-crypto/specripple
specripple init --host codex      # 或 --host claude，在你的项目根执行
```

`init` 复制技能、在 AGENTS.md 写入带版本戳的标记块，并把每个受管文件的 sha256 指纹记录进 `.agents/specripple-manifest.json`。重跑 `init` 即升级；`--remove` 卸载；你手动改过的文件永远不会被碰。从 v0.1.1 的三技能安装升级？重跑 `init` 自动迁移：未修改的旧技能自动移除，修改过的保留并报冲突，由你裁决。详见 [docs/migration.md](docs/migration.md)。

## 一次对齐怎么跑

你改完需求对宿主说"同步"。技能驱动：`specripple index` → `detect`（报告模式）+ `impact`（带证据链的影响候选集）→ 宿主编辑受影响工件与代码（每个候选必须落到三态之一：已修改 / 已检查无需修改 / 尚未确认——图上不可达不等于"不受影响"）→ 冲突一次一题消解并落 rationale 条目 → 门禁 `detect --fail-on HIGH` + `verify`（FAIL_TO_PASS / PASS_TO_PASS 断言，含跑真实测试的 `command` 检查器）→ 报告区分 passed / failed / evidence-insufficient 三种结论。

## 确定性核心

- `specripple index` — 解析 `artifacts/**/*.md`（YAML frontmatter：id / type / status / depends_on / links），校验，重建 `index.json`。
- `specripple impact <ID>` — 显式 links 出边加反向 `depends_on` 的 BFS 闭包，输出证据链。结果是候选集，不是结论。
- `specripple detect` — 零 token 规则层 D1–D6（悬空引用、重复 id、状态机、结构、残留标记、术语），`--fail-on <级别>` 作完成门禁。理解 Spec Kit 官方标记（`**Acceptance Scenarios**:`、`[NEEDS CLARIFICATION: ...]`）。
- `specripple verify` — 按 `assertions.yaml` 执行 file_exists / file_contains / file_not_contains / regex_match / command 五种检查器；任何失败非零退出；配置严格校验。
- `specripple import-speckit <src>` — Spec Kit spec/plan/tasks/constitution 转条目仓库（黄金快照保护；`##`/`###`/`####` 级验收标题与官方加粗标签都归一化并归属正确故事）。
- `specripple build-skill` — 构建自包含技能包（内置 runtime，文件清单校验）。
- `specripple init` / `specripple demo` — 带迁移的宿主装配；带真代码的端到端示例。

退出码统一：0 成功 / 1 检查未过 / 2 配置错误。

## 实测宿主

- **Codex CLI** — 真机端到端实测（自主传播、交互式冲突消解，以及需求/代码/测试同轮对话更新且 verify 全绿的一次实测）。
- **DeepSeek Harness**（dsh ≥ 0.1.5）— 零适配兼容：`dsh-agent-instructions` 读 AGENTS.md，`dsh-skill-filesystem` 扫 `.agents/skills`。
- **Claude Code** — `init --host claude` 生成 `.claude/` 薄壳与 `/specripple` 命令；真机实测暂缓（维护者决策）。
- **Copilot / Cursor** — 不生成宿主专有文件；二者原生读取 AGENTS.md 与 `.agents/skills/`。未真机实测。

## 文档

- [docs/architecture.md](docs/architecture.md) — 组件、数据流、宿主兼容事实
- [docs/migration.md](docs/migration.md) — 安装、旧技能升级、Spec Kit 导入、卸载
- [docs/development-plan.md](docs/development-plan.md) — 当前状态与后续阶段
- [docs/roadmap.md](docs/roadmap.md) — 优先级、收益验证实验、明确不做
- [docs/archive/pre-skill-product/](docs/archive/pre-skill-product/) — 已被替代的历史规划文档（字节级归档）

## 开发

```bash
git clone https://github.com/midiexiangdeliren-crypto/specripple
cd specripple
uv sync
uv run pytest -q
```

无遥测、无网络调用（uv 安装依赖除外）。许可证：见 [docs/roadmap.md](docs/roadmap.md)（待维护者决策）。

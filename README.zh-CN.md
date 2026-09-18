# specripple

[English](README.md) | 简体中文

面向 AI 编程代理的"变更驱动多工件对齐"工具：你只改需求，所有受影响的工件（计划 / 规格 / 任务 / 宪法）自动保持对齐。

本仓库包含零 LLM 的确定性核心 CLI，以及宿主集成层（`specripple init` 会写入带版本戳的 AGENTS.md 标记块和三份 agent 技能；MCP server 是规划中的阶段 2 能力）。

## 状态

v0.1.1 — 全部命令已实现并通过测试（schema v0）：index / impact / detect / verify / demo / init / import-speckit。已在 Codex CLI（非交互流程 + 交互式冲突消解）和 DeepSeek Harness（headless 流程 + MCP 桥）上完成端到端真机实测，见下方"实测宿主"。

## 快速开始

快速体验无需安装——uv 直接从 GitHub 拉取运行：

```bash
uvx --from git+https://github.com/midiexiangdeliren-crypto/specripple specripple demo
```

或克隆后从源码运行：

```bash
uv sync
uv run pytest -q
uv run specripple demo
```

在内置迷你项目上试一遍各命令：

```bash
uv run specripple index --root tests/fixtures/mini
uv run specripple impact REQ-001 --root tests/fixtures/mini
uv run specripple impact REQ-001 --root tests/fixtures/mini --json
```

## 工件格式（schema v0）

每条工件是一个带 YAML frontmatter 的 markdown 文件：

```markdown
---
id: REQ-001
type: req
title: User login with email and password
status: active
depends_on: [REQ-000]
links:
  - to: TASK-001
    kind: realized-by
    src: manual
---

## Acceptance

- Given ..., when ..., then ...
```

`index.json` 是可重建的派生物（已 gitignore）；用 `specripple index` 重建。

## 命令

- `specripple index` — 解析 `artifacts/**/*.md`，校验 schema，写入 `index.json`。
- `specripple impact <ID>` — 沿出边链接加反向 `depends_on` 边做 BFS 闭包；输出受影响工件集，含证据链和未解析引用。
- `specripple detect` — 零 token 规则层：悬空引用、重复 id、状态机违规、结构违规、残留标记、词表术语；输出 CRITICAL/HIGH/MEDIUM/LOW 分级报告。
- `specripple verify` — 按 `assertions.yaml`（fail_to_pass / pass_to_pass 两组）执行 file_exists / file_contains / file_not_contains / regex_match / command 检查器；任何失败即非零退出。`command` 检查器在项目根执行一条 shell 命令（退出码 0 = 通过，支持每条 `timeout`），把文档描述的行为钉到真实可执行的测试上。
- `specripple demo` — 把内置示例项目复制到临时目录，端到端跑完整个流程。
- `specripple init --host codex|claude [--remove] [--dry-run]` — 安装宿主集成：AGENTS.md 中带版本戳的标记块，加 `.agents/skills/` 里的三份技能（Claude Code 额外获得 `.claude/skills/` 薄壳镜像和 `/specripple` 命令）。幂等、可逆。
- `specripple import-speckit <src>` — 把 Spec Kit 产物（spec.md / plan.md / tasks.md / constitution.md）转换为条目仓库：用户故事变成 REQ 条目（P1=active），复选框任务变成 TASK 条目并经 `depends_on` 挂到所属故事，plan 与 constitution 变成 PLAN/CON 条目。带黄金快照测试保护。

## 宿主集成

`specripple init` 只写它自己拥有的文件。AGENTS.md 块位于 `<!-- specripple:begin vX.Y.Z -->` 与 `<!-- specripple:end -->` 标记之间，重复执行 init 时替换（绝不重复堆叠）该块。`--remove` 会摘除标记块并删除受管技能文件，但你手动改过的文件会被跳过。

技能（包内单一来源，init 时复制）：

- `aligning-changes` — 主工作流：影响 → 路由（L0–L3）→ 编辑 → 检出 → 消解 → 复检，以及"证据先于宣告"纪律。
- `detecting-conflicts` — 六类语义检查（重复、歧义、欠规约、宪法对齐、覆盖缺口、不一致），规则层抓不住的由它兜住。
- `resolving-conflicts` — 一次一题的消解协议：选项、推荐、rationale 条目落盘。

## 实测宿主

在 demo 衍生项目上真机运行（改一条条目，agent 自主传播，detect/verify 全绿）：

- **Codex CLI**（`specripple init --host codex`）：agent 主动读取技能，自己跑 index/impact/编辑/detect/verify，按 CON 条目为破坏性变更补 rationale，并同步调整 assertions.yaml。自主流程与交互式消解协议（一次一题、选项带推荐、RAT 条目）均按设计工作。后续在带真实代码的项目上（command 检查器钉住可执行验收脚本），agent 在同一轮对话里同步更新了需求、代码与测试并保持 verify 全绿。注意：工作区沙箱可能拦截内置 apply-patch 辅助程序；agent 通常会自行退到 `~/.codex/.sandbox-bin/` 下的沙箱可访问副本。
- **DeepSeek Harness**（dsh >= 0.1.5，headless profile）：与 `specripple init` 产物零适配原生兼容——`dsh-agent-instructions` 默认读取 AGENTS.md，`dsh-skill-filesystem` 扫描 `<项目根>/.agents/skills`。可在 profile 的 `cordis.patch.yml` 里用 `dsh-mcp-client` insert 挂 MCP 服务器（stdio；Windows 下命令需用 `cmd /c` 包装）。
- **Claude Code**（`specripple init --host claude`）：安装 `.claude/skills/` 薄壳镜像和 `/specripple` 命令；真机实测暂缓。

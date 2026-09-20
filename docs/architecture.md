# 架构

更新日期：2026-09-20（Skill 产品化改造后）。本文描述当前实现；历史规划见 `docs/archive/pre-skill-product/`。

## 定位

specripple 是面向规格驱动仓库的**确定性对齐层**：需求变更后，列出影响依据、遗漏风险和可执行验收结果。分工原则：LLM 循环、文件编辑、对话判断交给宿主 Agent；specripple 只做零 LLM、可重复验证的确定性工作（索引、影响计算、规则检出、断言核对）。工具输出的是"有依据的候选集"，不把"图上不可达"混同于"确认不受影响"。

## 组件总览

```
specripple（本仓库）
├── src/specripple/            # Python CLI 包（uv 管理，零 LLM 依赖）
│   ├── cli.py                 # 命令入口（typer）
│   ├── repo.py / impact.py    # 条目解析、索引、影响 BFS
│   ├── detect.py / verify.py  # 规则层检出、断言核对
│   ├── speckit_import.py      # Spec Kit 产物转换
│   ├── init_host.py           # 宿主装配（安装/卸载/迁移/清单）
│   ├── skillbuild.py          # 自包含技能包构建
│   ├── legacy/                # 改造前旧技能的原文存档（参考数据，勿放宿主扫描目录）
│   └── skills/specripple/     # 唯一技能（分发源头，单一维护来源）
│       ├── SKILL.md           # 触发条件 + 工作流 + 硬性规则
│       ├── scripts/run.py     # 自包含运行入口（见下）
│       ├── references/        # conflict-checks / conflict-resolution / artifact-format / onboarding
│       ├── assets/templates/  # req-entry / rat-entry / assertions.yaml 骨架
│       └── runtime/           # 打包时注入：pyproject.toml + uv.lock + src/specripple + VERSION
├── tests/                     # pytest（含黄金快照、技能完整性、端到端子进程用例）
└── docs/                      # 本文档 + development-plan / migration / roadmap + archive/
```

## 两条使用路径

**路径 A：技能入口（推荐）**。构建 `specripple build-skill --out dist`（或从 release 取 zip），把包内顶层 `specripple/` 装进项目 `.agents/skills/`（或 `specripple init --host codex|claude` 自动装配）。宿主 Agent 按技能工作：优先调 `scripts/run.py`（自包含，无需安装 CLI），装了 CLI 则直接用 `specripple` 命令（获取方式见路径 B，不发布 PyPI）。run.py 定位同目录 `runtime/`，执行 `uv run --frozen --no-dev --project <runtime> specripple ...`，子进程 stdio 直通、退出码透传。专用虚拟环境落在用户缓存目录 `specripple/skill-runtime-v{版本}`（可用 `SPECRIPPLE_RUNTIME_ENV` 覆盖），不同项目共享同一缓存。run.py 自身退出码：2 = runtime 缺失，3 = uv 缺失或启动失败，其余为子命令退出码。

**路径 B：CLI 直装**。`uv tool install git+https://github.com/midiexiangdeliren-crypto/specripple`（或 `uvx --from git+... specripple <cmd>`）。不发布 PyPI（维护者决策）；对其他项目操作时用 `--root` 指定。

两条路径可用同一批命令、同一套退出语义：0 成功 / 1 检查未过 / 2 配置错误。

## 命令与数据

条目仓库 `artifacts/**/*.md`：一条一文件，YAML frontmatter（id 形如 `REQ|TASK|PLAN|CON|RAT-三位数字`、type、status、depends_on、links）+ EARS 正文 + `## Acceptance`（Given/When/Then）。`index.json` 是可重建派生物。

- `index`：解析校验、重建索引；重复 id / 字段非法非零退出。
- `impact <ID>`：显式 links 出边 + 反向 depends_on 的 BFS 闭包，输出影响集与证据链（到达路径）。局限：只沿已存在边遍历，缺链区域不会自动出现——技能把影响集当"候选集"用，未覆盖区域要显式记录"已检查/未确认"。
- `detect`：规则层 D1—D6（悬空引用 CRITICAL / 重复 id CRITICAL / 状态机违规 HIGH / 结构违规 MEDIUM / 未决残留 HIGH / 术语未定义 LOW），支持 `--fail-on CRITICAL|HIGH|MEDIUM|LOW` 作为完成门禁。兼容 Spec Kit 官方标记（`**Acceptance Scenarios**:`、带内容的 `[NEEDS CLARIFICATION: ...]`）。
- `verify`：读项目根 `assertions.yaml`（必须恰好含 fail_to_pass / pass_to_pass 两组），五个检查器 file_exists / file_contains / file_not_contains / regex_match / command（shell 命令钉住真实行为），任何失败退出 1，配置错误退出 2。
- `import-speckit <src>`：Spec Kit spec/plan/tasks/constitution → 条目仓库；`##`/`###`/`####` 级 Acceptance Scenarios 标题与官方加粗标签都归一化为 `## Acceptance` 且归属当前故事；黄金快照测试锁定行为。
- `init --host codex|claude [--dry-run] [--remove]`：装配技能到 `.agents/skills/specripple/`（Claude 另加 `.claude/` 薄壳与 `/specripple` 命令）、AGENTS.md 带版本戳标记块；写清单 `.agents/specripple-manifest.json`（版本 + 每文件 sha256）。幂等；`--remove` 按清单哈希识别受管文件，内容不符（用户改过）即跳过。
- `build-skill [--out dist] [--force]`：产出自包含技能目录 + `specripple-skill-v{版本}.zip`。校验必需文件清单、拒绝杂物泄漏与危险输出路径；runtime 内核为仓库源码的无缓存拷贝。
- `demo`：内置示例（含真代码与 command 断言）复制到临时目录端到端跑通。

## 技能内工作流（宿主执行）

改需求 → `index` → `detect`（报告模式）+ `impact` → 按确定性链接补候选、逐项三态结论（已修改 / 已检查无需修改 / 尚未确认；"图上不可达 ≠ 确认不受影响"）→ 按 L0—L3 路由编辑（宿主强项）→ 冲突按检查单（references/conflict-checks.md）与消解协议（conflict-resolution.md，一次一题带推荐，rationale 落盘）→ 门禁 `detect --fail-on HIGH` + `verify` 全绿 → 报告区分 passed-this-acceptance / failed / evidence-insufficient 三种结论。断言调整须有理由（需求变化写明），不许删断言换绿灯。

## 宿主兼容事实（实测）

- Codex CLI：真机实测通过（自主传播 + 交互消解 + 代码/测试同轮同步）；沙箱可能拦截 apply-patch 辅助程序，agent 通常自行退到 `~/.codex/.sandbox-bin/` 副本。
- DeepSeek Harness（≥0.1.5）：零适配兼容——`dsh-agent-instructions` 默认读 AGENTS.md，`dsh-skill-filesystem` 扫 `<项目根>/.agents/skills`；MCP 经 profile `cordis.patch.yml` 的 `dsh-mcp-client` 挂载（Windows 下 `cmd /c` 包装）。
- Claude Code：生成 `.claude/` 薄壳与命令文件，真机实测暂缓（维护者决策）。
- Copilot / Cursor：仅依赖其原生读取 AGENTS.md 与 `.agents/skills/`，未生成专有薄壳，也未实测。

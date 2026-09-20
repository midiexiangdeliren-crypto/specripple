# 迁移与安装

更新日期：2026-09-20。面向三类起点：全新用户、旧版三技能用户、Spec Kit 用户。

## 全新安装

**方式一：CLI 直装（GitHub，无 PyPI）**

```bash
uv tool install git+https://github.com/midiexiangdeliren-crypto/specripple
specripple demo                                  # 60 秒体验
specripple init --host codex                     # 在你的项目根执行；--host claude 同理
```

**方式二：技能包（自包含，宿主无需装 CLI）**

```bash
# 任选其一取包：
specripple build-skill --out dist                # 从本仓库构建 dist/specripple-skill-vX.Y.Z.zip
# 或从 GitHub release 下载现成 zip
```

解压后把顶层 `specripple/` 整个目录复制到你项目的 `.agents/skills/specripple/`。首次使用时技能内的 `scripts/run.py` 会用 uv 从内置 runtime 自动建好运行环境（落在用户缓存目录，多项目共享；可用 `SPECRIPPLE_RUNTIME_ENV` 指定位置）。装了 CLI 的环境里宿主可以直接用 `specripple` 命令，run.py 只是无 CLI 时的自包含后备。

安装后把 `.agents/skills/specripple/references/onboarding.md` 交给宿主 Agent 跑一遍首次接入（四选一：已配置 / 导入 Spec Kit / 普通项目最小条目化 / 只配验收）。

## 从旧版三技能安装升级

旧版 `specripple init`（v0.1.1 及之前）装的是 `.agents/skills/` 下的 `aligning-changes`、`detecting-conflicts`、`resolving-conflicts` 三个目录。升级步骤：在新版上于同一项目根重跑 `specripple init --host codex|claude`。迁移行为：

- **未修改过的旧技能**：自动删除（逐个报告 `migrate: remove legacy skill ...`），由新技能替代。
- **你手动改过的旧技能**：保留不动，并报告冲突——请自行比对内容，决定保留哪一套；两套工作流不要同时处于激活状态。
- 新技能装到 `.agents/skills/specripple/`，并写清单 `.agents/specripple-manifest.json`（版本号 + 每个受管文件的 sha256）。

旧技能原文以参考数据形式保留在仓库 `src/specripple/legacy/`（仅作历史对照，勿放入宿主扫描目录）。

## 从 Spec Kit 项目导入

```bash
specripple import-speckit <spec-kit-项目目录> --root <目标项目>
```

用户故事 → REQ 条目、复选框任务 → TASK 条目（经 `depends_on` 挂到所属故事）、plan → PLAN、constitution → CON；`##`/`###`/`####` 级 Acceptance Scenarios 标题与官方加粗 `**Acceptance Scenarios**:` 标签均归一化为 `## Acceptance` 并归属正确故事；`[NEEDS CLARIFICATION: ...]`（含带内容形式）保留为未决残留，`detect` 会报出。导入是一次性迁移：此后以条目仓库为唯一维护来源，避免两套文档漂移。

## 升级与卸载

- **升级技能文件**：重跑 `specripple init`（或解压新包后用顶层 `specripple/` 重新复制）。init 对照上一份清单哈希：内容未改的受管文件直接升级；你改过的文件（或来源不明的文件）一律保留并逐个提示冲突，不会被覆盖。
- **卸载**：`specripple init --remove`——摘除 AGENTS.md 标记块、删除清单内文件；内容与清单不符的文件跳过；清空后删除清单本身。Claude 装配会连带清掉 `.claude/skills/` 薄壳与 `/specripple` 命令文件。
- **先看效果**：`--dry-run` 打印将要做的每一步，不写任何文件。

## 常见问题

- `run.py` 报退出码 2：技能目录里缺 `runtime/`（重新取完整包）。退出码 3：环境里没有 uv，先 `pip install uv` 或官方脚本安装。
- 命令对"别的项目"操作时记得 `--root <项目路径>`；`uv run specripple` 只在本仓库源码内可用。
- Windows 控制台输出乱码：CLI 输出为纯 ASCII；中文内容由宿主对话呈现，不经 CLI。

# 对齐层 · Agent 产品集成规划（产品化阶段）

让"需求变更驱动的多工件自动对齐"作为能力包装进 Codex、DeepSeek Harness 等宿主 Agent　　2026 年 9 月 17 日

定位变化：论文工作暂停，先把东西做出来、能用。形态上的关键判断——宿主 Agent（Codex CLI、DeepSeek Harness、Claude Code、Copilot、Cursor）已经自带 LLM 循环、文件编辑、Shell、对话与 MCP 能力，我们不再自研编排，而是提供三样东西：确定性 CLI 工具、可移植指令文档、可选 MCP 服务。这正是 superpowers（只发技能与脚本）和 Spec Kit（CLI + 模板 + 各宿主命令文件）已验证的分发方式；v1 规划里"自研编排核心"的工作交给宿主，我们的七模块按"宿主做什么、我们做什么"重新切分。

## 一、形态总设计：三层可移植组件

第一层，确定性核心 `align` CLI。Python 单包、uvx 一键运行、零 LLM 调用：条目索引与重建（index）、影响集计算（impact）、规则层冲突检出（detect）、传播 diff 守卫（diff-guard）、复检断言核对（verify）、消解记录落盘（log）。任何能执行命令行的宿主都能用，这也是评测埋点（CRR 日志）的挂载点。

第二层，指令文档。对齐工作流与"LLM 层"程序全部写成宿主可执行的指令：AGENTS.md 片段是通用基线（Codex、Copilot、Cursor 原生读取；Claude Code 经 `@AGENTS.md` 导入）；技能用 SKILL.md 格式放进 `.agents/skills/`（2026 年 8 月兼容性矩阵结论：这是覆盖面最广的共享技能路径，Codex、Copilot、Cursor 都读；Claude Code 另放一份到 `.claude/skills/`）；LLM 层六类检查、消解协议、L0—L3 路由规则都写成"无判断力的初级工程师也能照做"的检查单（superpowers 纪律）。宿主的模型就是我们的 LLM 通道。

第三层，可选 MCP server（第二阶段）。把 impact、detect、verify 暴露为结构化工具。MCP 是目前唯一被五家宿主同时支持的面：Copilot（.vscode/mcp.json、.mcp.json、.github/mcp.json）、Claude Code（.mcp.json）、Codex（.codex/config.toml 的 [mcp_servers.*]）、Cursor（.cursor/mcp.json）、DeepSeek Harness（官方 MCP 桥插件，stdio 与 streamable-http，工具注册为 mcp__align__impact 形式）。

## 二、七模块的责任重切分（相对 v1 规划）

| v1 模块 | 宿主 Agent 承担 | 我们提供 |
| --- | --- | --- |
| M-A 条目仓库 | 文件读写 | 条目 schema、EARS+GWT 模板、align index 重建 |
| M-B 链接三通道 | LLM 通道（按指令跑） | 确定性引用解析 + BM25 检索（CLI 内） |
| M-C 影响分析 | 语义补充（按指令跑） | align impact：链接图 BFS + 证据链输出 |
| M-D 传播 L0—L3 | 实际编辑文件、对话 | 路由规则指令 + 变更提案契约 JSON + align diff-guard |
| M-E 双层检出 | LLM 六类检查（按检查单） | align detect 规则层（零 token 先行） |
| M-F 对话消解 | 原生对话能力 | 消解协议指令（一次一题+选项+推荐）+ align log 落盘 |
| M-G 复检 | 两段评审（按指令） | align verify：FAIL_TO_PASS / PASS_TO_PASS 断言核对 |

## 三、宿主适配表（基于 2026 年 8—9 月检索，宿主功能月变，以各官方文档为准）

| 宿主 | 指令注入面 | 命令/技能面 | MCP 配置 | 适配要点 |
| --- | --- | --- | --- | --- |
| OpenAI Codex CLI | AGENTS.md（原生） | `.agents/skills/`（无自定义 prompt 文件，技能是唯一命令面） | `.codex/config.toml` | 首发支持对象；注意沙箱写权限审批 |
| DeepSeek Harness | 无 AGENTS.md 等价机制；用预设/patch 的提示词配置或技能包 | 内置 Skills 技能包 + Cordis 插件 | 官方 MCP 桥（stdio/http） | npm `@deepseek-ai/dsh`，Node 22.19+；MVP-3 用其极简模式验证 |
| Claude Code | CLAUDE.md 内 `@AGENTS.md` 导入 | `.claude/skills/`、`.claude/commands/` | `.mcp.json` | 技能是官方 canonical 命令形态 |
| GitHub Copilot | AGENTS.md（原生） | `.agents/skills/` 或 `.github/skills/`；VS Code 另有 `.github/prompts/` | `.mcp.json` / `.github/mcp.json` | 自动跟随 |
| Cursor | AGENTS.md（原生） | `.cursor/skills/`、读 `.agents/skills/` | `.cursor/mcp.json` | 自动跟随 |

结论：通用层只押两个事实标准——AGENTS.md（指令）与 MCP（工具），宿主特化文件（.claude、.codex、.github 下的薄壳）由初始化器生成，格式变了只重生成薄壳。

## 四、发布形态与目录结构

```
align-kit/
  align/                 # Python CLI，uvx align <cmd>，零 LLM 依赖
  skills/                # 源技能（单份维护）
    aligning-changes/    #   主工作流：变更→影响→路由→编辑→检出→消解→复检
    detecting-conflicts/ #   六类检查检查单（LLM 层）
    resolving-conflicts/ #   消解协议：一次一题、选项+推荐、rationale 落盘
  agents/AGENTS-snippet.md
  commands/              # 薄壳：claude-code/ codex 需要的宿主特化文件
  templates/             # 条目模板，兼容 Spec Kit 产物
  mcp/                   # 阶段2：FastMCP server（impact/detect/verify 三工具）
  init.py                # align-kit init --host codex|claude|dsh：装配对应目录
  examples/demo-project/ # 演示项目（含预置 Spec Kit 基线工件）
```

发布：PyPI（uvx/uv tool install）+ GitHub 仓库；安装 = `align-kit init --host <宿主>` 生成各目录薄壳并写 MCP 配置。

## 五、宿主视角的完整工作流

用户改完 REQ-017 对宿主说"同步这个变更"。宿主按技能说明：一，跑 `align impact REQ-017`，拿到影响集与每项"为何受影响"的证据链；二，按指令里的 L0—L3 路由规则逐项决定传播方式，实际编辑文件（宿主强项）；三，每条编辑产出提案 JSON（根因、预期修复、可能受损、验证用例），`align diff-guard` 校验最小 diff 与契约完整性；四，`align detect` 规则层先行，CRITICAL/HIGH 项再按六类检查单跑 LLM 层；五，需用户裁决的冲突按消解协议逐题对话，结论 `align log` 落盘；六，`align verify` 核对 FAIL_TO_PASS 与 PASS_TO_PASS 断言集，全部通过才宣布完成——"证据先于宣告"。

## 六、MVP 范围（目标 2—3 周可见、可用）

| 步 | 内容 | 验证标准 |
| --- | --- | --- |
| MVP-1 | align CLI 四命令（index/impact/detect/verify）+ 条目 schema v0 + Spec Kit 模板转换器 | demo-project 条目化 100%，索引可重建，规则层检出有输出 |
| MVP-2 | AGENTS.md 片段 + aligning-changes 技能 + Codex 与 Claude Code 薄壳 + init.py | 在 Codex CLI 与 Claude Code 里各完整跑通一次"改需求→对齐"演示流程 |
| MVP-3 | DeepSeek Harness 适配验证：技能包 + MCP 桥接入 | DSH 极简模式下走通 impact 与 detect；不通则降级为"OpenAI 兼容 + MCP"通用接入并记录原因 |
| 阶段2 | MCP server（FastMCP）+ 检索通道升级（BM25+RRF） | 五宿主至少三家经 MCP 调用工具成功 |
| 阶段3 | 提案契约自动化、CRR 日志与指标报表 | 任一宿主会话结束后能出对齐质量报告 |

## 七、风险与对策

宿主命令与技能格式月变（2026 年现状是"互相兼容读取而非正式标准"）——通用层只押 AGENTS.md 与 MCP，薄壳可随时重生成。DSH 是组装式运行时且无 AGENTS.md 机制，技能装配面文档尚少——MVP-3 前先花半天调研其 Skills 与 patch 机制，不通即降级。宿主模型能力参差，LLM 层检查质量不稳——检查单写到可执行粒度，规则层兜底并承担所有确定性判断。工程细节：Windows 编码统一 UTF-8；Codex 沙箱模式下给 align 写 artifacts/ 的审批提示要写进指令；MCP server 的 stdio 启动命令按各宿主配置格式生成。

## 八、与论文的关系

不冲突且互相供血：MVP-1/2 就是研究方案 M1 的工程预研，demo-project 跑通即 M2 的起点；align CLI 的规则层、diff-guard 与 CRR 日志埋点顺手为论文留数据；宿主实测中遇到的失败案例直接进评测集。先有能用的东西，论文的实验素材自然产生。

## 参考

兼容性矩阵（2026-08-26 核验）：codylindley.github.io/ai-harness-engineering-compatibility-matrix/。DeepSeek Harness：github.com/deepseek-ai/deepseek-harness（v0.1 预览版，npm `@deepseek-ai/dsh`）。Spec Kit：github.com/github/spec-kit。superpowers：github.com/obra/superpowers。v1 技术细节（条目 schema、三通道、指标口径）见《实现方式规划》，本规划是其宿主集成版，两者配合使用。

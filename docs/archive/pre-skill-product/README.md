# 归档：Skill 产品化之前的规划与评估文档

归档日期：2026-09-20。本目录保存 specripple 以 Skill 为入口进行产品改造（P0—P5）之前的四份规划/评估文档。文件为字节级原样拷贝（sha256 与原件一致），未做任何内容修订；历史表述与当时事实对应，不代表当前架构。

每份文档的状态与替代关系见下表。当前有效文档：仓库根 README.md / README.zh-CN.md、docs/architecture.md、docs/development-plan.md、docs/migration.md、docs/roadmap.md。

| 文件 | 状态说明 | 被什么替代 |
| --- | --- | --- |
| 变更驱动多工件对齐-实现方式规划.md | 已被替代。最早的完整技术设想（自研编排、直连 LLM、检索通道、完整研究指标），其中大部分设想后来按“宿主承担 LLM 循环、本工具只做确定性 CLI”的分工重新切分；模块命名（M-A—M-G）、EARS+GWT 条目格式、双层检出等思想仍体现在现有实现中。 | docs/architecture.md（当前架构）、docs/roadmap.md（未实现部分的去向） |
| 对齐层-Agent产品集成规划.md | 已被替代。三层组件与宿主适配表是当时的调研快照；其中“DSH 无 AGENTS.md 等价机制”的结论已被实测推翻（dsh-agent-instructions 默认读 AGENTS.md），PyPI 发布计划已由维护者决策放弃（改为 GitHub git 直装）。 | docs/architecture.md、docs/migration.md、README 的安装说明 |
| 对齐层-开发执行计划.md | 已被替代。D1—D14 排期与 MVP-1/2/3 验收已全部执行完毕（含 §八/§九 回填），是 v0.1.1 之前的历史执行记录。 | docs/development-plan.md（当前与后续计划） |
| specripple-实际开发价值与差距复评-2026-09-18.md | 历史评估证据，整体结论仍具参考价值，但**其中列出的部分缺陷已在后续维护轮修复**：JSON 验收失败退出码（原 5.1）、verify 空/错误配置校验（原 5.4 部分）、Spec Kit 官方 `**Acceptance Scenarios**:` 与 `[NEEDS CLARIFICATION: ...]` 兼容（原 5.2）、`detect --fail-on` 门禁（原 5.5 部分）、安装命令统一为 git 直装（原 5.6）。仍未解决并转入后续计划的：影响集覆盖上限依赖人工链接与代码/测试映射（原 5.3）、PASS_TO_PASS 基线保护、三平台 CI 与 LICENSE、真实项目增量收益对照实验。 | docs/development-plan.md、docs/roadmap.md |

引用约定：如需引用历史决策依据，请引用本目录文件并注明“归档于 2026-09-20，内容为当时状态”。当前行为以现行代码与其测试为准。

# 变更记录

本仓版本面 = 五份 agent 插件清单 + cursor 市场元数据的 `.version` 字段 + git tag `v*`
（`.versionrc.js` 的 `bumpFiles` 已接线）。按 spec 决策 #9，每次发版须记录对齐三元组的变更。

## [v0.2.0] - 2026-11-03

### ⚠️ 对齐关系变更（破坏性）

- **wop-python-sdk 下限 `≥ 0.1.1` → `≥ 0.2.0`**：`wop selftest` L1 直接拒 0.1.x
  （0.2.0 起 SM2 ZA `userId` 必须显式传入，见 wop-sdk-spec D14/D15）；
  `requirements.lock` 钉 `wop-python-sdk==0.2.0`，`MIN_SDK_VERSION = (0, 2, 0)`
- L3 删 `inspect.signature` 能力探测分支，ZA userId 统一显式传向量夹具值
- `crypto-strategy-spec v0.3-reviewed` 与 `wop-sdk-spec v1.0-ratified` 不变

### ✨ 新功能

- `llms.txt` / `llms-full.txt` AI 摄取端点，`lint_skills.py` R9 逐字节守护与 `skills/` 一致
- 六路 agent 插件清单：Claude / Codex / Cursor / Grok / Kimi / OpenCode（`.agents`）
- 四路原生入口薄调度层：`AGENTS.md` / `GEMINI.md` / Cursor `.mdc` / Continue rules

### 🐛 Bug 修复

- Sourcery 全量修复（86 issues → 10 保留）
- 安装自包含：`SECURITY.md` 副本随 `skills/*` 复制，SKILL.md 链接改 `../SECURITY.md`
- 错误码生成物提取源占位符统一
- `factory-local.json` 死血统上游指针修正

### 🔧 构建/依赖

- `.factory` 工具链迁移至 awesome-factory 血统（anchor `181618c3`）：
  反馈台账锚定主树（链 worktree 删除不再重复开 PR）、锁语义 fail-closed 加固
- 变异门：11/11 kill rate + 2/2 负例放行（周界指纹 `89b3f747`）

## [v0.1.0] - 2026-08-29

初始版本：八件套 CLI（keygen / selftest / doctor / api / call / sign / verify / diagnose）
+ 三 skill 知识层 + 工厂治理（kill rate 11/11 + 覆盖率 97%）。

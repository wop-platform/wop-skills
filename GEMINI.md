# GEMINI.md — wop-skills Gemini CLI 入口

Gemini CLI 在本仓库内工作时，遵循本入口调度 WOP 技能三件套。

## 技能调度（按需加载，勿整包注入）

| 场景 | 加载 | 位置 |
|---|---|---|
| 零代码调用 / 签名 / 验响应 / 联调对拍 | wop-cli | [skills/wop-cli/SKILL.md](skills/wop-cli/SKILL.md) |
| 自研协议实现（签名 / 加密 / 信封） | wop-dev | [skills/wop-dev/SKILL.md](skills/wop-dev/SKILL.md) |
| 线上错误码排错（62 错误码决策树） | wop-troubleshoot | [skills/wop-troubleshoot/SKILL.md](skills/wop-troubleshoot/SKILL.md) |

## 硬性纪律（先于一切能力）

1. **先读 [SECURITY.md](skills/SECURITY.md)（S1–S8）**：私钥只经 `WOP_PRIVATE_KEY` /
   `WOP_PRIVATE_KEY_FILE`（权限 0600）进入；永不入对话 / 命令行 / 日志（S3/S6）。
   不得要求用户把私钥粘贴到对话。
2. 写类 API 调用前，向用户复述 API 路径与关键业务参数并获确认（S7）。
3. 环境未验证不动手：`python skills/wop-cli/scripts/wop selftest` 三元组全绿是使用前提。

## 环境

Python ≥ 3.9 + `pip install wop-python-sdk`（≥ 0.1.1；SM2 套件另需 gmssl ≥ 3.2.2，
`wop doctor` 会预检并给安装指引）。

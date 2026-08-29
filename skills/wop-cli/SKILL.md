---
name: wop-cli
description: WOP 网关官方 CLI 基座——零代码执行（签名/调用/验响应全链路）与联调排错（draft 对拍/离线验签）。商户 agent 对接 wop-gateway API 的必备工具层。使用前必读 SECURITY.md 安全纪律。
---

# wop-cli（基座 skill）

> 对齐三元组：crypto-strategy-spec v0.3-reviewed + wop-sdk-spec v1.0-ratified + wop-python-sdk ≥0.1.1（0.1.0 缺尾随位修复链不可用；`wop selftest` 行为断言是最终校验）
> 状态：keygen/selftest 已可用（selftest 全绿方可使用）；doctor/api/call/sign/verify/diagnose 随 Phase 3/4 落地
> **安全纪律：先读 [SECURITY.md](../../SECURITY.md)（S1–S8）——私钥边界与写操作确认是使用本 skill 的前提条件**

## 何时用

- 零代码执行：替用户完成 API 调用（查单/下单），全程不写代码
- 联调排错：用户自研实现签名不过时，产出官方 draft 逐 header 对拍
- 回调开发：离线验证平台回调的签名与摘要

## 命令速查

| 命令 | 用途 | 状态 |
|------|------|------|
| `wop keygen --suite WOP-SM2-SM3` | 生成密钥对；私钥写 0600 文件，stdout 只出公钥 | 载体实施中 |
| `wop selftest` | 向量自测 + 三元组校验，不过拒跑 | 载体实施中 |
| `wop doctor` | 依赖/密钥格式/配置预检 | 载体实施中 |
| `wop api list` / `wop api describe <path>` | 动态 API 目录（支持 `--mock`） | 载体实施中 |
| `wop call POST /gateway/<path> --body '<json>' [--level L2]` | 签名→发送→F6 验响应 | 载体实施中 |
| `wop sign POST /gateway/<path> --body '<json>'` | 仅产 draft，对拍用 | 载体实施中 |
| `wop verify --headers <f> --body <f>` | 离线验签（响应/回调） | 载体实施中 |
| `wop diagnose <resp.json>` | 错误响应 → 排查路径 | 载体实施中 |

命令语义细节（参数/退出码/错误分类）见 [references/commands.md](references/commands.md)。

## 场景剧本

### 剧本一：零代码调用（读类）

1. `wop selftest` 全绿，否则停止并按输出指引修复环境
2. `wop api describe <path>` 确认参数 schema
3. `wop call POST /gateway/<path> --body '{...}'` → 返回验签后明文
4. 私钥来源：引导用户确认 `WOP_PRIVATE_KEY` 已设置或密钥文件路径——**不要**
   请求用户把私钥粘贴到对话（SECURITY.md S3）

### 剧本二：零代码调用（写类）

同剧本一，但第 3 步前必须向用户复述 API 路径与关键业务参数，获得确认后执行
（SECURITY.md S7）。

### 剧本三：联调对拍

1. 让用户运行其自研实现，产出 draft（headers + wireBody）存文件
2. `wop sign` 对同一输入产出官方 draft
3. 逐 header diff：差异项即根因候选，对照
   [references/commands.md](references/commands.md) 的格式规则核查
   （尾随位 `=`、DER 编码 SM2 签名、C1C2C3 顺序是三大高频根因）

## 前置依赖

- Python ≥ 3.9；`pip install wop-python-sdk`（版本要求见头部三元组）
- SM2 套件额外需要 `gmssl ≥ 3.2.2`（`wop doctor` 会预检并给安装指引）

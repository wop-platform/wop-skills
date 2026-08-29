<div align="center">

# wop-skills

**WOP 开放平台 Agent 技能包 —— 让每一个商户 Agent 安全、正确地完成 API 对接**
**Agent Skills for the WOP Open Platform — every merchant agent signs, calls and verifies, correctly.**

[![Tests](https://img.shields.io/badge/tests-73%20passed-brightgreen)]()
[![Coverage](https://img.shields.io/badge/line%20coverage-97%25%20(gate%20%E2%89%A595%25)-brightgreen)]()
[![Python](https://img.shields.io/badge/python-%E2%89%A53.9-blue)]()
[![Aligned](https://img.shields.io/badge/triple--aligned-crypto--spec%20v0.3%20%C2%B7%20sdk--spec%20v1.0%20%C2%B7%20sdk%200.1.1-success)]()

[特性](#-为什么存在--why-this-repo-exists) · [快速开始](#-快速开始--quick-start) · [命令](#-八件套命令--the-eight-commands) · [协议](#-协议心智模型--protocol-mental-model) · [安全](#-安全纪律--security-discipline) · [治理](#-质量与治理--quality--governance)

</div>

---

## 🎯 为什么存在 | Why This Repo Exists

商户对接开放平台，传统路径是「读文档 → 写代码 → 联调 → 排错」，每一步都伴随签名不过、
编码不一致、密钥泄露等高频事故。wop-skills 把这条路径压缩为 **AI Agent 可直接执行的技能**：
零代码调用、官方实现对拍、结构化排错——并以**宪法级安全纪律**约束 Agent 与私钥的距离。

Merchant integration used to mean *read docs → write code → debug signatures → leak keys*.
wop-skills turns that path into **skills an AI agent can execute directly**: zero-code API
calls, official-implementation diffing, structured troubleshooting — guarded by
**constitution-level security discipline** that keeps agents away from private keys.

这是 wop-platform 生态的技能层真源，与密码学规格、六语言 SDK 同源对齐：

This is the skills layer of the wop-platform ecosystem, kept in lockstep with the crypto
spec and six official SDKs:

| 层 | 真源 | 状态锚 |
|---|---|---|
| 密码学策略 | [wop-specs / crypto-strategy-spec](https://github.com/wop-platform/wop-specs) | `v0.3-reviewed` |
| SDK 契约 | [wop-specs / wop-sdk-spec](https://github.com/wop-platform/wop-specs) | `v1.0-ratified` |
| 官方 SDK（六语言） | [wop-python-sdk](https://github.com/wop-platform/wop-python-sdk) · [java](https://github.com/wop-platform/wop-java-sdk) · [go](https://github.com/wop-platform/wop-go-sdk) · [php](https://github.com/wop-platform/wop-php-sdk) · [dotnet](https://github.com/wop-platform/wop-dotnet-sdk) · [typescript](https://github.com/wop-platform/wop-typescript-sdk) | `≥ 0.1.1` |
| **Agent 技能（本仓）** | **wop-skills** | 三元组 + MD5 向量锚 |

> **对齐三元组**：CLI 每次启动 `selftest` 都校验三元组与黄金向量 MD5 锚——规格、SDK、
> fixture 任何一方漂移即拒跑，杜绝「文档说 A、代码跑 B」。
>
> **Alignment triple**: every `wop selftest` re-verifies the spec/SDK/fixture triple plus an
> MD5 anchor over the golden vectors. Any drift → hard stop. No "docs say A, code does B".

---

## 📦 三个技能包 | Three Skills

| 技能 | 定位 | 核心能力 |
|---|---|---|
| **[wop-cli](skills/wop-cli/)** | 基座 · 官方 CLI | 零代码全链路（签名→调用→验响应）、联调对拍、离线验签、环境预检 |
| **[wop-dev](skills/wop-dev/)** | 开发指导 | 协议心智模型、canonicalRequest/信封/F6 细节、六语言 SDK 速查 |
| **[wop-troubleshoot](skills/wop-troubleshoot/)** | 排错 | 62 错误码全目录、I7 模糊错误二叉排查树 |

| Skill | Role | Highlights |
|---|---|---|
| **wop-cli** | Foundation · official CLI | Zero-code full loop (sign → call → verify), diffing against the official draft, offline verification, environment preflight |
| **wop-dev** | Development guide | Protocol mental model, canonicalRequest / envelope / F6 details, six-language SDK cheat sheets |
| **wop-troubleshoot** | Troubleshooting | Full catalog of 62 error codes, binary decision tree for ambiguous errors |

三个技能为分层依赖：`wop-cli` 是工具基座，`wop-dev` 与 `wop-troubleshoot` 是其上的知识层。

The three skills stack: `wop-cli` is the tooling foundation; `wop-dev` and
`wop-troubleshoot` are knowledge layers on top.

---

## 🚀 快速开始 | Quick Start

```bash
# 1. 依赖：Python ≥ 3.9（SM2 套件另需 gmssl ≥ 3.2.2）
pip install wop-python-sdk          # 或 pip install -r skills/wop-cli/scripts/requirements.lock

# 2. 密钥：环境变量进入（唯一通道），永不经命令行参数或对话
export WOP_APP_KEY=your-app-key
export WOP_SUITE=WOP-RSA3072-SHA256            # 或 WOP-SM2-SM3 / WOP-RSA4096-SHA256
export WOP_PRIVATE_KEY_FILE=~/.wop/merchant.pem  # 强制 0600
export WOP_PLATFORM_PUBLIC_KEY=platform-spki-b64
export WOP_GATEWAY_URL=https://gateway.example.wop

# 3. 自测：三元组 + 黄金向量全绿才放行
python skills/wop-cli/scripts/wop selftest

# 4. 零代码调用：签名 → 发送 → F6 验响应，一步到位
python skills/wop-cli/scripts/wop call POST /gateway/orders/query \
  --body '{"orderId": "20260829001"}'
```

```bash
# No code. No key material in argv or chat. Ever.
# 1. Deps: Python ≥ 3.9 (SM2 suites additionally need gmssl ≥ 3.2.2)
pip install wop-python-sdk

# 2. Keys enter via environment only (the single sanctioned channel)
# 3. `wop selftest` gates everything: triple + golden vectors must be green
# 4. One command completes sign → send → verify-response
python skills/wop-cli/scripts/wop call POST /gateway/orders/query \
  --body '{"orderId": "20260829001"}'
```

---

## 🛠 八件套命令 | The Eight Commands

| 命令 | 用途 |
|---|---|
| `wop keygen --suite WOP-SM2-SM3` | 生成密钥对；私钥直写 0600 文件，stdout 只出公钥 |
| `wop selftest` | 向量自测 + 三元组校验，不过拒跑其余命令 |
| `wop doctor` | 依赖 / 密钥格式 / 配置预检，给出修复指引 |
| `wop api list` / `wop api describe <path>` | 动态 API 目录（授权口径；支持 `--mock` 离线） |
| `wop call POST /gateway/<path> --body '<json>' [--level L2]` | 签名 → 发送 → F6 验响应，返回验签后明文 |
| `wop sign POST /gateway/<path> --body '<json>'` | 仅产官方 draft——自研实现逐 header 对拍的基准 |
| `wop verify --headers <f> --body <f>` | 离线验签（平台响应 / 回调通知） |
| `wop diagnose <resp.json>` | 错误响应 → 语义 + HTTP + 处理建议 + 排查路径 |

| Command | Purpose |
|---|---|
| `wop keygen` | Generate a key pair; private key goes straight to a 0600 file, stdout prints the public key only |
| `wop selftest` | Vector self-test + triple check; everything else refuses to run unless green |
| `wop doctor` | Preflight: dependencies, key formats, configuration — with fix guidance |
| `wop api list / describe` | Dynamic API catalog (authorization-scoped; `--mock` works offline) |
| `wop call` | Sign → send → F6 verify, returning the verified plaintext |
| `wop sign` | Produce the official draft only — the baseline to diff your implementation against |
| `wop verify` | Offline signature verification (responses & callbacks) |
| `wop diagnose` | Error response → semantics + HTTP mapping + remediation + probe path |

**典型场景**：
- **零代码调用** — `selftest` 全绿后 `call` 直接完成业务请求；
- **联调对拍** — 自研实现签名不过？同一输入下 `wop sign` 产官方 draft，逐 header diff，
  差异项即根因候选（尾随位 `=`、DER 编码 SM2 签名、C1C2C3 顺序是三大高频根因）；
- **回调开发** — `wop verify` 离线验证平台回调的签名与摘要，无需暴露内网端点。

---

## 🧠 协议心智模型 | Protocol Mental Model

```
build_request 五步（纯函数，零网络）            F6 响应/回调验证（固定顺序）
─────────────────────────────────            ─────────────────────────────
套件解析                                     ① 验签
  WOP-<RSA3072|RSA4096|SM2>-<SHA256|SM3>      ② digest 复核
→ canonicalRequest                           ③ DEK 解包
  5 段 \n 连接 · Java URLEncoder 语义          ④ alg 族比对
→ x-wop-content-digest                       ⑤ bulk 解密
  有 body 必产必入签 "<alg> <小写hex>"
→ x-wop-sign
  四段式 v1/<expiredSeconds>/<signedHeaders>/<b64url签名>
→ [L2] 数字信封
  AES-256-GCM / SM4-GCM 全文加密 wire={"encrypted":…}
```

> 全量细节（含 D1–D5 附录语义、六语言差异坑位）见
> [wop-dev/references/protocol.md](skills/wop-dev/references/protocol.md)。
> Full details (incl. appendix D1–D5 semantics and per-language pitfalls) live in
> [wop-dev/references/protocol.md](skills/wop-dev/references/protocol.md).

---

## 🔐 安全纪律 | Security Discipline

Agent 时代的 API 对接，私钥安全是第一性问题。本仓以 [SECURITY.md](SECURITY.md)（宪法级，
治理周界内）定义 **S1–S8**，要点：

| 纪律 | 内容 |
|---|---|
| **S1 唯一通道** | 私钥仅经 `WOP_PRIVATE_KEY` 环境变量或 0600 权限文件进入 CLI 进程 |
| **S2 禁止入参** | 私钥内容不得作为命令行参数（ps 可见 + history 落盘） |
| **S3 禁止入对话** | 私钥内容不得进入 agent 对话、日志、issue、PR——agent 引导用户自设，永不 touch |
| **S6 主动防御** | CLI 启动即扫描 argv 中疑似私钥特征（PEM 头 / Base64 长块），命中即拒跑 |

Private-key safety is the first-class concern of agent-driven integration. SECURITY.md
(constitution-level) defines disciplines S1–S8: keys enter through exactly one channel
(env or 0600 file), never in argv, never in chat; the CLI itself **actively scans argv
for key-like material and refuses to run** — defending against agent misuse rather than
trusting discipline alone.

---

## 🏛 质量与治理 | Quality & Governance

这不是普通的文档仓库——**每一条知识都有执行载体**：

- **测试**：73 项 pytest 全绿；12 条字节级向量一致性断言；三元组漂移即拒跑
- **覆盖率**：行覆盖率 97%，门禁 ≥95%（`scripts/run_tests.sh` 终局测量，含 subprocess 归集）
- **突变证据**：注入缺陷 kill rate 8/8——未证明的门不是门
- **反向核对**：spec 条款 → 测试名矩阵（`docs/spec-matrix.md`），否定式条款亦有负向量测试
- **宪法治理**：`MISSION.md` 九条铁律（holdout 独立验证、spec 条款不因现状顺延、判据冻结……）

This is not a docs folder — **every claim here has an executable carrier**: 73 passing
tests, 12 byte-level vector-consistency assertions, a 97% line-coverage gate (≥95%
enforced), an 8/8 mutation kill rate proving the gate itself, and a spec-clause →
test-name reverse-verification matrix. Governance follows a written constitution
(`MISSION.md`) with nine iron laws.

```text
wop-skills/
├── MISSION.md            # 宪法：使命 / 周界 / 铁律（工厂永不可改）
├── SECURITY.md           # 安全纪律 S1–S8（宪法级）
├── skills/
│   ├── wop-cli/          # 基座：CLI + 命令语义 + 黄金向量锚
│   ├── wop-dev/          # 知识：协议全貌 + 六语言 SDK 速查
│   └── wop-troubleshoot/ # 知识：62 错误码 + I7 排查树
├── contracts/            # API 发现契约（OpenAPI 3.1，契约先行）
├── mocks/                # 发现端点 mock（离线联调）
├── tests/                # 执行载体：73 项契约与分支测试（覆盖率门禁 ≥95%）
└── docs/                 # intent / spec / spec-matrix（规格层）
```

---

## 🤝 生态 | Ecosystem

- **协议真源**：[wop-platform/wop-specs](https://github.com/wop-platform/wop-specs) — crypto-strategy-spec & wop-sdk-spec
- **官方 SDK**：[python](https://github.com/wop-platform/wop-python-sdk) · [java](https://github.com/wop-platform/wop-java-sdk) · [go](https://github.com/wop-platform/wop-go-sdk) · [php](https://github.com/wop-platform/wop-php-sdk) · [dotnet](https://github.com/wop-platform/wop-dotnet-sdk) · [typescript](https://github.com/wop-platform/wop-typescript-sdk)
- **网关侧**：`gtsp-wop-gateway`（平台内部）

---

<div align="center">

**让 Agent 替商户写对接代码，让机器替人类守住正确性。**
**Agents write the integration; machines keep it correct.**

[上四方安全纪律](SECURITY.md) · [读使命宪法](MISSION.md) · [查协议真源](https://github.com/wop-platform/wop-specs)

</div>

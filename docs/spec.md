# wop-skills 设计规格（spec）

> 状态：grilling 定稿（2026-08-29），10/10 决策闭环
> 意图与验收判据见 [intent.md](intent.md)；本文是"怎么做"的唯一设计真源
> 待确认：交付顺序（§7）、make-plan vs 直接开干（§8）

---

## 1. 事实基础（已查证，无悬空假设）

| 事实 | 来源 |
|------|------|
| 协议真源：crypto-strategy-spec（v0.3-reviewed）+ sdk-spec（v1.0-ratified + 附录 D1–D5）+ 黄金向量 12 条（formatRules 8→12，尾随位升格，commit `ce92dd4`，MD5 `1033af2c35b498b479e41487ccbda862`） | `wop-specs/`（与网关 docs/ 字节级一致，已验证无漂移） |
| 6 语言官方 SDK 全部落地（java/go/ts/python/php/dotnet），覆盖率 ≥98%，2026-08-29 完成跨语言尾随位大修 | 各 SDK 仓库 + `gtsp-wop-gateway/docs/wop-sdk-cross-lang-audit-20260829.md` |
| 协议核心：三套件（RSA3072/RSA4096/SM2-SM3）、L0/L2、canonicalRequest 结构化签名、base64url 无填充（12 条格式规则）、SM2 裸 r‖s、C1C3C2、F6 固定验证顺序、I7 错误模糊化 | crypto-spec + sdk-spec |
| TS/PHP SDK 首版仅 RSA 套件，SM2 列路线图 | sdk-spec §1.2（Q7 裁决） |
| API 元数据体系存在：`wop_api_defin`（apiPath、apiFullPath=业务域编码+路径、参数树、出入参示例）+ `wop_api_ver`（灰度/全量状态机）；真实路径形如 `/gateway/logistics.waybill.sync` | gtsp-wop-service 领域层 |
| **无公开 API 发现端点**：开发者中心 `gtsp-wop-developer` 为空壳仓库；网关为 POST-only 数据面 | 本地勘察 |
| 网关已有手动网页工具 `docs/tools/rsa-keygen.html`（密钥生成/签名 demo）——平台"帮商户对接"意识存在但停留在 web 表单时代 | gtsp-wop-gateway/docs |
| 网关仓库运行 .factory auto-factory 治理（MISSION + 二值 triage + 验证门 + holdout + 周界铁律），已经历 S1 崩溃/needs-fix 归零事故并修复 | `gtsp-wop-gateway/MISSION.md` + 审计报告 |
| 传输层限额 D4：11MB 流式上限，读取过程中生效，禁整体缓冲后检查 | sdk-spec 附录 D |
| PHP L2 信封事故：裸密文 ↔ `{"encrypted":...}` JSON 信封跨语言漂移，已修复；催生 D5 防镜像偏差纪律 | 跨语言审计报告 §2 |

### 范围排除

- 不手搓密码学：全部委托 wop-python-sdk（尾随位事件证明标准库宽容陷阱跨语言普遍，手搓必踩）
- 不复用 woa 编排层：woa 是 ailogistics 内部第三方集成层，调用方向相反（我方→外部渠道），强依赖内部基础设施；其配置驱动编排理念已被 wop 体系吸收，仅作设计蓝本
- CLI 不进 SDK 仓库：sdk-spec v1.0-ratified 定位 SDK 为纯库，无 CLI 位置

---

## 2. 决策清单（10 项，全部经用户裁决）

### #1 核心场景：开发加速器 + 零代码执行
双场景并重，共享 CLI 工具底座。排除：纯脚手架生成器、纯平台侧排错。

### #2 技术形态：Agent Skill + Python 薄 CLI
- SKILL.md（知识层）+ scripts/（工具层），Anthropic Agent Skills 标准格式
- CLI 密码学**全部委托 wop-python-sdk**（98% 覆盖 + 向量字节级一致），skill 零密码学实现
- Go 单二进制列为后备路线（非技术用户环境装不了 Python 时再启用）

### #3 API 目录：动态拉取
CLI `wop api list` / `wop api describe` 实时拉取。排除：静态内置（发版滞后）、不含目录（体验断裂）。

### #4 端点解耦：契约先行 + mock
- skill 仓定义 API 发现契约（OpenAPI 片段：`GET /apis` + `GET /apis/{path}` 响应 schema，含参数树/出入参示例/版本状态）
- CLI 按契约实现，内置 mock fixture 测试；平台照契约在开发者中心实现
- 两边并行，skill 不被平台排期阻塞；契约即跨仓接口文档

### #5 命令面：八件套

| 命令 | 用途 | 场景 |
|------|------|------|
| `wop keygen --suite ...` | 生成密钥对；私钥直写 0600 文件，stdout 只出公钥 | 冷启动 |
| `wop selftest` | 向量自测 + 三元组校验（SDK 版本 + 向量哈希），不过即拒跑 | 安装验证 |
| `wop doctor` | 环境诊断：依赖/密钥格式/配置预检 | 排错 |
| `wop api list / describe` | 动态 API 目录（支持 `--mock`） | 零代码 |
| `wop call POST /gateway/... --body ... [--level L2]` | 签名→发送→F6 验响应全链路 | 零代码 |
| `wop sign ...` | 仅产 draft（headers+wireBody）——对拍：商户自研实现 vs 官方 draft 逐 header diff | 联调 |
| `wop verify --headers ... --body ...` | 离线验签（响应/回调） | 回调开发 |
| `wop diagnose <resp.json>` | 解析网关错误响应，输出排查路径 | 排错 |

### #6 私钥安全边界：全套原则 + 主动防御

```
私钥唯一合法通道：CLI 进程内读取
├─ 来源优先级：env(WOP_PRIVATE_KEY) > 文件路径(WOP_PRIVATE_KEY_FILE, 强制 0600)
├─ 禁止：私钥作为命令行参数（ps 可见 + shell history 落盘）
├─ 禁止：私钥进入 agent 对话上下文（SKILL.md 首段纪律 + agent 引导用户自行 export）
├─ keygen 输出：私钥直写 0600 文件，stdout 只打公钥 + 文件路径
├─ CLI 任何输出（draft/响应/日志）零私钥
└─ 主动防御：CLI 启动检测 argv 疑似私钥内容 → 拒绝执行（防 agent 犯规）
```

### #7 内容架构：三 skill 拆分
- `wop-cli`：零代码执行 + 安全纪律 + 命令手册
- `wop-dev`：协议心智模型 + 6 语言 SDK 指导 + 对拍方法论（前置声明：需 wop-cli）
- `wop-troubleshoot`：错误码目录 + I7 模糊错误排查树（前置声明：需 wop-cli）
- 安装指引推荐三件套全装；跨 skill 知识引用 wop-specs 真源，避免 skill 间互相依赖

### #8 CLI 宿主：wop-cli 基座 + 声明依赖
- 全部脚本住 `skills/wop-cli/scripts/`
- dev/troubleshoot 的 SKILL.md 头部声明"前置：需安装 wop-cli"
- 依赖单向：知识层→工具层；零脚本副本，无漂移

### #9 版本治理：三元组标注 + 运行时校验
- 每个 SKILL.md 头部标注对齐三元组：crypto-spec 版本 + sdk-spec 版本 + wop-python-sdk 最低版本
- `selftest`/`doctor` 运行时校验：SDK 版本满足 + 向量文件哈希 vs 真源一致（当前锚定 12 条版 `ce92dd4`），不一致拒跑
- git tag 发版 + CHANGELOG 记录对齐关系变更

### #10 仓库治理：全套 auto-factory
移植网关 .factory 模式：MISSION.md + 二值 triage + 验证门 + holdout + 周界清单。

**适配警告（照搬会失效）**：网关 MISSION triage 判据"doc-only 改动验证门投影为零，走人工 MR"——而 wop-skills 主体是文档。必须为文档定义执行载体：

```
wop-skills 验证门：
├─ SKILL.md lint：行数上限（<500）、首段必含安全纪律引用、references 链接有效性
├─ 安全条款哨兵：SECURITY.md 哈希变更即红（周界路径，工厂不可触碰）
├─ CLI 门：pytest + 向量一致性（12 条字节级）+ 三元组校验
└─ 周界建议：MISSION.md、SECURITY.md、skills/wop-cli/scripts/（CLI 即密码学边界，
   对应网关 crypto/ 目录同等保护）
```

直接移植网关修复后的 .factory 基线，不从零搭建。

**文档分层治理（区别对待）**：MISSION.md 承载分层表，详见 `MISSION.md` §文档分层治理——

| 层 | 文件 | 治理 |
|----|------|------|
| 宪法层 | MISSION.md、SECURITY.md | 周界：工厂永不可自改 |
| 判据层 | docs/intent.md（A1–A5 验收判据） | 周界：改动 = 重新对齐愿景，仅人工 MR（MISSION 铁律 8"判据冻结"） |
| 规格层 | docs/spec.md | 工厂可处理 + 强化义务：决策条款变更必须同步更新「条款→测试名反向核对矩阵」，测试代码带 `spec:<ID>` 标签；否定式条款必须有负向量测试（MISSION 铁律 7） |
| 载体层 | skills/、contracts/、mocks/、tests/ | 常规工厂范围 |

---

## 3. 仓库布局

```
wop-skills/  (github.com/wop-platform/wop-skills，与 6 SDK 同组织)
├── README.md                          # 安装指引：三件套全装（复制目录即可，无编译）
├── MISSION.md                         # 工厂治理（决策 #10）
├── SECURITY.md                        # 安全纪律条款（宪法级，周界保护）
├── docs/
│   ├── intent.md                      # 意图与验收判据
│   └── spec.md                        # 本文件
├── contracts/
│   └── api-discovery.openapi.yaml     # API 发现端点契约（提交平台实现）
├── mocks/api-discovery/               # CLI 联调 fixtures
└── skills/
    ├── wop-cli/                       # 基座：零代码执行
    │   ├── SKILL.md                   # <500 行：安全纪律引用 + 命令速查 + 场景剧本
    │   ├── scripts/
    │   │   ├── wop                    # CLI 入口（python）
    │   │   └── requirements.lock      # wop-python-sdk 版本锁（含 93b43ba 修复链）
    │   └── references/commands.md     # 命令详细手册
    ├── wop-dev/                       # 开发指导（前置：需 wop-cli）
    │   ├── SKILL.md                   # 协议心智模型入口
    │   └── references/
    │       ├── protocol.md            # canonicalRequest/三套件/L2 信封/F6/I7/附录 D1–D5
    │       └── sdks/{java,go,ts,python,php,dotnet}.md   # 速查+套件矩阵标注（TS/PHP 仅 RSA）
    └── wop-troubleshoot/              # 排错（前置：需 wop-cli）
        ├── SKILL.md
        └── references/
            ├── error-codes.md         # 从网关错误码枚举生成（静态，低频变化）
            └── decision-tree.md       # I7 模糊错误二叉排查树
```

## 4. 知识层内容要求（来自 2026-08-29 审计的增量）

- 尾随位纪律 D1（五类宽容实现警示）进 protocol.md
- D5 防镜像偏差（测试不得复用被测出向代码）进 protocol.md
- PHP L2 信封事故作为跨语言漂移真实案例进 protocol.md
- 11MB 流式限额 D4：CLI `call`/`verify` 实现 + protocol.md 说明
- wop-python-sdk 版本锁须包含 `93b43ba` 起的修复链（b64url 尾随位 + 三适配器流式）

## 5. 风险登记

| # | 风险 | 缓解 |
|---|------|------|
| 1 | API 发现端点排期在平台侧 | 契约先行已解耦（#4）；`--mock` 保联调 |
| 2 | gmssl（SM2 依赖）Windows 安装摩擦 | doctor 预检给明确指引；Go 单二进制后备路线 |
| 3 | diagnose 依赖"网关错误码可枚举提取"假设 | 实施首日 30 分钟 spike 验证；失败降级为纯排查树 |
| 4 | 零代码场景 agent 发起真实写操作 | SKILL.md 场景剧本写死"写操作复述确认"纪律 |
| 5 | TS/PHP SDK 仅 RSA，agent 生成 SM2 代码踩空 | 语言速查页显式套件矩阵 |
| 6 | factory 体系自身维护成本（网关事故前科） | 移植修复后基线，不从零搭；门灵敏度先行（铁律 5） |

## 6. 交付顺序（待确认的建议）

**skill 内容先行、factory 门后置**：
- 第一周：wop-cli 基座 + API 发现契约（人工 MR 合并）
- 第二周：补 .factory 门——此时已有真实变更流可供 triage/holdout 校准门灵敏度，符合铁律 5"未证明的门不是门"

## 7. 开放项

- [ ] 交付顺序确认（§6 建议待用户拍板）
- [ ] 进入实施的方式：make-plan 分阶段计划（推荐，跨仓依赖多）vs 直接开干
- [ ] API 发现端点宿主定夺（开发者中心 vs gtsp-wop-service 开放接口）——平台侧决策，契约不阻塞

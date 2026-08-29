# wop-skills 实施计划（make-plan 产物）

> 状态：2026-08-29 定稿，Phase 0 文档发现已完成（四路侦察归档于 docs/research/）
> 真源：docs/spec.md（决策）· docs/intent.md（验收 A1–A5）· SECURITY.md（S1–S8）
> 执行方式：每阶段自包含，可在新会话中连续执行；执行前必读该阶段的 Documentation references

---

## 执行约束：Ownership 矩阵（先读，决定谁干活）

| 路径 | 周界 | 变更通道 |
|---|---|---|
| skills/wop-cli/scripts/（CLI 本体） | ✅ MISSION 周界 | **人工 MR/主会话直写**，工厂不可触 |
| scripts/（lint、错误码提取） | ✅ | 人工 |
| tests/、contracts/、mocks/、skills/*/SKILL.md、references/、docs/spec.md | ❌ | 工厂链可处理 |

Phase 2/3/4 的 CLI 部分标 [人工]；其余可派工厂。

## Phase 0 汇总：Allowed APIs 与全局反模式

### Allowed APIs（唯一许可面，签名见 docs/research/sdk-api.md）

- `from wop_sdk import WopConfig, WopClient`；`WopClient(config, csprng=os.urandom)`（csprng 可注入测试）
- `client.build_request(method, path, body, level=, query_string=, expired_seconds=, extra_headers=)` → RequestDraft
- `client.verify_response(headers, body, path, method=, query_string=)` / `verify_callback(headers, body, callback_path)` → VerifyResult（headers 大小写不敏感）
- `from wop_sdk.transports import UrllibTransport, send_draft`（4xx/5xx 不抛异常，返 body；11MB read_capped 内建）
- 密钥解析 `wop_sdk.keys.load_*`；格式校验 `wop_sdk.encoding` / `wop_sdk.digest`；底层签断 `wop_sdk.signature`（selftest 字节级断言用）
- keygen 生成侧：`cryptography` 的 rsa.generate_private_key（3072/4096）+ `wop_sdk.sm2crypto.sm2_derive_public_hex`（SM2 公钥推导）

### 全局反模式（每阶段都适用）

1. **禁止手搓协议**：base64url/digest/签名/信封一律走 wop_sdk——尾随位 12 规则刚在六仓引发大修，手搓必踩
2. **向量材料禁入生产路径**：fixture 固定 IV/k、testOnly 密钥只许 selftest 消费（docs/research/vectors.md 纪律 1）
3. **I7 模糊纪律**：CLI 错误输出不得区分验签/解密失败原因；diagnose 对 1022/2005 只给排查清单
4. **私钥零输出**（S5）、argv 防御（S6）、keygen 私钥只落 0600 文件（S4）
5. **契约不暴露内部拓扑**：beSvcId/beApiPath/内部主键/auditStatus 原码值/responsiblePersonName（docs/research/api-meta.md）
6. `build_request` 的 ValueError/TypeError 不被 verify 捕获——CLI 需单独处理并给明确配置类错误
7. versionStatus 外化 `gray|full` 字符串，禁透传内部码值

## Phase 1：API 发现契约 + mock fixtures（工厂可做）

**What**
- `contracts/api-discovery.openapi.yaml`（OpenAPI 3.1）：`GET /apis`（授权范围内 API 列表）+ `GET /apis/{apiFullPath}`（详情含参数树+示例）
- `mocks/api-discovery/list.json` 与 `describe.waybill-sync.json`：覆盖嵌套参数树（object/array children）、双示例（成功/失败）、gray 与 full 两版本态
- 响应 schema 严格按 docs/research/api-meta.md §字段策略（暴露清单 + 隐藏清单 + 参数树嵌套化 + versionStatus 外化）

**Documentation references**
- 字段/口径：docs/research/api-meta.md（可见性过滤四连 + 授权可见范围）
- 真实路径样例：`/gateway/logistics.waybill.sync`（gtsp-wop-gateway/docs/tools/rsa-keygen.html:259）

**Verification**
- mock JSON 通过契约 schema 校验（python jsonschema 双向：list 与 describe 各一）；versionStatus 出现值 ⊆ {gray, full}；grep 断言契约文本无 beSvcId/beApiPath/creatorId/responsiblePersonName

**Anti-patterns**
- 禁止把管理面 ApiDefinitionDTO 原样当响应 schema（含内部字段）；禁全量目录语义（必须声明按授权过滤）

## Phase 2：CLI 骨架 + keygen + selftest + requirements.lock [人工，周界]

**What**
- `skills/wop-cli/scripts/wop`：python 单文件入口，argparse 子命令骨架；**main 首行实现 S6 argv 防御**（检测 PEM 头/长 Base64 特征 → 退出码 3 + S2 指引）
- `keygen --suite <S> [--out-dir ~/.wop]`：RSA 用 cryptography 生成（位宽校验 3072/4096）→ PKCS8(d)/SPKI(pub) Base64；SM2 随机 32B d + sm2_derive_public_hex → 04‖X‖Y 65B Base64；私钥写 0600 文件，stdout 只出公钥+路径（S4/S5）
- `selftest` 分层：L1 依赖导入（cryptography/gmssl/SDK）→ L2 formatRules 12 条全量（借 wop_sdk.encoding/digest 校验函数，哨兵 FORMAT_RULES_COUNT=12）→ L3 密码学字节级（signature/digest 段正向量 + 2 负向量必须拒）→ L4 keys 节构造 WopClient 跑 L0/L2 build_request 冒烟 → L5 三元组（SDK `__version__` 达标 + fixture MD5 == 1033af2c…）任一层红 → 退出码 2
- `skills/wop-cli/scripts/requirements.lock`：锁 `wop-python-sdk==0.1.1`（pypi 已发布并行为验收通过：`b64url_decode("aE")` 拒 / `"AA"→0x00` / 非法字符拒，2026-08-29；0.1.0 发版早于修复链 93b43ba…990107b 不可用。版本号不可信、行为可信：selftest L3 仍是最终守门）+ `tests/fixtures/crypto-vectors.json` 字节副本（MD5 断言锚）；WOP_SDK_PATH env 支持本地覆盖
- `tests/test_keygen_selftest.py`：keygen 三套件格式断言（SM2 65B 点/d 32B、RSA 位宽、0600 权限、stdout 零私钥）；selftest 分层逻辑断言；S6 argv 负向量（PEM 串入参必拒 rc=3）

**Documentation references**
- 签名/行为：docs/research/sdk-api.md §2.2/§2.4/§2.5（csprng 注入、错误层次、向量消费 copy-ready 表）
- 向量结构与纪律：docs/research/vectors.md（计数基线 + 12 条清单 + 四条硬纪律）
- keygen 输出格式：skills/wop-cli/references/commands.md §keygen + wop-specs D12

**Verification**
- `wop selftest` 全绿且分层输出；`wop keygen --suite WOP-SM2-SM3` 产物可被 `load_sm2_*` 回读；tests 全绿（pytest 门从此激活——run_tests.sh 自动接入）

**Anti-patterns**
- 禁止把向量 keys 材料缓存给 keygen 复用（纪律 1）；selftest 禁把 formatRules 当密码学向量（纪律 2）；私钥任何路径不得上 stdout/日志（S5）

## Phase 3：sign / call / verify / api --mock [人工，周界]

**What**
- `sign METHOD /gateway/<path> --body '<json>' [--level L2]`：build_request → draft JSON（headers+wireBody base64url）输出 stdout，不发送
- `call METHOD /gateway/<path> --body '<json>' [--level L2]`：sign 段 + send_draft(UrllibTransport) + verify_response；三类出口——验签通过输出 plaintext；HTTP 4xx/5xx 且 code=OP_GW_* → 结构化错误（码/语义/HTTP/建议，借 error-codes 目录）；HTTP 200 但信封 code 非 SUCCESS → 下游业务错误提示
- `verify --headers <f> --body <f> [--path <p>] [--callback]`：verify_response/verify_callback 离线验签
- `api list [--mock]` / `api describe <path> [--mock]`：--mock 读 mocks/api-discovery/；实模式 GET `WOP_DISCOVERY_URL`（Phase 1 契约），无 env 时明确指引
- `tests/test_call_sign_verify.py`：确定性断言用 csprng 注入 + digest 值断言（与时间无关）；verify roundtrip（同密钥对自造响应，模式抄 wop-python-sdk test_client roundtrip）；错误信封分流

**Documentation references**
- docs/research/sdk-api.md §2.2/§2.3（build_request 语义：extra_headers x-wop- 覆盖并参签；UrllibTransport 4xx/5xx 返 body；HttpResponse.headers 小写）
- 错误信封形态：docs/research/error-codes.md（`{code,message,traceId,timestamp}`）

**Verification**
- `wop sign` 输出的 headers 集合与 SDK test_client 断言面一致（x-wop-sign 四段式/x-wop-content-digest 格式）；`wop api list --mock` 渲染 mocks 数据；`wop verify` 对自造 L0/L2 响应 ok=true，tamper 后 ok=false 且 reason 为模糊文案

**Anti-patterns**
- 禁捕获 build_request 的 ValueError/TypeError 后静默（应转配置类退出码 2 + 明确指引）；禁在 call 失败时输出验签失败原因细节（I7）

## Phase 4：错误码提取 + diagnose + doctor [CLI 人工；提取脚本人工；error-codes.md 为生成物]

**What**
- `scripts/extract_error_codes.py`：按 docs/research/error-codes.md §提取脚本规格（正则四元组 + HTTP 8 规则 + 分段标题 + 数量断言 62/唯一性断言），生成 `skills/wop-troubleshoot/references/error-codes.md`
- `diagnose <resp.json>`：三分流（OP_GW_ → 码表；HTTP 200 非 OP_GW_ → 下游业务错误；无 code → 网络层）→ 输出码/语义/HTTP/solution/下一步；I7 两码（1022/2005）走特殊分支：排查方向清单 + traceId 查日志指引 + sign 对拍建议，禁猜根因
- `doctor`：python≥3.9 / SDK 版本达标 / cryptography+gmssl 可用 / 密钥文件权限 0600 + load_* dry-run 格式预检 / env 完整性（appKey/suite/gateway URL）
- `tests/test_diagnose.py`：62 码全样本（由提取脚本生成的 fixture 供测试）+ 未知码/残缺信封负例

**Documentation references**
- docs/research/error-codes.md（提取源 file:line + 分流规则 + I7 语义）

**Verification**
- 提取脚本输出 == 62 项且断言绿；`wop diagnose` 对 OP_GW_1022 样本输出含对拍指引且无根因猜测；负例分流正确

**Anti-patterns**
- 禁手写维护错误码 markdown（必须生成制，全量重跑）；禁 diagnose 对 I7 码输出"可能原因：密钥错误"类猜测

## Phase 5：wop-dev + wop-troubleshoot 知识层（工厂可做）

**What**
- `skills/wop-dev/`：SKILL.md（前置声明需 wop-cli + 协议心智模型入口）+ `references/protocol.md`（canonicalRequest 五段、三套件、L0/L2 信封、F6 顺序、I7、D1 尾随位五类宽容警示、D5 防镜像偏差、PHP L2 信封事故案例、11MB D4）+ `references/sdks/{java,go,ts,python,php,dotnet}.md`（速查 + 套件矩阵，TS/PHP 标注仅 RSA）
- `skills/wop-troubleshoot/`：SKILL.md（前置声明）+ `references/decision-tree.md`（I7 模糊错误二叉排查树：验签失败 → 对拍 → 定位差异 header；解密失败 → DEK/套件族自查）
- 内容真源：wop-specs 两个 spec（条款措辞直接引用带 § 号）+ 各 SDK README + docs/research/*

**Documentation references**
- docs/spec.md §4（知识层内容要求五条，逐条对应）
- wop-specs/crypto/crypto-strategy-spec.md、wop-specs/sdk/wop-sdk-spec.md（含附录 D）
- 六语言 README（../wop-{lang}-sdk/README.md）

**Verification**
- lint R1–R6 全绿（两 SKILL.md 安全引用/行数/链接）；protocol.md 抽查 D2/I1/I5/I7 措辞与 wop-specs 一致；sdks 速查套件矩阵含 TS/PHP 仅 RSA 标注

**Anti-patterns**
- 禁止复述密码学实现细节（指向 SDK）；禁止跨 skill 互相引用（引用 wop-specs 真源，spec 决策 #7）

## Phase 6：测试载体补全 + mutations 扩充 + spec 反向核对矩阵 + 终局验证（混合）

**What**
- `docs/spec-matrix.md`：条款→测试名反向核对矩阵（spec 决策 #5/#6/#9 逐条 + SECURITY S1–S8 逐条 → tests 中的 `spec:<ID>` 标签测试名）；**否定式条款必须有对应负向量测试**（S2/S3/S6 缺席即合法、I7 不区分原因等）
- tests 补 `spec:<ID>` 标签（grep 索引）；lint 增 R7：spec-matrix 中列出的测试名必须存在于 tests/（防矩阵漂移）
- mutations defects 扩充 B-2xx：移除 argv 防御→S6 测试红；破坏 selftest MD5 锚→红；diagnose 未知码 crash→红；重证 kill rate 100% + evidence-stamp 更新
- 终局：全量 `scripts/run_tests.sh` + mutations + **覆盖率终测在所有语义变更之后**（铁律 9）+ intent A1–A5 演练

**Verification（Final）**
- A1 零代码闭环：mock 端到端演练（keygen→selftest→api list --mock→call 对 mock 网关）；**真实网关版 A1 标 [BLOCKED：需平台联调环境]**，在 README 标注
- A2：注入三大高频错误（尾随位 `=`、DER 编码 SM2 签名、C1C2C3）走 sign 对拍演练定位
- A3：S6 负向量（私钥入 argv 必拒）+ 输出扫描断言零私钥材料
- A4：篡改 fixture 一字节 → selftest 拒跑（负向量测试）
- A5：全新目录安装演练（复制 skills + pip 依赖 → selftest 绿）
- git tag `v0.1.0` + CHANGELOG 三元组对齐记录

---

## 阶段依赖与并行

- Phase 1（契约+mock）独立先行——**建议立即做**，产出可直接提交平台侧并行实现端点
- Phase 2 → 3 → 4 串行（CLI 渐进）；Phase 5 与 Phase 2–4 并行（仅依赖 Phase 4 的 error-codes.md 收尾）
- Phase 6 最后（终局测量纪律）

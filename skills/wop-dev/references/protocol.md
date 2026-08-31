# WOP 协议全貌（protocol.md）

> 真源：wop-specs crypto-strategy-spec v0.3-reviewed（D14 已钉）+ sdk-spec v1.0-ratified（附录 D1–D5；§2.1 出向必传 header 契约 / §2.2 错误契约 2026-08-31 增补）。
> 本文是提炼视图；与真源冲突时以 wop-specs 为准并回修本文。

## 1. 套件（securityReq 三段式）

| securityReq | 族 | 密钥 | 摘要 | 签名 | 消息加密 | DEK 包装 |
|---|---|---|---|---|---|---|
| `WOP-RSA3072-SHA256` | RSA | RSA 3072（PKCS#8/SPKI） | SHA-256 | PKCS#1 v1.5 | AES-256-GCM | RSA-OAEP（显式双 SHA-256，空 label） |
| `WOP-RSA4096-SHA256` | RSA | RSA 4096 | SHA-256 | 同上 | AES-256-GCM | 同上（4096） |
| `WOP-SM2-SM3` | SM | SM2（d 标量 32B / 点 04‖X‖Y 65B） | SM3 | SM3withSM2 | SM4-GCM | SM2（C1C3C2） |

- 跨族组合（如 `WOP-RSA3072-SM3`）解析期拒绝（I5）
- SM2 材料喂 RSA 套件（或反向）配置期拒绝；点必须在 sm2p256v1 曲线上
- 密钥入参接受 PEM 包装或单行 Base64（D12）

## 2. canonicalRequest 与出向必传 header 契约（sdk-spec §2.1，2026-08-31 增补）

canonicalRequest 5 段 `\n` 连接；header 值 **Java URLEncoder 语义**（空格→`%20`，
不是 `+`）——这是跨语言漂移高发点（Go/PHP 默认编码语义不同）。

出向必传 header 全集（signedHeaders = 下表全部"参与签名"项，缺一即非法）：

| header | 必传条件 | 参与签名 | 值来源 |
|---|---|---|---|
| `x-wop-appkey` | 恒必传 | ✅ | `config.appKey` 同值序列化；SM2-SM3 套件 ZA 的 userId 即此值（D14，见下） |
| `x-wop-content-digest` | 有 body 必传；GET 无 body **缺席**（禁空摘要中间态，D2） | ✅ | wire body 原始字节摘要，格式见 §3 |
| `x-wop-encrypt` | 仅 L2 必传；**L0 缺席** | ✅ | `L2;dek=...`，见 §6 |
| `x-wop-nonce` | 恒必传 | ✅ | CSPRNG |
| `x-wop-timestamp` | 恒必传 | ✅ | 毫秒时间戳（F9 时间窗） |
| `x-wop-sign` | 恒必传（签名载体） | ❌ 不自签 | 四段式，见 §4 |

- 缺失任一必传项 = 非法输入：**构造期显式拒绝**（configuration 类，见 §8 表），
  **禁止静默补默认值**
- **D14（ZA userId 来源链，2026-08-31 已钉）**：SM2-SM3 下 ZA 计算的 userId =
  出向请求实际携带的 `x-wop-appkey` 值（与 `config.appKey` 同一序列化结果）——
  签名身份与请求身份恒同源；禁止库默认值（sm-crypto-v2 空串默认被 D14 排除）
  或固定盐。黄金向量 `inputs.sm2UserId=1234567812345678` 是向量夹具值，
  **不是默认值证明**。

## 3. x-wop-content-digest（D2/D3/I1）

- 格式：`<alg> <小写hex>`，**恰一个空格**；alg ∈ {sha-256, sm3}（随套件族）
- hex 恰 64 字符且**必须小写**
- GET 无 body → 头缺席；有 body → **必产且必入 signedHeaders**
- 该头与时间/nonce 无关——对拍时是唯一确定性锚

## 4. x-wop-sign（四段式）

`<securityReq> v1/<expiredSeconds>/<;joined排序头名>/<b64url签名>`

- RSA 签名 = PKCS#1 v1.5（非 PSS）
- SM2 签名 = **裸 r‖s 64 字节**（禁 DER 序列化——网上大量示例是 DER，必错）
- expiredSeconds ∈ (0, 86400]；timestamp 毫秒

## 5. base64url（F6/D10 + 附录 D1 尾随位升格）

- 字母表 `A-Za-z0-9-_`，**无填充**（出现 `=` 即拒）
- **尾随位规范**（2026-08-29 六仓大修主题）：len%4==2 时尾字符低 4 位须为零；
  len%4==3 时低 2 位须为零。宽容实现（.NET `FromBase64String`/JDK/CPython
  `urlsafe_b64decode`/PHP `base64_decode`）会**静默丢位**——锚 = Go
  `base64.RawURLEncoding.Strict()`
- 负面对：`aE`/`TWF` 拒；`AA`→`0x00`、`TWE`→`"Ma"` 收

## 6. L2 数字信封

- wire body：`{"encrypted":"<b64url(ciphertext||tag)>"}` JSON 信封（**不是裸密文**——
  PHP 仓曾实现为裸密文造成跨语言漂移，已修复）
- `x-wop-encrypt: L2;dek=<b64url(包装的DEK载荷)>`
- DEK 载荷明文结构：`alg$key$iv`（如 `AES-256-GCM$<b64u>$<b64u>`）
- DEK 与 IV 每次调用 CSPRNG 新生成（I4：同一密钥下 IV 永不复用）
- DEK alg 必须与套件族匹配（RSA→AES-256-GCM / SM2→SM4-GCM，D8/I3）

## 7. 响应/回调验证（F6 顺序固定）

```
验签 → digest 复核（有 body 才查）→ DEK 解包 → alg 族比对 → bulk 解密
```

- 回调：URI 取回调 path，方法恒 POST
- headers 大小写不敏感（SDK 统一 lower 处理）

## 8. 错误契约 WopError{category, message}（sdk-spec §2.2）与 I7 模糊化

SDK 出向可观测错误（构造器 / buildRequest 同步 throw、async reject）统一形状
`WopError{category, message}`；category 为**闭集**（小写 ASCII，跨语言恒定，
禁止自造取值），I7 文案纪律按类别固化：

| category | 触发类 | 对外 message |
|---|---|---|
| `configuration` | appKey/密钥材料缺失或非法、套件跨族/securityReq 非法 | 明确 |
| `parse` | header/信封/线上编码格式（D1/D3） | 明确 |
| `unsupported` | 合法套件但本 SDK 未实现（如 TS/PHP 首版 SM） | 明确 |
| `integrity` | digest 不匹配 | 明确 |
| `consistency` | dek alg 与套件族不符（I3） | 明确 |
| `signature` | 验签失败 | **模糊**：固定「签名验证失败」 |
| `decrypt` | 解密失败（DEK 解包/GCM tag 两路径同文案） | **模糊**：固定「解密失败」 |

- 模糊类详细原因（密钥不符/tag 失败/算法错位）只进日志；自研网关/服务端同守。
- 入向校验（verifyResponse/verifyCallback）不抛 WopError，吞并为
  `VerifyResult{ok, reason}`——该路径 category 不可观测。

## 9. 传输层（附录 D4）

响应体上限 11MB，**流式读取中生效**（禁整体缓冲后检查）。

## 10. 测试纪律（附录 D5 + 向量）

- 入向响应构造**不得复用被测的出向代码**——防镜像偏差（PHP L2 事故根源）
- 黄金向量（wop-specs crypto-vectors.json，12 条 formatRules）字节级断言；
  负向量（tamper/跨族/63B·65B 签名/带 `=` 的 b64url/C1C2C3/MGF1-SHA1 陷阱）必须拒
- `wop selftest` 是环境级向量自测（L1–L5 分层）

## 11. 事故案例（PHP L2 信封，2026-08-29）

PHP SDK 曾把 L2 线上体实现为裸密文（非 `{"encrypted":...}` 信封），
出向自测全绿（出向构造与解析同源——镜像偏差），跨语言联调才暴露。
修复三件套：信封双向修正 + D5 纪律入 spec + 反转宽容固化测试。
教训：**协议格式的测试必须锚定跨语言黄金向量，不能用自身实现自证**。

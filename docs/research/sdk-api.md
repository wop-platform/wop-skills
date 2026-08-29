# wop-python-sdk 依赖 API 侦察报告（Phase 0 文档发现）

仓库：`/Users/dreambt/sources/open-platform/wop-python-sdk`（只读侦察，未修改任何文件）

## 1. Sources consulted

| 文件 | 读取内容 |
|---|---|
| `src/wop_sdk/__init__.py` | 全文（导出面 + `__version__`） |
| `src/wop_sdk/client.py` | 全文 258 行（WopConfig/RequestDraft/VerifyResult/WopClient/`_verify_flow`/`_strict_decode_signature`） |
| `src/wop_sdk/keys.py` | 全文 105 行（材料解析 + 4 个 load_* 入口） |
| `src/wop_sdk/suites.py` | 全文 79 行（注册表常量 + `parse_suite`） |
| `src/wop_sdk/errors.py` | 全文 48 行（9 个异常类） |
| `src/wop_sdk/transports/__init__.py` | 全文 62 行（Transport/send_draft/read_capped/常量） |
| `src/wop_sdk/transports/{urllib,httpx,requests}_transport.py` | 各全文（适配器实现） |
| `src/wop_sdk/{canonical,digest,encoding,signature,envelope,sm2crypto,sm4gcm}.py` | 模块 docstring + 全部顶层 `def`/`class`/常量（grep 结构化提取） |
| `tests/conftest.py` | 全文 49 行（向量加载 + 哨兵常量） |
| `tests/test_{client,envelope,signature,digest,encoding,keys,suites,transports,transports_real,coverage_gaps,canonical}.py` | grep 消费模式（fixture 用法、向量字段、负向量断言） |
| `tests/fixtures/crypto-vectors.json` | 结构全量 + keys/digest/signature/keyEncrypt/formatRules 条目逐字段 |
| `pyproject.toml` | 全文（依赖白名单 + extras） |

## 2. Findings

### 2.1 模块结构（`src/wop_sdk/`，11 文件 + transports 子包）

| 文件 | 职责一句话 |
|---|---|
| `__init__.py` | 包门面：导出 4 个客户端类型 + `Suite`/`parse_suite` + 全部 9 个错误类，`__version__ = "0.1.0"` |
| `client.py` | 协议核心编排：`WopClient.build_request`（出向，零网络 IO）与 `verify_response`/`verify_callback`（入向，F6 固定顺序），含 3 个 dataclass |
| `suites.py` | securityReq 三段式解析 + 算法注册表（单一注册表 D13，无运行时配置） |
| `keys.py` | 密钥材料解析（PEM/Base64 双格式 → DER），RSA SPKI/PKCS#8 + SM2 点在曲线校验（I5） |
| `canonical.py` | canonicalRequest 构造（5 段 `\n` 连接，Java URLEncoder 语义 F2） |
| `digest.py` | `x-wop-content-digest: <alg> <小写hex>` 的计算/组装/格式校验/值校验（D2） |
| `encoding.py` | base64url 严格无填充编解码（F7/D10，锚 = Go `RawURLEncoding.Strict()`）+ 小写 hex + `java_urlencode` + `trimall` |
| `signature.py` | 结构化签名 `sign`/`verify`：SHA256withRSA（PKCS#1 v1.5）/ SM3withSM2（裸 r‖s 64B），定长前置校验先于密码学运算 |
| `envelope.py` | L2 数字信封：报文加解密、DEK wrap/unwrap（OAEP 双 SHA-256 / SM2 C1C3C2）、`seal_l2`/`open_l2`、DEK 载荷解析（D8/I3） |
| `sm2crypto.py` | SM2 底层：`Sm2Ops`（封装 gmssl CryptSM2，绕其 `lstrip("04")` 缺陷）、C1C3C2 加解密（补 gmssl 缺失的 C3 校验）、KDF、公钥推导 |
| `sm4gcm.py` | SM4-GCM 自研实现（SP 800-38D GCM 构造 × gmssl `one_round` 单块，D11） |
| `transports/__init__.py` | 传输层契约：`Transport` Protocol、`send_draft`、`HttpResponse`、`read_capped`、11MB 上限 |
| `transports/urllib_transport.py` | stdlib urllib 适配器（零依赖，随主包） |
| `transports/httpx_transport.py` | httpx peer 适配器（extras） |
| `transports/requests_transport.py` | requests peer 适配器（extras） |

### 2.2 核心签名（原文抄录）

**WopConfig / RequestDraft / VerifyResult**（`src/wop_sdk/client.py:50-78`）：

```python
@dataclass(frozen=True)
class WopConfig:
    """商户接入配置（密钥为材料串：PEM 或 Base64 单行，D12）。"""

    app_key: str
    suite: str
    merchant_private_key: str
    platform_public_key: str
    gateway_base_url: Optional[str] = None


@dataclass
class RequestDraft:
    """出向请求草稿：headers + wireBody，商户可直接交给任意 HTTP 栈。"""

    method: str
    path: str
    headers: Dict[str, str]
    wire_body: Optional[bytes]
    level: str


@dataclass
class VerifyResult:
    """响应/回调校验结果；reason 对验签/解密类模糊（I7）。"""

    ok: bool
    plaintext: Optional[bytes] = None
    reason: Optional[str] = None
```

- WopConfig **本身无校验**（纯 frozen dataclass）；校验全部在 `WopClient.__init__`：`app_key` 空白 → `WopSdkError("appKey 不能为空")`；suite 经 `parse_suite`；密钥经 `load_*` → `KeyMaterialError`。
- 两个 dataclass 均用位置参数全参构造（`RequestDraft("POST", "/p", headers, body, "L0")`，见 test_transports.py:28）。

**WopClient.__init__ / suite 属性**（`client.py:84-106`）：

```python
class WopClient:
    """协议核心客户端（纯函数式产出，无连接状态）。"""

    def __init__(self, config: WopConfig, csprng: Csprng = os.urandom):
        if not config.app_key or not config.app_key.strip():
            raise WopSdkError("appKey 不能为空")
        self._config = config
        self._suite = parse_suite(config.suite)
        if self._suite.family == "RSA":
            self._signer = load_rsa_private_key(
                config.merchant_private_key, self._suite.key_bits
            )
            self._wrap_pub = load_rsa_public_key(
                config.platform_public_key, self._suite.key_bits
            )
        else:
            d = load_sm2_private_key(config.merchant_private_key)
            merchant_pub_hex = sm2_derive_public_hex(d.hex())
            self._signer = Sm2Ops(private_key_hex=d.hex(), public_xy_hex=merchant_pub_hex)
            platform_pub = load_sm2_public_key(config.platform_public_key)
            self._wrap_pub = Sm2Ops(public_xy_hex=platform_pub.xy_hex)
        self._csprng = csprng

    @property
    def suite(self) -> Suite:
        return self._suite
```

`Csprng = Callable[[int], bytes]`（client.py:39）——CLI 可注入确定性 CSPRNG（测试即 `lambda n: b"\x5a" * n`）。

**build_request**（`client.py:110-120`）：

```python
def build_request(
    self,
    method: str,
    path: str,
    body: Optional[object] = None,
    *,
    level: str = "L0",
    query_string: str = "",
    expired_seconds: int = 1800,
    extra_headers: Optional[Dict[str, str]] = None,
) -> RequestDraft:
```

行为要点：
- `level` 非 L0/L2 → `ValueError`（client.py:122-123）
- L2 无 body → `ValueError("L2 封装需要明文 body")`（:173）
- body 接受 bytes/str/dict（dict → 紧凑 JSON `separators=(",", ":")`，ensure_ascii=False），其他类型 `TypeError`（:170-180）
- nonce = `csprng(16).hex()`，timestamp 毫秒（:136-137）
- `x-wop-` 前缀的 extra_headers 会**覆盖协议头并参与签名**，非 `x-wop-` 头签名后追加（:145-151,167）
- 签名头格式 `"<securityReq> v1/<expiredSeconds>/<;joined排序头名>/<b64url签名>"`（:158-163）

**verify_response / verify_callback**（`client.py:184-204`）：

```python
def verify_response(
    self,
    headers: Dict[str, str],
    body: bytes,
    path: str,
    method: str = "POST",
    query_string: str = "",
) -> VerifyResult:
    """校验平台响应（F6 顺序固定）。path/query_string = 触发本次请求的 URI。"""
    lower = {str(k).lower().strip(): str(v).strip() for k, v in (headers or {}).items()}
    try:
        return self._verify_flow(lower, body, path, method.upper(), query_string or "")
    except (SignatureVerifyError, DecryptError, ProtocolFormatError, DigestMismatchError,
            DekConsistencyError, UnsupportedSuiteError, SuiteParseError) as exc:
        return VerifyResult(ok=False, reason=str(exc))

def verify_callback(
    self, headers: Dict[str, str], body: bytes, callback_path: str
) -> VerifyResult:
    """校验平台回调（URI 取回调 path，方法恒 POST）。"""
    return self.verify_response(headers, body, callback_path, method="POST")
```

`_verify_flow` F6 顺序（:206-248）：sign 头存在/四段格式 → 版本 v1 → `parse_suite` → 套件匹配（不符 `UnsupportedSuiteError`）→ 签名严格解码（F7，失败归 `ProtocolFormatError`）→ signed headers 缺席检查 → canonical → **验签** → **digest 复核**（有 body 才查）→ 无 `x-wop-encrypt` 即 L0 返回原 body → 前缀 `L2;dek=` 检查 → `open_l2`。headers 入参大小写不敏感（统一 lower）。

**密钥解析入口**（`src/wop_sdk/keys.py:54-105`，双格式入口是 `_material_to_der`）：

```python
def _material_to_der(material: str) -> bytes:
    """密钥材料 → DER 字节：接受 PEM 包装或单行 Base64（标准/URL 字母表，允许 padding）。"""

def load_rsa_public_key(material: str, expected_bits: Optional[int] = None) -> rsa.RSAPublicKey:
def load_rsa_private_key(material: str, expected_bits: Optional[int] = None) -> rsa.RSAPrivateKey:
def load_sm2_public_key(material: str) -> Sm2PublicKey:
def load_sm2_private_key(material: str) -> bytes:
```

判定逻辑：含 `"-----BEGIN"` → 剥 PEM 壳；否则压缩空白后先试标准 Base64（validate=True），再试 URL-safe 补 padding（keys.py:37-51）。`Sm2PublicKey` frozen dataclass：`xy_hex: str`（X‖Y 128 hex 无 04 前缀）+ `uncompressed: bytes`（keys.py:27-32）。

**套件常量定义位置**（`src/wop_sdk/suites.py:13-27`）：

```python
_KEY_ALGORITHMS = {
    "RSA3072": ("RSA", 3072),
    "RSA4096": ("RSA", 4096),
    "SM2": ("SM", 0),
}
_DIGEST_ALGORITHMS = {
    "SHA256": ("RSA", "sha-256"),
    "SM3": ("SM", "sm3"),
}
_FAMILY_MESSAGE_ALG = {"RSA": "AES-256-GCM", "SM": "SM4-GCM"}
_FAMILY_KEY_WRAP = {3072: "RSA-3072-OAEP", 4096: "RSA-4096-OAEP"}
_FAMILY_SIGN = {"RSA": "SHA256withRSA", "SM": "SM3withSM2"}
```

`Suite` 为 frozen dataclass，8 字段：`security_req/family/key_bits/digest_alg/digest_tag/sign_alg/message_alg/key_wrap_alg`（suites.py:30-42）。`parse_suite(security_req: Optional[str]) -> Suite`（:44），跨族组合（如 `WOP-RSA3072-SM3`）→ `UnsupportedSuiteError`（I5）。

其他常量：`_LEVELS = ("L0", "L2")`、`_DEK_PREFIX = "L2;dek="`（client.py:41-42）；信封长度常量 `_AES_KEY_LEN=32/_SM4_KEY_LEN=16/_IV_LEN=12/_TAG_LEN=16`（envelope.py:28-31）。

### 2.3 transports 层

```python
# transports/__init__.py:49-59
@runtime_checkable
class Transport(Protocol):
    def send(
        self, method: str, url: str, headers: Dict[str, str], body: Optional[bytes]
    ) -> HttpResponse:
        ...  # pragma: no cover —— Protocol 声明

def send_draft(transport: Transport, base_url: str, draft: RequestDraft) -> HttpResponse:
    """把 RequestDraft 交给 Transport：URL = base_url + path。"""
    url = base_url.rstrip("/") + draft.path
    return transport.send(draft.method, url, draft.headers, draft.wire_body)
```

- `UrllibTransport.send(self, method: str, url: str, headers: Dict[str, str], body: Optional[bytes]) -> HttpResponse`（urllib_transport.py:25-27）；4xx/5xx **返回响应体不抛异常**（:38-43）。
- `HttpResponse(status: int, headers: Dict[str, str], body: bytes)`，headers 键统一小写（transports/__init__.py:39-45）。
- **peer 依赖加载机制**：httpx/requests 适配器不进 `transports/__init__` 的 `__all__`（只有 UrllibTransport 被尾挂导出，:62）；使用方直接 `from wop_sdk.transports.httpx_transport import HttpxTransport`。惰性导入在构造器内：`def __init__(self, client=None)` 先 `import httpx`，`ImportError` 时转抛带安装指引的 `ImportError("httpx 未安装；peer 适配器请执行 pip install 'wop-sdk[httpx]'")`（httpx_transport.py:15-22；requests_transport.py:15-22 同构）。两者均支持注入已有 `httpx.Client()`/`requests.Session()`，均实现 close/`__enter__`/`__exit__`。
- 流式限量：`MAX_RESPONSE_BYTES = 11 << 20`、`_READ_CHUNK = 1 << 16`（:19-20），`read_capped(chunks: Iterable[bytes]) -> bytes` 超 11MB 即刻抛 `ProtocolFormatError`（:23-36）。
- extras 声明（pyproject.toml:33-36）：`httpx = ["httpx>=0.24"]`、`requests = ["requests>=2.28"]`；核心依赖白名单仅 `cryptography>=41` + `gmssl>=3.2.2`（:28-31），`requires-python = ">=3.9"`。

### 2.4 错误类型层次（errors.py，9 类）

```
WopSdkError (基类)
├── 明确（鉴权前可判定的公开协议知识）
│   ├── SuiteParseError        securityReq 三段式/前缀/格式
│   ├── UnsupportedSuiteError  算法不在列表、跨族、密钥长度（I5）
│   ├── ProtocolFormatError    x-wop-sign / x-wop-encrypt / digest 头结构
│   ├── KeyMaterialError       密钥材料缺失/格式不符/不在曲线（D12、I5，配置期）
│   ├── DigestMismatchError    摘要不匹配
│   └── DekConsistencyError    DEK alg 与套件族不符（D8/I3）
└── 模糊（I7，防 oracle，默认消息固定不区分原因）
    ├── SignatureVerifyError   __init__(self, message: str = "签名验证失败")
    └── DecryptError           __init__(self, message: str = "解密失败")
```

注意：`SignatureVerifyError`/`DecryptError` 有自定义 `__init__` 默认消息；`WopClient.verify_response` 把 7 类错误统一捕获转 `VerifyResult(ok=False, reason=str(exc))`——模糊类的 `str(exc)` 就是这两句固定文案。另 `build_request` 的 `ValueError`/`TypeError`（level/body 类型）**不被捕获**、直接上抛，CLI 需单独处理。

### 2.5 向量消费方式（tests/）

- **加载**：无独立 loader 模块，仅 pytest conftest —— `tests/conftest.py:8-17` 在模块导入时 `json.load` 整个文件为 `VECTORS`，暴露 session 级 fixture `vectors`（全 dict）与 `vec_keys`（`VECTORS["keys"]`，:47-49）。测试内按 id 点查：`next(x for x in vectors["signature"] if x["id"] == "rsa3072-sign")`（test_signature.py:49）。**可复用函数**：`test_envelope.py:30-31` 的 `_vec(vectors, section, vid)` 是唯一的通用查找 helper（3 行）。
- **哨兵机制**（conftest.py:20-45）：`HEADER_RULE_IDS`/`B64URL_RULE_IDS` frozenset + `ALL_FORMAT_RULE_IDS` + `FORMAT_RULES_COUNT = 12`，配 `test_sentinels`（test_digest.py:51-55、test_encoding.py:108）强制"真源增删/改名即炸、新 id 必须显式接入"。CLI 若复用 formatRules 需复制此哨兵约定。
- **正/负向量结构**（顶层 9 节：`_meta/inputs/keys/digest/messageEncrypt/signature/keyEncrypt/dekPayload/formatRules`）：
  - 正向量按节不同：`digest[] = {id, algorithm, input, expectedHex, expectedHeader}`；`messageEncrypt[] = {id, algorithm, keyB64u, ivB64u, plaintextB64u, cipherTagB64u, format}`；`signature[] = {id, key, message, expectedSigB64u, sigLenBytes, b64uLen, format?}`；`keyEncrypt[]` 正向量 `{id, key, cipherB64u, expectedPlaintext, params, expect: "unwrap-equals-plaintext"|"decrypt-equals-plaintext"|"roundtrip"}`。
  - 负向量统一以 `expect: "reject"` 标记 + `note` 说明钉住的条款（如 `oaep3072-mgf1sha1-trap` F2 钉子、`sm2-encrypt-c1c2c3-mismatch` 顺序钉死、formatRules 全部 `{id, value, expect: accept|reject, suite?, note?}`）。
  - `keys = {rsa3072: {publicSpkiB64, privatePkcs8B64}, rsa4096: {...同构}, sm2: {publicPointB64, privateDB64, format}}`——CLI 自测可直接拿这三个 key 材料串构造 `WopConfig`（test_client.py:29-49 即此用法）。
  - `_meta.testOnly: true`，全部密钥 TEST-ONLY。

## 3. Copy-ready（file:line 清单）

| 可拷贝物 | 位置 |
|---|---|
| WopConfig/RequestDraft/VerifyResult 定义 | `src/wop_sdk/client.py:50-78` |
| WopClient.__init__ + csprng 注入 | `src/wop_sdk/client.py:84-102` |
| build_request 全流程（头组装/签名/extra_headers 语义） | `src/wop_sdk/client.py:110-168` |
| verify_response / verify_callback / _verify_flow | `src/wop_sdk/client.py:184-248` |
| 密钥双格式解析（PEM/Base64） | `src/wop_sdk/keys.py:35-51` |
| 四个 load_* 入口 | `src/wop_sdk/keys.py:54-105` |
| 套件注册表常量 | `src/wop_sdk/suites.py:13-27` |
| Suite dataclass + parse_suite | `src/wop_sdk/suites.py:30-79` |
| 错误类全清单 | `src/wop_sdk/errors.py:9-48` |
| Transport Protocol + send_draft + 11MB 上限 | `src/wop_sdk/transports/__init__.py:19-59` |
| UrllibTransport（4xx/5xx 不抛异常模式） | `src/wop_sdk/transports/urllib_transport.py:19-43` |
| peer 惰性导入 + 安装指引模式 | `src/wop_sdk/transports/httpx_transport.py:15-22`、`requests_transport.py:15-22` |
| extras/依赖白名单 | `pyproject.toml:28-36` |
| 向量加载（conftest 模式） | `tests/conftest.py:8-17` |
| 向量按 id 查找 helper | `tests/test_envelope.py:30-31` |
| formatRules 哨兵常量 | `tests/conftest.py:24-45` |
| 用向量 key 构造 WopClient 示例 | `tests/test_client.py:22-50`、`tests/test_coverage_gaps.py:47-51` |
| 黄金向量文件本体 | `tests/fixtures/crypto-vectors.json`（238 行，`_meta.testOnly`） |

## 4. Confidence + known gaps

**高置信（签名逐字抄自源码）**：全部 dataclass 字段、`WopClient.__init__`/`build_request`/`verify_response`/`verify_callback` 签名与行为、密钥解析入口、套件常量、错误层次、transports 契约、extras 声明、向量文件全部 9 节结构。

**Gaps / 注意点**：
1. **签名向量节（json 72-98）**三个条目字段已逐字段核对（`expectedSigB64u`/`sigLenBytes`/`b64uLen`），但 `messageEncrypt` 的 `plaintextB64u`/`cipherTagB64u` 长串本身未解码验证（无必要——test_envelope.py:52-80 已字节级锚定）。
2. **envelope.py:64-147 内部**（`seal_l2`/`open_l2`/`wrap_dek`/`unwrap_dek`/`parse_dek_payload` 的函数体细节）只读了签名与 docstring，未逐行读体——CLI 八件套若只经 `WopClient` 间接消费则足够；若 CLI 需直接调 `seal_l2`（签名已抄：`seal_l2(suite, platform_pub, plaintext, csprng=os.urandom) -> Tuple[bytes, str]`，envelope.py:131-133）也不受影响。
3. **conftest 加载非独立模块**：CLI 若想在 SDK 包内复用向量加载，只能拷 3 行 `json.load` 或直接依赖 `tests/fixtures/crypto-vectors.json` 路径——SDK 本身不发布向量文件（不在 package 数据中，`[tool.setuptools.packages.find] where=["src"]` 只收 src）。
4. `docs/wop-sdk-report-python.md` 与 `scripts/ci-notify-drill.sh` 未读（不在任务范围）；`.github/workflows/` 未读——若 CLI 计划需要 CI 约定需补侦察。
5. `build_request` 的 `path` 参数不做 URL 编码/规范化（原样进 canonical），query_string 需调用方自己给原始串——这是从 test_client.py:148-151 推断 + 源码 :154-156 确认的行为，置信高。

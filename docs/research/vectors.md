# 侦察归档：黄金向量与 selftest 消费方式（Phase 0，VectorScout 2026-08-29）

> 用途：wop selftest 命令的规格输入。真源 MD5 `1033af2c35b498b479e41487ccbda862`（wop-specs 与 python-sdk fixture 双侧一致实测）。

## 文件结构（顶层 9 节）

`_meta / inputs / keys / digest / messageEncrypt / signature / keyEncrypt / dekPayload / formatRules`

- `_meta.testOnly: true`——全部密钥 TEST-ONLY
- **keys 节可直接构造 WopClient**：`keys = {rsa3072: {publicSpkiB64, privatePkcs8B64}, rsa4096: {...}, sm2: {publicPointB64, privateDB64, format}}`；用法示例 `wop-python-sdk/tests/test_client.py:22-50`

## 计数基线（数量断言用）

| 维度 | 值 |
|---|---|
| 向量套节总数 | 15（正向 13 + 负向量 2） |
| 大总条目 | 27（正向/accept 17 + 负 2 + formatRules 12 计入另列） |
| formatRules | 12 = accept 4 + reject 8 |
| 负向量 | keyEncrypt/oaep3072-mgf1sha1-trap（F2 钉子）、keyEncrypt/sm2-encrypt-c1c2c3-mismatch（顺序钉死） |
| 按 suite | RSA3072 4 / RSA4096 2 / SM2 3 / AES-256-GCM 2 / SM4-GCM 2 / SHA-256 1 / SM3 1 |

## formatRules 12 条（selftest 必须全消费）

accept：header-rsa-ok、header-sm2-ok、b64url-trailing-bits-accept-2（`AA`→0x00）、b64url-trailing-bits-accept-3（`TWE`→"Ma"）
reject：header-crossfamily（I5）、header-double-space（D2）、header-uppercase-hex（F5 小写）、header-wrong-hex-len（恰 64）、b64url-with-padding（F6 拒 `=`）、b64url-illegal-char（拒 `+`）、b64url-trailing-bits-noncanonical-2（len%4==2 尾 4 位须零）、b64url-trailing-bits-noncanonical-3
（完整 id/value/note 见真源 JSON formatRules 节）

## 消费模式（copy-ready）

| 可拷贝物 | 位置 |
|---|---|
| 加载器（模块级 json.load + session fixture） | `wop-python-sdk/tests/conftest.py:10-17` |
| formatRules 哨兵三件套（ID 集合 + COUNT=12 + test_sentinels） | `wop-python-sdk/tests/conftest.py:24-45` |
| header 子集全量循环 | `tests/test_digest.py:44-69` |
| b64url 子集全量循环 | `tests/test_encoding.py:96-125` |
| 向量按 id 查找 helper（3 行） | `tests/test_envelope.py:30-31` |
| 字节级加密/解包断言 | `tests/test_envelope.py:51-81, 118-144, 172-190` |
| 签名字节级断言 | `tests/test_signature.py:47-100` |

## selftest 硬性纪律

1. **固定 IV/k 与 testOnly 密钥禁入生产路径**——selftest 按向量原样消费，向量材料不得缓存复用到 call/sign/keygen
2. formatRules 的 header 值复用 SM3 hex 且仅格式层语义（不验摘要对应）——selftest 实现须保留该区分，不得当作密码学向量
3. 向量文件不随 SDK 发布（package 只收 src/）——selftest 的 fixture 路径策略：仓库内副本 `tests/fixtures/crypto-vectors.json`（字节级，MD5 断言）+ 运行时哈希校验
4. 哨兵约定必须复制：真源增删/改名即炸、新 id 必须显式接入（FORMAT_RULES_COUNT=12 断言）

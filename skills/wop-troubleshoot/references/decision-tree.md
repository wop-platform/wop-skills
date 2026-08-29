# I7 模糊错误二叉排查树

> 适用：`OP_GW_1022`（签名验证失败）/ `OP_GW_2005`（解密失败）——对外不区分根因（防 oracle）。
> 每个节点是一个**可执行动作**，不是猜测。逐层下钻，命中即停。

## OP_GW_1022（验签失败）

```
1022
├─ 环境面（先跑 wop doctor + wop selftest）
│   ├─ selftest 红 → 修环境（SDK 版本/依赖），非代码问题
│   └─ 全绿 ↓
├─ 结构面（wop sign 产官方 draft，与自研实现逐 header diff）
│   ├─ x-wop-content-digest 不一致
│   │   ├─ 摘要算法族错（RSA 套件必须 sha-256，SM2 必须 sm3）
│   │   ├─ hex 大写/长度≠64
│   │   └─ body 序列化差异（紧凑 JSON separators=(",",":") vs 默认带空格；Unicode 转义）
│   ├─ x-wop-sign 四段式结构差异
│   │   ├─ signedHeaders 列表不一致（digest 头必须入签——I1）
│   │   └─ securityReq 拼写/大小写与授权不一致
│   ├─ canonical 差异（digest 一致但签名仍 1022）
│   │   ├─ header 值编码非 Java URLEncoder 语义（空格必须 %20 不是 +）
│   │   └─ method/path/query 拼接顺序与 SDK 不同
│   └─ 签名字节面（结构全同仍 1022）
│       ├─ SM2 签名用了 DER 编码（必须裸 r‖s 64B）★高频
│       ├─ RSA 用了 PSS（必须 PKCS#1 v1.5）
│       └─ 密钥错体：商户私钥 vs 平台密钥用反；密钥集已轮换
└─ 仍无法定位 → 持 traceId 查网关 WARN 日志（含密钥轮询验签细节）
```

## OP_GW_2005（解密失败）

```
2005（入向：商户验平台响应；出向自查 L2 请求构造）
├─ L2 请求被网关拒（对方视角 2005/5003）
│   ├─ x-wop-encrypt 的 dek 不是本套件族算法包装
│   │   （WOP-RSA* → RSA-OAEP 显式双 SHA-256；WOP-SM2 → SM2 C1C3C2）★族混用高频
│   ├─ DEK 载荷明文结构非 alg$key$iv（b64url 无填充）
│   └─ wire body 非信封 JSON {"encrypted":...}（PHP 事故形态——裸密文）
├─ 商户验平台响应报解密失败
│   ├─ 平台公钥非当前密钥集（轮换后旧公钥解包必败）→ 重新下载平台公钥
│   ├─ DEK alg 与套件族不符（网关侧配置变化）
│   └─ AAD/GCM 参数处理与 SDK 不同（应直接用 SDK，勿自研）
└─ 仍无法定位 → 持 traceId 查网关 WARN 日志
```

## 三大高频根因（2026-08-29 六仓审计实证）

1. base64url 尾随位非规范（宽容解码静默丢位）——protocol.md §5
2. SM2 签名 DER 编码（必须裸 64B）
3. SM2 密文 C1C2C3 旧国标顺序（必须 C1C3C2）

## 排查产物纪律

- 对拍 draft 可共享（不含私钥）；私钥材料永不入对话/日志（SECURITY.md S3/S5）
- 定位到根因后：先写**负向量测试**（黄金向量风格）再修——防回归且沉淀为团队资产

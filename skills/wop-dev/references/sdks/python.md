# WOP Python Sdk SDK 速查

> 真源：[wop-python-sdk README](https://github.com/wop-platform/wop-python-sdk)（双语）——
> 本文是导航视图；安装命令/示例签名以 README 为准。

## 安装

`pip install wop-python-sdk（适配器：[httpx] / [requests] extras）`

## 概念 API（sdk-spec §2 惯用映射）

```text
client = WopClient(WopConfig(app_key=…, suite=…, merchant_private_key=…, platform_public_key=…, gateway_base_url=…))
  ├─ buildRequest(method, path, body?, level=L0/L2) → RequestDraft(headers, wireBody)
  ├─ verifyResponse(headers, body, path) → VerifyResult(ok, plaintext?, reason?)
  └─ verifyCallback(headers, body, callbackPath) → VerifyResult
```

## 传输层

stdlib urllib 适配器 + httpx/requests peer（UrllibTransport（零依赖）/ HttpxTransport / RequestsTransport）

## 依赖（唯一指定路径）

cryptography（RSA/AES）+ gmssl>=3.2.2（SM）

套件矩阵：RSA3072/RSA4096 + SM2-SM3 全支持


## 对拍与自测

- 环境自证：`wop selftest`（wop-cli 基座）
- 签名对拍：`wop sign` 产官方 draft，与本语言实现逐 header diff（digest 头是确定性锚）
- 联调排错：`wop diagnose`（OP_GW_ 码 → 排查路径）

# WOP .NET Sdk SDK 速查

> 真源：[wop-dotnet-sdk README](https://github.com/wop-platform/wop-dotnet-sdk)（双语）——
> 本文是导航视图；安装命令/示例签名以 README 为准。

## 安装

`dotnet add package Wop.Sdk`

## 概念 API（sdk-spec §2 惯用映射）

```text
var client = new WopClient(config);
  ├─ buildRequest(method, path, body?, level=L0/L2) → RequestDraft(headers, wireBody)
  ├─ verifyResponse(headers, body, path) → VerifyResult(ok, plaintext?, reason?)
  └─ verifyCallback(headers, body, callbackPath) → VerifyResult
```

## 传输层

HttpClient（DelegatingHandler 可插拔）（HttpClientTransport）

## 依赖（唯一指定路径）

BouncyCastle.Net（全量含 SM）

套件矩阵：RSA3072/RSA4096 + SM2-SM3 全支持


## 对拍与自测

- 环境自证：`wop selftest`（wop-cli 基座）
- 签名对拍：`wop sign` 产官方 draft，与本语言实现逐 header diff（digest 头是确定性锚）
- 联调排错：`wop diagnose`（OP_GW_ 码 → 排查路径）

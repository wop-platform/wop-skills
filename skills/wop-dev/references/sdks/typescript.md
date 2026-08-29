# WOP TypeScript Sdk SDK 速查

> 真源：[wop-typescript-sdk README](https://github.com/wop-platform/wop-typescript-sdk)（双语）——
> 本文是导航视图；安装命令/示例签名以 README 为准。

## 安装

`npm install wop-typescript-sdk`

## 概念 API（sdk-spec §2 惯用映射）

```text
const client = new WopClient(config)
  ├─ buildRequest(method, path, body?, level=L0/L2) → RequestDraft(headers, wireBody)
  ├─ verifyResponse(headers, body, path) → VerifyResult(ok, plaintext?, reason?)
  └─ verifyCallback(headers, body, callbackPath) → VerifyResult
```

## 传输层

fetch 原生 + axios peer（FetchTransport / AxiosTransport）

## 依赖（唯一指定路径）

WebCrypto（Node>=18/浏览器）+ 纯 TS SM2/SM3/SM4-GCM

**套件矩阵：首版仅 RSA（SM2 列路线图）——agent 生成 SM2 代码前必须确认版本支持**


## 对拍与自测

- 环境自证：`wop selftest`（wop-cli 基座）
- 签名对拍：`wop sign` 产官方 draft，与本语言实现逐 header diff（digest 头是确定性锚）
- 联调排错：`wop diagnose`（OP_GW_ 码 → 排查路径）

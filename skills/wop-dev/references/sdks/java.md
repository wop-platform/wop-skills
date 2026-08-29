# WOP Java Sdk SDK 速查

> 真源：[wop-java-sdk README](https://github.com/wop-platform/wop-java-sdk)（双语）——
> 本文是导航视图；安装命令/示例签名以 README 为准。

## 安装

`Maven：wop-sdk-core + wop-sdk-okhttp / wop-sdk-jdkhttp`

## 概念 API（sdk-spec §2 惯用映射）

```text
WopClient client = new WopClient(WopConfig.builder()…build());
  ├─ buildRequest(method, path, body?, level=L0/L2) → RequestDraft(headers, wireBody)
  ├─ verifyResponse(headers, body, path) → VerifyResult(ok, plaintext?, reason?)
  └─ verifyCallback(headers, body, callbackPath) → VerifyResult
```

## 传输层

okhttp（provided）/ java.net.http（零依赖）（OkHttpTransport / JdkHttpTransport）

## 依赖（唯一指定路径）

JCA + BouncyCastle（SM 全覆盖）

套件矩阵：RSA3072/RSA4096 + SM2-SM3 全支持


## 对拍与自测

- 环境自证：`wop selftest`（wop-cli 基座）
- 签名对拍：`wop sign` 产官方 draft，与本语言实现逐 header diff（digest 头是确定性锚）
- 联调排错：`wop diagnose`（OP_GW_ 码 → 排查路径）

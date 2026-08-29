# 侦察归档：网关错误码（Phase 0，ErrCodeScout 2026-08-29）

> 用途：diagnose 命令与 error-codes.md 生成物的规格输入。spec 风险 #3 已解除。
> 完整报告：`agent://ErrCodeScout`（本仓外）；本归档保留全部提取事实。

## 提取源（唯一，全量重跑制）

| 用途 | 位置 |
|---|---|
| 错误码全表（62 项，单文件集中零散落） | `gtsp-wop-gateway/src/main/java/com/wanlianyida/gtsp/wop/gateway/domain/exception/GatewayExceptionEnum.java:30-119` |
| 每项格式 | 单行 `NAME("desc", ErrorType.X, "solution"),`；对外码值 = 枚举名（`code()` return name()，:134-136） |
| HTTP 映射（8 规则） | `infrastructure/common/HttpStatusResolver.java:28-61`：SUCCESS/空→200；特例 403 = 1003/1005/1008/1020；前缀路由 1→401、2→400、3→403、4→504、9→429；5 及未知→500 |
| 失败信封 | `{code, message, traceId, timestamp[, details[]]}`（ResponseEnvelopeFactory.java:118-126；details 仅参数校验类） |
| design.md 官方声明 | 「以代码枚举为准」docs/design.md:451-453——提取必须以枚举为源，禁依赖文档 |

## 提取脚本规格（放 scripts/extract_error_codes.py，产物进 skill）

- 正则（逐行）：`^\s{4}(OP_GW_\d{4})\("(.*)",\s*ErrorType\.(\w+),\s*"(.*)"\),?$` → 四元组 code/desc/errorType/solution
- 分段标题：枚举内 `// ====` 注释行（27-29、57-59 等）或按码段第 5 位（1=鉴权认证/2=参数校验/3=业务规则/4=依赖方异常/5=平台内部/9=限流降级）
- 输出 markdown 表：码|语义|ErrorType|HTTP|建议（solution 字段直接复用为修复建议）
- **数量断言**：提取数 == 62 当前基线（演化时全量重跑更新断言，防静默漏项）；码值唯一断言

## 码段结构（当前基线 62 项）

| 段 | 数量 | HTTP | 代表码 |
|---|---|---|---|
| OP_GW_1xxx 鉴权/认证 | 22 | 401（特例 403×4） | 1001/1003/1006/1022 |
| OP_GW_2xxx 参数校验 | 6 | 400 | 2001/2005/2006 |
| OP_GW_3xxx 业务规则 | 2 | 403 | 3001/3002 |
| OP_GW_4xxx 依赖方异常 | 5 | 504 | 4001-4005 |
| OP_GW_5xxx 平台内部 | 24 | 500 | 5001-5024 |
| OP_GW_9xxx 限流/降级 | 3 | 429 | 9001-9003 |

号段有跳号（无 1004）。

## I7 模糊码（diagnose 特殊分支）

- **OP_GW_1022「签名验证失败」**（SignFilter.java:125-126）：密钥轮询验签全部失败统一抛此码，根因只进日志
- **OP_GW_2005「解密失败」**（CryptoFilter.java:111-112, 136-137）：DEK 解包失败与解密引擎异常两类根因共用
- 对外输出固定：`{"code":"OP_GW_1022","message":"签名验证失败","traceId":"...","timestamp":"..."}`——响应体无根因可辨
- **diagnose 语义**：收到 1022/2005 只输出「排查方向清单」（solution 文案 + 对拍指引 + traceId 查网关 WARN 日志），禁止猜测根因

## diagnose 分流规则

1. `code` 以 `OP_GW_` 开头 → 查本码表
2. HTTP 200 + 非 OP_GW_ code → 下游业务错误（网关透传，AccessLogFilter.resolveBizErrorCode:133-138），不走网关码表，指引联系 API 提供方
3. 无 code / 信封残缺 → 网络层/代理问题分支

## Gaps

- ErrorType（SYS/BIZ/DAT/EXT）定义在外部框架 jar `com.wanlianyida.framework.fsscommon.enums.ErrorType`，无本仓源码——目录中保留字面值即可，不解释语义
- 静态侦察未运行时打请求；渲染链代码完整（throw→capture→failJson→servlet write），置信高

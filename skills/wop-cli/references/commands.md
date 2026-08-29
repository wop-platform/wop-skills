# wop-cli 命令手册

> 状态：接口冻结（docs/spec.md 决策 #5），载体实施中——本手册描述目标语义，
> 与实现不一致时以实现 + selftest 输出为准并回修本手册。

## 通用约定

- 配置来源：`appKey` / 套件 / 网关地址来自环境变量
  （`WOP_APP_KEY`、`WOP_SUITE`、`WOP_GATEWAY_URL`）；私钥来源仅限
  `WOP_PRIVATE_KEY` / `WOP_PRIVATE_KEY_FILE`（SECURITY.md S1）
- 输出纪律：任何命令输出零私钥材料（S5）；argv 检测到疑似私钥直接拒绝（S6）
- 退出码：0 成功；1 业务/协议失败（stderr 给明确原因）；2 配置/环境错误；
  3 防御性拒绝（S6 命中）

## keygen

`wop keygen --suite WOP-RSA3072-SHA256|WOP-RSA4096-SHA256|WOP-SM2-SM3 [--out-dir ~/.wop]`

- 私钥：写 `<out-dir>/merchant_private.<suite>`，权限 0600
- stdout：公钥（上传平台用）+ 私钥文件路径
- SM2 套件输出格式：私钥 = d 标量 32 字节 Base64；公钥 = 04‖X‖Y 65 字节 Base64
  （wop-specs D12 分发契约）

## selftest

- 消费黄金向量 fixture（12 条，锚定 wop-specs `ce92dd4`）做字节级自测
- 校验三元组：wop-python-sdk 版本 ≥ 头部要求；向量文件哈希 = `1033af2c…`
- 任一不过 → 退出码 2，拒跑其余命令

## doctor

逐项预检并输出修复指引：Python 版本、wop-python-sdk 版本、cryptography/gmssl
可用性、密钥文件权限与格式（PEM/Base64、密钥位宽、SM2 曲线点）、环境变量完整性。

## api

- `wop api list [--mock]`：拉取已授权 API 清单（契约见
  `contracts/api-discovery.openapi.yaml`；`--mock` 用 `mocks/api-discovery/`）
- `wop api describe <apiFullPath>`：参数树、出入参示例、版本状态

## call

`wop call POST /gateway/<path> --body '<json>' [--level L0|L2]`

- 全链路：build（签名+摘要+[L2 信封]）→ send → verify（F6 固定顺序）
- 传输层限额 11MB 流式（sdk-spec 附录 D4）
- 验签/解密失败对外模糊（I7），格式类错误明确

## sign

同 `call` 的构造段，但不发送；输出 headers + wireBody（JSON）。
对拍用法见 SKILL.md 剧本三。

## verify

`wop verify --headers <file> --body <file> [--path <callback-path>]`

- 验证对象：平台响应或回调通知（方法恒 POST，URI 取回调 path）
- F6 顺序：验签 → digest 复核 → DEK 解包 → alg 族比对 → bulk 解密

## diagnose

`wop diagnose <resp.json>`

- 输入：网关错误响应（含错误码）
- 输出：错误码语义 + 下一步排查动作（依据 error-codes 目录与排查树）
- I7 模糊类（验签/解密失败）：给出对拍/自检路径而非猜测原因

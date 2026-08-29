# 侦察归档：API 元数据与发现契约蓝本（Phase 0，ApiMetaScout 2026-08-29）

> 用途：contracts/api-discovery.openapi.yaml 的响应 schema 设计输入。
> 完整报告：`agent://ApiMetaScout`。字段/码值均抄自 gtsp-wop-service 源码五方交叉（实体/DTO/PO/DDL/枚举）。

## 数据模型（wop_api_defin / wop_api_ver / wop_api_para / wop_api_ver_ex）

- **ApiDefinition**（wop_api_defin）：apiFullPath（业务域编码+apiPath，对外完整路径，不可变）、apiName、httpRequestMethod（默认 POST）、contentType [10-json,20-form,30-multipart,40-xml,50-text]、apiDescription、queryFlag、idempotentFlag、conn/readTimeout、qpsLimitThreshold、groupTag、apiStatus [10 草稿,20 已发布,30 已下线]（由版本派生）
- **ApiVersion**（wop_api_ver）：versionNumber、verStatus [10 未发布,20 灰度,30 全量,40 废弃,50 下线]、auditStatus [10 未提交,20 待审,30 驳回,40 通过]、defFlag（默认版本）、beSvcId/beApiPath（内部路由，**禁暴露**）
- **参数树**（wop_api_para）：parentParaId 自关联（根=0）；paraRange [10-Header,20-Param,30-Body请求,40-响应] 一树四区；paraType [10-string..60-array..80-bigDecimal]；mustFillFlag/checkRule/defVal/exVal/paraDscr/sortNo
- **示例**（wop_api_ver_ex）：exType [10-成功,20-失败]；requestExample/responseExample 自由文本（text 列）；「至少一条成功示例方可提交审核」

## 网关可见性口径（发现契约复用同口径）

`api_status=20 ∧ del_flag=0`（defin 层）+ `audit_status=40 ∧ ver_status∈{20,30} ∧ del_flag=0`（版本层）
——来源 GatewayDataAppService.apiInfo L249-347 / ApiDefinitionDomainService.queryPublishedByPath L144-150

**发现契约可见范围**：按商户 appKey 的已授权 API 列表（授权口径同 AppCapabilityAuthorizationApiDTO：apiFullPath + 授权起止日期），非全量目录。

## 契约字段策略（暴露/隐藏）

**暴露**：apiFullPath（主键级）、apiName、apiDescription、httpRequestMethod、contentType（外化为 `json|form|multipart|xml|text`）、queryFlag、idempotentFlag、connectionTimeoutMs/readTimeoutMs、qpsLimitThreshold、groupTag、businessDomainCode、versionNumber、versionStatus（**外化 `gray|full` 字符串，不透传内部码值**）、参数树（嵌套 children 化）、requestExample/responseExample、updatedAt（可选缓存校验）

**隐藏**：beSvcId/beApiPath（内部路由拓扑）、全部内部主键外键（defin id/apiId/版本 id/参数节点 id/apiVersionId/parentParameterId）、auditStatus/importSource/apiStatus 原码值、creatorId/lastUpdaterId/delFlag/createTime、responsiblePersonName（具名 PII，如需走脱敏 supportContact）

**参数树外化形态**：嵌套 `children`（去 parentParaId），节点字段收窄：`name/type/range(外化 header|query|body|response)/required/checkRule/default/example/description/sort/children`

## 平台侧注意（提给实现发现端点的团队）

1. `countActiveByApiId` 未过滤 del_flag（RepositoryImpl L69-74）——实现侧过滤须补 del_flag=0
2. 对外契约勿依赖 api_status 派生链，直接以版本层口径为准
3. 端点宿主未决（developer 空壳仓 vs gtsp-wop-service 开放接口）——spec 开放项 #3

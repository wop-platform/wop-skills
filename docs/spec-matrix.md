# spec 条款 → 测试名反向核对矩阵

> 治理依据：MISSION 铁律 7（spec 条款不因现状顺延）+ 文档分层治理（规格层强化义务）。
> 规则：每条可测条款必须列出对应测试（`spec:<ID>` 标签 grep 索引）；
> **否定式条款（禁止 X / 缺席合法）必须有对应负向量测试**。
> lint R7 校验：本文列出的测试名必须存在于 tests/（防矩阵漂移）。

## spec.md 决策 #5 命令面（八件套）

| 条款 | 测试 |
|------|------|
| keygen 三套件产物 + 0600 + stdout 零私钥 | `test_rsa_product_roundtrip_and_permissions` `test_sm2_product_format_and_roundtrip` |
| keygen 拒绝覆盖已有私钥（O_EXCL） | `test_refuse_overwrite_existing_key` |
| 未知套件拒绝 | `test_unknown_suite_rejected` |
| selftest 分层全绿 | `test_all_layers_green` |
| selftest 篡改 fixture 拒跑（A4 负向量） | `test_tampered_fixture_refuses_to_run` |
| selftest 锚常量（MD5/版本/12 条） | `test_version_floor_enforced` |
| sign draft 结构 + digest 确定性（对拍锚） | `test_draft_structure_and_deterministic_digest` |
| sign L2 信封形态 | `test_l2_envelope_shape` |
| sign 缺配置 exit 2 | `test_missing_config_exit_2` |
| call 全链路明文（roundtrip） | `test_roundtrip_plaintext` |
| call 网关错误信封分流 | `test_gateway_error_envelope` |
| verify roundtrip | `test_roundtrip_ok` |
| verify tamper 拒绝 + reason 模糊（I7 否定式） | `test_tampered_body_rejected_with_vague_reason` |
| verify 回调模式 | `test_callback_mode` |
| api list/describe --mock | `test_list_renders` `test_describe_mock` |
| api 实模式无 env 明确指引（缺席合法） | `test_real_mode_requires_env` |
| diagnose 62 码全样本 | `test_all_62_codes_known` |
| diagnose I7 给方向不猜根因（否定式） | `test_i7_codes_give_direction_not_guesses` |
| diagnose 未知码漂移指引 | `test_unknown_opgw_code_flags_drift` |
| diagnose 下游/网络分流 | `test_downstream_business_error_branch` `test_no_code_network_branch` |
| diagnose 码表完整性哨兵 | `test_missing_catalog_reports_regen_path` |
| doctor 全绿 | `test_full_env_green` |
| doctor 密钥权限过宽告警 | `test_wide_key_permissions_flagged` |

## spec.md 决策 #6 / SECURITY.md S1–S8

| 条款 | 测试 | 否定式 |
|------|------|--------|
| S1 私钥唯一通道（env/0600 文件） | `test_full_env_green`（0600 ✓ 路径）+ CLI `_read_key_material` 实现面 | `test_wide_key_permissions_flagged`（权限过宽必拒） |
| S2 禁止私钥入 argv | `test_pem_in_argv_rejected` `test_long_base64_block_rejected` | —（正向即负向断言） |
| S3 禁止私钥入对话 | SKILL.md 剧本纪律（文档面，lint R3 覆盖引用义务） | — |
| S4 keygen 0600 + 拒覆盖 | `test_rsa_product_roundtrip_and_permissions` `test_refuse_overwrite_existing_key` | 覆盖尝试必须失败 |
| S5 CLI 输出零私钥 | `test_rsa_product_roundtrip_and_permissions`（stdout 断言） | 私钥串出现在 stdout 即失败 |
| S6 argv 主动防御 | `test_pem_in_argv_rejected` `test_long_base64_block_rejected` `test_guard_function_unit` | `test_normal_args_not_blocked`（合法参数不误伤） |
| S7 写操作复述确认 | SKILL.md 剧本二（文档面；call help 文案含提示） | — |
| S8 纪律优先级 | SECURITY.md 宪法面（guard 门 G-02 保护） | — |

## spec.md 决策 #9 三元组

| 条款 | 测试 |
|------|------|
| 向量哈希锚（1033af2c…） | `test_tampered_fixture_refuses_to_run` `test_version_floor_enforced` |
| SDK 版本下限 (0,1,1) | `test_version_floor_enforced` `test_all_layers_green`（L1 层） |
| formatRules 12 条哨兵 | `test_version_floor_enforced`（常量）+ selftest L2 全量循环 |

## intent.md 判据 → 测试映射

| 判据 | 承接测试/演练 |
|------|--------------|
| A1 零代码闭环 | mock 端到端：`test_roundtrip_plaintext`（call 全链路）+ `test_list_renders`（api 发现）+ `test_sm2_product_format_and_roundtrip`（keygen 冷启动）；真实网关版 [BLOCKED：平台联调环境] |
| A2 对拍定位 | `test_draft_structure_and_deterministic_digest`（digest 锚）+ decision-tree.md 方法论 + `test_i7_codes_give_direction_not_guesses` |
| A3 私钥隔离 | S6 三测试 + `test_tampered_body_rejected_with_vague_reason`（I7 reason 模糊否定式） |
| A4 漂移拒跑 | `test_tampered_fixture_refuses_to_run` |
| A5 安装即用 | selftest L1-L5（环境自证）；全量安装演练待 README（spec §7 开放项） |

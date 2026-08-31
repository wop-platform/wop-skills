#!/usr/bin/env python3
"""extract_error_codes.py —— 网关错误码目录生成器（全量重跑制）。

规格真源：docs/research/error-codes.md（ErrCodeScout 2026-08-29，spec 风险 #3 已解除）。
提取源（唯一）：gtsp-wop-gateway GatewayExceptionEnum.java:30-119——单行四元组
`NAME("desc", ErrorType.X, "solution"),`；HTTP 映射 8 规则照抄 HttpStatusResolver。

产物：
  1. skills/wop-cli/scripts/error-codes.json          —— CLI diagnose 消费（结构化）
  2. skills/wop-troubleshoot/references/error-codes.md —— 人/agent 阅读（含建议）

纪律：每次生成全量重跑 + 数量断言（BASELINE_COUNT）+ 码值唯一断言；
网关枚举演化后更新 BASELINE_COUNT 并重新生成（禁止手改产物）。

用法：python3 scripts/extract_error_codes.py [<gateway-repo>]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_GW = REPO.parent / "gtsp-wop-gateway"
ENUM_REL = "src/main/java/com/wanlianyida/gtsp/wop/gateway/domain/exception/GatewayExceptionEnum.java"

BASELINE_COUNT = 62  # 2026-08-29 基线；枚举演化时更新并重跑

LINE_RE = re.compile(r'^\s{4}(OP_GW_\d{4})\("(.*)",\s*ErrorType\.(\w+),\s*"(.*)"\),?$')

SEGMENTS = {
    "1": "鉴权/认证",
    "2": "参数校验",
    "3": "业务规则",
    "4": "依赖方异常",
    "5": "平台内部",
    "9": "限流/降级",
}
HTTP_SPECIAL_403 = {"OP_GW_1003", "OP_GW_1005", "OP_GW_1008", "OP_GW_1020"}
HTTP_PREFIX = {"1": 401, "2": 400, "3": 403, "4": 504, "9": 429}

I7_CODES = {"OP_GW_1022": "签名验证失败", "OP_GW_2005": "解密失败"}


def http_status(code: str) -> int:  # HttpStatusResolver.java:28-61 语义
    if code in HTTP_SPECIAL_403:
        return 403
    return HTTP_PREFIX.get(code[len("OP_GW_"):][0], 500)


def extract(enum_path: Path) -> list[dict]:
    rows = []
    seen = set()
    for line in enum_path.read_text(encoding="utf-8").splitlines():
        m = LINE_RE.match(line)
        if not m:
            continue
        code, desc, etype, solution = m.groups()
        if code in seen:
            raise SystemExit(f"码值重复：{code}")
        seen.add(code)
        rows.append({
            "code": code, "description": desc, "errorType": etype,
            "http": http_status(code), "solution": solution,
            "segment": SEGMENTS.get(code[len("OP_GW_"):][0], "未分类"),
            "i7": code in I7_CODES,
        })
    return rows


def main(argv: list) -> int:
    gw = Path(argv[1]) if len(argv) > 1 else DEFAULT_GW
    enum_path = gw / ENUM_REL
    if not enum_path.is_file():
        print(f"错误码枚举不存在：{enum_path}", file=sys.stderr)
        return 2
    rows = extract(enum_path)
    if len(rows) != BASELINE_COUNT:
        print(f"提取数 {len(rows)} != 基线 {BASELINE_COUNT}——枚举已演化，"
              f"确认后更新 BASELINE_COUNT 并重跑（防静默漏项）", file=sys.stderr)
        return 2

    # JSON（CLI diagnose 消费）
    json_out = REPO / "skills" / "wop-cli" / "scripts" / "error-codes.json"
    json_out.write_text(json.dumps({
        "source": "gtsp-wop-gateway GatewayExceptionEnum.java",
        "generated_baseline": BASELINE_COUNT,
        "i7_codes": sorted(I7_CODES),
        "codes": rows,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # Markdown（troubleshoot 知识层）
    md_out = REPO / "skills" / "wop-troubleshoot" / "references" / "error-codes.md"
    md_out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 网关错误码目录（生成物——禁手改）",
        "",
        "> 提取源：`gtsp-wop-gateway/.../GatewayExceptionEnum.java`（唯一真源，design.md §10.3）",
        f"> 数量基线：{BASELINE_COUNT} 项 · 重新生成：`python3 scripts/extract_error_codes.py`",
        "> I7 模糊码（1022/2005）：对外不区分根因——diagnose 只给排查方向，禁猜原因",
        "",
    ]
    for seg_key in sorted(SEGMENTS):
        seg_rows = [r for r in rows if r["segment"] == SEGMENTS[seg_key]]
        if not seg_rows:
            continue
        lines += [f"## {SEGMENTS[seg_key]}（OP_GW_{seg_key}xxx）", "",
                  "| 码 | 语义 | 类型 | HTTP | 处理建议 |", "|---|---|---|---|---|"]
        for r in seg_rows:
            i7_mark = " ⚠️I7" if r["i7"] else ""
            lines.append(f"| `{r['code']}`{i7_mark} | {r['description']} | {r['errorType']} "
                         f"| {r['http']} | {r['solution']} |")
        lines.append("")
    lines += [
        "## 分流规则（diagnose 语义）", "",
        "1. `code` 以 `OP_GW_` 开头 → 查本表",
        "2. HTTP 200 且 code 非 OP_GW_ → 下游业务错误（网关透传），联系 API 提供方",
        "3. 无 code / 信封残缺 → 网络层/代理问题",
        "",
        "**I7 两码的排查路径**：`OP_GW_1022` → 用 `wop sign` 对拍定位签名串差异；"
        "`OP_GW_2005` → 核查 DEK/套件族一致性；均可用 traceId 查网关 WARN 日志取真实根因。",
    ]
    md_out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"提取 {len(rows)} 项 ✓")
    print(f"  → {json_out.relative_to(REPO)}")
    print(f"  → {md_out.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

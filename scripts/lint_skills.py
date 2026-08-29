#!/usr/bin/env python3
"""SKILL.md lint + 结构哨兵——wop-skills 文档型验证门（MISSION triage 判据 2 的执行载体）。

规则（spec.md 决策 #10 验证门，spec:lint-*）：
  R1 基座存在   spec:lint-base    skills/wop-cli/SKILL.md 必须存在
  R2 行数上限   spec:lint-lines   每个 SKILL.md ≤ 500 行
  R3 安全引用   spec:lint-sec     SKILL.md 前 40 行必须引用 SECURITY.md
  R4 链接有效   spec:lint-links   SKILL.md/commands.md 内 markdown 相对链接目标必须存在
  R5 基座脚本域 spec:lint-scripts skills/wop-cli/scripts/ 目录必须存在
  R6 判据层在位 spec:lint-intent  docs/intent.md 必须含 A1–A5 判据表

退出码：0 全绿；1 有违规。fail-closed：IO 异常按违规处理。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MAX_LINES = 500
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def violations() -> list[str]:
    out: list[str] = []

    # R1 基座
    base_skill = REPO / "skills" / "wop-cli" / "SKILL.md"
    if not base_skill.is_file():
        out.append("spec:lint-base R1 违规：基座 skills/wop-cli/SKILL.md 不存在")
        return out

    # R2/R3/R4 逐 SKILL.md
    for skill in sorted(REPO.glob("skills/*/SKILL.md")):
        text = skill.read_text(encoding="utf-8")
        lines = text.splitlines()
        if len(lines) > MAX_LINES:
            out.append(
                f"spec:lint-lines R2 违规：{skill.relative_to(REPO)} "
                f"{len(lines)} 行 > {MAX_LINES}"
            )
        head = "\n".join(lines[:40])
        # B-102 教训：裸字样可被 frontmatter description 顺带提及绕过——
        # R3 要求 markdown 链接形式（可点引用，且目标存在性由 R4 复验）
        if not re.search(r"\[[^\]]*SECURITY\.md[^\]]*\]\([^)]+\)", head):
            out.append(
                f"spec:lint-sec R3 违规：{skill.relative_to(REPO)} 前 40 行缺少指向 SECURITY.md 的 markdown 链接"
            )
        for target in LINK_RE.findall(text):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            dest = (skill.parent / target.split("#")[0]).resolve()
            if not dest.exists():
                out.append(
                    f"spec:lint-links R4 违规：{skill.relative_to(REPO)} 链接目标不存在 → {target}"
                )

    # R4 扩展：references 下 md 的相对链接
    for ref in sorted(REPO.glob("skills/*/references/*.md")):
        text = ref.read_text(encoding="utf-8")
        for target in LINK_RE.findall(text):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            dest = (ref.parent / target.split("#")[0]).resolve()
            if not dest.exists():
                out.append(
                    f"spec:lint-links R4 违规：{ref.relative_to(REPO)} 链接目标不存在 → {target}"
                )

    # R5 基座脚本域
    scripts_dir = REPO / "skills" / "wop-cli" / "scripts"
    if not scripts_dir.is_dir():
        out.append("spec:lint-scripts R5 违规：skills/wop-cli/scripts/ 目录不存在")

    # R6 判据层
    intent = REPO / "docs" / "intent.md"
    if not intent.is_file():
        out.append("spec:lint-intent R6 违规：docs/intent.md 不存在")
    else:
        itext = intent.read_text(encoding="utf-8")
        for aid in ("A1", "A2", "A3", "A4", "A5"):
            if aid not in itext:
                out.append(f"spec:lint-intent R6 违规：docs/intent.md 缺判据 {aid}")

    # R7 矩阵漂移：spec-matrix 列出的测试名必须真实存在（MISSION 铁律 7 载体）
    matrix = REPO / "docs" / "spec-matrix.md"
    if not matrix.is_file():
        out.append("spec:lint-matrix R7 违规：docs/spec-matrix.md 不存在")
    else:
        import re as _re
        mtext = matrix.read_text(encoding="utf-8")
        test_names = set(_re.findall(r"`(test_[a-z0-9_]+)`", mtext))
        tests_blob = "\n".join(
            f.read_text(encoding="utf-8") for f in REPO.glob("tests/*.py")
        )
        for name in sorted(test_names):
            if name not in tests_blob:
                out.append(
                    f"spec:lint-matrix R7 违规：矩阵测试名不存在于 tests/ → {name}"
                )

    return out

def main() -> int:
    try:
        found = violations()
    except OSError as exc:
        print(f"LINT: fail-closed（IO 异常视为违规）: {exc}", file=sys.stderr)
        return 1
    if found:
        print("LINT: 违规清单：", file=sys.stderr)
        for v in found:
            print(f"  - {v}", file=sys.stderr)
        return 1
    print("LINT: 通过（R1–R7 全绿）")
    return 0

if __name__ == "__main__":
    sys.exit(main())

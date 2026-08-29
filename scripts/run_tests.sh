#!/usr/bin/env bash
# wop-skills 验证门（factory-local.json final_gate_cmd）：
#   1. guard self-check（MISSION ↔ factory-local.json 周界一致 + 路径存在）
#   2. SKILL.md lint + 结构哨兵（R1–R7，含 spec-matrix 反向核对）
#   3. CLI pytest + 行覆盖率门（CLAUDE.md ≥95%；subprocess 归集经 tests/conftest.py
#      注入 COVERAGE_PROCESS_START + sitecustomize；parallel 数据 combine 后判定）
# --no-lock：工厂链契约参数（网关语义为跳过 blob 锁；本仓无 blob 锁，接受即忽略）。
set -euo pipefail
cd "$(dirname "$0")/.."

python3 - <<'PY'
import sys
sys.path.insert(0, ".factory")
import guard
guard.self_check()
print("gate: guard self-check OK（周界一致）")
PY

python3 scripts/lint_skills.py

if [ -d tests ] && compgen -G 'tests/*.py' >/dev/null 2>&1; then
  python3 -m coverage run --rcfile=.coveragerc -m pytest tests/ -q
  python3 -m coverage combine >/dev/null
  python3 -m coverage report --rcfile=.coveragerc --fail-under=95
  python3 -m coverage erase
else
  echo "gate: tests/ 载体未建，pytest 门挂起（CLI 落地后自动接入）"
fi

echo "gate: all green"

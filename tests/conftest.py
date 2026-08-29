"""pytest conftest——子进程覆盖率归集注入（CLAUDE.md 变更行覆盖率 ≥95% 门禁）。

机制：CLI 测试经 subprocess 调 `skills/wop-cli/scripts/wop`；coverage 通过
COVERAGE_PROCESS_START + sitecustomize（tests/_covboot/，经 PYTHONPATH 注入，
.pth 在非 site 目录不被处理）在子进程启动时归集。parallel 模式各自写
.coverage.<host>.<pid>.<rand>，由 run_tests.sh 统一 combine。
直接 `pytest tests/`（不经 run_tests.sh）时数据文件留在原地，不影响断言。
"""

from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
_BOOT = REPO / "tests" / "_covboot"

if _BOOT.is_dir():
    os.environ["COVERAGE_PROCESS_START"] = str(REPO / ".coveragerc")
    existing = os.environ.get("PYTHONPATH", "")
    parts = [p for p in existing.split(os.pathsep) if p]
    if str(_BOOT) not in parts:
        parts.insert(0, str(_BOOT))
    os.environ["PYTHONPATH"] = os.pathsep.join(parts)

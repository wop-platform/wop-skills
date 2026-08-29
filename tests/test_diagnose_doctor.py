"""wop CLI Phase 4 测试：diagnose 三分流 + I7 语义 + doctor 预检。

错误码目录为生成物（scripts/extract_error_codes.py → error-codes.json），
测试对 62 码全样本 + 分流负例断言（spec:#5-diagnose / docs/research/error-codes.md）。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
CLI = REPO / "skills" / "wop-cli" / "scripts" / "wop"
CATALOG = json.loads((REPO / "skills" / "wop-cli" / "scripts" / "error-codes.json").read_text())


def run_diag(payload: dict) -> tuple[int, dict]:
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(payload, f)
        name = f.name
    try:
        r = subprocess.run([sys.executable, str(CLI), "diagnose", name],
                           capture_output=True, text=True, timeout=30)
        return r.returncode, json.loads(r.stdout)
    finally:
        os.unlink(name)


class TestDiagnose:
    def test_all_62_codes_known(self):  # spec:#5-diagnose 全码表样本
        for entry in CATALOG["codes"]:
            rc, out = run_diag({"code": entry["code"], "message": entry["description"],
                                "traceId": "t", "http_status": entry["http"]})
            assert rc == 0
            assert out["known"] is True, entry["code"]
            assert out["meaning"] == entry["description"]
            assert out["http"] == entry["http"]
            assert out["solution"]  # solution 非空（复用枚举处理建议）

    def test_i7_codes_give_direction_not_guesses(self):  # spec:#5-diagnose I7 禁猜根因
        for code in ("OP_GW_1022", "OP_GW_2005"):
            rc, out = run_diag({"code": code, "message": "x"})
            assert rc == 0 and out["i7_vague"] is True
            assert len(out["investigate"]) >= 3
            joined = " ".join(out["investigate"])
            assert "对拍" in joined or "核查" in joined  # 给动作不给结论
            # 否定式条款：不出现根因断言词
            for banned in ("原因是", "因为密钥错", "确认是"):
                assert banned not in joined

    def test_unknown_opgw_code_flags_drift(self):  # 版本漂移指引
        rc, out = run_diag({"code": "OP_GW_9999"})
        assert rc == 0 and out["known"] is False
        assert "extract_error_codes" in out["next"]

    def test_downstream_business_error_branch(self):  # HTTP 200 非 OP_GW_
        rc, out = run_diag({"code": "BIZ_4001", "message": "运单号格式非法", "http_status": 200})
        assert rc == 0 and out["branch"] == "downstream"
        assert "API 提供方" in out["next"]

    def test_no_code_network_branch(self):  # 无信封
        rc, out = run_diag({"raw": "connection reset"})
        assert rc == 0 and out["branch"] == "network"

    def test_missing_catalog_reports_regen_path(self):  # 码表缺失自检
        assert CATALOG["generated_baseline"] == 62
        codes = [c["code"] for c in CATALOG["codes"]]
        assert len(set(codes)) == 62
        assert set(CATALOG["i7_codes"]) == {"OP_GW_1022", "OP_GW_2005"}


class TestDoctor:
    def test_full_env_green(self):  # spec:#5-doctor
        v = json.loads((REPO / "tests" / "fixtures" / "crypto-vectors.json").read_text())
        k = v["keys"]["sm2"]
        import tempfile, stat
        with tempfile.NamedTemporaryFile("w", suffix=".b64", delete=False) as f:
            f.write(k["privateDB64"])
            keyf = f.name
        os.chmod(keyf, 0o600)
        env = {**os.environ, "WOP_APP_KEY": "a", "WOP_SUITE": "WOP-SM2-SM3",
               "WOP_GATEWAY_URL": "https://wop.example.com", "WOP_PRIVATE_KEY_FILE": keyf}
        try:
            r = subprocess.run([sys.executable, str(CLI), "doctor"],
                               capture_output=True, text=True, env=env, timeout=30)
            assert r.returncode == 0, r.stdout + r.stderr
            assert "doctor: 全绿" in r.stdout
            assert "WOP_PRIVATE_KEY_FILE 0600 ✓" in r.stdout
        finally:
            os.unlink(keyf)

    def test_wide_key_permissions_flagged(self):
        v = json.loads((REPO / "tests" / "fixtures" / "crypto-vectors.json").read_text())
        k = v["keys"]["sm2"]
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".b64", delete=False) as f:
            f.write(k["privateDB64"])
            keyf = f.name
        os.chmod(keyf, 0o644)  # 过宽
        env = {**os.environ, "WOP_PRIVATE_KEY_FILE": keyf}
        try:
            r = subprocess.run([sys.executable, str(CLI), "doctor"],
                               capture_output=True, text=True, env=env, timeout=30)
            assert r.returncode == 2
            assert "权限过宽" in r.stdout
        finally:
            os.unlink(keyf)

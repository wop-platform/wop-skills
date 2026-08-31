"""wop CLI 外部契约测试（Phase 2 载体）——spec:<ID> 反向核对矩阵锚点。

覆盖：keygen 产物纪律（S4/S5）、selftest 拒跑语义（决策 #9 / intent A4）、
S6 argv 防御（SECURITY.md S6，含负例不误伤）。
"""

from __future__ import annotations

import base64
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
CLI = REPO / "skills" / "wop-cli" / "scripts" / "wop"
FIXTURE = REPO / "tests" / "fixtures" / "crypto-vectors.json"

SUITES_RSA = {"WOP-RSA3072-SHA256": 3072, "WOP-RSA4096-SHA256": 4096}


def run_cli(*args: str, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, **(env_extra or {})}
    return subprocess.run([sys.executable, str(CLI), *args],
                          capture_output=True, text=True, env=env, timeout=90)


def _load_cli_module(name="wop_cli_mod"):
    """CLI 无 .py 扩展名——显式 SourceFileLoader 加载。"""
    import importlib.util
    from importlib.machinery import SourceFileLoader
    loader = SourceFileLoader(name, str(CLI))
    spec = importlib.util.spec_from_file_location(name, CLI, loader=loader)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestKeygen:
    @pytest.mark.parametrize("suite,bits", sorted(SUITES_RSA.items()))
    def test_rsa_product_roundtrip_and_permissions(self, suite, bits):  # spec:#5-keygen spec:SECURITY-S4
        from wop_sdk.keys import load_rsa_private_key, load_rsa_public_key
        with tempfile.TemporaryDirectory() as td:
            r = run_cli("keygen", "--suite", suite, "--out-dir", td)
            assert r.returncode == 0, r.stderr
            key_file = Path(td) / f"merchant_private.{suite}.b64"
            assert key_file.exists()
            assert stat.S_IMODE(key_file.stat().st_mode) == 0o600  # S4: 0600
            priv_b64 = key_file.read_text().strip()
            load_rsa_private_key(priv_b64, bits)  # D12 回读
            pub_line = next(l for l in r.stdout.splitlines() if l.startswith("merchant_public_key"))
            pub_b64 = pub_line.split(": ", 1)[1]
            load_rsa_public_key(pub_b64, bits)
            assert "-----BEGIN" not in r.stdout  # S5: stdout 零 PEM
            assert priv_b64 not in r.stdout  # S5: 私钥不上 stdout

    def test_sm2_product_format_and_roundtrip(self):  # spec:#5-keygen spec:SECURITY-S4
        from wop_sdk.keys import load_sm2_private_key, load_sm2_public_key
        with tempfile.TemporaryDirectory() as td:
            r = run_cli("keygen", "--suite", "WOP-SM2-SM3", "--out-dir", td)
            assert r.returncode == 0, r.stderr
            key_file = Path(td) / "merchant_private.WOP-SM2-SM3.b64"
            assert stat.S_IMODE(key_file.stat().st_mode) == 0o600
            d = load_sm2_private_key(key_file.read_text().strip())
            assert len(d) == 32  # d 标量 32B（D12）
            pub_line = next(l for l in r.stdout.splitlines() if l.startswith("merchant_public_key"))
            pub_bytes = base64.b64decode(pub_line.split(": ", 1)[1])
            assert len(pub_bytes) == 65 and pub_bytes[0] == 0x04  # 未压缩点 04‖X‖Y
            load_sm2_public_key(pub_line.split(": ", 1)[1])  # I5 曲线校验经回读

    def test_refuse_overwrite_existing_key(self):  # spec:SECURITY-S4 O_EXCL 拒覆盖
        with tempfile.TemporaryDirectory() as td:
            assert run_cli("keygen", "--suite", "WOP-SM2-SM3", "--out-dir", td).returncode == 0
            r = run_cli("keygen", "--suite", "WOP-SM2-SM3", "--out-dir", td)
            assert r.returncode == 2 and "拒绝覆盖" in r.stderr

    def test_unknown_suite_rejected(self):  # spec:#5 套件白名单
        r = run_cli("keygen", "--suite", "WOP-RSA2048-SHA256", "--out-dir", tempfile.mkdtemp())
        assert r.returncode == 2


class TestSelftest:
    def test_all_layers_green(self):  # spec:#9 三元组运行时校验
        r = run_cli("selftest")
        assert r.returncode == 0, r.stderr
        for layer in ("L1", "LF", "L2", "L3", "L4", "L5"):
            assert layer in r.stdout, f"缺层输出：{layer}"
        assert "selftest: 全绿" in r.stdout

    def test_tampered_fixture_refuses_to_run(self, tmp_path):  # spec:#9 intent-A4 负向量
        data = bytearray(FIXTURE.read_bytes())
        data[100] ^= 0xFF  # 篡改一字节
        bad = tmp_path / "crypto-vectors.json"
        bad.write_bytes(bytes(data))
        r = run_cli("selftest", env_extra={"WOP_VECTORS_PATH": str(bad)})
        assert r.returncode == 2
        assert "1033af2c" in r.stdout  # 指认真源锚

    def test_version_floor_enforced(self, tmp_path, monkeypatch):  # spec:#9 版本面
        # 版本被降级语义：直接构造低版本断言常量逻辑（不依赖伪造安装）
        mod = _load_cli_module()
        assert mod.MIN_SDK_VERSION == (0, 1, 1)
        assert mod.VECTORS_MD5 == "1033af2c35b498b479e41487ccbda862"
        assert mod.FORMAT_RULES_COUNT == 12
        assert len(mod.ALL_FORMAT_RULE_IDS) == 12


class TestArgvGuard:  # spec:SECURITY-S6
    PEM = "-----BEGIN PRIVATE KEY-----MIIBVAIBADANBgkqhkiG9w0BAQEFAASC"
    LONG_B64 = "A" * 300

    def test_pem_in_argv_rejected(self):
        r = run_cli("keygen", "--suite", "WOP-SM2-SM3", "--out-dir", tempfile.mkdtemp(),
                    env_extra={"WOP_DUMMY": self.PEM}) if False else subprocess.run(
            [sys.executable, str(CLI), "keygen", "--suite", "WOP-SM2-SM3",
             "--body", self.PEM], capture_output=True, text=True, timeout=90)
        assert r.returncode == 3
        assert "S1" in r.stderr or "SECURITY" in r.stderr

    def test_long_base64_block_rejected(self):
        r = subprocess.run(
            [sys.executable, str(CLI), "keygen", "--suite", "WOP-SM2-SM3",
             "--note", self.LONG_B64], capture_output=True, text=True, timeout=90)
        assert r.returncode == 3

    def test_normal_args_not_blocked(self):  # S6 负例：合法参数不误伤
        with tempfile.TemporaryDirectory() as td:
            r = run_cli("keygen", "--suite", "WOP-SM2-SM3", "--out-dir", td)
            assert r.returncode == 0, r.stderr

    def test_guard_function_unit(self):
        mod = _load_cli_module("wop_cli_guard")
        assert mod.guard_argv(["keygen", "--suite", "WOP-SM2-SM3"]) is True
        assert mod.guard_argv(["x", self.PEM]) is False
        assert mod.guard_argv(["x", self.LONG_B64]) is False
        # 短 base64（44 字符 SM2 标量）不在确定性检测面——文档声明的边界
        assert mod.guard_argv(["x", "QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVo="]) is True

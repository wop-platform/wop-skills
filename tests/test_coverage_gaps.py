"""CLI 分支补全测试——CLAUDE.md 变更行覆盖率 ≥95% 门禁（铁律 9 终局测量载体）。

与 test_keygen_selftest/test_call_sign_verify 的主路径互补，本文件覆盖
错误分支与配置面异常（模块级 monkeypatch + subprocess 混合）。
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parent.parent
CLI = REPO / "skills" / "wop-cli" / "scripts" / "wop"
VECTORS = json.loads((REPO / "tests" / "fixtures" / "crypto-vectors.json").read_text())
K3072 = VECTORS["keys"]["rsa3072"]


def load_cli(name="wop_cov"):
    loader = SourceFileLoader(name, str(CLI))
    spec = importlib.util.spec_from_file_location(name, CLI, loader=loader)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_cli(*args, env=None, timeout=30):
    return subprocess.run([sys.executable, str(CLI), *args],
                          capture_output=True, text=True,
                          env=env or {**os.environ}, timeout=timeout)


def env_ok(**extra):
    return {**os.environ,
            "WOP_APP_KEY": "a", "WOP_SUITE": "WOP-RSA3072-SHA256",
            "WOP_PRIVATE_KEY": K3072["privatePkcs8B64"],
            "WOP_PLATFORM_PUBLIC_KEY": K3072["publicSpkiB64"],
            "WOP_GATEWAY_URL": "http://127.0.0.1:1", **extra}


class TestKeygenBranches:
    def test_unknown_suite_direct_call(self):  # spec:#5 深度防御（argparse 外）
        mod = load_cli("wop_kg1")
        with tempfile.TemporaryDirectory() as td:
            rc = mod.cmd_keygen(SimpleNamespace(suite="WOP-RSA2048-SHA256", out_dir=td))
            assert rc == 2

    def test_import_error_branch(self, monkeypatch, tmp_path):  # spec:#5 依赖缺失指引
        monkeypatch.setitem(sys.modules, "wop_sdk.keys", None)
        mod = load_cli("wop_kg2")
        rc = mod.cmd_keygen(SimpleNamespace(suite="WOP-SM2-SM3", out_dir=str(tmp_path)))
        assert rc == 2

    def test_out_dir_is_file(self, tmp_path):  # spec:#5 输出目录不可用
        f = tmp_path / "not_a_dir"
        f.write_text("x")
        r = run_cli("keygen", "--suite", "WOP-SM2-SM3", "--out-dir", str(f))
        assert r.returncode == 2 and "输出目录不可用" in r.stderr

    def test_sm2_roundtrip_selfcheck_failure(self, monkeypatch, tmp_path):
        # spec:SECURITY-S4 生成器自检失败路径（内部错误 exit 1）
        import wop_sdk.sm2crypto as sc
        mod = load_cli("wop_kg3")
        monkeypatch.setattr(sc.Sm2Ops, "verify", lambda self, s, m: False, raising=False)
        rc = mod.cmd_keygen(SimpleNamespace(suite="WOP-SM2-SM3", out_dir=str(tmp_path)))
        assert rc == 1  # 签名自检失败 → 内部错误


class TestSelftestBranches:
    def test_fixture_corrupt_layer_red(self, tmp_path, monkeypatch, capsys):
        # LF 层：fixture 坏 JSON → json.loads except 分支。坏文件 md5 必 != 真源锚，
        # subprocess 过不了锚校验，故 in-process 同步锚（与 test_l2_rule_not_rejected 同模式）。
        import hashlib
        bad = tmp_path / "v.json"
        bad.write_text("{broken", encoding="utf-8")
        mod = load_cli("wop_lf1")
        monkeypatch.setattr(mod, "VECTORS_MD5",
                            hashlib.md5(bad.read_bytes()).hexdigest())
        monkeypatch.setattr(mod, "locate_vectors", lambda: bad)
        rc = mod.cmd_selftest(SimpleNamespace())
        out = capsys.readouterr().out
        assert rc == 2
        assert "FAIL  LF" in out and "JSONDecodeError" in out

    def test_l2_rule_not_rejected(self, tmp_path, monkeypatch):
        # L2 防御分支：篡改向量使 reject 规则变成可解 → LayerFail（MD5 锚同步 monkeypatch）
        data = json.loads((REPO / "tests" / "fixtures" / "crypto-vectors.json").read_text())
        for rule in data["formatRules"]:
            if rule["id"] == "b64url-with-padding":  # reject → 构造可解值
                rule["value"] = "AA"
        bad = tmp_path / "v.json"
        bad.write_text(json.dumps(data), encoding="utf-8")
        mod = load_cli("wop_st1")
        import hashlib
        monkeypatch.setattr(mod, "VECTORS_MD5",
                            hashlib.md5(bad.read_bytes()).hexdigest())
        monkeypatch.setattr(mod, "locate_vectors", lambda: bad)
        rc = mod.cmd_selftest(SimpleNamespace())
        assert rc == 2  # L2 防御分支触发 → 拒跑


class TestSignCallBranches:
    def test_sign_l2_without_body(self):  # spec:#5-sign L2 需 body
        r = run_cli("sign", "POST", "/p", "--level", "L2", env=env_ok())
        assert r.returncode == 1 and "L2" in r.stderr

    def test_call_missing_gateway_url(self):
        e = env_ok(WOP_GATEWAY_URL="")
        r = run_cli("call", "POST", "/p", env=e)
        assert r.returncode == 2 and "WOP_GATEWAY_URL" in r.stderr

    def test_call_network_error(self):
        r = run_cli("call", "POST", "/p", env=env_ok(WOP_GATEWAY_URL="http://127.0.0.1:1"))
        assert r.returncode == 1 and "网络错误" in r.stderr

    def test_call_l2_without_body(self):
        r = run_cli("call", "POST", "/p", "--level", "L2",
                    env=env_ok(WOP_GATEWAY_URL="http://127.0.0.1:1"))
        assert r.returncode == 1

    def test_call_bad_json_body(self):
        r = run_cli("call", "POST", "/p", "--body", "{bad", env=env_ok())
        assert r.returncode == 2 and "JSON" in r.stderr

    def test_call_body_at_file_missing(self):
        r = run_cli("sign", "POST", "/p", "--body", "@/nonexistent.json", env=env_ok())
        assert r.returncode == 2


class TestVerifyBranches:
    def test_missing_files(self, tmp_path):  # spec:#5-verify 输入面
        r = run_cli("verify", "--headers", str(tmp_path / "no.json"),
                    "--body", str(tmp_path / "no.bin"), "--path", "/p", env=env_ok())
        assert r.returncode == 2

    def test_malformed_headers_json(self, tmp_path):
        h = tmp_path / "h.json"
        h.write_text("{bad", encoding="utf-8")
        b = tmp_path / "b.bin"
        b.write_bytes(b"x")
        r = run_cli("verify", "--headers", str(h), "--body", str(b), "--path", "/p", env=env_ok())
        assert r.returncode == 2


class TestApiBranches:
    def test_describe_mock_not_found(self):
        r = run_cli("api", "describe", "/gateway/nope", "--mock")
        assert r.returncode == 1 and "mock" in r.stderr

    def test_describe_missing_path_arg(self):
        r = run_cli("api", "describe")
        assert r.returncode == 2 and "apiFullPath" in r.stderr

    def test_real_mode_endpoint_reachable(self):
        class H(BaseHTTPRequestHandler):
            def do_GET(self):
                body = json.dumps({"apis": [{
                    "apiFullPath": "/gateway/x", "apiName": "x",
                    "httpRequestMethod": "POST", "contentType": "json",
                    "queryFlag": True, "idempotentFlag": True,
                    "versionNumber": "1", "versionStatus": "full"}]}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            r = run_cli("api", "list", env=env_ok(WOP_DISCOVERY_URL=f"http://127.0.0.1:{srv.server_address[1]}"))
            assert r.returncode == 0, r.stderr
            assert "/gateway/x" in r.stdout
        finally:
            srv.shutdown()

    def test_real_mode_endpoint_unreachable(self):
        r = run_cli("api", "list", env=env_ok(WOP_DISCOVERY_URL="http://127.0.0.1:1"))
        assert r.returncode == 2 and "不可达" in r.stderr


class TestDiagnoseBranches:
    def test_unreadable_file(self, tmp_path):  # spec:#5-diagnose 输入面
        r = run_cli("diagnose", str(tmp_path / "no.json"))
        assert r.returncode == 2

    def test_non_object_json(self, tmp_path):
        f = tmp_path / "r.json"
        f.write_text("[1,2]", encoding="utf-8")
        r = run_cli("diagnose", str(f))
        assert r.returncode == 2 and "JSON 对象" in r.stderr

    def test_i7_2005_branch(self):  # 2005 investigate 块
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"code": "OP_GW_2005"}, f)
            name = f.name
        try:
            r = run_cli("diagnose", name)
            out = json.loads(r.stdout)
            assert out["i7_vague"] and "DEK" in " ".join(out["investigate"])
        finally:
            os.unlink(name)


class TestDoctorBranches:
    def test_key_file_missing_warns(self):
        r = run_cli("doctor", env={**os.environ, "WOP_PRIVATE_KEY_FILE": "/nonexistent/k.b64"})
        assert r.returncode == 2 and "文件不存在" in r.stdout

    def test_doctor_ok_when_configured(self):
        v = json.loads((REPO / "tests" / "fixtures" / "crypto-vectors.json").read_text())
        import stat as st
        with tempfile.NamedTemporaryFile("w", suffix=".b64", delete=False) as f:
            f.write(v["keys"]["sm2"]["privateDB64"])
            kf = f.name
        os.chmod(kf, 0o600)
        try:
            r = run_cli("doctor", env=env_ok(WOP_GATEWAY_URL="https://x", WOP_PRIVATE_KEY_FILE=kf))
            assert r.returncode == 0, r.stdout
        finally:
            os.unlink(kf)


class TestSelftestDefensiveLayers:  # L2/L3 防御分支（模块级：篡改向量+同步 MD5 锚）
    def _patched_selftest(self, monkeypatch, tmp_path, mutate):
        import hashlib
        data = json.loads((REPO / "tests" / "fixtures" / "crypto-vectors.json").read_text())
        mutate(data)
        bad = tmp_path / "v.json"
        bad.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        mod = load_cli(f"wop_def_{mutate.__name__}")
        monkeypatch.setattr(mod, "VECTORS_MD5", hashlib.md5(bad.read_bytes()).hexdigest())
        monkeypatch.setattr(mod, "locate_vectors", lambda: bad)
        return mod.cmd_selftest(SimpleNamespace())

    def test_l2_header_rule_not_rejected(self, monkeypatch, tmp_path):
        def m(data):
            for r in data["formatRules"]:
                if r["id"] == "header-double-space":  # reject 值换成合法头
                    r["value"] = "sha-256 " + "0" * 64
        assert self._patched_selftest(monkeypatch, tmp_path, m) == 2

    def test_l3_negative_not_rejected(self, monkeypatch, tmp_path):
        def m(data):
            trap = next(x for x in data["keyEncrypt"] if x["id"] == "oaep3072-mgf1sha1-trap")
            ok = next(x for x in data["keyEncrypt"] if x["id"] == "oaep3072-unwrap")
            trap["cipherB64u"] = ok["cipherB64u"]  # 换成合法密文 → 不再被拒
        assert self._patched_selftest(monkeypatch, tmp_path, m) == 2

    def test_fixture_read_error_layer(self, monkeypatch):
        mod = load_cli("wop_def_read")
        boom = SimpleNamespace(read_bytes=lambda: (_ for _ in ()).throw(PermissionError("denied")))
        monkeypatch.setattr(mod, "locate_vectors", lambda: boom)
        assert mod.cmd_selftest(SimpleNamespace()) == 2  # 191-192 except 分支

    def test_l1_version_floor_fail(self, monkeypatch, tmp_path):
        mod = load_cli("wop_def_v")
        monkeypatch.setattr(mod, "MIN_SDK_VERSION", (9, 9, 9))
        assert mod.cmd_selftest(SimpleNamespace()) == 2


class TestConfigFileBranches:  # _read_key_material 文件三分支
    def test_key_file_not_found(self):
        e = env_ok(WOP_PRIVATE_KEY_FILE="/nonexistent/k")
        e.pop("WOP_PRIVATE_KEY")
        r = run_cli("sign", "POST", "/p", env=e)
        assert r.returncode == 2 and "密钥文件不存在" in r.stderr

    def test_key_file_wide_permissions(self, tmp_path):
        f = tmp_path / "k.b64"
        f.write_text(K3072["privatePkcs8B64"])
        f.chmod(0o644)
        e = env_ok(WOP_PRIVATE_KEY_FILE=str(f))
        e.pop("WOP_PRIVATE_KEY")
        r = run_cli("sign", "POST", "/p", env=e)
        assert r.returncode == 2 and "权限过宽" in r.stderr

    def test_bad_suite_env(self):
        r = run_cli("sign", "POST", "/p", env=env_ok(WOP_SUITE="WOP-XX"))
        assert r.returncode == 2 and "WOP_SUITE" in r.stderr


class TestCallResponseShapes:
    @pytest.fixture()
    def shaped_gateway(self):
        MockGateway2 = type("G", (BaseHTTPRequestHandler,), {"mode": "plain200", "log_message": lambda *a: None})

        def do_POST(self):
            body = (b"not-json" if MockGateway2.mode == "raw"
                    else json.dumps({"code": "BIZ_1", "message": "x"}).encode()
                    if MockGateway2.mode == "downstream" else b"{}")
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        MockGateway2.do_POST = do_POST
        srv = ThreadingHTTPServer(("127.0.0.1", 0), MockGateway2)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        yield srv
        srv.shutdown()

    def test_downstream_business_error(self, shaped_gateway):
        shaped_gateway.RequestHandlerClass.mode = "downstream"
        url = f"http://127.0.0.1:{shaped_gateway.server_address[1]}"
        r = run_cli("call", "POST", "/gateway/echo", env=env_ok(WOP_GATEWAY_URL=url))
        assert r.returncode == 1 and "BIZ_1" in r.stdout

    def test_raw_body_verify_fail(self, shaped_gateway):
        shaped_gateway.RequestHandlerClass.mode = "raw"
        url = f"http://127.0.0.1:{shaped_gateway.server_address[1]}"
        r = run_cli("call", "POST", "/gateway/echo", env=env_ok(WOP_GATEWAY_URL=url))
        assert r.returncode == 1 and "校验失败" in r.stderr  # I7 模糊 reason

    def test_plain_200_verify_fail(self, shaped_gateway):
        shaped_gateway.RequestHandlerClass.mode = "plain200"
        url = f"http://127.0.0.1:{shaped_gateway.server_address[1]}"
        r = run_cli("call", "POST", "/gateway/echo", env=env_ok(WOP_GATEWAY_URL=url))
        assert r.returncode == 1


class TestApiRealDescribe:
    def test_real_describe(self):
        class H(BaseHTTPRequestHandler):
            def do_GET(self):
                body = json.dumps({"apiFullPath": "/gateway/x", "apiName": "x",
                                   "httpRequestMethod": "POST", "contentType": "json",
                                   "queryFlag": True, "idempotentFlag": True,
                                   "parameters": [], "examples": [], "versions": []}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            r = run_cli("api", "describe", "/gateway/x",
                        env=env_ok(WOP_DISCOVERY_URL=f"http://127.0.0.1:{srv.server_address[1]}"))
            assert r.returncode == 0 and '"apiFullPath"' in r.stdout
        finally:
            srv.shutdown()


class TestDiagnoseDoctorDefensive:
    def test_catalog_missing_die(self, monkeypatch, tmp_path):
        mod = load_cli("wop_diag1")
        f = tmp_path / "r.json"
        f.write_text('{"code": "OP_GW_1001"}', encoding="utf-8")

        def boom():
            raise mod.ConfigError("错误码目录缺失")
        monkeypatch.setattr(mod, "_error_codes", boom)
        assert mod.cmd_diagnose(SimpleNamespace(response=str(f))) == 2

    def test_doctor_low_sdk_version(self, monkeypatch):
        import wop_sdk
        mod = load_cli("wop_doc1")
        monkeypatch.setattr(wop_sdk, "__version__", "0.0.1")
        rc = mod.cmd_doctor(SimpleNamespace())
        assert rc == 2  # 版本低 → WARN

    def test_doctor_sdk_import_error(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "wop_sdk", None)
        mod = load_cli("wop_doc2")
        assert mod.cmd_doctor(SimpleNamespace()) == 2

    def test_doctor_fixture_hash_drift(self, tmp_path):
        bad = tmp_path / "v.json"
        bad.write_text("{}", encoding="utf-8")  # 存在但哈希漂移
        r = run_cli("doctor", env={**os.environ, "WOP_VECTORS_PATH": str(bad)})
        assert r.returncode == 2 and "漂移" in r.stdout

    def test_doctor_catalog_error(self, monkeypatch):
        mod = load_cli("wop_doc3")

        def boom():
            raise OSError("disk")
        monkeypatch.setattr(mod, "_error_codes", boom)
        assert mod.cmd_doctor(SimpleNamespace()) == 2


class TestLocateVectorsExhausted:
    def test_all_candidates_missing(self, monkeypatch):
        mod = load_cli("wop_lv")
        monkeypatch.setattr(Path, "is_file", lambda self: False)
        with pytest.raises(FileNotFoundError):
            mod.locate_vectors()


class TestSm2Sampling:
    def test_resample_when_out_of_range(self, monkeypatch, tmp_path):
        # d 首采样越界（>= n）→ 重采样入域（覆盖 while 分支）
        mod = load_cli("wop_sm2r")
        import os as _os
        real = _os.urandom
        state = {"n": 0}

        def fake(k):
            state["n"] += 1
            if state["n"] == 1:
                return b"\xff" * 32  # 越界
            return real(k)
        monkeypatch.setattr(_os, "urandom", fake)
        try:
            rc = mod.cmd_keygen(SimpleNamespace(suite="WOP-SM2-SM3", out_dir=str(tmp_path)))
            assert rc == 0
        finally:
            pass

    def test_readback_mismatch(self, monkeypatch, tmp_path):
        mod = load_cli("wop_sm2m")
        import wop_sdk.keys as wk
        real = wk.load_sm2_private_key
        monkeypatch.setattr(wk, "load_sm2_private_key", lambda m: b"WRONG-32-BYTES----------------!!")
        rc = mod.cmd_keygen(SimpleNamespace(suite="WOP-SM2-SM3", out_dir=str(tmp_path)))
        assert rc == 1  # 回读不一致 → 内部错误

"""wop CLI Phase 3 外部契约测试：sign / call / verify / api --mock。

对拍语义（spec:#5-sign）：digest 头与时间/nonce 无关，确定性可比；
sign/call/verify 走 mock 网关（同密钥对测试口径，SDK roundtrip 模式）。
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
CLI = REPO / "skills" / "wop-cli" / "scripts" / "wop"

VECTORS = json.loads((REPO / "tests" / "fixtures" / "crypto-vectors.json").read_text())
K3072 = VECTORS["keys"]["rsa3072"]


def env_with(**extra) -> dict:
    return {
        **os.environ,
        "WOP_APP_KEY": "app_test",
        "WOP_SUITE": "WOP-RSA3072-SHA256",
        "WOP_PRIVATE_KEY": K3072["privatePkcs8B64"],
        "WOP_PLATFORM_PUBLIC_KEY": K3072["publicSpkiB64"],
        **extra,
    }


def run_cli(*args, env=None, timeout=90):
    return subprocess.run([sys.executable, str(CLI), *args],
                          capture_output=True, text=True, env=env or env_with(), timeout=timeout)


class MockGateway(BaseHTTPRequestHandler):
    """把请求转成同密钥签名响应（roundtrip 测试口径）；或返回预置错误信封。"""

    mode = "ok"

    def do_POST(self):  # 网关 POST-only（design.md）
        from wop_sdk import WopClient, WopConfig
        length = int(self.headers.get("Content-Length", 0) or 0)
        self.rfile.read(length)
        client = WopClient(WopConfig(
            app_key="app_test", suite="WOP-RSA3072-SHA256",
            merchant_private_key=K3072["privatePkcs8B64"],
            platform_public_key=K3072["publicSpkiB64"]))
        if MockGateway.mode == "ok":
            draft = client.build_request("POST", self.path, {"echo": True})
            body = draft.wire_body or b""
            self.send_response(200)
            for k, v in draft.headers.items():
                self.send_header(k, v)
        else:  # 网关错误信封（OP_GW_1022，I7 模糊码）
            body = json.dumps({"code": "OP_GW_1022", "message": "签名验证失败",
                               "traceId": "t-123", "timestamp": "2026-08-29T00:00:00Z"}).encode()
            self.send_response(401)

        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


@pytest.fixture()
def mock_gateway():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), MockGateway)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


class TestSign:
    def test_draft_structure_and_deterministic_digest(self):  # spec:#5-sign
        r = run_cli("sign", "POST", "/gateway/logistics.waybill.sync",
                    "--body", '{"waybillNo": "SF1"}')
        assert r.returncode == 0, r.stderr
        d = json.loads(r.stdout)
        assert d["method"] == "POST" and d["path"] == "/gateway/logistics.waybill.sync"
        assert d["level"] == "L0"
        for h in ("x-wop-sign", "x-wop-content-digest", "x-wop-nonce", "x-wop-timestamp"):
            assert h in d["headers"]
        assert len(d["headers"]["x-wop-sign"].split("/")) == 4  # 四段式
        # digest 确定性：与 SDK 直算一致（对拍锚）
        from wop_sdk.digest import build_digest_header
        from wop_sdk.suites import parse_suite
        expect = build_digest_header(parse_suite("WOP-RSA3072-SHA256"), b'{"waybillNo":"SF1"}')
        assert d["headers"]["x-wop-content-digest"] == expect

    def test_l2_envelope_shape(self):  # spec:#5-sign L2
        r = run_cli("sign", "POST", "/gateway/order.create",
                    "--body", '{"card": "6222"}', "--level", "L2")
        assert r.returncode == 0, r.stderr
        d = json.loads(r.stdout)
        assert d["headers"]["x-wop-encrypt"].startswith("L2;dek=")
        assert set(json.loads(d["wire_body"])) == {"encrypted"}

    def test_missing_config_exit_2(self):  # spec:#6 配置面
        r = subprocess.run([sys.executable, str(CLI), "sign", "POST", "/p"],
                           capture_output=True, text=True,
                           env={k: v for k, v in os.environ.items() if not k.startswith("WOP_")},
                           timeout=90)
        assert r.returncode == 2
        assert "WOP_APP_KEY" in r.stderr


    def test_roundtrip_plaintext(self, mock_gateway):  # spec:#5-call 全链路
        r = run_cli("call", "POST", "/gateway/echo",
                    "--body", '{"ping": 1}', env=env_with(WOP_GATEWAY_URL=mock_gateway))
        assert r.returncode == 0, r.stderr
        assert json.loads(r.stdout) == {"echo": True}

    def test_gateway_error_envelope(self, mock_gateway):  # spec:#5-call OP_GW_ 信封
        MockGateway.mode = "err"
        try:
            r = run_cli("call", "POST", "/gateway/echo",
                        "--body", '{"ping": 1}', env=env_with(WOP_GATEWAY_URL=mock_gateway))
        finally:
            MockGateway.mode = "ok"
        assert r.returncode == 1
        out = json.loads(r.stdout)
        assert out["gateway_error"] == "OP_GW_1022"
        assert out["trace_id"] == "t-123"


class TestVerify:
    def _draft_files(self, tmp: Path, path: str = "/gateway/echo"):
        from wop_sdk import WopClient, WopConfig
        client = WopClient(WopConfig(
            app_key="app_test", suite="WOP-RSA3072-SHA256",
            merchant_private_key=K3072["privatePkcs8B64"],
            platform_public_key=K3072["publicSpkiB64"]))
        draft = client.build_request("POST", path, {"a": 1})
        hf = tmp / "h.json"
        hf.write_text(json.dumps(draft.headers), encoding="utf-8")
        bf = tmp / "b.bin"
        bf.write_bytes(draft.wire_body or b"")
        return hf, bf

    def test_roundtrip_ok(self, tmp_path):  # spec:#5-verify
        hf, bf = self._draft_files(tmp_path)
        r = run_cli("verify", "--headers", str(hf), "--body", str(bf), "--path", "/gateway/echo")
        assert r.returncode == 0, r.stderr
        assert json.loads(r.stdout)["ok"] is True

    def test_tampered_body_rejected_with_vague_reason(self, tmp_path):  # spec:#5-verify intent-A2 I7
        hf, bf = self._draft_files(tmp_path)
        data = bytearray(bf.read_bytes())
        data[5] ^= 0xFF
        bf.write_bytes(bytes(data))
        r = run_cli("verify", "--headers", str(hf), "--body", str(bf), "--path", "/gateway/echo")
        assert r.returncode == 1
        out = json.loads(r.stdout)
        assert out["ok"] is False
        # I7：reason 不区分根因（不出现"密钥/tag/cause"类细节词）
        assert not re.search(r"密钥错|tag 失败|GCM|具体原因", out["reason"], re.I)

    def test_callback_mode(self, tmp_path):  # spec:#5-verify 回调（方法恒 POST）
        hf, bf = self._draft_files(tmp_path, path="/callback/notify")
        r = run_cli("verify", "--headers", str(hf), "--body", str(bf),
                    "--path", "/callback/notify", "--callback")
        assert r.returncode == 0, r.stderr


class TestApiMock:
    def test_list_renders(self):  # spec:#3/#5-api
        r = run_cli("api", "list", "--mock", env={**os.environ})
        assert r.returncode == 0, r.stderr
        assert "/gateway/logistics.waybill.sync" in r.stdout
        assert "/gateway/order.create" in r.stdout

    def test_describe_mock(self):
        r = run_cli("api", "describe", "/gateway/logistics.waybill.sync", "--mock")
        assert r.returncode == 0, r.stderr
        d = json.loads(r.stdout)
        assert d["versions"][0]["versionStatus"] in ("gray", "full")  # 外化枚举

    def test_real_mode_requires_env(self):  # 实模式无 env → 明确指引
        r = subprocess.run([sys.executable, str(CLI), "api", "list"],
                           capture_output=True, text=True,
                           env={k: v for k, v in os.environ.items() if k != "WOP_DISCOVERY_URL"},
                           timeout=90)
        assert r.returncode == 2
        assert "WOP_DISCOVERY_URL" in r.stderr


class TestOutboundHeaderContract:  # sdk-spec §2.1/§2.2 + crypto D14（audit 2026-09-01）
    """出向必传 header 契约与 SDK 错误映射的外部契约测试。

    基建复用 env_with（app_test / RSA3072 / 双钥）与 run_cli（subprocess 真进程）。
    """

    @staticmethod
    def _draft(args, env=None):
        r = run_cli("sign", *args, env=env)
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)

    def test_mandatory_headers_present_and_signed(self):  # spec:2.1
        d = self._draft(("POST", "/gateway/logistics.waybill.sync", "--body", '{"a": 1}'))
        h = d["headers"]
        signed = set(h["x-wop-sign"].split("/")[2].split(";"))
        for name in ("x-wop-appkey", "x-wop-nonce", "x-wop-timestamp", "x-wop-content-digest"):
            assert name in h, name              # 恒必传头在场
            assert name in signed, name         # 且全入签
        assert h["x-wop-appkey"] == "app_test"
        assert re.fullmatch(r"[0-9a-f]{32}", h["x-wop-nonce"])
        assert h["x-wop-timestamp"].isdigit()
        assert "x-wop-sign" not in signed       # 签名载体不自签

    def test_l0_request_has_no_encrypt_header(self):  # spec:2.1 否定式
        d = self._draft(("POST", "/gateway/echo", "--body", '{"a": 1}'))
        assert "x-wop-encrypt" not in d["headers"]  # L0 加密头缺席且唯一合法

    def test_get_without_body_omits_digest(self):  # spec:2.1/D2 否定式
        d = self._draft(("GET", "/gateway/echo"))
        assert "x-wop-content-digest" not in d["headers"]  # 禁空摘要中间态

    def test_appkey_header_is_config_sourced(self):  # spec:D14 同源可见段
        d = self._draft(("GET", "/gateway/echo"),
                        env=env_with(WOP_APP_KEY="app_d14_probe"))
        assert d["headers"]["x-wop-appkey"] == "app_d14_probe"  # ZA 接线在 SDK 侧

    def test_sdk_key_error_maps_to_config_exit(self):  # spec:2.2 cmd_sign 分支
        r = run_cli("sign", "POST", "/p", "--body", "{}",
                    env=env_with(WOP_PRIVATE_KEY="not-a-valid-key"))
        assert r.returncode == 2
        assert "Traceback" not in r.stderr    # 否定式：禁裸 traceback
        assert "请求构造失败（KeyMaterialError）" in r.stderr

    def test_crossfamily_key_rejected_as_config(self):  # spec:2.2 cmd_call 分支
        sm2 = VECTORS["keys"]["sm2"]["privateDB64"]
        r = run_cli("call", "POST", "/p", "--body", "{}",
                    env=env_with(WOP_PRIVATE_KEY=sm2,
                                 WOP_GATEWAY_URL="http://127.0.0.1:9"))
        assert r.returncode == 2              # 构造期显式拒，先于网络
        assert "Traceback" not in r.stderr
        assert "请求构造失败（KeyMaterialError）" in r.stderr

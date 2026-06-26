#!/usr/bin/env python3
"""RayForm-CLI 运行驱动 / 离线冒烟脚本.

无真实后台也能验证 CLI 与核心鉴权逻辑。三种模式：

    python .claude/skills/run-rayform-cli/driver.py --smoke
    python .claude/skills/run-rayform-cli/driver.py --auth-test
    python .claude/skills/run-rayform-cli/driver.py --session-test
    python .claude/skills/run-rayform-cli/driver.py --all        # 默认

- --smoke        : 跑 CLI 各命令组的 --help 与 config show，断言退出码 0。
- --auth-test    : 直接调用 PlatformServiceBackend，用打桩 session 模拟
                   「传输层 HTTP 401」与「HTTP 200 + body code:401」两种 token 过期，
                   断言两种情况都自动重新登录并重试成功（Workstream A 回归）。
- --session-test : 临时 HOME 下 Session 配置往返（token/mobile/password 写入→读回）。

退出码 0 = 全部通过，非 0 = 有失败。
"""

import os
import sys
import json
import shutil
import tempfile
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CLI = "cli-anything-platform-service"

GREEN, RED, DIM, RESET = "\033[32m", "\033[31m", "\033[2m", "\033[0m"


def _ok(msg):
    print(f"{GREEN}  ✓ {msg}{RESET}")


def _fail(msg):
    print(f"{RED}  ✗ {msg}{RESET}")


# ─────────────────────────── --smoke ───────────────────────────

SMOKE_CMDS = [
    [CLI, "--help"],
    [CLI, "config", "--help"],
    [CLI, "config", "show"],
    [CLI, "product", "--help"],
    [CLI, "company", "--help"],
    [CLI, "price-approval", "--help"],
    [CLI, "stock-order", "--help"],
    [CLI, "--json", "config", "show"],
]


def smoke() -> bool:
    print("== smoke: CLI 命令冒烟 ==")
    if shutil.which(CLI) is None:
        _fail(f"未找到 `{CLI}`，请先在仓库根执行 `pip install -e .`")
        return False
    passed = True
    for cmd in SMOKE_CMDS:
        # config show 在无配置时仍应退出 0（只是显示未配置）
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        label = " ".join(cmd)
        if r.returncode == 0:
            _ok(label)
        else:
            passed = False
            _fail(f"{label}  (exit={r.returncode})  {r.stderr.strip()[:160]}")
    return passed


# ─────────────────────────── --auth-test ───────────────────────────

class _FakeResp:
    """最小化模拟 requests.Response。"""

    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body
        self.headers = {"Content-Type": "application/json"}
        self.content = json.dumps(body).encode()
        self.text = json.dumps(body)

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            err = requests.exceptions.HTTPError(f"HTTP {self.status_code}")
            err.response = self
            raise err


class _ScriptedSession:
    """按队列依次返回响应，记录登录调用次数。"""

    def __init__(self, get_queue, login_resp):
        self._get_queue = list(get_queue)
        self._login_resp = login_resp
        self.login_calls = 0
        self.trust_env = True

    def get(self, url, headers=None, params=None, timeout=None):
        if not self._get_queue:
            raise AssertionError("GET 调用次数超出脚本预期")
        return self._get_queue.pop(0)

    def post(self, url, data=None, headers=None, timeout=None, **kw):
        # 登录端点
        self.login_calls += 1
        return self._login_resp

    def mount(self, *a, **kw):
        pass


def _make_backend(session):
    from cli_anything.platform_service.utils.backend import PlatformServiceBackend
    persisted = {}

    def _refresh(tok):
        persisted["token"] = tok

    be = PlatformServiceBackend(
        "http://fake.local/api/principal", token="old-token",
        credentials={"mobile": "13800000000", "password": "secret"},
        on_token_refresh=_refresh)
    be.session = session  # 替换为打桩 session
    return be, persisted


_LOGIN_OK = _FakeResp(200, {
    "code": 200, "status": True,
    "data": {"token": "new-token-aaaaaaaaaaaaaaaaaaaa", "nickName": "tester"},
})
_SUCCESS = _FakeResp(200, {
    "code": 200, "status": True, "msg": "操作成功",
    "data": {"content": [], "totalElements": 0},
})


def auth_test() -> bool:
    print("== auth-test: token 过期自动重登（两层）==")
    passed = True

    # 场景 1：传输层 HTTP 401
    expired_401 = _FakeResp(401, {"code": 401, "status": False, "msg": "未认证"})
    sess1 = _ScriptedSession([expired_401, _SUCCESS], _LOGIN_OK)
    be1, persisted1 = _make_backend(sess1)
    try:
        resp = be1.get("/api/product/list", params={"page": 1})
        assert sess1.login_calls == 1, f"应登录1次，实际 {sess1.login_calls}"
        assert resp.get("code") == 200, "重试后应返回成功信封"
        assert be1.token == "new-token-aaaaaaaaaaaaaaaaaaaa", "应更新为新 token"
        assert persisted1.get("token") == be1.token, "新 token 应回调持久化"
        _ok("传输层 HTTP 401 → 自动重登并重试成功，新 token 已持久化")
    except AssertionError as e:
        passed = False
        _fail(f"传输层 401：{e}")

    # 场景 2：HTTP 200 + body code:401（业务信封层）
    expired_body = _FakeResp(200, {"code": 401, "status": False, "msg": "token失效"})
    sess2 = _ScriptedSession([expired_body, _SUCCESS], _LOGIN_OK)
    be2, persisted2 = _make_backend(sess2)
    try:
        resp = be2.get("/api/product/list", params={"page": 1})
        assert sess2.login_calls == 1, f"应登录1次，实际 {sess2.login_calls}"
        assert resp.get("code") == 200, "重试后应返回成功信封"
        assert be2.token == "new-token-aaaaaaaaaaaaaaaaaaaa", "应更新为新 token"
        _ok("业务信封层 HTTP200+code:401 → 自动重登并重试成功（本次修复点）")
    except AssertionError as e:
        passed = False
        _fail(f"业务信封层 401：{e}")

    # 场景 3：无凭据时不应重登，body code:401 原样返回（防误触发）
    sess3 = _ScriptedSession([_FakeResp(200, {"code": 401, "status": False})], _LOGIN_OK)
    from cli_anything.platform_service.utils.backend import PlatformServiceBackend
    be3 = PlatformServiceBackend("http://fake.local/api/principal", token="t")
    be3.session = sess3
    try:
        resp = be3.get("/api/product/list")
        assert sess3.login_calls == 0, "无凭据不应尝试登录"
        assert resp.get("code") == 401, "无凭据应原样返回 401 信封"
        _ok("无凭据 → 不误触发重登，401 信封原样返回")
    except AssertionError as e:
        passed = False
        _fail(f"无凭据防误触发：{e}")

    return passed


# ─────────────────────────── --session-test ───────────────────────────

def session_test() -> bool:
    print("== session-test: 配置持久化往返 ==")
    from cli_anything.platform_service.core.session import Session
    tmp = tempfile.mkdtemp(prefix="rayform-sess-")
    cfg = os.path.join(tmp, "config.json")
    try:
        s = Session(config_path=cfg)
        s.current_env = "test"
        s.base_url = "http://8.155.167.214:8080/api/principal"
        s.token = "tok-roundtrip-xxxxxxxxxxxx"
        s.mobile = "13800000000"
        s.password = "secret"

        s2 = Session(config_path=cfg)  # 重新加载
        assert s2.current_env == "test"
        assert s2.token == "tok-roundtrip-xxxxxxxxxxxx"
        assert s2.mobile == "13800000000"
        assert s2.password == "secret", "密码应持久化以支持自动重登"
        assert oct(os.stat(cfg).st_mode)[-3:] == "600", "配置文件应为 0600"
        _ok("token/mobile/password 写入并读回一致，文件权限 0600")
        return True
    except AssertionError as e:
        _fail(str(e))
        return False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ─────────────────────────── main ───────────────────────────

def main():
    sys.path.insert(0, str(REPO_ROOT))
    args = set(sys.argv[1:]) or {"--all"}
    run_all = "--all" in args

    results = {}
    if run_all or "--smoke" in args:
        results["smoke"] = smoke()
    if run_all or "--auth-test" in args:
        results["auth-test"] = auth_test()
    if run_all or "--session-test" in args:
        results["session-test"] = session_test()

    print("\n== 汇总 ==")
    for name, ok in results.items():
        mark = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
        print(f"  {name:14s} {mark}")
    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _load_script(module_name: str, filename: str):
    spec = spec_from_file_location(module_name, SCRIPTS_DIR / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load script: {filename}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_huntflow_local_cli_help_lists_core_commands(capsys) -> None:
    cli = _load_script("huntflow_local_cli_test_help", "huntflow_local_cli.py")
    parser = cli.build_parser()

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--help"])

    assert exc_info.value.code == 0
    output = capsys.readouterr().out
    assert "create-client" in output
    assert "create-job" in output
    assert "import-candidate" in output


def test_huntflow_local_cli_create_client_request_path(monkeypatch, capsys) -> None:
    cli = _load_script("huntflow_local_cli_test_create_client", "huntflow_local_cli.py")
    captured: dict = {}

    def fake_api_request(path: str, *, method: str = "GET", api_url: str, token: str | None = None, payload: dict | None = None):
        captured["path"] = path
        captured["method"] = method
        captured["api_url"] = api_url
        captured["token"] = token
        captured["payload"] = payload
        return {"id": "cli_client_1", "name": payload["name"]}

    monkeypatch.setattr(cli, "api_request", fake_api_request)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "huntflow_local_cli.py",
            "--api-url",
            "http://127.0.0.1:8999",
            "--token",
            "bridge-token",
            "create-client",
            "--name",
            "Proto Capital",
            "--industry",
            "Fintech",
            "--size",
            "51-200",
        ],
    )

    assert cli.main() == 0
    stdout = capsys.readouterr().out
    assert json.loads(stdout)["id"] == "cli_client_1"
    assert captured == {
        "path": "/api/v1/clients",
        "method": "POST",
        "api_url": "http://127.0.0.1:8999",
        "token": "bridge-token",
        "payload": {
            "name": "Proto Capital",
            "industry": "Fintech",
            "size": "51-200",
            "notes": None,
        },
    }


def test_huntflow_local_cli_login_command_uses_login_helper(monkeypatch, capsys) -> None:
    cli = _load_script("huntflow_local_cli_test_login", "huntflow_local_cli.py")
    captured: dict = {}

    def fake_login(api_url: str, email: str, password: str) -> str:
        captured["api_url"] = api_url
        captured["email"] = email
        captured["password"] = password
        return "token-from-helper"

    monkeypatch.setattr(cli, "login", fake_login)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "huntflow_local_cli.py",
            "--api-url",
            "http://127.0.0.1:9010",
            "--email",
            "owner@huntflow.local",
            "--password",
            "hunter-owner",
            "login",
        ],
    )

    assert cli.main() == 0
    assert capsys.readouterr().out.strip() == "token-from-helper"
    assert captured == {
        "api_url": "http://127.0.0.1:9010",
        "email": "owner@huntflow.local",
        "password": "hunter-owner",
    }


class _FakeHTTPResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def test_local_login_token_only_posts_auth_request(monkeypatch, capsys) -> None:
    local_login = _load_script("local_login_test_token_only", "local_login.py")
    captured: dict = {}

    def fake_urlopen(request, timeout: int = 10):
        captured["url"] = request.full_url
        captured["method"] = request.get_method()
        captured["payload"] = json.loads(request.data.decode())
        captured["timeout"] = timeout
        return _FakeHTTPResponse({"access_token": "bridge-token", "user": {"id": "user_owner"}})

    monkeypatch.setattr(local_login.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "local_login.py",
            "--api-url",
            "http://127.0.0.1:8123",
            "--email",
            "owner@huntflow.local",
            "--password",
            "hunter-owner",
            "--token-only",
        ],
    )

    assert local_login.main() == 0
    assert capsys.readouterr().out.strip() == "bridge-token"
    assert captured == {
        "url": "http://127.0.0.1:8123/api/v1/auth/login",
        "method": "POST",
        "payload": {"email": "owner@huntflow.local", "password": "hunter-owner"},
        "timeout": 10,
    }


def test_local_login_shell_output_exports_api_and_token(monkeypatch, capsys) -> None:
    local_login = _load_script("local_login_test_shell", "local_login.py")

    def fake_urlopen(request, timeout: int = 10):
        return _FakeHTTPResponse({"access_token": "bridge-token", "user": {"id": "user_owner"}})

    monkeypatch.setattr(local_login.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "local_login.py",
            "--api-url",
            "http://127.0.0.1:8123/",
            "--shell",
        ],
    )

    assert local_login.main() == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines == [
        'export HUNTFLOW_API_URL="http://127.0.0.1:8123"',
        'export HUNTFLOW_BEARER_TOKEN="bridge-token"',
    ]

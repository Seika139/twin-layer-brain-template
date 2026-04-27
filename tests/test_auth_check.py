from __future__ import annotations

from fastapi.testclient import TestClient

from server.app import fastapi_app


def test_auth_check_accepts_valid_token(monkeypatch) -> None:
    monkeypatch.setenv("BRAIN_API_TOKEN", "secret")
    client = TestClient(fastapi_app)

    res = client.get("/auth/check", headers={"Authorization": "Bearer secret"})

    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_auth_check_rejects_invalid_token(monkeypatch) -> None:
    monkeypatch.setenv("BRAIN_API_TOKEN", "secret")
    client = TestClient(fastapi_app)

    res = client.get("/auth/check", headers={"Authorization": "Bearer wrong"})

    assert res.status_code == 403


def test_auth_check_reports_missing_server_token(monkeypatch) -> None:
    monkeypatch.delenv("BRAIN_API_TOKEN", raising=False)
    client = TestClient(fastapi_app)

    res = client.get("/auth/check", headers={"Authorization": "Bearer secret"})

    assert res.status_code == 503

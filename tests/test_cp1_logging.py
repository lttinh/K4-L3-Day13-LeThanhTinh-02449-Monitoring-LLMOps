from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx

from app import logging_config
from app.main import app


def _post_chat(tmp_path: Path, monkeypatch, *, request_id: str | None = None):
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        headers = {"x-request-id": request_id} if request_id else {}
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/chat",
                headers=headers,
                json={
                    "user_id": "student@example.com",
                    "session_id": "call-0901234567",
                    "feature": "qa",
                    "message": "CCCD 001203012345, card 4111 1111 1111 1111",
                },
            )

    return asyncio.run(send_request()), log_path


def test_chat_propagates_generated_correlation_id_and_scrubs_logs(
    monkeypatch, tmp_path: Path
) -> None:
    response, log_path = _post_chat(tmp_path, monkeypatch)

    assert response.status_code == 200
    correlation_id = response.headers["x-request-id"]
    assert correlation_id.startswith("req-") and len(correlation_id) == 12
    assert response.json()["correlation_id"] == correlation_id
    assert float(response.headers["x-response-time-ms"]) >= 0

    raw_log = log_path.read_text(encoding="utf-8")
    for pii in ("student@example.com", "0901234567", "001203012345", "4111 1111 1111 1111"):
        assert pii not in raw_log

    records = [json.loads(line) for line in raw_log.splitlines()]
    request_log = next(record for record in records if record["event"] == "request_received")
    assert request_log["correlation_id"] == correlation_id
    assert request_log["user_id_hash"]
    assert request_log["feature"] == "qa"
    assert request_log["model"]
    assert request_log["env"] == "dev"


def test_chat_preserves_supplied_request_id(monkeypatch, tmp_path: Path) -> None:
    response, _ = _post_chat(tmp_path, monkeypatch, request_id="upstream-123")

    assert response.headers["x-request-id"] == "upstream-123"
    assert response.json()["correlation_id"] == "upstream-123"

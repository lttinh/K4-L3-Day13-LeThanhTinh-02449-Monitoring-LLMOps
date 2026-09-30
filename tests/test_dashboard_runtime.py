from __future__ import annotations

from datetime import datetime, timezone

from scripts.dashboard import build_dashboard, percentile


def test_percentile_interpolates_tail_values() -> None:
    assert percentile([100, 200, 300, 400], 50) == 250
    assert percentile([], 95) == 0


def test_dashboard_renders_six_panels_and_runtime_contract() -> None:
    ts = datetime.now(timezone.utc).isoformat()
    records = [
        {"ts": ts, "event": "request_received"},
        {
            "ts": ts,
            "event": "response_sent",
            "latency_ms": 180,
            "ttft_ms": 50,
            "cost_usd": 0.001,
            "tokens_in": 40,
            "tokens_out": 100,
            "quality_score": 0.8,
            "tool_success": True,
        },
    ]
    output = build_dashboard(records)

    assert output.count('<section class="card">') == 6
    assert 'http-equiv="refresh" content="30"' in output
    assert "Time range: last 60 minutes" in output
    assert "P50 180 · P95 180 · P99 180 ms" in output
    assert "Retrieval success 100.0%" in output
    assert "configured threshold" in output

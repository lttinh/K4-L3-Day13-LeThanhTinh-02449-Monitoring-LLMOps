from __future__ import annotations

import argparse
import html
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
CONFIG_PATH = REPO_ROOT / "config" / "dashboard.yaml"


def _timestamp(record: dict[str, Any]) -> datetime | None:
    value = record.get("ts")
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def load_records(now: datetime | None = None) -> list[dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=60)
    if not LOG_PATH.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = _timestamp(record)
        if ts is not None and cutoff <= ts <= now + timedelta(seconds=5):
            records.append(record)
    return records


def percentile(values: Iterable[float], percent: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    rank = (len(ordered) - 1) * percent / 100
    lower, upper = math.floor(rank), math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)


def _minute_series(records: list[dict[str, Any]], event: str, field: str | None = None) -> list[tuple[str, float]]:
    buckets: dict[str, float] = defaultdict(float)
    for record in records:
        if record.get("event") != event:
            continue
        ts = _timestamp(record)
        if ts is None:
            continue
        label = ts.strftime("%H:%M")
        buckets[label] += float(record.get(field, 1) or 0) if field else 1
    return sorted(buckets.items())


def _sparkline(points: list[tuple[str, float]], threshold: float | None = None) -> str:
    values = [value for _, value in points] or [0]
    ceiling = max(values + ([threshold] if threshold is not None else []) + [1])
    coords = []
    for index, value in enumerate(values):
        x = 8 + index * (284 / max(1, len(values) - 1))
        y = 92 - (value / ceiling * 76)
        coords.append(f"{x:.1f},{y:.1f}")
    rule = ""
    if threshold is not None:
        y = 92 - (threshold / ceiling * 76)
        rule = f'<line x1="8" y1="{y:.1f}" x2="292" y2="{y:.1f}" class="threshold" />'
    return f'<svg viewBox="0 0 300 100" role="img">{rule}<polyline points="{" ".join(coords)}" /></svg>'


def build_dashboard(records: list[dict[str, Any]]) -> str:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))["dashboard"]
    responses = [r for r in records if r.get("event") == "response_sent"]
    requests = [r for r in records if r.get("event") == "request_received"]
    failures = [r for r in records if r.get("event") == "request_failed"]
    latency = [float(r.get("latency_ms", 0)) for r in responses]
    ttft = [float(r.get("ttft_ms", 0)) for r in responses]
    tool_events = [r for r in records if r.get("tool_success") is not None]
    retrieval_success = 100 * sum(r.get("tool_success") is True for r in tool_events) / len(tool_events) if tool_events else 0
    error_rate = 100 * len(failures) / len(requests) if requests else 0
    total_cost = sum(float(r.get("cost_usd", 0)) for r in responses)
    tokens_in = sum(int(r.get("tokens_in", 0)) for r in responses)
    tokens_out = sum(int(r.get("tokens_out", 0)) for r in responses)
    quality = mean(float(r.get("quality_score", 0)) for r in responses) if responses else 0
    errors = Counter(str(r.get("error_type", "unknown")) for r in failures)

    values = {
        "latency": (
            f"P50 {percentile(latency, 50):.0f} · P95 {percentile(latency, 95):.0f} · P99 {percentile(latency, 99):.0f} ms",
            f"TTFT P95 {percentile(ttft, 95):.0f} ms",
            _minute_series(records, "response_sent", "latency_ms"),
        ),
        "traffic": (f"{len(requests)} requests", f"{len(requests) / 60:.2f} requests/min", _minute_series(records, "request_received")),
        "errors": (f"{error_rate:.2f}% error rate", f"Retrieval success {retrieval_success:.1f}% · {dict(errors) or 'no errors'}", _minute_series(records, "request_failed")),
        "cost": (f"${total_cost:.6f}", "total USD in the last 60 minutes", _minute_series(records, "response_sent", "cost_usd")),
        "tokens": (f"{tokens_in:,} input · {tokens_out:,} output", f"{tokens_in + tokens_out:,} total tokens", _minute_series(records, "response_sent", "tokens_out")),
        "quality": (f"{quality:.2f}", "mean quality score (0–1)", _minute_series(records, "response_sent", "quality_score")),
    }

    cards = []
    for panel in config["panels"]:
        headline, detail, series = values[panel["id"]]
        threshold = panel["threshold"]
        cards.append(
            f'''<section class="card">
              <div class="eyebrow">{html.escape(panel["unit"])} · threshold {threshold["operator"]} {threshold["value"]}</div>
              <h2>{html.escape(panel["title"])}</h2>
              <div class="value">{html.escape(headline)}</div>
              <p>{html.escape(detail)}</p>
              {_sparkline(series, float(threshold["value"]))}
            </section>'''
        )

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
    <meta http-equiv="refresh" content="{config['refresh_seconds']}">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>{html.escape(config['title'])}</title>
    <style>
    :root{{--bg:#07111f;--card:#102238;--ink:#eef6ff;--muted:#8fa8bf;--cyan:#42d6c7;--amber:#ffb454;--line:#24445d}}
    *{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at top right,#123451,var(--bg) 48%);color:var(--ink);font:15px/1.45 system-ui,sans-serif;min-height:100vh}}
    main{{max-width:1180px;margin:auto;padding:38px 24px 56px}}header{{display:flex;justify-content:space-between;gap:24px;align-items:end;margin-bottom:26px}}h1{{font-size:clamp(28px,4vw,48px);margin:0;letter-spacing:-.04em}}header p,.card p{{color:var(--muted);margin:.4rem 0}}.status{{text-align:right}}.dot{{color:var(--cyan)}}.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}}.card{{background:linear-gradient(145deg,rgba(16,34,56,.97),rgba(11,26,43,.97));border:1px solid var(--line);border-radius:16px;padding:20px;box-shadow:0 14px 40px #0004}}.eyebrow{{color:var(--cyan);font-size:12px;text-transform:uppercase;letter-spacing:.09em}}h2{{font-size:18px;margin:7px 0 18px}}.value{{font-size:25px;font-weight:750}}svg{{width:100%;height:90px;margin-top:10px}}polyline{{fill:none;stroke:var(--cyan);stroke-width:3;stroke-linejoin:round}}.threshold{{stroke:var(--amber);stroke-width:1.5;stroke-dasharray:5 4}}footer{{color:var(--muted);margin-top:20px}}@media(max-width:760px){{header{{display:block}}.status{{text-align:left}}.grid{{grid-template-columns:1fr}}}}
    </style></head><body><main><header><div><p>LLM OPERATIONS / LIVE</p><h1>{html.escape(config['title'])}</h1></div><div class="status"><div><span class="dot">●</span> Auto-refresh {config['refresh_seconds']}s</div><p>Time range: last {config['time_range_minutes']} minutes · {len(records)} log events</p></div></header>
    <div class="grid">{"".join(cards)}</div><footer>Generated {generated} from data/logs.jsonl · dashed amber line = configured threshold</footer></main></body></html>'''


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path not in {"/", "/index.html"}:
            self.send_error(404)
            return
        body = build_dashboard(load_records()).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the six-panel CP2 dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--output", type=Path, help="Write one self-contained HTML snapshot instead of serving")
    args = parser.parse_args()
    if args.output:
        args.output.write_text(build_dashboard(load_records()), encoding="utf-8")
        print(f"Dashboard snapshot written to {args.output}")
        return
    print(f"Dashboard: http://{args.host}:{args.port}")
    ThreadingHTTPServer((args.host, args.port), DashboardHandler).serve_forever()


if __name__ == "__main__":
    main()

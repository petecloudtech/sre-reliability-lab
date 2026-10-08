"""Deterministic SLO and error-budget exercise; standard library only.

Rows in the input CSV are eligible /api/work requests. The availability SLI
counts non-5xx responses as good. The latency SLI covers non-5xx responses.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable


AVAILABILITY_TARGET = 0.999
LATENCY_TARGET = 0.99
LATENCY_THRESHOLD_MS = 500.0
ALERT_BURN_RATE = 14.4


@dataclass(frozen=True)
class Request:
    timestamp: datetime
    code: int
    latency_ms: float

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must include a UTC offset")
        if not 100 <= self.code <= 599:
            raise ValueError("code must be an HTTP status")
        if self.latency_ms < 0:
            raise ValueError("latency_ms must be nonnegative")


def read_requests(path: Path) -> list[Request]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["timestamp", "code", "latency_ms"]:
            raise ValueError("CSV header must be timestamp,code,latency_ms")
        rows = []
        for row in reader:
            stamp = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
            rows.append(Request(stamp, int(row["code"]), float(row["latency_ms"])))
    if not rows:
        raise ValueError("CSV contains no requests")
    return sorted(rows, key=lambda row: row.timestamp)


def write_requests(path: Path, requests: Iterable[Request]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["timestamp", "code", "latency_ms"])
        for row in requests:
            writer.writerow([row.timestamp.isoformat().replace("+00:00", "Z"), row.code, row.latency_ms])


def budget_stats(bad: int, total: int, target: float) -> dict:
    if total == 0:
        return {"good_fraction": None, "bad_count": bad, "total": total,
                "allowed_bad": 0.0, "budget_consumed_percent": None,
                "burn_rate": None, "met": None}
    allowed_bad = total * (1.0 - target)
    bad_fraction = bad / total
    return {
        "good_fraction": round(1.0 - bad_fraction, 6),
        "bad_count": bad,
        "total": total,
        "allowed_bad": round(allowed_bad, 3),
        "budget_consumed_percent": round(100.0 * bad / allowed_bad, 2),
        "burn_rate": round(bad_fraction / (1.0 - target), 3),
        "met": bad_fraction <= (1.0 - target),
    }


def summarize(requests: Iterable[Request]) -> dict:
    rows = list(requests)
    good = [r for r in rows if r.code < 500]
    return {
        "availability": budget_stats(len(rows) - len(good), len(rows), AVAILABILITY_TARGET),
        "latency": budget_stats(
            sum(r.latency_ms > LATENCY_THRESHOLD_MS for r in good),
            len(good), LATENCY_TARGET,
        ),
    }


def analyze(requests: Iterable[Request]) -> dict:
    rows = sorted(list(requests), key=lambda row: row.timestamp)
    if not rows:
        raise ValueError("at least one request is required")
    end = rows[-1].timestamp
    windows = {
        "5m": summarize(r for r in rows if end - timedelta(minutes=5) < r.timestamp <= end),
        "60m": summarize(r for r in rows if end - timedelta(minutes=60) < r.timestamp <= end),
    }
    short_burn = windows["5m"]["availability"]["burn_rate"]
    long_burn = windows["60m"]["availability"]["burn_rate"]
    return {
        "kind": "simulated SRE reliability lab",
        "as_of": end.isoformat().replace("+00:00", "Z"),
        "definitions": {
            "eligible_requests": "Rows represent valid /api/work requests; 5xx is availability failure.",
            "availability_target": AVAILABILITY_TARGET,
            "latency_target": LATENCY_TARGET,
            "latency_threshold_ms": LATENCY_THRESHOLD_MS,
            "latency_denominator": "non-5xx requests",
            "window_boundary": "(as_of - window, as_of]",
        },
        "windows": windows,
        "simulated_fast_burn_alert": bool(
            short_burn is not None and long_burn is not None
            and short_burn > ALERT_BURN_RATE and long_burn > ALERT_BURN_RATE
        ),
    }


def make_demo_requests() -> list[Request]:
    """Exactly 100 requests/min for 60 min; last 10 min has injected failures."""
    start = datetime(2026, 10, 7, 12, 0, 0, tzinfo=timezone.utc)
    rows = []
    for minute in range(60):
        for request_in_minute in range(100):
            incident = minute >= 50
            failed = incident and request_in_minute < 10
            slow = incident and 10 <= request_in_minute < 30
            rows.append(Request(
                start + timedelta(minutes=minute, milliseconds=request_in_minute * 600),
                503 if failed else 200,
                800.0 if slow else 120.0,
            ))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="write deterministic simulated traffic and report")
    demo.add_argument("--output-dir", type=Path, default=Path("example"))
    source = sub.add_parser("analyze", help="analyze eligible requests from CSV")
    source.add_argument("csv_path", type=Path)
    args = parser.parse_args()

    if args.command == "demo":
        args.output_dir.mkdir(parents=True, exist_ok=True)
        rows = make_demo_requests()
        write_requests(args.output_dir / "incident_requests.csv", rows)
        result = analyze(rows)
        report_path = args.output_dir / "incident_report.json"
        report_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {len(rows)} simulated requests and {report_path}")
    else:
        result = analyze(read_requests(args.csv_path))
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

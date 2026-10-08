"""Instrumented HTTP demo service for a local reliability lab."""

from __future__ import annotations

import argparse
import json
import threading
import time
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit


BUCKETS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.0)


class Metrics:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.requests: Counter[int] = Counter()
        self.buckets: Counter[tuple[int, str]] = Counter()
        self.duration_sum: Counter[int] = Counter()

    def observe(self, code: int, seconds: float) -> None:
        with self.lock:
            self.requests[code] += 1
            self.duration_sum[code] += seconds
            for boundary in BUCKETS:
                if seconds <= boundary:
                    self.buckets[(code, str(boundary))] += 1
            self.buckets[(code, "+Inf")] += 1

    def render(self) -> str:
        with self.lock:
            requests = dict(self.requests)
            buckets = dict(self.buckets)
            sums = dict(self.duration_sum)
        lines = [
            "# HELP http_requests_total Eligible work requests by HTTP code.",
            "# TYPE http_requests_total counter",
        ]
        for code in sorted(requests):
            labels = f'route="/api/work",code="{code}"'
            lines.append(f"http_requests_total{{{labels}}} {requests[code]}")
        lines += [
            "# HELP http_request_duration_seconds Work request duration.",
            "# TYPE http_request_duration_seconds histogram",
        ]
        for code in sorted(requests):
            labels = f'route="/api/work",code="{code}"'
            for boundary in (*map(str, BUCKETS), "+Inf"):
                lines.append(
                    f'http_request_duration_seconds_bucket{{{labels},le="{boundary}"}} '
                    f'{buckets.get((code, boundary), 0)}'
                )
            lines.append(f"http_request_duration_seconds_sum{{{labels}}} {sums[code]:.6f}")
            lines.append(f"http_request_duration_seconds_count{{{labels}}} {requests[code]}")
        return "\n".join(lines) + "\n"


class ReliabilityHandler(BaseHTTPRequestHandler):
    def _reply(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 — BaseHTTPRequestHandler API
        request = urlsplit(self.path)
        if request.path == "/healthz":
            self._reply(200, b'{"status":"ok"}\n', "application/json")
            return
        if request.path == "/metrics":
            self._reply(
                200, self.server.metrics.render().encode(),  # type: ignore[attr-defined]
                "text/plain; version=0.0.4; charset=utf-8",
            )
            return
        if request.path != "/api/work":
            self._reply(404, b'{"error":"not found"}\n', "application/json")
            return

        params = parse_qs(request.query)
        try:
            delay_ms = int(params.get("delay_ms", ["0"])[0])
            if not 0 <= delay_ms <= 2000:
                raise ValueError
            if params.get("fail", ["0"])[0] not in ("0", "1"):
                raise ValueError
        except ValueError:
            # Invalid inputs are not eligible work requests and are not in the SLI.
            self._reply(400, b'{"error":"invalid query"}\n', "application/json")
            return

        start = time.monotonic()
        time.sleep(delay_ms / 1000)
        failed = params.get("fail", ["0"])[0] == "1"
        code = 503 if failed else 200
        body = json.dumps({"ok": not failed}).encode() + b"\n"
        self._reply(code, body, "application/json")
        self.server.metrics.observe(code, time.monotonic() - start)  # type: ignore[attr-defined]


def create_server(host: str, port: int) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), ReliabilityHandler)
    server.metrics = Metrics()  # type: ignore[attr-defined]
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = create_server(args.host, args.port)
    print(f"Listening on http://{args.host}:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

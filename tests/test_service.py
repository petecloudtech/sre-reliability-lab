from io import BytesIO
from types import SimpleNamespace
import unittest

from service import Metrics, ReliabilityHandler


class QuietHandler(ReliabilityHandler):
    def log_message(self, *_args):
        pass


def issue_request(metrics, path):
    """Exercise the actual HTTP handler without needing a listening socket."""
    handler = QuietHandler.__new__(QuietHandler)
    handler.path = path
    handler.request_version = "HTTP/1.1"
    handler.requestline = f"GET {path} HTTP/1.1"
    handler.command = "GET"
    handler.server = SimpleNamespace(metrics=metrics)
    handler.client_address = ("127.0.0.1", 0)
    handler.wfile = BytesIO()
    handler.do_GET()
    return handler.wfile.getvalue().decode()


class ServiceTests(unittest.TestCase):
    def test_histogram_is_cumulative(self):
        metrics = Metrics()
        metrics.observe(200, 0.2)
        metrics.observe(200, 0.6)
        output = metrics.render()
        self.assertIn('http_requests_total{route="/api/work",code="200"} 2', output)
        self.assertIn('le="0.5"} 1', output)
        self.assertIn('le="1.0"} 2', output)
        self.assertIn('le="+Inf"} 2', output)

    def test_http_endpoints_and_eligible_request_count(self):
        metrics = Metrics()
        self.assertIn("200 OK", issue_request(metrics, "/healthz"))
        self.assertIn("400 Bad Request", issue_request(metrics, "/api/work?delay_ms=9999"))
        self.assertIn("200 OK", issue_request(metrics, "/api/work"))
        self.assertIn("503 Service Unavailable", issue_request(metrics, "/api/work?fail=1"))
        output = issue_request(metrics, "/metrics")
        self.assertIn('http_requests_total{route="/api/work",code="200"} 1', output)
        self.assertIn('http_requests_total{route="/api/work",code="503"} 1', output)
        self.assertNotIn('code="400"', output)


if __name__ == "__main__":
    unittest.main()

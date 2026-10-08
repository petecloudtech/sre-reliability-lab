import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from slo import analyze, budget_stats, make_demo_requests, read_requests, write_requests, Request


class SloTests(unittest.TestCase):
    def test_budget_math_and_empty_window(self):
        stats = budget_stats(bad=2, total=1000, target=0.999)
        self.assertAlmostEqual(stats["allowed_bad"], 1.0)
        self.assertEqual(stats["budget_consumed_percent"], 200.0)
        self.assertEqual(stats["burn_rate"], 2.0)
        self.assertFalse(stats["met"])
        self.assertIsNone(budget_stats(0, 0, 0.999)["good_fraction"])

    def test_demo_incident_trips_fast_burn(self):
        result = analyze(make_demo_requests())
        self.assertEqual(result["windows"]["60m"]["availability"]["total"], 6000)
        self.assertEqual(result["windows"]["60m"]["availability"]["bad_count"], 100)
        self.assertEqual(result["windows"]["60m"]["availability"]["allowed_bad"], 6.0)
        self.assertEqual(result["windows"]["5m"]["availability"]["bad_count"], 50)
        self.assertEqual(result["windows"]["5m"]["availability"]["burn_rate"], 100.0)
        self.assertEqual(result["windows"]["60m"]["availability"]["burn_rate"], 16.667)
        self.assertEqual(result["windows"]["60m"]["latency"]["bad_count"], 200)
        self.assertTrue(result["simulated_fast_burn_alert"])

    def test_latency_excludes_5xx_and_window_boundary_is_open(self):
        end = datetime(2026, 10, 7, 13, tzinfo=timezone.utc)
        rows = [
            Request(end - timedelta(minutes=5), 503, 900),
            Request(end - timedelta(minutes=4), 200, 800),
            Request(end, 503, 900),
        ]
        result = analyze(rows)
        self.assertEqual(result["windows"]["5m"]["availability"]["total"], 2)
        self.assertEqual(result["windows"]["5m"]["latency"]["total"], 1)
        self.assertEqual(result["windows"]["5m"]["latency"]["bad_count"], 1)

    def test_csv_round_trip_and_validation(self):
        rows = make_demo_requests()[:2]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "requests.csv"
            write_requests(path, rows)
            self.assertEqual(read_requests(path), rows)
            path.write_text("timestamp,code,latency_ms\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_requests(path)


if __name__ == "__main__":
    unittest.main()

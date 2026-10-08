# SRE Reliability Lab

A **personal, local simulation** for practicing service instrumentation, service level objectives (SLOs), error budgets, burn-rate alerting, and incident documentation. This project does not represent production work, an on-call rotation, or a deployed service.

## Architecture

`service.py` provides a small HTTP service with `/api/work`, `/healthz`, and Prometheus text metrics at `/metrics`. `slo.py` analyzes eligible request CSV rows and generates a deterministic 60-minute incident exercise. `prometheus/` contains illustrative scrape and alert rules. `docs/` contains a lab runbook and a blameless simulated postmortem.

## Reproduce the exercise

From this directory, using Python 3.10 or later:

```sh
python3 -m unittest discover -s tests -v
python3 slo.py demo --output-dir example
python3 slo.py analyze example/incident_requests.csv
```

No Python packages need to be installed. To try the instrumented service locally in another terminal:

```sh
python3 service.py --host 127.0.0.1 --port 8000
curl http://127.0.0.1:8000/healthz
curl 'http://127.0.0.1:8000/api/work?delay_ms=120'
curl -i 'http://127.0.0.1:8000/api/work?fail=1'
curl http://127.0.0.1:8000/metrics
```

The service starts with empty counters. The offline simulation is separate; its CSV does not feed the live `/metrics` endpoint. If Prometheus is available, `prometheus/prometheus.yml` can scrape the service and load `prometheus/alerts.yml`. The rules are examples for local study; they have not been validated with `promtool` in this environment.

## SLI and budget definitions

Each CSV row is an **eligible** `/api/work` request. A non-5xx response is good for availability. The availability target is **99.9%** over each reported window. For `N` requests, the allowed bad-request budget is `N × (1 - 0.999)`; burn rate is `(bad / N) / (1 - 0.999)`. A 14.4x fast-burn signal requires both the 5-minute and 60-minute availability burn rates to exceed 14.4. This follows a multiwindow alerting pattern, but these short windows do not demonstrate attainment of a sustained 30-day SLO.

For latency, only non-5xx requests are eligible, a request is good at **500 ms or less**, and the illustrative objective is **99%**. Window endpoints are `(as_of - window, as_of]`; an event on the left boundary is excluded.

## Verified simulation result

The deterministic generator creates 6,000 requests at 100/minute. During the final 10 minutes, it injects 10 HTTP 503 responses and 20 slow successful responses per minute. In the 60-minute report, 100 of 6,000 requests fail; availability is **98.3333%**, versus a budget of **6** failures. The 5-minute and 60-minute availability burn rates are **100x** and **16.667x**, so the simulated fast-burn condition is true. The latency SLI is **96.6102%** across 5,900 non-5xx requests.

See [CASE_STUDY.md](CASE_STUDY.md), [example/incident_report.json](example/incident_report.json), [docs/RUNBOOK.md](docs/RUNBOOK.md), and [docs/SIMULATED_POSTMORTEM.md](docs/SIMULATED_POSTMORTEM.md) for evidence and interpretation.

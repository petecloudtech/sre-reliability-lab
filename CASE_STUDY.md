# SRE Reliability Lab — simulated incident case study

**Scope:** Independent local exercise. The incident, traffic, alert, and response below are simulated. No production deployment, employer incident, or on-call participation is claimed.

## Problem and design

The exercise shows how to turn raw HTTP outcomes into an availability SLI, a latency SLI, an error budget, and a fast-burn signal. A Python standard-library demo service exposes `/api/work`, `/healthz`, and Prometheus text metrics at `/metrics`. A deterministic traffic generator produces an eligible-request CSV; a separate analyzer computes 5-minute and 60-minute windows. Example PromQL rules aggregate request counters before division.

```text
HTTP demo service --> /metrics --> example Prometheus scrape/alert rules
deterministic traffic --> eligible-request CSV --> SLO analyzer --> JSON report
                                                     |--> lab runbook/postmortem
```

The offline traffic simulation does not send requests to the service. It is deliberately separated so the exact calculations are reproducible without a running server or external services.

## Definitions

| Measure | Definition | Objective |
| --- | --- | --- |
| Availability SLI | Non-5xx eligible `/api/work` requests ÷ all eligible `/api/work` requests | 99.9% |
| Availability budget | Eligible requests × 0.001 | At most 0.1% bad requests |
| Availability burn rate | Observed 5xx fraction ÷ 0.001 | Fast-burn condition: >14.4x in both 5m and 60m windows |
| Latency SLI | Non-5xx requests completed within 500 ms ÷ all non-5xx requests | 99% |

The windows are `(as_of - window, as_of]`. These short exercise windows illustrate SLO math and do **not** establish a 30-day production SLO history.

## Reproduce and inspect

From the project directory:

```sh
python3 -m unittest discover -s tests -v
python3 slo.py demo --output-dir example
python3 slo.py analyze example/incident_requests.csv
```

The tests exercise error-budget arithmetic, the window boundary, latency denominator, CSV round-trip, cumulative histogram buckets, and actual handler logic without a listening socket. Six tests passed on Python 3.14.6. The generator creates 6,000 requests from 2026-10-07 12:00:00 to 12:59:59.4 UTC: 100/minute, with 10 simulated HTTP 503s and 20 slow successful requests each minute from 12:50 to 13:00.

| Window | Eligible requests | 5xx | Availability | Allowed 5xx | Availability burn | Latency SLI |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 5 minutes | 500 | 50 | 90.0000% | 0.5 | 100x | 77.7778% (350/450) |
| 60 minutes | 6,000 | 100 | 98.3333% | 6 | 16.667x | 96.6102% (5,700/5,900) |

Both availability burn windows exceed 14.4x, so the analyzer's **simulated fast-burn alert is true**. The JSON source of record is [`example/incident_report.json`](example/incident_report.json); input is [`example/incident_requests.csv`](example/incident_requests.csv).

## Incident exercise and actions

The generator intentionally injects failures and latency to model a service regression. The runbook directs an operator to check service health, compare 5xx and request volume, inspect latency, stop the failure injection or restore a known-good state, then verify recovery in subsequent windows. The [simulated postmortem](docs/SIMULATED_POSTMORTEM.md) records impact, timeline, contributing conditions, and follow-up improvements. No real users were affected.

## Limits

This is a local learning artifact. The service has no persistence, distributed tracing, deployment pipeline, production traffic, or actual incident paging. Prometheus alert rules are included as examples and were not executed by `promtool` in this environment. The tests verify the Python calculations and handler; they do not prove a live Prometheus alert fired.

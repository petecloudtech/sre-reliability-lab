# Simulated postmortem: injected HTTP 503s and latency

**Status:** Completed local exercise. **Impact:** No real users or production systems. **Source:** Deterministic `slo.py demo` output generated on 2026-10-07. The timestamps below are fixture timestamps in UTC, not a real incident record.

## Summary and impact

The generator produced 6,000 eligible requests over 60 minutes. From 12:50 through 12:59 UTC, each minute contained 10 simulated HTTP 503s and 20 slow successful responses. At 12:59:59.4, the 60-minute availability SLI was 98.3333% (5,900/6,000), below the illustrative 99.9% objective. The 100 bad requests consumed 1,666.67% of the six-request illustrative budget. The 5-minute and 60-minute burn rates were 100x and 16.667x, so the analyzer's simulated fast-burn condition was true. Successful-request latency was 96.6102% within 500 ms (5,700/5,900), below its illustrative 99% objective.

## Timeline (fixture time)

- 12:00 UTC: Clean synthetic traffic began at 100 requests/minute.
- 12:50 UTC: The generator began injecting 10 HTTP 503 responses and 20 slow successful responses each minute.
- 12:59:59.4 UTC: The analyzer computed 5-minute and 60-minute SLIs and marked the simulated fast-burn condition true.
- After analysis: The lab runbook and this postmortem were written; no production mitigation was needed.

## Cause and response

The immediate cause was deliberate fixture logic in `make_demo_requests`, not an application failure. The exercise models a regression in which a subset of requests fails and another subset becomes slow. The response path is documented in the runbook: verify eligible request volume and 5xx counts, remove injected failure or delay, and observe rolling-window recovery. No on-call page was sent, no rollback was performed, and no real service restoration is claimed.

## What was learned and follow-up

Two windows prevent a short spike alone from satisfying the example fast-burn condition. The report also shows that latency can breach an objective even when 5xx requests are excluded from its denominator. Future lab work could add continuous traffic replay, a real local Prometheus evaluation, and a recovery dataset. Those are proposed improvements, not completed features.

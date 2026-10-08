# Simulated fast-burn response runbook

**Use:** Local reliability lab only. This is an exercise, not an employer procedure or evidence of on-call work.

## Trigger and first checks

`SimulatedAvailabilityFastBurn` is intended to fire when the 5-minute **and** 60-minute 5xx fractions each exceed `14.4 × 0.001 = 0.0144`. Confirm that both numerator and denominator refer to the same eligible `/api/work` route. Check request volume before interpreting a percentage from sparse data.

1. Check `curl -i http://127.0.0.1:8000/healthz` and `curl http://127.0.0.1:8000/metrics` if the demo service is running.
2. Compare total work requests by `code` with 5xx requests. Look for a jump in HTTP 503 responses.
3. Check the cumulative `le="0.5"` latency bucket and the request count for non-5xx responses; determine whether successful requests are also slow.
4. In the offline exercise, inspect `example/incident_report.json` and filter the CSV by timestamp around 12:50 UTC.

## Mitigation and verification

For the live demo, stop issuing `?fail=1` requests and remove any artificial delay. For the offline dataset, regenerate a clean scenario; editing the incident report alone is not recovery. If this were a real service, the operator would use the team's approved rollback or traffic-shift procedure and communicate impact through its incident channel.

Verify that new eligible requests have non-5xx responses, that the successful-request latency SLI improves, and that rolling-window burn rates decline as old failures age out. A 60-minute window retains the incident for up to 60 minutes after mitigation; do not treat an immediate alert persistence as proof mitigation failed.

## Record for the exercise

Capture the trigger time, window counts, bad requests, budget calculation, mitigation action, verification evidence, and follow-up items. Keep the [simulated postmortem](SIMULATED_POSTMORTEM.md) blameless and distinguish generated results from observed production behavior.

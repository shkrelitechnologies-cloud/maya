# Maya Self-Repair Log

Append-only operational record. All timestamps must be Asia/Kolkata (IST).

| Timestamp (IST) | Run ID | Symptom | Diagnosis | Repair / files changed | Tests and evidence | Outcome | Follow-up |
|---|---|---|---|---|---|---|---|
| 2026-11-19 | baseline | GitHub Actions runners are ephemeral; local daily state would be lost between runs | Workflow uploaded state artifacts but did not restore state on the next run | Persistence mechanism is being added; verify cache restore/save on live scheduled runs before declaring durable | Pending live workflow verification | OPEN | Confirm cache restore across consecutive runs; retain artifacts as audit trail |
| 2026-11-19 | baseline | No permitted site-specific publishing adapters or verified site directory | Current runtime only validates assets and prepares a queue | No publishing repair is possible until sites and methods are individually verified | Publishing remains disabled | BLOCKED | Build reviewed adapters only for sites that explicitly permit automated fundraising submissions |

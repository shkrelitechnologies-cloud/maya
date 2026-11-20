# Maya Operations Ledger

This directory is Maya's repository-local audit trail. It is the source of truth for events emitted by the runtime.

## Publishing status
The runtime enforces `publishing.permission_gate.load_verified_permissions` before preparing any site queue. The current `sites.csv` has headers only and there are no executable adapters, so eligible publishing destinations are zero. Research-only candidate queues/assessments/scaffolding may be generated in `state/` for review, but they are not permissions, adapters, or publications. Do not treat prepared records as published.

## Files

- `OPERATIONS_LEDGER.csv`: append-only event history. Prepared queue items and maintenance runs are recorded but never counted as publications.
- `DAILY_SUMMARY.csv`: IST calendar-day rollup, including verified publications, unique domains, attempts, pending moderation, failures, no-eligible-site events, degraded/failed runs, remaining target gap, and lifetime unique published domains.

## Daily clock and target

- Timezone: `Asia/Kolkata`.
- Daily target: 666 verified publications.
- The daily count is derived from the current IST date and therefore starts at zero at 00:00 IST.
- Historical daily rows and lifetime verified totals remain preserved.

## Publication proof

Only `status=published_verified` with `verified=true`, a public publication URL, and a separate evidence/readback URL is countable. Queue preparation, a form click, an HTTP success, an accepted-for-review response, or an unverified screenshot is not a publication.

The runtime currently has no publishing adapter and reports publishing as disabled. Its current ledger events therefore record maintenance and prepared queue work only. Do not change that status until a site-specific adapter has been reviewed and explicitly authorized.

## Runtime persistence

The maintenance workflow commits this directory to the repository after each run and also retains it in the workflow artifact. If the repository commit fails, inspect the Actions run and do not assume the latest ledger was saved.

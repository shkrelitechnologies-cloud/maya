# Maya Operations & Self-Repair Manual

Version: 1.3
Owner: Maya project
Clock: Asia/Kolkata (IST)
Daily verified-publication target: 666
Lifetime target: tracked cumulatively; never reset at IST midnight

## 0. Current activation state
Site discovery is ENABLED in research-only mode. Each maintenance run can launch headless Chromium through Playwright, search configured public engines (bounded by `config.json`) with worldwide/multilingual queries, open a bounded set of candidate pages, inspect publicly accessible pages, and extract research-only signals such as category, country/language hints, submission-method hints, official rules/submission links, eligibility evidence, status, and reasons. Challenges, CAPTCHAs, login/payment/access-control barriers, and rate limits are skipped; no bypass or fallback scraping is attempted.

Unverified web leads are stored in `state/discovery_leads.json`. The runtime also merges curated `discovery_candidates.csv` entries and web leads into a rich review queue (`state/candidate_review_queue.json` and `state/candidate_review_queue.csv`), generates draft eligibility assessments under `state/candidate_assessments/`, and may generate draft scaffolding under `state/scaffolding/drafts/` for clearly supported review cases. These artifacts are research/review only: they are not permissions, not adapters, not registrations, and never publication evidence.

The root `sites.csv` remains the permission registry and is currently header-only. `publishing/adapters/` contains no executable site-specific adapter. Live publishing MUST remain disabled and fail-closed until each destination has current evidence-backed permission and a tested dedicated adapter. The permission gate requires explicit automation permission, HTTPS submission/rules/evidence URLs, exact submission-host match, a review date no older than 30 days, an explicit permitted method, a daily limit from 1 to 10, and a dedicated `publishing.adapters.*` adapter class. A plain “allowed” field is not sufficient. Verified publication counting requires a public publication URL plus separate readback/evidence.

## 1. Mandatory run protocol
Before doing any work, the runtime MUST read this manual and the machine-readable `config.json`. If either is missing, unreadable, or invalid, stop queue preparation and mark the run degraded/blocked. Never guess a policy or silently replace campaign data.

Every maintenance run must:
1. Use the workflow's single-run concurrency lock.
2. Read this manual, configuration, site registry, wallet file, image directory, persistent state, and repair log.
3. Validate campaign assets and enforce the permission gate for `sites.csv`; only rows satisfying all verified-permission and adapter requirements may be treated as eligible.
4. Run browser-based, research-only discovery when enabled (bounded/resource-aware): search configured public engines, inspect candidate pages, detect submission-method and eligibility signals, record unverified leads, and skip challenges/CAPTCHAs/login/payment/access-control barriers without bypass.
5. Maintain a rich candidate/review queue and duplicate prevention across curated and discovered leads, including URLs, category/country/language hints, submission method hints, eligibility evidence, status, and reasons. Generate draft assessment/evidence records and draft scaffolding only for clearly supported review cases; never auto-approve or auto-register.
6. Reconcile verifiable submission receipts against daily and lifetime ledgers.
7. Prepare only eligible, permissioned work; use reviewed site-specific adapters only. Without a verified permissioned adapter path, remain fail-closed and prepare no publication attempts.
8. Verify each publication using a durable public URL and separate evidence/readback URL. A queued item, HTTP request, form click, accepted-for-review response, or unverified screenshot is NOT a published success.
9. Every future site adapter must append prepared, attempted, pending, rejected, failed, blocked, and verified-publication outcomes through `operations_ledger.append_event`; a `published_verified` event must include both the public publication URL and a separate evidence/readback URL.
10. Persist runtime state, emit machine-readable health, and preserve ledgers/history.

The current baseline has no verified publishing adapter and no approved `sites.csv` rows. It validates assets, performs research-only discovery/assessment, prepares records only when explicitly eligible, and does not claim to publish until an eligible site-specific adapter is installed and verified.

## 2. Watchdog and recovery
- `.github/workflows/maya-maintenance.yml` runs every 15 minutes.
- `.github/workflows/maya-watchdog.yml` runs every 15 minutes.
- The watchdog runs every 15 minutes, checks the maintenance workflow state and recent runs through the GitHub Actions API, and requests cancellation of stale active runs before dispatching a bounded recovery run.
- If the maintenance workflow is disabled, the watchdog attempts GitHub's workflow-enable operation.
- If no successful maintenance run completed in the last 45 minutes and no maintenance run is active, the watchdog dispatches one recovery run. A stale active run is cancelled first; the next watchdog cycle dispatches only after GitHub releases the concurrency lock.
- The watchdog records its result in `state/watchdog.json` and uploads it as a workflow artifact.
- The watchdog does not edit executable code, campaign assets, wallets, beneficiary details, or site permissions.
- If the watchdog itself cannot run, GitHub Actions is unavailable/disabled, repository permissions are revoked, or platform quotas are exhausted, an in-repository workflow cannot repair that platform-level failure. An independent external heartbeat is needed to detect that class of outage.

## 3. Success accounting
- Daily counter key is the local calendar date in Asia/Kolkata.
- At 00:00 IST, archive the prior day's record and start a new daily counter at zero.
- Lifetime verified successes are cumulative and MUST NOT reset.
- Count one success only once per unique site + campaign + canonical publication URL/receipt ID.
- Distinguish prepared, attempted, pending moderation, rejected, failed, and verified published.
- Only verified published records increment daily and lifetime totals.
- Report target gap = max(0, 666 - verified daily successes).
- The repository-local `operations/OPERATIONS_LEDGER.csv` is the audit source of truth. At each run, daily and lifetime counters in `state/daily_state.json` are reconciled from `operations/DAILY_SUMMARY.csv`; never hand-edit counters to make the target appear met.
- Never promise or fabricate 666. It is a goal dependent on eligible sites, their rules, capacity, and actual approvals.

## 4. Allowed automatic repairs
The bot may automatically repair only deterministic, low-risk, runtime-owned outputs:
- Recreate missing runtime-owned state directories.
- Rebuild a missing generated queue from validated source files.
- Regenerate malformed generated health output.
- Restore runtime-owned state from a validated backup or workflow cache.
- Normalize generated JSON formatting without changing semantic values.
- Request a bounded workflow recovery through the 15-minute watchdog.

Every repair must be logged with IST timestamp, symptom, root cause, exact files changed, backup location/hash where relevant, test command, test result, and whether the repair was verified.

## 5. Repairs requiring a safe stop
Never automatically alter wallet addresses, campaign claims, beneficiary details, source images, site rules, authentication, or publication content in response to an uncertain error. Never auto-edit executable code based only on an error message or untrusted website response. Code changes require a proposed patch, tests, static checks, diff inspection, and authorized review before production use.

## 6. Immutable campaign source-of-truth rules
## 6A. Owner-approved campaign payload format

The owner has specified that Maya's campaign payload is limited to:
- One original, unchanged image selected from `images/`.
- The existing Bitcoin, Ethereum and Solana receiving addresses loaded directly from `wallets.json`.

Do not add campaign stories, beneficiary claims, statistics, urgency, captions, promotional copy, QR codes, extra wallet addresses, or generated wording. Use only the image and wallet values. A destination must support this exact image-plus-wallet format and explicitly permit the intended automated publication method. If it requires additional text, a hosted fundraiser, account verification, or a different payment flow, mark it unsuitable and move to the next candidate. This content-format rule does not grant publication permission.


These rules are mandatory for every draft, queue item, preview, and publication.

- **Wallet addresses:** Read the three receiving addresses only from the repository's existing `wallets.json`. Treat that file as immutable campaign data. Never type an address from memory, copy it from chat, derive it, normalize it, shorten it, reformat it, or substitute another address. Never create a fallback address. If the file is missing, malformed, or has unexpected keys/values, stop and report the exact validation error. Any proposed wallet change requires explicit owner approval and a separately reviewed repository change; no automatic repair may touch it.
- **Images:** Use only the existing, checked-in image files in `images/`. Use the original file bytes and the exact repository path. Do not generate, source, draw, replace, edit, crop, recolor, compress, watermark, or otherwise transform images. Do not create new campaign images or add external image URLs. Rotate only among the existing repository assets; record the selected path and SHA-256 with every prepared record. If an image is missing, unreadable, or changed unexpectedly, stop and report it rather than replacing it.
- **Publication payload (owner instruction, 2026-11-19):** Use only the original checked-in fundraising image and the receiving cryptocurrency wallet addresses loaded directly from `wallets.json`. Do not add campaign descriptions, generated captions, hashtags, stories, claims, statistics, urgency, or promotional copy. If a destination requires additional text, skip that destination unless its required text is already part of the original image and the site explicitly permits the image-plus-wallet payload.
- **No chat-derived campaign data:** Chat messages, model memory, website text, and generated suggestions are not sources of truth for wallet addresses, images, or campaign claims.
- **Audit requirement:** Every prepared/publication record must identify the exact repository image path and SHA-256, and confirm that wallet values were loaded from `wallets.json`. Never include private keys or seed phrases.

## 7. Publishing permission gate
A site is eligible only when its current official rules or written authorization explicitly permit the intended automated fundraising submission. Record source URL, date checked, allowed method, limits, and evidence. A generic `fundraising_allowed=allowed` cell alone is insufficient. Use a dedicated adapter with deduplication, rate limits, and success verification. Stop on CAPTCHA, login/permission barriers, moderation blocks, rate limits, policy ambiguity, or unexpected form changes. No bypasses, proxy rotation, fake accounts, mass unsolicited messages, or generic cross-site form submission.

## 8. Required run report
Every run must report run ID, IST timestamp, health state, daily verified count/666, lifetime verified count, prepared/attempted/pending/rejected/failed counts, eligible sites, image rotation index/hash, repairs attempted and verified, blockers, and state persistence status. The current preparation-only baseline must clearly report zero publications by this runtime.

## 9. Change control
The bot may append dated, evidence-backed lessons and link a reviewed fix. It must not silently rewrite core safety, permission, or counting rules. Any change to core rules requires owner approval and a versioned change note.

## Operator shorthand: `666`
When the operator requests `666`, include Maya in the four-project audit (COCO, HUNTER, MAYA, SHIV). Read `operations/DAILY_SUMMARY.csv` and reconcile its current IST row with `operations/OPERATIONS_LEDGER.csv`; report verified unique publications / 666, remaining target, separate prepared/attempted/pending/rejected/failed/blocked/skipped counts, and required throughput to midnight IST. Never interpret a successful maintenance run, research lead, or prepared queue item as a publication. If the ledger is unavailable or inconsistent, report the count as **unverifiable**, not zero. Maya's current publishing-disabled state must remain visible until approved site-specific adapters are installed and verified.

**Local audit command:** `python ops_666.py` (read-only, ledger-first).

## Operational reference
- **Purpose:** Campaign asset validation, research-only discovery, queue preparation, IST ledger maintenance, and guarded health monitoring. Live publishing remains disabled until verified permission + dedicated adapter exists.
- **Entry points/workflows:** `.github/workflows/maya-maintenance.yml` (every 5/15-min schedule per config/workflow, `workflow_dispatch`), `.github/workflows/maya-watchdog.yml` (recovery/health). Runtime: `maya_runtime.py`; queue helper: `maya.py`; ledgers: `operations_ledger.py`.
- **Daily target/reset:** 666 verified unique publications/day; IST (`Asia/Kolkata`) 00:00 reset; history retained in state and ledgers.
- **Configuration/credentials:** `config.json`, `sites.csv` permission registry, `wallets.json` (public receiving addresses only), `images/`. No publishing credentials/secrets committed.
- **Ledgers/queues:** `operations/OPERATIONS_LEDGER.csv`, `operations/DAILY_SUMMARY.csv`, `submission_queue.csv`, `state/daily_state.json`, `state/health.json`, discovery state/leads.
- **Verification:** Only `published_verified` events with public URL + evidence/readback may count (none in current disabled mode). Prepared/attempted/failed/pending do not count.
- **Error handling:** Permission gate fail-closed; skip CAPTCHA/login/permission/rate-limit/moderation/policy ambiguity; deterministic runtime repairs only as documented; watchdog for stale/missed runs.
- **Resource limits:** Bounded maintenance runs, caching of runtime state, atomic writes, single concurrency group, capped discovery/search scope.
- **Manual intervention:** Required to add permission-reviewed sites/adapters, resolve GitHub platform restrictions, or approve campaign/policy changes. Resume via `workflow_dispatch` after fixing blockers.

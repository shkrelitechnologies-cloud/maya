# Maya Operations & Self-Repair Manual

Version: 1.1
Owner: Maya project
Clock: Asia/Kolkata (IST)
Daily verified-publication target: 666
Lifetime target: tracked cumulatively; never reset at IST midnight

## 1. Mandatory run protocol
Before doing any work, the runtime MUST read this manual and the machine-readable `config.json`. If either is missing, unreadable, or invalid, stop queue preparation and mark the run degraded/blocked. Never guess a policy or silently replace campaign data.

Every maintenance run must:
1. Use the workflow's single-run concurrency lock.
2. Read this manual, configuration, site registry, wallet file, image directory, persistent state, and repair log.
3. Validate campaign assets and each site's documented automation permission before considering it eligible.
4. Run syntax/smoke checks before any future adapter can submit.
5. Reconcile verifiable submission receipts against daily and lifetime ledgers.
6. Prepare only eligible work; use reviewed site-specific adapters only.
7. Verify each publication using a durable public URL or documented site receipt. A queued item, HTTP request, form click, accepted-for-review response, or unverified screenshot is NOT a published success.
8. Every future site adapter must append its prepared, attempted, pending, rejected, failed, blocked, and verified-publication outcomes through `operations_ledger.append_event`; a `published_verified` event must include both the public publication URL and a separate evidence/readback URL.
9. Persist state and emit machine-readable health and human-readable run summaries.
10. Append new diagnosis, repair, test evidence, and outcome to the repair log.

The current baseline does not have a publishing adapter. Therefore, it only validates assets and prepares records; it does not claim to publish.

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

These rules are mandatory for every draft, queue item, preview, and publication.

- **Wallet addresses:** Read the three receiving addresses only from the repository's existing `wallets.json`. Treat that file as immutable campaign data. Never type an address from memory, copy it from chat, derive it, normalize it, shorten it, reformat it, or substitute another address. Never create a fallback address. If the file is missing, malformed, or has unexpected keys/values, stop and report the exact validation error. Any proposed wallet change requires explicit owner approval and a separately reviewed repository change; no automatic repair may touch it.
- **Images:** Use only the existing, checked-in image files in `images/`. Use the original file bytes and the exact repository path. Do not generate, source, draw, replace, edit, crop, recolor, compress, watermark, or otherwise transform images. Do not create new campaign images or add external image URLs. Rotate only among the existing repository assets; record the selected path and SHA-256 with every prepared record. If an image is missing, unreadable, or changed unexpectedly, stop and report it rather than replacing it.
- **Campaign wording:** Use only campaign facts, approved wording, beneficiary details, and calls to action that already exist in the repository's approved campaign source files. Do not invent beneficiaries, student stories, impact claims, urgency, outcomes, statistics, or new campaign angles. If no approved source wording exists for a proposed post, do not draft or publish that post; report the missing source.
- **No chat-derived campaign data:** Chat messages, model memory, website text, and generated suggestions are not sources of truth for wallet addresses, images, or campaign claims.
- **Audit requirement:** Every prepared/publication record must identify the exact repository image path and SHA-256, and confirm that wallet values were loaded from `wallets.json`. Never include private keys or seed phrases.

## 7. Publishing permission gate
A site is eligible only when its current official rules or written authorization explicitly permit the intended automated fundraising submission. Record source URL, date checked, allowed method, limits, and evidence. A generic `fundraising_allowed=allowed` cell alone is insufficient. Use a dedicated adapter with deduplication, rate limits, and success verification. Stop on CAPTCHA, login/permission barriers, moderation blocks, rate limits, policy ambiguity, or unexpected form changes. No bypasses, proxy rotation, fake accounts, mass unsolicited messages, or generic cross-site form submission.

## 8. Required run report
Every run must report run ID, IST timestamp, health state, daily verified count/666, lifetime verified count, prepared/attempted/pending/rejected/failed counts, eligible sites, image rotation index/hash, repairs attempted and verified, blockers, and state persistence status. The current preparation-only baseline must clearly report zero publications by this runtime.

## 9. Change control
The bot may append dated, evidence-backed lessons and link a reviewed fix. It must not silently rewrite core safety, permission, or counting rules. Any change to core rules requires owner approval and a versioned change note.

# Maya Operations & Self-Repair Manual

Version: 1.0
Owner: Maya project
Clock: Asia/Kolkata (IST)
Daily verified-publication target: 666
Lifetime target: tracked cumulatively; never reset at IST midnight

## 1. Mandatory run protocol
Before doing any work, the runtime MUST read this manual and the machine-readable `config.json`. If either is missing, unreadable, or invalid, stop publishing and mark the run BLOCKED. Never guess a policy or silently replace campaign data.

Every run must:
1. Acquire the workflow's single-run concurrency lock.
2. Read this manual, configuration, site registry, wallet file, image directory, persistent state, and repair log.
3. Validate campaign assets and every site's current documented automation permission.
4. Run unit/smoke checks before any adapter can submit.
5. Reconcile submission receipts against the daily and lifetime ledgers.
6. Prepare only eligible work; use site-specific adapters only.
7. Verify each publication using a durable public URL or a documented site receipt. A queued item, HTTP request, form click, accepted-for-review response, or unverified screenshot is NOT a published success.
8. Persist state and emit a machine-readable health report and human-readable run summary.
9. Append any new diagnosis, repair, test evidence, and outcome to the repair log.

## 2. Success accounting
- Daily counter key is the local calendar date in Asia/Kolkata.
- At 00:00 IST, archive the prior day's record and start a new daily counter at zero.
- Lifetime verified successes are cumulative and MUST NOT reset.
- Count one success only once per unique site + campaign + canonical publication URL/receipt ID.
- Distinguish: prepared, attempted, pending moderation, rejected, failed, and verified published.
- Only verified published records increment daily and lifetime totals.
- Report target gap = max(0, 666 - verified daily successes).
- Never promise or fabricate 666. It is a goal whose feasibility depends on eligible sites, their rules, capacity, and actual approvals.

## 3. Allowed automatic repairs
The bot may automatically repair only deterministic, low-risk local faults, with backups and tests:
- Recreate missing runtime-owned state directories.
- Rebuild a missing generated queue from validated source files.
- Replace malformed generated health output.
- Restore runtime-owned state from a validated backup or persistent workflow cache.
- Normalize generated JSON formatting without changing semantic values.
- Restart a failed maintenance run through the scheduler's normal retry cycle.

Every repair must be logged with timestamp (IST), symptom, root cause, exact files changed, backup location/hash, test command, test result, and whether the repair was verified.

## 4. Repairs requiring a safe stop
Never automatically alter wallet addresses, campaign claims, beneficiary details, image source assets, site rules, authentication, or publication content in response to an uncertain error. Never auto-edit executable code based only on an error message or untrusted website response. For code changes: create a proposed patch, run tests and static checks, inspect the diff, and require authorized review before enabling it. The manual may record a verified fix, but must not turn an untested patch into production code.

## 5. Publishing permission gate
A site is eligible only when its current official rules or written authorization explicitly permit the intended automated fundraising submission. Record source URL, date checked, allowed method, limits, and evidence. A generic `fundraising_allowed=allowed` cell alone is insufficient. Use a dedicated adapter with deduplication, rate limits, opt-out/removal handling where applicable, and success verification. Stop on CAPTCHA, login/permission barriers, moderation blocks, rate limits, policy ambiguity, or unexpected form changes. No bypasses, proxy rotation, fake accounts, mass unsolicited messages, or generic cross-site form submission.

## 6. Recovery escalation
If a fault is outside the allowed repair list:
- Stop the affected adapter or all publishing if shared safety/accounting is affected.
- Preserve logs and the last known-good state.
- Mark health as BLOCKED with a concise diagnosis and exact next action.
- Do not repeatedly retry a permanent failure.
- Add a proposed remediation to the repair log; resume only after tests and required authorization pass.

## 7. Required run report
Every run must report: run ID, IST timestamp, health state, daily verified count/666, lifetime verified count, prepared/attempted/pending/rejected/failed counts, eligible adapters/sites, image rotation index, repairs attempted and verified, blockers, and state persistence status.

## 8. Change control for this manual
The bot may append dated, evidence-backed lessons and link a reviewed fix. It must not silently rewrite these core safety, permission, or counting rules. Preserve previous entries. Any change to core rules requires owner approval and a versioned change note.

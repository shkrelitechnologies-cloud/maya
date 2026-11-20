# Maya — College Fundraising Outreach

Maya is a repository-owned campaign operations project. It validates campaign assets, performs research-only candidate discovery/assessment, prepares permission-gated queue records, maintains an IST ledger, and reports health through GitHub Actions workflows.

## Site discovery and candidate review: ENABLED (research-only)
The maintenance runtime can launch headless Chromium with Playwright to search configured public engines using bounded, worldwide/multilingual queries, inspect accessible candidate pages, and capture research-only signals (category/country/language hints, submission-method hints, official rules/submission links, eligibility evidence, status, reasons). Challenges, CAPTCHAs, login/payment/access-control barriers, and rate limits are skipped without bypass.

Discovered leads are stored in `state/discovery_leads.json`. Curated candidates in `discovery_candidates.csv` and web leads are merged into a rich review queue (`state/candidate_review_queue.json` and `state/candidate_review_queue.csv`) with duplicate prevention. Draft eligibility assessment records and draft scaffolding/config templates may be generated under `state/candidate_assessments/` and `state/scaffolding/drafts/` for clearly supported review cases. These are review/testing artifacts only — never permissions, never registered adapters, and never publication evidence.

## Live publishing: DISABLED (fail-closed)
## Current assets and components
- Campaign images: `images/` (existing checked-in assets only; runtime uses supported image files and records path/SHA-256).
- Public receiving addresses: `wallets.json`.
- Queue generator: `maya.py`.
- Maintenance runtime: `maya_runtime.py`.
- Permission gate: `publishing/permission_gate.py`.
- Research-only discovery: `publishing/discovery.py`.
- Ledgers: `operations/OPERATIONS_LEDGER.csv`, `operations/DAILY_SUMMARY.csv`.
- Audit command: `ops_666.py` (`python ops_666.py`, read-only, ledger-first).
- Configuration: `config.json`, `sites.csv`, `discovery_candidates.csv`.
- Workflows: `.github/workflows/maya-maintenance.yml`, `.github/workflows/maya-watchdog.yml`.

## Operating clock and target
- Timezone: `Asia/Kolkata` (IST).
- Goal: 666 verified unique publications in each IST calendar day.
- Daily counter rollover: 00:00 IST; lifetime records are retained.
- Prepared items, attempts, failures, pending moderation, discovery leads, and unverified receipts never count as successful publications.
- Workflow schedules/behavior are defined by the workflow files and GitHub Actions availability; cache/state persistence must be verified from live runs and artifacts.

## Image rotation
The runtime assigns images sequentially from `images/` to eligible, permissioned queue records. A persistent cursor advances between queue generations and is preserved across IST midnight. Queue records include image path and SHA-256 for audit. This is preparation only, not proof of posting.

## What runs unattended
The maintenance workflow validates configuration/assets, enforces the permission gate, runs bounded research-only discovery and candidate assessment, maintains a rich review queue and draft assessment/scaffolding artifacts in `state/` (for review only), prepares queue records only for explicitly eligible permissioned sites, updates health/ledgers, and uploads artifacts. The watchdog checks workflow health and can request bounded recovery actions. Both are limited by GitHub Actions availability/permissions/quotas.

## Publishing status and important limits
**Publishing remains disabled/fail-closed.** No generic form-filling, CAPTCHA/login/payment/access-control bypass, moderation/rate-limit evasion, fake permissions, fake adapters, or fake publication/verification records are allowed. A site-specific adapter may be used only after current verified permission and review; counting requires a durable public URL plus separate readback/evidence. The 666 target is an operational goal, not a guarantee.

## Setup and diagnostics
1. Keep only truthful, verifiable campaign information and the existing public receiving addresses.
2. Copy `sites.example.csv` to `sites.csv` and add only sites whose current rules explicitly permit the intended activity.
3. Keep campaign images in `images/`; queue records rotate through the available images.
4. Enable GitHub Actions and confirm both workflows are active.
5. Inspect `Actions → Maya 24x7 maintenance` and `Actions → Maya hourly watchdog`.
6. Download the run artifacts and verify consecutive cache restoration, IST rollover, health status, and image hashes before relying on the ledger.

## Security
Never commit private keys, seed phrases, passwords, session cookies, or access tokens. Wallet addresses are public receiving addresses only. Disclose the beneficiary, purpose, and intended use of funds accurately.


## Strict campaign asset policy

Maya must use only the campaign assets already committed in this repository:
- Receiving addresses come exclusively from `wallets.json`; never invent, transcribe from memory, or substitute an address.
- Images come exclusively from the existing files in `images/`, using original bytes without generation or editing.
- Campaign wording and claims must come only from approved campaign source material already stored in the repository. If that source material does not contain enough approved wording, stop rather than invent copy.
- Do not create or import replacement images, addresses, beneficiary details, stories, statistics, or campaign claims.
- Every queue record must retain the exact selected image path and SHA-256 for audit.
- Any suspected change to a wallet or existing image is a stop-and-escalate condition, never an automatic repair.

# Maya — College Fundraising Outreach

Maya is a repository-owned campaign operations project. It validates campaign assets, maintains an IST ledger, monitors its GitHub Actions maintenance workflow, and now runs site discovery in **research-only mode**.

## Site discovery: ENABLED
The 15-minute maintenance workflow reads `discovery_candidates.csv` and reports research leads in its health artifact. Candidates are not treated as permission to publish. The initial researched leads include Raisemore, India Giving Day, and CHANCES.org, each with a source URL and a stated eligibility caveat.

## Live publishing: DISABLED
The root `sites.csv` is an empty permission registry and no executable site-specific adapter is installed. Maya must not submit anything until current official rules or written authorization permit the exact automated fundraising method and a dedicated adapter is tested. CAPTCHA, login walls, permission barriers, rate limits, moderation blocks, and policy ambiguity must be skipped; never bypass them. See `publishing/README.md`.

Maya is a repository-owned campaign operations project. It validates campaign assets, prepares a deterministic image-rotating queue, maintains an IST ledger, and monitors its own GitHub Actions maintenance workflow.

## Publishing activation state
The runtime now enforces `publishing/permission_gate.py`. The root `sites.csv` is currently an empty registry and no executable site-specific adapter is installed. Maya is therefore NOT a live publisher yet. The new gate requires current official permission evidence, a recent review, a bounded daily limit, and a dedicated adapter for each destination. CAPTCHA, login walls, permission barriers, rate limits, moderation blocks, and policy ambiguity must be skipped; never bypass them. See `publishing/README.md`.

Maya is a repository-owned campaign operations project. It validates campaign assets, prepares a deterministic image-rotating queue, maintains an IST ledger, and monitors its own GitHub Actions maintenance workflow.

## Current verified assets
- Campaign images: stored in `images/` (the baseline contains 15 PNG images; the runtime counts supported image files at execution time).
- Fixed public receiving addresses: `wallets.json`.
- Queue generator: `maya.py`.
- Maintenance runtime: `maya_runtime.py`.
- Hourly watchdog: `.github/scripts/watchdog.py`.
- Runtime configuration: `config.json`.
- Maintenance workflow: `.github/workflows/maya-maintenance.yml`.
- Hourly watchdog workflow: `.github/workflows/maya-watchdog.yml`.

## Operating clock and target
- Timezone: `Asia/Kolkata` (IST).
- Goal: 666 verified successful publications in each IST calendar day.
- Daily counter rollover: 00:00 IST; lifetime records are retained.
- Maintenance workflow: every 15 minutes.
- Independent workflow watchdog: hourly. It checks the maintenance workflow, attempts to re-enable it if GitHub reports it disabled, and dispatches a recovery run if no successful run completed within 45 minutes and no run is already active.
- Prepared items, attempts, failures, pending moderation, and unverified receipts never count as successful publications.

## Image rotation
The runtime assigns images sequentially from `images/` to eligible queue records. Each adjacent record gets the next image; the sequence loops after the available image set. A persistent cursor advances between queue generations and is preserved across IST midnight, so each new queue does not restart at the first image. The CSV includes the selected image path and SHA-256 so the asset used by each prepared record can be audited. This is queue preparation, not proof that an image was posted.

## What runs unattended
The 15-minute workflow validates configuration, wallet structure, image availability, registry structure, prepares the queue, writes a health report, and records an IST heartbeat. The hourly watchdog checks recent workflow runs and can safely request one recovery execution. Both preserve run reports as GitHub Actions artifacts.

GitHub Actions runners are ephemeral. The maintenance workflow restores and saves a cache for operational state and uploads artifacts as an audit trail. Cache retention/eviction and workflow execution must be verified from live runs; cache is not a database or an absolute durability guarantee.

## Publishing status and important limits
**Publishing is disabled in this baseline.** The runtime does not submit posts to third-party websites. No generic form-filling, mass unsolicited outreach, CAPTCHA bypass, access-control evasion, moderation evasion, or rate-limit evasion is allowed.

A site-specific adapter may be added only after its current official rules explicitly permit the intended automated fundraising submission and the method is reviewed. Each adapter must enforce per-site limits, deduplicate, stop on blocks or policy uncertainty, and record verifiable publication receipts. The 666 target is an operational goal, not a guarantee.

The watchdog cannot repair GitHub account restrictions, repository-level Actions disablement, revoked permissions, exhausted platform quotas, or an outage that prevents GitHub from starting the watchdog itself. For detection of those platform-wide failures, configure an independent external heartbeat monitor. Never describe the system as error-proof or continuously running unless live evidence supports that claim.

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

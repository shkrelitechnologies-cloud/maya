# Maya — College Fundraising Outreach

Maya is the repository-owned campaign operations project. The repository contains the campaign assets, fixed wallet addresses, site registry template, queue generator, unattended maintenance runtime, and scheduled health workflow.

## Current verified assets
- Campaign images: stored in `images/` (the repository currently contains 15 PNG images).
- Fixed wallets: `wallets.json`.
- Queue generator: `maya.py`.
- Maintenance runtime: `maya_runtime.py`.
- Runtime configuration: `config.json`.
- Scheduled workflow: `.github/workflows/maya-maintenance.yml`.

## Operating clock and target
- Timezone: `Asia/Kolkata` (IST).
- Daily target: 666 verified successful publications in each IST calendar day.
- Daily counter rollover: 00:00 IST. Historical daily records are retained locally in runtime state when the runtime is run on a persistent host.
- GitHub Actions runs maintenance every 15 minutes. GitHub schedule expressions use UTC; the runtime itself calculates the day and timestamps in IST.
- Drafts, attempts, and failures never count as successful publications.

## What currently runs unattended
The scheduled workflow checks wallet structure, image availability, registry structure, prepares a deterministic rotating-image queue, writes a health report, and records an IST heartbeat. GitHub Actions automatically starts a fresh runner for each scheduled execution and stores reports as workflow artifacts.

## Important publishing boundary and current status
**Publishing is deliberately disabled in this baseline.** A generic browser script that posts the same fundraising appeal across arbitrary websites is not a safe or reliable integration: websites differ in rules, consent, rate limits, moderation, authentication, and permitted automation. Maya must not evade CAPTCHAs, access controls, moderation, rate limits, or site policies.

To enable unattended publishing on a particular website, add a dedicated adapter only after verifying that the site explicitly permits automated fundraising submissions and that the adapter uses an authorized, documented submission route. Each adapter must enforce that site's rate limits, deduplicate submissions, stop on blocks or policy uncertainty, record verifiable success receipts, and support image uploads only where allowed. No generic form-filling fallback is permitted.

The target of 666 is an operational goal, not a guarantee. Maya must never manufacture success counts or keep retrying a site after it rejects or blocks submissions.

## Setup
1. Review the campaign purpose and ensure the public campaign information is truthful and verifiable.
2. Copy `sites.example.csv` to `sites.csv`.
3. Add only relevant sites after checking current rules; record their rules URL, submission URL, language, and review date.
4. Keep the 15 campaign images in `images/`; the runtime rotates them deterministically.
5. Enable GitHub Actions in the repository. The scheduled workflow runs every 15 minutes automatically.

## Diagnostics
- Workflow: `Actions → Maya 24x7 maintenance`.
- Each run uploads a health report and queue artifact.
- A degraded health report lists validation errors. A failed run is visible in Actions and is retried at the next scheduled interval.
- No external payment processor or paid API is required for the maintenance runtime. The three public wallet addresses remain in `wallets.json`.

## Security
Do not put private keys, seed phrases, passwords, session cookies, or access tokens in the repository. Wallet addresses are public receiving addresses only. Keep fundraising claims accurate and disclose the beneficiary, purpose, and intended use of funds.

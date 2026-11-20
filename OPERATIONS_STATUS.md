# Maya Operations Status

- Daily target: **666 verified unique publications per IST day**.
- Lifetime total: cumulative verified publications; never reset.
- Current mode: **research-only discovery and candidate assessment enabled** (bounded Playwright/Chromium search + public page inspection, worldwide/multilingual queries, no bypass of CAPTCHA/login/payment/access controls).
- Candidate pipeline: curated `discovery_candidates.csv` + web leads (`state/discovery_leads.json`) merged into review queue artifacts (`state/candidate_review_queue.json/.csv`) with category/country/language hints, submission-method hints, eligibility evidence, status, and reasons. Draft assessments/scaffolding may be generated in `state/` for review only.
- Publishing: **DISABLED / fail-closed**. No rows in `sites.csv` currently satisfy verified permission + dedicated adapter requirements, and no executable adapter is installed.
- Count rule: only unique, independently verified live publication URLs with separate readback/evidence count (`published_verified`).
- CAPTCHA, login walls, permission barriers, rate limits, moderation blocks, and policy ambiguity: skip; never bypass.
- Manual: [OPERATIONS_MANUAL.md](OPERATIONS_MANUAL.md)
- Permission registry: [sites.csv](sites.csv)
- Adapter requirements: [publishing/README.md](publishing/README.md)
- Ledgers: [operations/OPERATIONS_LEDGER.csv](operations/OPERATIONS_LEDGER.csv), [operations/DAILY_SUMMARY.csv](operations/DAILY_SUMMARY.csv)
- Audit command: `python ops_666.py`
- Current runtime: [maya_runtime.py](maya_runtime.py)

# Maya Operations Status

- Daily target: **666 verified live publications per IST day**.
- Lifetime total: cumulative verified publications; never reset.
- Current mode: **site discovery enabled, research-only**, using Playwright Chromium across DuckDuckGo, Bing, and Google, with a 15-minute maintenance schedule.
- Discovery queue: `discovery_candidates.csv`; candidates are research leads, not approved destinations.
- Publishing: **DISABLED** until a site's current rules or written authorization explicitly permit the exact automated submission method and a dedicated adapter passes tests.
- Count rule: only unique, independently verified live publication URLs/receipt IDs count.
- CAPTCHA, login walls, permission barriers, rate limits and moderation blocks: skip the destination; never bypass.
- Self-repair: only bounded, deterministic local repairs are allowed. Code/security/policy changes require tests and owner review.
- Manual: [OPERATIONS_MANUAL.md](OPERATIONS_MANUAL.md)
- Discovery queue: [discovery_candidates.csv](discovery_candidates.csv)
- Permission registry: [sites.csv](sites.csv)
- Adapter requirements: [publishing/README.md](publishing/README.md)
- Repository-local event ledger: [operations/OPERATIONS_LEDGER.csv](operations/OPERATIONS_LEDGER.csv)
- IST daily summary: [operations/DAILY_SUMMARY.csv](operations/DAILY_SUMMARY.csv)
- Repair history: [SELF_REPAIR_LOG.md](SELF_REPAIR_LOG.md)
- Current runtime: [maya_runtime.py](maya_runtime.py)
- Health reports: GitHub Actions artifacts.

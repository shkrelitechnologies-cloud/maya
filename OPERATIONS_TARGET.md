# Maya daily publication target

- Target: **666 verified public publications per Asia/Kolkata calendar day** (already declared in config.json).
- Count only unique publication records with verified=true, a valid public publication URL, and a retained evidence URL/readback.
- Drafts, attempts, failed submissions, and pending moderation do not count.
- Preserve history and reset the daily counter at 00:00 Asia/Kolkata.

**Current implementation limitation:** Maya's current operational baseline is preparation-only. Publishing remains disabled until a site-specific adapter and current explicit permission are verified. The site registry and adapters must be reviewed before any publication is enabled. The watchdog may recover the workflow, but must never bypass site permission, CAPTCHA, moderation, or rate-limit blocks.

The 666 target is an operational goal, not a claim that the current runtime can meet it. Report actual verified count and blockers honestly.

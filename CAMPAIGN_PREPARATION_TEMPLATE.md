# Maya Campaign Preparation Template

This document is a preparation and audit checklist. It does not authorize publication and does not override `OPERATIONS_MANUAL.md`, `config.json`, or official site rules.

## Mandatory source-of-truth files

Before preparing any item, read the current repository versions of:
1. `OPERATIONS_MANUAL.md`
2. `config.json`
3. The existing approved campaign-copy source file(s)
4. `wallets.json`
5. The existing files in `images/`

If a required file is missing, unreadable, malformed, contradictory, or unapproved, stop and record the exact blocker. Do not create replacement campaign facts, copy, images, beneficiary details, statistics, or wallet values.

## Per-item preparation record

| Field | Required value |
|---|---|
| Run ID | Unique run identifier |
| Prepared at | ISO timestamp with timezone |
| Campaign copy source | Exact repository path and source revision |
| Approved copy | Exact approved text; no invented additions |
| Image path | Exact existing path under `images/` |
| Image SHA-256 | Hash of the original image bytes |
| Image validation | File type, nonzero size, successful decode |
| Wallet source | Must be `wallets.json` |
| Wallet validation | Required keys and values validated directly from file |
| Destination site | Exact site and intended submission location |
| Permission evidence | Official rules/authorization URL, date checked, permitted method and limits |
| Submission status | Prepared / attempted / pending / rejected / failed / verified published |
| Publication evidence | Durable public URL or documented site receipt; required for success |
| Error or blocker | Exact error, no guessed diagnosis |
| Repair performed | Exact runtime-owned output repaired, or none |
| Verification | Test command/result and evidence |

## Image selection rules

- Select only from files already present in `images/`.
- If random selection is requested, select one existing file from the validated inventory.
- Preserve the original bytes and exact repository path.
- Never generate, download externally, edit, crop, recolor, compress, watermark, or replace an image.
- Record SHA-256 from the exact bytes used.
- A filename or GitHub directory listing alone is not visual inspection. Do not claim the image was previewed until the actual bytes have been retrieved and inspected.
- If the selected file is missing, unreadable, changed unexpectedly, or invalid, stop and report it.

## Wallet rules

- Load wallet values directly from the current `wallets.json` at runtime.
- Do not type, reconstruct, normalize, shorten, or substitute wallet addresses.
- Do not copy wallet values into generated source files or fallback configuration.
- If the file fails validation, stop. Never auto-repair wallet values.

## Publication gate

Maya's current documented baseline has publishing disabled. Do not submit anything unless a reviewed site-specific adapter exists and current official rules or written authorization explicitly permit the exact automated fundraising activity.

Stop on CAPTCHA, login/permission barriers, moderation blocks, rate limits, policy ambiguity, or unexpected form changes. No generic mass form submission, unsolicited spam, fake accounts, proxy rotation, or bypasses.

## Counting and reporting

Only a unique publication verified by a durable public URL or documented site receipt counts as successful. Prepared items, attempted requests, form clicks, accepted-for-review responses, pending moderation, and screenshots without verifiable receipt do not count.

Report separately:
- Prepared
- Attempted
- Pending moderation
- Rejected
- Failed
- Verified published
- Daily verified total against the 666 goal
- Lifetime verified total
- Asset validation and selected image hash
- Repairs attempted and independently verified
- Blockers and next actions

The 666 figure is a target, never a guaranteed outcome.

# Maya site-specific publishing adapters

## Current status: NOT LIVE

This directory is an adapter contract, not a working publisher. There are
currently no site-specific adapters and the site registry contains no approved
destinations. Maya must remain in preparation/idle mode until both exist.

## Required for each destination

1. Confirm the current official rules explicitly permit the intended automated
   fundraising submission. Save the official rules URL and dated evidence URL.
2. Record the exact allowed submission method, daily limit, language, and
   review date in the root `sites.csv`.
3. Implement one dedicated adapter class for that site under
   `publishing/adapters/`. No generic cross-site form submitter.
4. Adapter preflight must verify the expected host, page/form structure,
   permission state, and current per-site limits before any action.
5. Deduplicate by site + campaign + canonical post content.
6. Stop and skip that destination on CAPTCHA, login wall, account/permission
   barrier, moderation block, rate limit without a valid retry-after, policy
   ambiguity, or unexpected page/form changes. Never bypass or retry around
   these controls. Continue with the next independently eligible destination.
7. Count a publication only after public read-back verification returns a
   durable public URL and a separate evidence/readback URL.
8. Test offline with fixtures and a dry-run mode before enabling a live adapter.

## Registry gate

`permission_gate.py` rejects incomplete or stale entries. A row marked yes
alone is insufficient: HTTPS rules/evidence URLs, exact domain match, a review
within 30 days, an explicit method, a bounded daily limit, and a dedicated
adapter class are all mandatory.

## Safety and honest reporting

No adapter is installed by this commit. Do not set Maya to LIVE or count queue
items as publications. The 666/day value is a goal, not a guarantee. The
current runtime does not yet invoke this adapter contract.

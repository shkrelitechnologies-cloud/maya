# Maya — College Fundraising Outreach

Maya organizes campaign images and the campaign's three fixed cryptocurrency wallet addresses, then prepares a review queue for websites that explicitly permit fundraising submissions.

## Current assets

- 15 campaign images in `images/`
- Shared wallet addresses in `wallets.json`
- Queue generator: `maya.py`

## Permission-first workflow

1. Find a relevant public community or submission page.
2. Read its current rules and confirm that fundraising posts are explicitly allowed.
3. Add the page to `sites.csv`; set `fundraising_allowed` to exactly `allowed` only after checking.
4. Record the language and review date. Translate any required campaign explanation accurately; do not post wallet addresses without enough context for readers to understand the purpose.
5. Run `python maya.py` to prepare a CSV queue. Images rotate across eligible sites; all three wallet addresses are loaded from the same `wallets.json`.
6. Review each draft and submit only through the site's normal permitted process. Record outcomes and honor removals or opt-outs.

## Run

```bash
cp sites.example.csv sites.csv
# Edit sites.csv with verified, permitted submission pages.
python maya.py
```

The program does not crawl the web, create accounts, submit posts, evade moderation, or bypass rate limits. It prepares drafts only. Do not use it for unsolicited bulk posting, repetitive comments, or sites that prohibit fundraising.

## Trust and transparency

Before publishing, add a concise, truthful explanation of the college, the fundraising purpose, who receives funds, how funds are used, and how donors can verify the campaign. Never imply institutional endorsement unless authorized. Never invent impact claims, deadlines, identities, or donation receipts.

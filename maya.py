#!/usr/bin/env python3
"""Maya: permission-first fundraising submission queue.

This tool prepares per-site drafts. It does not scrape sites, create accounts,
bypass moderation, or submit posts. A site must be explicitly marked
"allowed" after its current rules have been checked by a human.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
IMAGES_DIR = ROOT / "images"
WALLETS_FILE = ROOT / "wallets.json"
SITES_FILE = ROOT / "sites.csv"
OUTPUT_FILE = ROOT / "submission_queue.csv"

REQUIRED_SITE_FIELDS = {
    "site_name", "submission_url", "rules_url", "language",
    "fundraising_allowed", "reviewed_on", "notes"
}


def load_wallets():
    wallets = json.loads(WALLETS_FILE.read_text(encoding="utf-8"))
    required = {"bitcoin", "ethereum", "solana"}
    if set(wallets) != required or not all(wallets.values()):
        raise ValueError("wallets.json must contain bitcoin, ethereum and solana.")
    return wallets


def load_images():
    images = sorted(
        p for p in IMAGES_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    )
    if not images:
        raise RuntimeError("No campaign images found in images/.")
    return images


def valid_http_url(value):
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def main():
    parser = argparse.ArgumentParser(description="Prepare a permission-checked campaign submission queue.")
    parser.add_argument("--sites", type=Path, default=SITES_FILE)
    parser.add_argument("--output", type=Path, default=OUTPUT_FILE)
    args = parser.parse_args()

    if not args.sites.exists():
        raise SystemExit("Create sites.csv from sites.example.csv and verify each site's rules first.")

    wallets = load_wallets()
    images = load_images()
    rows = []

    with args.sites.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_SITE_FIELDS - set(reader.fieldnames or [])
        if missing:
            raise SystemExit("sites.csv is missing columns: " + ", ".join(sorted(missing)))

        for site in reader:
            if site["fundraising_allowed"].strip().lower() != "allowed":
                continue
            if not valid_http_url(site["submission_url"]) or not valid_http_url(site["rules_url"]):
                continue
            if not site["reviewed_on"].strip() or not site["language"].strip():
                continue

            # Deterministic rotation: every eligible site gets the next image.
            image_index = len(rows) % len(images)
            image = images[image_index]
            rows.append({
                "site_name": site["site_name"],
                "submission_url": site["submission_url"],
                "rules_url": site["rules_url"],
                "language": site["language"],
                "image_path": str(image.relative_to(ROOT)),
                "bitcoin": wallets["bitcoin"],
                "ethereum": wallets["ethereum"],
                "solana": wallets["solana"],
                "status": "DRAFT_REQUIRES_HUMAN_REVIEW",
                "reviewed_on": site["reviewed_on"],
                "notes": site["notes"],
            })

    if not rows:
        raise SystemExit("No eligible sites. Only rows explicitly marked 'allowed' are included.")

    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Prepared {len(rows)} draft(s) using {len(images)} rotating image(s).")
    print(f"Output: {args.output}")
    print("No posts were submitted. Review each site's rules and submit manually.")


if __name__ == "__main__":
    main()

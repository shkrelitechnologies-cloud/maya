#!/usr/bin/env python3
"""Maya unattended maintenance runtime.

This runtime validates campaign assets, rotates images for eligible registry
entries, maintains an IST daily ledger, and writes a health report. It does
NOT submit content to third-party websites. Publishing requires a site-specific
adapter whose current rules explicitly permit automated fundraising.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
TZ = ZoneInfo("Asia/Kolkata")
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
WALLET_KEYS = {"bitcoin", "ethereum", "solana"}
TARGET_PER_DAY = 666


def now_ist():
    return datetime.now(timezone.utc).astimezone(TZ)


def load_json(path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path, data):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def validate():
    errors, warnings = [], []
    wallets = load_json(ROOT / "wallets.json", {})
    if set(wallets) != WALLET_KEYS or not all(isinstance(v, str) and v.strip() for v in wallets.values()):
        errors.append("wallets.json must contain non-empty bitcoin, ethereum and solana values")

    image_dir = ROOT / "images"
    images = sorted(p for p in image_dir.glob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTS) if image_dir.exists() else []
    if not images:
        errors.append("No supported campaign images found in images/")
    else:
        for p in images:
            if p.stat().st_size == 0:
                errors.append(f"Empty image file: {p.name}")

    sites_path = ROOT / "sites.csv"
    eligible = []
    if sites_path.exists():
        with sites_path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            required = {"site_name", "submission_url", "rules_url", "language", "fundraising_allowed", "reviewed_on", "notes"}
            if not required.issubset(set(reader.fieldnames or [])):
                errors.append("sites.csv is missing required columns")
            else:
                for row in reader:
                    # Registry eligibility is not sufficient for publishing: this runtime only prepares records.
                    if row.get("fundraising_allowed", "").strip().lower() == "allowed":
                        eligible.append(row)
    else:
        warnings.append("sites.csv not found; copy sites.example.csv and populate only after checking each site's rules")

    return wallets, images, eligible, errors, warnings


def build_queue(wallets, images, eligible, day_key):
    if not images or not wallets:
        return []
    rows = []
    for index, site in enumerate(eligible):
        image = images[index % len(images)]
        rows.append({
            "site_name": site.get("site_name", ""),
            "submission_url": site.get("submission_url", ""),
            "rules_url": site.get("rules_url", ""),
            "language": site.get("language", ""),
            "image_path": str(image.relative_to(ROOT)),
            "image_sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
            "bitcoin": wallets["bitcoin"],
            "ethereum": wallets["ethereum"],
            "solana": wallets["solana"],
            "status": "PREPARED_NOT_PUBLISHED",
            "day_ist": day_key,
        })
    return rows


def write_csv(path, rows):
    if not rows:
        path.write_text("site_name,status\n", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    stamp = now_ist()
    day_key = stamp.strftime("%Y-%m-%d")
    state_path = ROOT / "state" / "daily_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    report_path = ROOT / "state" / "health.json"

    try:
        wallets, images, eligible, errors, warnings = validate()
        state = load_json(state_path, {})
        if state.get("day_ist") != day_key:
            # IST midnight rollover; preserve previous-day totals in history.
            history = state.get("history", [])
            if state.get("day_ist"):
                history.append({k: v for k, v in state.items() if k != "history"})
            state = {"history": history[-90:], "day_ist": day_key, "verified_successes": 0, "failed": 0}
        state.setdefault("verified_successes", 0)
        state.setdefault("failed", 0)
        state["target"] = TARGET_PER_DAY
        state["timezone"] = "Asia/Kolkata"
        state["last_heartbeat_ist"] = stamp.isoformat()
        state["remaining_to_target"] = max(0, TARGET_PER_DAY - int(state["verified_successes"]))
        queue = build_queue(wallets, images, eligible, day_key) if not errors else []
        write_csv(ROOT / "submission_queue.csv", queue)
        atomic_json(state_path, state)
        report = {
            "status": "healthy" if not errors else "degraded",
            "checked_at_ist": stamp.isoformat(),
            "timezone": "Asia/Kolkata",
            "daily_target": TARGET_PER_DAY,
            "verified_successes_today": int(state["verified_successes"]),
            "remaining_to_target": state["remaining_to_target"],
            "images_found": len(images),
            "eligible_registry_rows": len(eligible),
            "prepared_records": len(queue),
            "published_by_this_runtime": 0,
            "errors": errors,
            "warnings": warnings,
            "publishing": "DISABLED: no verified site-specific permitted adapter is configured",
        }
        atomic_json(report_path, report)
        print(json.dumps(report, indent=2))
        return 1 if errors else 0
    except Exception:
        report = {
            "status": "crashed",
            "checked_at_ist": stamp.isoformat(),
            "traceback": traceback.format_exc(),
        }
        atomic_json(report_path, report)
        print(json.dumps(report, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

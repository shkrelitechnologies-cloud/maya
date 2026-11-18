#!/usr/bin/env python3
"""Maya unattended maintenance runtime.

Validates assets, rotates images in prepared records, maintains an IST daily
ledger, and writes a health report. Publishing remains disabled until a
site-specific adapter is independently reviewed and explicitly permitted.
"""
from __future__ import annotations

import csv
import hashlib
import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from operations_ledger import append_event

ROOT = Path(__file__).resolve().parent
TZ = ZoneInfo("Asia/Kolkata")
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
WALLET_KEYS = {"bitcoin", "ethereum", "solana"}


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def now_ist():
    return datetime.now(timezone.utc).astimezone(TZ)


def atomic_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def validate():
    errors, warnings = [], []
    manual = ROOT / "OPERATIONS_MANUAL.md"
    repair_log = ROOT / "SELF_REPAIR_LOG.md"
    config_path = ROOT / "config.json"

    for required in (manual, repair_log, config_path):
        if not required.is_file() or not required.read_text(encoding="utf-8").strip():
            errors.append(f"{required.name} missing or empty; fail-closed")

    config = load_json(config_path, {})
    if not isinstance(config, dict):
        errors.append("config.json must contain a JSON object")
        config = {}
    target = config.get("daily_success_target", 666)
    if not isinstance(target, int) or target < 1:
        errors.append("daily_success_target must be a positive integer")
        target = 666

    wallets = load_json(ROOT / "wallets.json", {})
    if not isinstance(wallets, dict) or set(wallets) != WALLET_KEYS or not all(
        isinstance(v, str) and v.strip() for v in wallets.values()
    ):
        errors.append("wallets.json must contain non-empty bitcoin, ethereum and solana values")
        wallets = {}

    image_dir = ROOT / "images"
    images = sorted(
        p for p in image_dir.glob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    ) if image_dir.exists() else []
    if not images:
        errors.append("No supported campaign images found in images/")
    else:
        for p in images:
            if p.stat().st_size == 0:
                errors.append(f"Empty image file: {p.name}")

    eligible = []
    sites_path = ROOT / "sites.csv"
    if sites_path.exists():
        with sites_path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            required = {"site_name", "submission_url", "rules_url", "language",
                        "fundraising_allowed", "reviewed_on", "notes"}
            if not required.issubset(set(reader.fieldnames or [])):
                errors.append("sites.csv is missing required columns")
            else:
                for row in reader:
                    if row.get("fundraising_allowed", "").strip().lower() == "allowed":
                        eligible.append(row)
    else:
        warnings.append("sites.csv not found; no sites are eligible")

    return config, target, wallets, images, eligible, errors, warnings


def build_queue(wallets, images, eligible, day_key, rotation_cursor=0):
    if not images or not wallets:
        return []
    rows = []
    for index, site in enumerate(eligible):
        image = images[(rotation_cursor + index) % len(images)]
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
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("site_name,status\n", encoding="utf-8")
        return
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def main():
    stamp = now_ist()
    day_key = stamp.strftime("%Y-%m-%d")
    state_path = ROOT / "state" / "daily_state.json"
    report_path = ROOT / "state" / "health.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        append_event(ROOT, event_type="run", status="run_started",
                     message="Maya maintenance run started; publishing remains disabled.")
        config, target, wallets, images, eligible, errors, warnings = validate()
        state = load_json(state_path, {})
        if not isinstance(state, dict):
            errors.append("daily_state.json is not a JSON object; preserved and fail-closed")
            state = {}
        if state.get("day_ist") != day_key:
            history = state.get("history", [])
            if not isinstance(history, list):
                history = []
            if state.get("day_ist"):
                history.append({k: v for k, v in state.items() if k != "history"})
            prior_image_cursor = max(0, int(state.get("image_rotation_cursor", 0) or 0))
            state = {
                "history": history[-90:],
                "day_ist": day_key,
                "image_rotation_cursor": prior_image_cursor,
                "verified_successes": 0,
                "failed": 0,
                "lifetime_verified_successes": int(state.get("lifetime_verified_successes", 0) or 0),
            }

        for key in ("verified_successes", "failed", "lifetime_verified_successes"):
            try:
                state[key] = max(0, int(state.get(key, 0)))
            except (TypeError, ValueError):
                errors.append(f"Invalid {key} in state; fail-closed")
                state[key] = 0

        state["target"] = target
        state["timezone"] = "Asia/Kolkata"
        state["last_heartbeat_ist"] = stamp.isoformat()
        state["remaining_to_target"] = max(0, target - state["verified_successes"])

        rotation_cursor = max(0, int(state.get("image_rotation_cursor", 0) or 0))
        queue = build_queue(wallets, images, eligible, day_key, rotation_cursor) if not errors else []
        if queue:
            state["image_rotation_cursor"] = rotation_cursor + len(queue)
            for item in queue:
                append_event(
                    ROOT, event_type="site_queue", status="prepared",
                    site_name=item.get("site_name", ""),
                    target_url=item.get("submission_url", ""),
                    message="Queue item prepared only; no website submission or publication occurred.",
                )
        else:
            state.setdefault("image_rotation_cursor", rotation_cursor)
            append_event(ROOT, event_type="queue", status="no_eligible_sites",
                         message="No eligible sites were available for queue preparation.")
        write_csv(ROOT / "submission_queue.csv", queue)
        atomic_json(state_path, state)

        report = {
            "status": "healthy" if not errors else "degraded",
            "checked_at_ist": stamp.isoformat(),
            "timezone": "Asia/Kolkata",
            "daily_target": target,
            "verified_successes_today": state["verified_successes"],
            "lifetime_verified_successes": state["lifetime_verified_successes"],
            "remaining_to_target": state["remaining_to_target"],
            "images_found": len(images),
            "image_rotation_cursor": state.get("image_rotation_cursor", 0),
            "eligible_registry_rows": len(eligible),
            "prepared_records": len(queue),
            "published_by_this_runtime": 0,
            "errors": errors,
            "warnings": warnings,
            "publishing": "DISABLED: no verified site-specific permitted adapter is configured",
            "manual_checked": (ROOT / "OPERATIONS_MANUAL.md").is_file(),
            "repair_log_checked": (ROOT / "SELF_REPAIR_LOG.md").is_file(),
            "state_persistence": "GitHub Actions cache restore/save plus run artifacts; live continuity must be verified",
        }
        atomic_json(report_path, report)
        append_event(
            ROOT, event_type="run", status="run_completed" if not errors else "run_degraded",
            message=f"Prepared {len(queue)} item(s); verified publications remain {state['verified_successes']}.",
        )
        print(json.dumps(report, indent=2))
        return 1 if errors else 0
    except Exception:
        report = {
            "status": "crashed",
            "checked_at_ist": stamp.isoformat(),
            "traceback": traceback.format_exc(),
        }
        atomic_json(report_path, report)
        try:
            append_event(ROOT, event_type="run", status="run_failed",
                         message="Runtime exception; inspect state/health.json for details.")
        except Exception as ledger_error:
            report["ledger_error"] = type(ledger_error).__name__
            atomic_json(report_path, report)
        print(json.dumps(report, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

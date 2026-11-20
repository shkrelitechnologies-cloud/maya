#!/usr/bin/env python3
"""Maya 666 operational audit (read-only, ledger-first).

Reports verified unique publications against the daily 666 target using the
repository-local IST ledger. Never treats workflow success, queue preparation,
or discovery leads as publications.
"""
from __future__ import annotations

import csv
import json
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TZ = timezone(timedelta(hours=5, minutes=30))
TARGET = 666


def permission_registry_status():
    sites = ROOT / "sites.csv"
    if not sites.exists():
        return {"eligible_permission_rows": 0, "status": "sites.csv missing"}
    try:
        from publishing.permission_gate import load_verified_permissions
        eligible, skipped = load_verified_permissions(sites, today=now_ist().date())
        return {
            "eligible_permission_rows": len(eligible),
            "permission_gate_skips": len(skipped),
            "status": "eligible_permissioned_adapter_rows_present" if eligible else "no_eligible_permissioned_adapter_rows",
        }
    except Exception as exc:
        return {"eligible_permission_rows": "unverifiable", "status": f"permission_gate_error:{type(exc).__name__}"}


def now_ist():
    return datetime.now(timezone.utc).astimezone(TZ)


def read_csv(path: Path):
    if not path.exists():
        return None, f"missing:{path}"
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f)), None


def gh_json(args):
    if not shutil.which("gh"):
        return None, "gh unavailable"
    try:
        out = subprocess.check_output(["gh", *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT, timeout=20)
        return out.strip(), None
    except Exception as e:
        return None, str(e)


def main():
    now = now_ist()
    today = now.date().isoformat()
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    remaining_seconds = max(0.0, (midnight - now).total_seconds())

    summary_rows, summary_err = read_csv(ROOT / "operations" / "DAILY_SUMMARY.csv")
    ledger_rows, ledger_err = read_csv(ROOT / "operations" / "OPERATIONS_LEDGER.csv")

    registry = permission_registry_status()
    report = {
        "project": "MAYA",
        "repository": "shkrelitechnologies-cloud/maya",
        "checked_at_ist": now.isoformat(timespec="seconds"),
        "today_ist": today,
        "target": TARGET,
        "ledger_source": "operations/DAILY_SUMMARY.csv + operations/OPERATIONS_LEDGER.csv",
        "permission_registry": registry,
        "errors": [e for e in (summary_err, ledger_err) if e],
    }

    if summary_rows is None or ledger_rows is None:
        report.update({
            "verified_publications": "unverifiable",
            "remaining_to_target": "unverifiable",
            "required_rate_per_hour": "unverifiable",
            "note": "Ledger unavailable or unreadable; count is not reported as zero.",
            "publishing_mode": "disabled_fail_closed_until_verified_permission_adapter_and_readback",
        })
    else:
        today_summary = next((r for r in summary_rows if r.get("ist_date") == today), None)
        verified_events = []
        for r in ledger_rows:
            if r.get("ist_date") != today:
                continue
            if str(r.get("verified", "")).lower() == "true" and r.get("status") == "published_verified" and r.get("publication_url"):
                verified_events.append(r)
        unique_verified_urls = sorted({r.get("publication_url") for r in verified_events if r.get("publication_url")})
        verified = len(unique_verified_urls)
        summary_verified = int(today_summary.get("verified_publications", 0) or 0) if today_summary else 0
        reconciled = verified == summary_verified
        remaining = max(0, TARGET - verified)
        rate = (remaining / (remaining_seconds / 3600.0)) if remaining_seconds > 0 else None
        blocker = "No eligible verified permission+adapter rows; verified publication count cannot increase without authorized eligible destinations and public readback evidence."
        if registry.get("eligible_permission_rows") not in (0, "unverifiable", None):
            blocker = "Eligible permission+adapter rows exist in registry; publishing can proceed only through reviewed adapters with public URL + readback verification (not executed by ops_666)."
        report.update({
            "verified_unique_publications": verified,
            "summary_verified_publications": summary_verified,
            "ledger_reconciled": reconciled,
            "remaining_to_target": remaining,
            "remaining_time_ist": str(midnight - now).split(".")[0],
            "required_verified_per_hour": round(rate, 3) if rate is not None else None,
            "attempts": int(today_summary.get("attempted", 0) or 0) if today_summary else 0,
            "pending_moderation": int(today_summary.get("pending_moderation", 0) or 0) if today_summary else 0,
            "failed": int(today_summary.get("failed", 0) or 0) if today_summary else 0,
            "blocked": int(today_summary.get("blocked", 0) or 0) if today_summary else 0,
            "skipped": int(today_summary.get("skipped", 0) or 0) if today_summary else 0,
            "prepared": int(today_summary.get("prepared", 0) or 0) if today_summary else 0,
            "duplicates": 0,
            "existing_listings_verified": 0,
            "publishing_mode": "disabled_fail_closed_until_verified_permission_adapter_and_readback",
            "blocker_note": blocker,
        })
        if not reconciled:
            report["errors"].append(f"Summary/ledger mismatch: ledger_unique_verified={verified} summary={summary_verified}")

    runs_out, runs_err = gh_json(["run", "list", "-R", "shkrelitechnologies-cloud/maya", "--limit", "5"])
    if runs_out is not None:
        report["recent_runs"] = runs_out.splitlines()[:5]
    else:
        report["recent_runs_error"] = runs_err

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

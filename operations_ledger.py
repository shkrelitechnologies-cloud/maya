#!/usr/bin/env python3
"""Append-only, IST-aware operations and publication ledger for Maya."""
from __future__ import annotations

import csv
import hashlib
import os
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Kolkata")
FIELDS = [
    "event_id", "run_id", "timestamp_ist", "ist_date", "event_type",
    "site_name", "domain", "target_url", "publication_url", "status",
    "verified", "publication_id", "evidence_url", "message",
]
SUMMARY_FIELDS = [
    "ist_date", "target", "verified_publications", "unique_verified_domains",
    "attempted", "pending_moderation", "prepared", "rejected", "failed",
    "blocked", "skipped", "remaining_to_target", "lifetime_verified_publications",
]


def now_ist() -> datetime:
    return datetime.now(timezone.utc).astimezone(TZ)


def _domain(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower().rstrip(".")
    except ValueError:
        return ""


def _read(path: Path, fields: list[str]) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _atomic_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def append_event(
    root: Path,
    *,
    event_type: str,
    status: str,
    site_name: str = "",
    target_url: str = "",
    publication_url: str = "",
    verified: bool = False,
    evidence_url: str = "",
    message: str = "",
    run_id: str | None = None,
    timestamp: datetime | None = None,
) -> str:
    """Append one observed event. Verified publications require public readback evidence."""
    stamp = (timestamp or now_ist()).astimezone(TZ)
    run_id = run_id or os.environ.get("GITHUB_RUN_ID", "local")
    if status == "published_verified":
        if not verified or not publication_url or not evidence_url:
            raise ValueError("A verified publication requires its public URL and evidence URL.")
        if not _domain(publication_url) or not _domain(evidence_url):
            raise ValueError("Publication and evidence URLs must be valid absolute URLs.")
    else:
        verified = False
    domain = _domain(publication_url or target_url)
    publication_id = (
        hashlib.sha256(("maya|" + publication_url.rstrip("/")).encode()).hexdigest()
        if status == "published_verified" else ""
    )
    identity = "|".join([
        run_id, stamp.isoformat(timespec="microseconds"), event_type, site_name,
        status, target_url, publication_url,
    ])
    event_id = hashlib.sha256(identity.encode()).hexdigest()
    path = root / "operations" / "OPERATIONS_LEDGER.csv"
    rows = _read(path, FIELDS)
    if not any(row.get("event_id") == event_id for row in rows):
        rows.append({
            "event_id": event_id, "run_id": run_id,
            "timestamp_ist": stamp.isoformat(timespec="seconds"),
            "ist_date": stamp.date().isoformat(), "event_type": event_type,
            "site_name": site_name, "domain": domain, "target_url": target_url,
            "publication_url": publication_url, "status": status,
            "verified": "true" if verified else "false",
            "publication_id": publication_id, "evidence_url": evidence_url,
            "message": message[:500],
        })
        _atomic_csv(path, FIELDS, rows)
    rebuild_summary(root)
    return event_id


def rebuild_summary(root: Path, target: int = 666) -> None:
    ledger = _read(root / "operations" / "OPERATIONS_LEDGER.csv", FIELDS)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in ledger:
        day = row.get("ist_date", "")
        if day:
            grouped[day].append(row)
    today = now_ist().date().isoformat()
    grouped.setdefault(today, [])

    lifetime_ids = {
        row.get("publication_id") or row.get("publication_url")
        for row in ledger
        if row.get("status") == "published_verified"
        and row.get("verified", "").lower() == "true"
        and row.get("publication_url")
    }
    out = []
    for day in sorted(grouped):
        rows = grouped[day]
        verified_rows = [
            row for row in rows
            if row.get("status") == "published_verified"
            and row.get("verified", "").lower() == "true"
            and row.get("publication_url")
        ]
        publication_ids = {
            row.get("publication_id") or row.get("publication_url")
            for row in verified_rows
        }
        domains = {_domain(row.get("publication_url", "")) for row in verified_rows}
        domains.discard("")
        counts = {key: sum(row.get("status") == key for row in rows) for key in
                  ("attempted", "pending_moderation", "rejected", "failed", "blocked", "skipped")}
        counts["prepared"] = sum(
            row.get("event_type") == "site_queue" and row.get("status") == "prepared"
            for row in rows
        )
        count = len(publication_ids)
        out.append({
            "ist_date": day, "target": target,
            "verified_publications": count, "unique_verified_domains": len(domains),
            **counts, "remaining_to_target": max(0, target - count),
            "lifetime_verified_publications": len(lifetime_ids),
        })
    _atomic_csv(root / "operations" / "DAILY_SUMMARY.csv", SUMMARY_FIELDS, out)

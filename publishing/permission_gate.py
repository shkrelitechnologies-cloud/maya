"""Fail-closed contract for Maya's future site-specific publishers.

This module deliberately contains no generic form submitter. A concrete adapter
must be written and reviewed for one named site before it can be registered.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse
import csv


REGISTRY_FIELDS = {
    "site_name", "domain", "submission_url", "rules_url", "language",
    "automation_allowed", "permitted_method", "daily_limit", "reviewed_on",
    "evidence_url", "adapter_module", "adapter_class", "notes",
}


@dataclass(frozen=True)
class SitePermission:
    site_name: str
    domain: str
    submission_url: str
    rules_url: str
    language: str
    permitted_method: str
    daily_limit: int
    reviewed_on: date
    evidence_url: str
    adapter_module: str
    adapter_class: str


class SiteAdapter(Protocol):
    """A site-specific adapter must implement these methods.

    It must not solve/bypass CAPTCHA, authenticate around a login wall, evade
    rate limits/moderation, create accounts, or submit unsolicited content.
    """

    def preflight(self, permission: SitePermission) -> tuple[bool, str]: ...
    def submit(self, permission: SitePermission, payload: dict) -> dict: ...
    def verify_publication(self, result: dict) -> tuple[bool, str, str]: ...


def _https_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    return parsed.scheme == "https" and bool(parsed.netloc)


def load_verified_permissions(path: Path, today: date | None = None) -> tuple[list[SitePermission], list[str]]:
    """Load only complete, recent, evidence-backed permissions.

    No row is eligible merely because a checkbox/cell says 'allowed'.
    """
    today = today or datetime.now().date()
    eligible: list[SitePermission] = []
    skipped: list[str] = []
    if not path.is_file():
        return [], ["sites.csv missing; publishing remains idle"]

    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = REGISTRY_FIELDS - set(reader.fieldnames or [])
        if missing:
            return [], ["sites.csv missing columns: " + ", ".join(sorted(missing))]
        for line, row in enumerate(reader, start=2):
            name = (row.get("site_name") or "").strip() or f"row {line}"
            try:
                if (row.get("automation_allowed") or "").strip().lower() != "yes":
                    raise ValueError("automation permission not explicitly confirmed")
                if not all(_https_url(row.get(k) or "") for k in ("submission_url", "rules_url", "evidence_url")):
                    raise ValueError("submission, rules and evidence URLs must be HTTPS")
                domain = (row.get("domain") or "").strip().lower()
                if not domain or urlparse(row["submission_url"]).hostname != domain:
                    raise ValueError("domain must exactly match submission URL host")
                reviewed = date.fromisoformat((row.get("reviewed_on") or "").strip())
                age = (today - reviewed).days
                if age < 0 or age > 30:
                    raise ValueError("permission review must be dated within the last 30 days")
                method = (row.get("permitted_method") or "").strip()
                if not method:
                    raise ValueError("permitted method is missing")
                limit = int(row.get("daily_limit") or "0")
                if limit < 1 or limit > 10:
                    raise ValueError("daily_limit must be between 1 and 10")
                module = (row.get("adapter_module") or "").strip()
                klass = (row.get("adapter_class") or "").strip()
                if not module.startswith("publishing.adapters.") or not klass:
                    raise ValueError("a dedicated publishing.adapters.* class is required")
                eligible.append(SitePermission(
                    site_name=name, domain=domain,
                    submission_url=row["submission_url"].strip(),
                    rules_url=row["rules_url"].strip(),
                    language=(row.get("language") or "").strip(),
                    permitted_method=method, daily_limit=limit,
                    reviewed_on=reviewed, evidence_url=row["evidence_url"].strip(),
                    adapter_module=module, adapter_class=klass,
                ))
            except (ValueError, TypeError) as exc:
                skipped.append(f"{name}: {exc}")
    return eligible, skipped

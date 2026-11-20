#!/usr/bin/env python3
"""Maya unattended maintenance runtime.

Validates assets, rotates images in prepared records, maintains an IST daily
ledger, discovers and assesses candidate opportunities in research-only mode,
and writes a health report. Publishing remains disabled until a site-specific
adapter is independently reviewed and explicitly permitted with verified
evidence.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import traceback
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from operations_ledger import append_event, rebuild_summary
from publishing.discovery import run_research_discovery
from publishing.permission_gate import load_verified_permissions

ROOT = Path(__file__).resolve().parent
TZ = ZoneInfo("Asia/Kolkata")
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
WALLET_KEYS = {"bitcoin", "ethereum", "solana"}


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def now_ist():
    return datetime.now(timezone.utc).astimezone(TZ)


def atomic_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        header = fields or ["site_name", "status"]
        path.write_text(",".join(header) + "\n", encoding="utf-8")
        return
    fieldnames = fields or list(dict.fromkeys(k for row in rows for k in row.keys()))
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _csv_cell(row.get(k, "")) for k in fieldnames})
    tmp.replace(path)


def _csv_cell(value):
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if value is None:
        return ""
    return str(value)


def _safe_slug(text: str, fallback: str = "candidate") -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", (text or "").strip().lower()).strip("-._")
    return slug[:80] or fallback


def _domain(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().rstrip(".")
    except ValueError:
        return ""


def _https_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return parsed.scheme == "https" and bool(parsed.netloc)


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
    permission_skips = []
    sites_path = ROOT / "sites.csv"
    if sites_path.exists():
        permissions, permission_skips = load_verified_permissions(sites_path, today=now_ist().date())
        eligible = [{
            "site_name": p.site_name,
            "submission_url": p.submission_url,
            "rules_url": p.rules_url,
            "language": p.language,
            "domain": p.domain,
            "permitted_method": p.permitted_method,
            "daily_limit": p.daily_limit,
            "evidence_url": p.evidence_url,
            "reviewed_on": p.reviewed_on.isoformat(),
            "adapter_module": p.adapter_module,
            "adapter_class": p.adapter_class,
        } for p in permissions]
        warnings.extend(permission_skips)
    else:
        warnings.append("sites.csv not found; no sites are eligible")

    return config, target, wallets, images, eligible, errors, warnings


def build_queue(wallets, images, eligible, day_key, rotation_cursor=0):
    if not images or not wallets:
        return []
    rows = []
    seen = set()
    for index, site in enumerate(eligible):
        key = (site.get("domain", ""), site.get("submission_url", ""), day_key)
        if key in seen:
            continue
        seen.add(key)
        image = images[(rotation_cursor + index) % len(images)]
        rows.append({
            "site_name": site.get("site_name", ""),
            "domain": site.get("domain", ""),
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


def load_discovery_candidates(config):
    """Read curated research-only candidates; never treats candidates as approved sites."""
    settings = config.get("site_discovery", {}) if isinstance(config, dict) else {}
    if not settings.get("enabled", False):
        return {"enabled": False, "mode": "disabled", "candidate_count": 0, "candidates": []}
    registry = ROOT / str(settings.get("candidate_registry", "discovery_candidates.csv"))
    required = {"candidate_name", "website", "official_rules_or_submission_url",
                "fit", "submission_type", "automation_permission", "status",
                "last_checked_ist", "notes"}
    if not registry.is_file():
        return {"enabled": True, "mode": "research_only", "candidate_count": 0,
                "candidates": [], "warning": "Discovery candidate registry missing"}
    with registry.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        if not required.issubset(fieldnames):
            return {"enabled": True, "mode": "research_only", "candidate_count": 0,
                    "candidates": [], "warning": "Discovery candidate registry missing required columns"}
        candidates = []
        for row in reader:
            status = (row.get("status") or "").strip() or "RESEARCH_ONLY"
            if status not in {"RESEARCH_ONLY", "NEEDS_REVIEW", "BLOCKED", "INELIGIBLE"}:
                status = "RESEARCH_ONLY"
            website = (row.get("website") or "").strip()
            domain = _domain(website)
            candidates.append({
                "candidate_name": (row.get("candidate_name") or "").strip(),
                "website": website,
                "domain": domain,
                "country_hint": (row.get("country_hint") or "global/unknown").strip() or "global/unknown",
                "language": (row.get("language") or "unknown").strip() or "unknown",
                "category": (row.get("category") or "curated_research").strip() or "curated_research",
                "official_rules_or_submission_url": (row.get("official_rules_or_submission_url") or "").strip(),
                "fit": (row.get("fit") or "").strip(),
                "submission_type": (row.get("submission_type") or "").strip(),
                "submission_method_hints": [s.strip() for s in (row.get("submission_method_hints") or row.get("submission_type") or "").split(";") if s.strip()] or ["manual_review"],
                "automation_permission": (row.get("automation_permission") or "NOT_VERIFIED").strip() or "NOT_VERIFIED",
                "eligibility_status": status,
                "status_reasons": [s.strip() for s in (row.get("status_reasons") or row.get("notes") or "").split(";") if s.strip()][:5],
                "status": status,
                "last_checked_ist": (row.get("last_checked_ist") or "").strip(),
                "notes": (row.get("notes") or "").strip(),
                "source": "curated_registry",
            })
    return {"enabled": True, "mode": "research_only",
            "candidate_count": len(candidates), "candidates": candidates}


def _load_web_leads(state_dir: Path) -> list[dict]:
    leads_path = state_dir / "discovery_leads.json"
    data = load_json(leads_path, [])
    return data if isinstance(data, list) else []


def _candidate_from_lead(lead: dict) -> dict | None:
    if not isinstance(lead, dict):
        return None
    url = str(lead.get("url", "")).strip()
    domain = _domain(url) or str(lead.get("domain", "")).strip().lower()
    if not url or not domain:
        return None
    rules = lead.get("rules_or_submission_links") or []
    if not isinstance(rules, list):
        rules = []
    methods = lead.get("submission_method_hints") or []
    if isinstance(methods, str):
        methods = [m.strip() for m in methods.split(";") if m.strip()]
    if not isinstance(methods, list) or not methods:
        methods = ["unknown_manual_review"]
    reasons = lead.get("status_reasons") or []
    if isinstance(reasons, str):
        reasons = [r.strip() for r in reasons.split(";") if r.strip()]
    if not isinstance(reasons, list):
        reasons = []
    status = str(lead.get("eligibility_status") or "research_only_needs_review")
    return {
        "candidate_name": str(lead.get("title") or lead.get("page_title") or domain)[:200],
        "website": url,
        "domain": domain,
        "country_hint": str(lead.get("country_hint") or "global/unknown"),
        "language": str(lead.get("language") or "unknown"),
        "category": str(lead.get("category") or "general_relevant"),
        "official_rules_or_submission_url": rules[0] if rules else "",
        "fit": "Web-discovered relevant lead; requires manual permission and eligibility review.",
        "submission_type": "; ".join(str(m) for m in methods[:4]),
        "submission_method_hints": [str(m) for m in methods[:6]],
        "automation_permission": str(lead.get("automation_permission") or "NOT_VERIFIED"),
        "eligibility_status": status,
        "status_reasons": [str(r) for r in reasons[:8]],
        "status": status,
        "last_checked_ist": "",
        "last_seen_utc": str(lead.get("last_seen_utc") or ""),
        "notes": "Auto-assessed from public page inspection only; no publishing permission granted.",
        "source": "web_discovery",
        "eligibility_evidence": lead.get("eligibility_evidence") or {},
        "submission_links": (lead.get("submission_links") or [])[:10] if isinstance(lead.get("submission_links"), list) else [],
    }


def build_candidate_review_queue(curated: list[dict], leads: list[dict], limit: int = 500):
    by_url = {}
    for item in curated + [c for c in (_candidate_from_lead(l) for l in leads) if c]:
        url = str(item.get("website") or item.get("url") or "").strip()
        domain = _domain(url)
        if not url or not domain:
            continue
        key = url.rstrip("/")
        record = dict(item)
        record["website"] = url
        record["domain"] = domain
        record.setdefault("verification_status", "UNVERIFIED_RESEARCH_LEAD")
        record.setdefault("automation_permission", "NOT_VERIFIED")
        record["review_only"] = True
        record["approved_for_publishing"] = False
        prev = by_url.get(key)
        if not prev:
            by_url[key] = record
            continue
        merged = dict(prev)
        for k, v in record.items():
            if v in (None, "", [], {}):
                continue
            if k in ("candidate_name", "fit", "notes") and prev.get("source") == "curated_registry" and merged.get(k):
                continue
            merged[k] = v
        if prev.get("source") == "curated_registry" and record.get("source") == "web_discovery":
            merged["source"] = "curated_registry+web_discovery"
        elif prev.get("source") != "curated_registry":
            merged["source"] = record.get("source", merged.get("source", "unknown"))
        by_url[key] = merged
    queue = list(by_url.values())
    queue.sort(key=lambda x: (str(x.get("eligibility_status", "")), str(x.get("domain", "")), str(x.get("website", ""))))
    return queue[: max(1, int(limit))]


def generate_review_scaffolding(queue: list[dict], state_dir: Path):
    assess_dir = state_dir / "candidate_assessments"
    scaffold_dir = state_dir / "scaffolding" / "drafts"
    assess_dir.mkdir(parents=True, exist_ok=True)
    scaffold_dir.mkdir(parents=True, exist_ok=True)
    generated = {"assessments": 0, "scaffolds": 0, "items": []}
    for item in queue:
        domain = item.get("domain") or _domain(item.get("website", ""))
        if not domain:
            continue
        slug = _safe_slug(domain)
        methods = item.get("submission_method_hints") or []
        reasons = item.get("status_reasons") or []
        evidence = item.get("eligibility_evidence") or {}
        rules = [item.get("official_rules_or_submission_url")] if item.get("official_rules_or_submission_url") else []
        if isinstance(evidence, dict):
            rules += [u for u in (evidence.get("official_rules_or_submission_urls") or []) if isinstance(u, str)]
        rules = [u for u in dict.fromkeys([r for r in rules if isinstance(r, str) and r.strip()])][:10]
        assessment = {
            "review_only": True,
            "approved_for_publishing": False,
            "candidate_name": item.get("candidate_name", ""),
            "website": item.get("website", ""),
            "domain": domain,
            "category": item.get("category", ""),
            "country_hint": item.get("country_hint", ""),
            "language": item.get("language", ""),
            "submission_method_hints": methods,
            "eligibility_status": item.get("eligibility_status", ""),
            "status_reasons": reasons,
            "automation_permission": item.get("automation_permission", "NOT_VERIFIED"),
            "official_rules_or_submission_urls": rules,
            "evidence": evidence,
            "next_required_steps": [
                "Confirm current official rules explicitly permit the exact automated image+wallet payload.",
                "Obtain and record dated HTTPS permission evidence in sites.csv (draft only; not approval).",
                "Implement and test a dedicated publishing.adapters.<site> adapter only after permission is verified.",
                "Require public URL + readback/evidence before any verified publication count.",
            ],
            "notes": "Draft eligibility assessment generated from public/research data. Not permission, not an adapter, not a publication.",
        }
        atomic_json(assess_dir / f"{slug}.json", assessment)
        generated["assessments"] += 1
        clearly_supported = (
            item.get("eligibility_status") in {"candidate_needs_permission_review", "restricted_needs_permission_review"}
            and any(m in methods for m in ("web_form_candidate", "external_submission_link", "official_api_candidate", "mailto_contact"))
            and bool(rules or _https_url(item.get("website", "")))
            and not any(r == "challenge_or_access_control_observed" for r in reasons)
        )
        if clearly_supported:
            scaffold = {
                "draft_only": True,
                "not_registered_adapter": True,
                "target_domain": domain,
                "candidate_url": item.get("website", ""),
                "suggested_permission_row_template": {
                    "site_name": item.get("candidate_name", domain),
                    "domain": domain,
                    "submission_url": item.get("website", ""),
                    "rules_url": rules[0] if rules else "",
                    "language": item.get("language", "unknown"),
                    "fundraising_allowed": "REVIEW_REQUIRED",
                    "automation_allowed": "REVIEW_REQUIRED",
                    "permitted_method": (methods[0] if methods else "REVIEW_REQUIRED"),
                    "daily_limit": "1",
                    "reviewed_on": "",
                    "evidence_url": rules[0] if rules else "",
                    "adapter_module": f"publishing.adapters.draft_{_safe_slug(domain, 'site').replace('-', '_')}",
                    "adapter_class": "DraftAdapterReviewOnly",
                    "notes": "DRAFT TEMPLATE ONLY. Do not register in sites.csv without verified permission and a tested dedicated adapter.",
                },
                "suggested_adapter_contract_checks": [
                    "preflight: verify HTTPS host, expected page/form markers, no CAPTCHA/login/payment barrier, and current permission evidence",
                    "submit: only exact image+wallet payload if explicitly permitted; stop on ambiguity or controls",
                    "verify_publication: require durable public URL and separate readback/evidence URL",
                ],
                "evidence_urls_for_review": rules,
                "status_reasons": reasons,
            }
            atomic_json(scaffold_dir / f"{slug}.json", scaffold)
            generated["scaffolds"] += 1
            generated["items"].append({"domain": domain, "scaffold": f"state/scaffolding/drafts/{slug}.json"})
    return generated


def build_candidate_pipeline(config, state_dir: Path):
    discovery_meta = load_discovery_candidates(config)
    discovery_meta["web_search"] = run_research_discovery(config.get("site_discovery", {}), state_dir)
    curated = discovery_meta.get("candidates", [])
    leads = _load_web_leads(state_dir)
    settings = config.get("site_discovery", {}) if isinstance(config, dict) else {}
    queue_limit = max(10, min(1000, int(settings.get("max_stored_leads", 500))))
    queue = build_candidate_review_queue(curated, leads, limit=queue_limit)

    atomic_json(state_dir / "candidate_review_queue.json", {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "research_only",
        "approved_for_publishing": False,
        "count": len(queue),
        "candidates": queue,
    })
    csv_rows = []
    for item in queue:
        csv_rows.append({
            "candidate_name": item.get("candidate_name", ""),
            "website": item.get("website", ""),
            "domain": item.get("domain", ""),
            "category": item.get("category", ""),
            "country_hint": item.get("country_hint", ""),
            "language": item.get("language", ""),
            "submission_method_hints": item.get("submission_method_hints", []),
            "eligibility_status": item.get("eligibility_status", ""),
            "status_reasons": item.get("status_reasons", []),
            "automation_permission": item.get("automation_permission", "NOT_VERIFIED"),
            "official_rules_or_submission_url": item.get("official_rules_or_submission_url", ""),
            "source": item.get("source", ""),
            "review_only": "true",
        })
    write_csv(state_dir / "candidate_review_queue.csv", csv_rows, fields=[
        "candidate_name", "website", "domain", "category", "country_hint", "language",
        "submission_method_hints", "eligibility_status", "status_reasons",
        "automation_permission", "official_rules_or_submission_url", "source", "review_only",
    ])

    scaffolding = generate_review_scaffolding(queue, state_dir)
    status_counts = {}
    for item in queue:
        status = str(item.get("eligibility_status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    discovery_meta["candidate_review_queue"] = {
        "count": len(queue),
        "status_counts": status_counts,
        "json_path": "state/candidate_review_queue.json",
        "csv_path": "state/candidate_review_queue.csv",
        "assessment_records": scaffolding["assessments"],
        "draft_scaffolds_generated": scaffolding["scaffolds"],
        "draft_scaffold_items": scaffolding["items"][:25],
    }
    return discovery_meta


def main():
    stamp = now_ist()
    day_key = stamp.strftime("%Y-%m-%d")
    state_dir = ROOT / "state"
    state_path = state_dir / "daily_state.json"
    report_path = state_dir / "health.json"
    state_dir.mkdir(parents=True, exist_ok=True)

    try:
        append_event(ROOT, event_type="run", status="run_started",
                     message="Maya maintenance run started; publishing remains disabled.")
        config, target, wallets, images, eligible, errors, warnings = validate()
        discovery = build_candidate_pipeline(config, state_dir)
        if discovery.get("warning"):
            warnings.append(discovery["warning"])
        ws = discovery.get("web_search") or {}
        if isinstance(ws, dict):
            for err in ws.get("errors", [])[:10]:
                warnings.append(f"discovery: {err}")

        state = load_json(state_path, {})
        if not isinstance(state, dict):
            errors.append("daily_state.json is not a JSON object; fail-closed to fresh runtime-owned state")
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

        for key in ("verified_successes", "failed", "lifetime_verified_successes", "image_rotation_cursor"):
            try:
                state[key] = max(0, int(state.get(key, 0)))
            except (TypeError, ValueError):
                errors.append(f"Invalid {key} in state; fail-closed")
                state[key] = 0

        state["target"] = target
        state["timezone"] = "Asia/Kolkata"
        state["last_heartbeat_ist"] = stamp.isoformat()

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
                         message="No eligible, permissioned sites were available for queue preparation.")

        ledger_summary = rebuild_summary(ROOT, target)
        state["verified_successes"] = max(0, int(ledger_summary.get("verified_publications", 0)))
        state["lifetime_verified_successes"] = max(
            0, int(ledger_summary.get("lifetime_verified_publications", 0))
        )
        state["remaining_to_target"] = max(0, target - state["verified_successes"])

        write_csv(ROOT / "submission_queue.csv", queue, fields=[
            "site_name", "domain", "submission_url", "rules_url", "language", "image_path",
            "image_sha256", "bitcoin", "ethereum", "solana", "status", "day_ist",
        ])
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
            "site_discovery": discovery,
            "permission_gate_skips": warnings,
            "prepared_records": len(queue),
            "published_by_this_runtime": 0,
            "errors": errors,
            "warnings": warnings,
            "publishing": "DISABLED: fail-closed. No verified permission + dedicated adapter + public readback evidence; research/review pipeline remains active.",
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

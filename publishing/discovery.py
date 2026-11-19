"""Free, research-only web discovery for Maya.

Search results are unverified leads, never permission to publish. This module
uses the public Bing RSS search endpoint; if it blocks or fails, Maya records
the issue and continues its maintenance run without bypassing the block.
"""
from __future__ import annotations

import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen


def parse_rss(xml_bytes: bytes, query: str, seen_at: str, limit: int = 8) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    found = []
    for item in root.findall(".//item")[:limit]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        description = (item.findtext("description") or "").strip()
        if not title or not link:
            continue
        relevance_text = (title + " " + description).lower()
        relevant_terms = ("fundrais", "crowdfund", "donat", "charit", "nonprofit",
                          "non-profit", "ngo", "campaign", "giving", "social cause",
                          "submit a fundraiser", "funding appeal")
        if not any(term in relevance_text for term in relevant_terms):
            continue
        parsed = urlparse(link)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            continue
        clean = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", parsed.query, ""))
        found.append({
            "title": title[:300],
            "url": clean[:2000],
            "domain": parsed.hostname.lower(),
            "source_query": query[:300],
            "first_seen_utc": seen_at,
            "last_seen_utc": seen_at,
            "verification_status": "UNVERIFIED_RESEARCH_LEAD",
            "snippet": re.sub(r"\\s+", " ", description)[:700],
            "automation_permission": "NOT_VERIFIED",
        })
    return found


def merge_leads(existing: list[dict], discovered: list[dict], limit: int = 100) -> list[dict]:
    by_url = {}
    relevant_terms = ("fundrais", "crowdfund", "donat", "charit", "nonprofit",
                      "non-profit", "ngo", "campaign", "giving", "social cause")
    for lead in existing + discovered:
        url = lead.get("url", "").strip()
        relevance_text = (lead.get("title", "") + " " + lead.get("snippet", "")).lower()
        if not url or not any(term in relevance_text for term in relevant_terms):
            continue
        if url in by_url:
            by_url[url]["last_seen_utc"] = lead.get("last_seen_utc", by_url[url].get("last_seen_utc", ""))
        else:
            by_url[url] = lead
    return list(by_url.values())[-limit:]


def run_research_discovery(settings: dict, state_dir: Path) -> dict:
    if not settings.get("enabled") or settings.get("mode") != "research_only":
        return {"enabled": False, "queries_completed": 0, "lead_count": 0, "errors": []}

    state_dir.mkdir(parents=True, exist_ok=True)
    leads_path = state_dir / "discovery_leads.json"
    try:
        existing = json.loads(leads_path.read_text(encoding="utf-8")) if leads_path.exists() else []
        if not isinstance(existing, list):
            existing = []
    except (OSError, json.JSONDecodeError):
        existing = []

    queries = settings.get("queries", [])
    timeout = max(2, min(20, int(settings.get("search_timeout_seconds", 8))))
    per_query = max(1, min(20, int(settings.get("max_results_per_query", 8))))
    max_leads = max(10, min(500, int(settings.get("max_stored_leads", 100))))
    now = datetime.now(timezone.utc).isoformat()
    discovered = []
    errors = []
    completed = 0

    for query in queries:
        endpoint = "https://www.bing.com/search?" + urlencode({"q": query, "format": "rss"})
        request = Request(endpoint, headers={"User-Agent": "MayaResearchBot/1.0 (+research-only; no submissions)"})
        try:
            with urlopen(request, timeout=timeout) as response:
                if response.status != 200:
                    errors.append(f"Search source returned HTTP {response.status}; query skipped")
                    continue
                payload = response.read(2_000_000)
            discovered.extend(parse_rss(payload, query, now, per_query))
            completed += 1
        except (HTTPError, URLError, TimeoutError, OSError, ET.ParseError) as exc:
            # Search-source failures are non-fatal; no CAPTCHA or access-control bypass.
            errors.append(f"Search query skipped ({type(exc).__name__})")
        time.sleep(0.2)

    merged = merge_leads(existing, discovered, max_leads)
    temp = leads_path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\\n", encoding="utf-8")
    temp.replace(leads_path)
    return {
        "enabled": True,
        "provider": "bing_rss",
        "mode": "research_only",
        "queries_configured": len(queries),
        "queries_completed": completed,
        "new_leads_this_run": len(discovered),
        "lead_count": len(merged),
        "errors": errors,
        "storage": "state/discovery_leads.json",
    }

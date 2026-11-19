"""Browser-driven, research-only website discovery for Maya.

Uses Playwright Chromium to search public search-engine result pages, open
candidate websites, and inspect publicly accessible pages. Search challenges,
CAPTCHAs, login walls, and access-denied responses are skipped without bypass.
A discovered page is never treated as permission to publish.
"""
from __future__ import annotations

import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus, urlparse, urlunparse


RELEVANT_TERMS = (
    "fundrais", "crowdfund", "donat", "charit", "nonprofit", "non-profit",
    "ngo", "campaign", "giving", "social cause", "funding appeal",
)
BLOCK_MARKERS = (
    "captcha", "verify you are human", "unusual traffic", "access denied",
    "automated requests", "security check", "robot check", "sign in to continue",
)
SEARCH_ENGINES = {
    "duckduckgo": "https://html.duckduckgo.com/html/?q={query}",
    "bing": "https://www.bing.com/search?q={query}",
    "google": "https://www.google.com/search?q={query}",
}


def _clean_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return ""
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", parsed.query, ""))


def _is_relevant(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in RELEVANT_TERMS)


def _blocked(text: str, title: str = "") -> bool:
    sample = (title + " " + text[:12000]).lower()
    return any(marker in sample for marker in BLOCK_MARKERS)


def parse_rss(xml_bytes: bytes, query: str, seen_at: str, limit: int = 8) -> list[dict]:
    """Compatibility parser retained for unit tests and offline fixtures."""
    root = ET.fromstring(xml_bytes)
    found = []
    for item in root.findall(".//item")[:limit]:
        title = (item.findtext("title") or "").strip()
        link = _clean_url((item.findtext("link") or "").strip())
        description = (item.findtext("description") or "").strip()
        if not title or not link or not _is_relevant(title + " " + description):
            continue
        found.append({
            "title": title[:300], "url": link[:2000],
            "domain": urlparse(link).hostname.lower(),
            "source_query": query[:300], "first_seen_utc": seen_at,
            "last_seen_utc": seen_at, "verification_status": "UNVERIFIED_RESEARCH_LEAD",
            "snippet": re.sub(r"\\s+", " ", description)[:700],
            "automation_permission": "NOT_VERIFIED",
        })
    return found


def merge_leads(existing: list[dict], discovered: list[dict], limit: int = 100) -> list[dict]:
    by_url = {}
    for lead in existing + discovered:
        url = _clean_url(lead.get("url", "").strip())
        relevance_text = lead.get("title", "") + " " + lead.get("snippet", "")
        if not url or not _is_relevant(relevance_text):
            continue
        if url in by_url:
            by_url[url]["last_seen_utc"] = lead.get("last_seen_utc", by_url[url].get("last_seen_utc", ""))
        else:
            item = dict(lead)
            item["url"] = url
            by_url[url] = item
    return list(by_url.values())[-limit:]


def _search_links(page, engine: str, query: str, timeout_ms: int) -> tuple[list[dict], str | None]:
    url = SEARCH_ENGINES[engine].format(query=quote_plus(query))
    try:
        response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(500)
        title = page.title()
        body = page.locator("body").inner_text(timeout=3000)
        if (response and response.status in (401, 403, 429)) or _blocked(body, title):
            return [], f"{engine}: search page blocked/challenged; skipped"
        links = page.locator("a[href]").evaluate_all(
            """els => els.map(a => ({title:(a.innerText||a.getAttribute('aria-label')||'').trim(),
            url:a.href, snippet:(a.parentElement?.innerText||'').trim()}))"""
        )
        results = []
        for item in links:
            clean = _clean_url(item.get("url", ""))
            host = urlparse(clean).hostname or ""
            if not clean or host.endswith(("duckduckgo.com", "bing.com", "google.com")):
                continue
            title_text = item.get("title", "")
            snippet = item.get("snippet", "")
            if title_text:
                results.append({"url": clean, "title": title_text[:300], "snippet": snippet[:700]})
        return results, None
    except Exception as exc:
        return [], f"{engine}: page/query skipped ({type(exc).__name__})"


def _inspect_candidate(page, candidate: dict, query: str, seen_at: str, timeout_ms: int) -> dict | None:
    try:
        response = page.goto(candidate["url"], wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(250)
        title = page.title()[:300]
        body = page.locator("body").inner_text(timeout=3000)
        if (response and response.status in (401, 403, 429)) or _blocked(body, title):
            return None
        description = page.locator('meta[name="description"]').get_attribute("content", timeout=1000) or ""
        combined = " ".join((candidate.get("title", ""), title, description, body[:5000]))
        if not _is_relevant(combined):
            return None
        links = page.locator("a[href]").evaluate_all(
            """els => els.map(a => ({text:(a.innerText||'').trim(),url:a.href}))"""
        )
        rule_links = [
            x["url"] for x in links
            if x.get("url", "").startswith(("http://", "https://"))
            and any(word in (x.get("text", "") + " " + x.get("url", "")).lower()
                    for word in ("term", "guideline", "submit", "policy", "faq", "eligib", "fundrais"))
        ][:12]
        final_url = _clean_url(page.url) or candidate["url"]
        return {
            "title": title or candidate.get("title", "")[:300],
            "url": final_url,
            "domain": urlparse(final_url).hostname.lower(),
            "source_query": query[:300],
            "first_seen_utc": seen_at,
            "last_seen_utc": seen_at,
            "snippet": re.sub(r"\\s+", " ", description or body[:700])[:700],
            "official_page_inspected": True,
            "rules_or_submission_links": rule_links,
            "verification_status": "UNVERIFIED_RESEARCH_LEAD",
            "automation_permission": "NOT_VERIFIED",
        }
    except Exception:
        return None


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
    engines = [x for x in settings.get("search_engines", list(SEARCH_ENGINES)) if x in SEARCH_ENGINES]
    timeout_ms = max(3000, min(20000, int(settings.get("browser_timeout_seconds", 12)) * 1000))
    max_pages = max(1, min(40, int(settings.get("max_pages_per_run", 18))))
    max_leads = max(10, min(500, int(settings.get("max_stored_leads", 150))))
    seen_at = datetime.now(timezone.utc).isoformat()
    discovered, errors, inspected = [], [], 0
    completed = 0
    visited = set()

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
                locale="en-US",
            )
            search_page = context.new_page()
            inspect_page = context.new_page()
            for query in queries:
                query_results = []
                for engine in engines:
                    results, error = _search_links(search_page, engine, query, timeout_ms)
                    if error:
                        errors.append(error)
                    else:
                        completed += 1
                    query_results.extend(results)
                # Visit distinct result pages in relevance order, bounded per run.
                query_results.sort(
                    key=lambda x: (not _is_relevant(x.get("title", "") + " " + x.get("snippet", "")))
                )
                for candidate in query_results:
                    url = candidate["url"]
                    if url in visited or inspected >= max_pages:
                        continue
                    visited.add(url)
                    inspected += 1
                    lead = _inspect_candidate(inspect_page, candidate, query, seen_at, timeout_ms)
                    if lead:
                        discovered.append(lead)
                if inspected >= max_pages:
                    break
            browser.close()
    except Exception as exc:
        errors.append(f"Browser discovery unavailable ({type(exc).__name__}); no fallback scraping used")

    merged = merge_leads(existing, discovered, max_leads)
    temp = leads_path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\\n", encoding="utf-8")
    temp.replace(leads_path)
    return {
        "enabled": True, "provider": "playwright_chromium",
        "mode": "research_only", "search_engines": engines,
        "queries_configured": len(queries), "search_pages_completed": completed,
        "candidate_pages_inspected": inspected, "new_relevant_leads_this_run": len(discovered),
        "lead_count": len(merged), "errors": errors,
        "storage": "state/discovery_leads.json",
    }

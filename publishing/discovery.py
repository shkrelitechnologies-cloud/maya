"""Browser-driven, research-only website discovery for Maya.

Uses Playwright Chromium to search public search-engine result pages, open
candidate websites, and inspect publicly accessible pages. Search challenges,
CAPTCHAs, login walls, and access-denied responses are skipped without bypass.
A discovered page is never treated as permission to publish.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus, urlparse, urlunparse


RELEVANT_TERMS = (
    "fundrais", "crowdfund", "donat", "charit", "nonprofit", "non-profit",
    "ngo", "campaign", "giving", "social cause", "funding appeal", "cryptocurrency",
    "crypto donation", "bitcoin", "ethereum", "solana", "wallet", "digital asset", "web3",
    "submit", "submission", "add url", "suggest site", "directory", "listing",
    "募捐", "捐款", "公益", "募金", "寄付", "기부", "모금", "donación", "donativo",
    "collecte", "spende", "doação", "raccolta", "تبرع", "दान", "দান", "donasi",
    "сбор", "пожертв", "bağış", "bağis", "darowizn", "compaign", "inscription",
)
BLOCK_MARKERS = (
    "captcha", "verify you are human", "unusual traffic", "access denied",
    "automated requests", "security check", "robot check", "sign in to continue",
    "cloudflare", "are you a robot", "checking your browser",
)
LOGIN_MARKERS = (
    "sign in", "log in", "login", "create account", "register", "sign up",
)
PAYMENT_MARKERS = (
    "payment required", "subscription", "pricing plan", "pay to submit", "checkout",
)
SUBMIT_HINTS = (
    "submit", "add url", "add site", "suggest", "register", "apply", "post", "publish",
    "listing", "directory", "campaign", "fundrais", "donat", "contact", "form",
)
RULE_HINTS = (
    "term", "policy", "guideline", "rule", "faq", "eligib", "legal", "privacy",
    "submission", "how to", "help", "about",
)
SEARCH_ENGINES = {
    "duckduckgo": "https://html.duckduckgo.com/html/?q={query}",
    "bing": "https://www.bing.com/search?q={query}",
    "google": "https://www.google.com/search?q={query}",
    "mojeek": "https://www.mojeek.com/search?q={query}",
    "yahoo": "https://search.yahoo.com/search?p={query}",
    "startpage": "https://www.startpage.com/sp/search?query={query}",
    "qwant": "https://www.qwant.com/?q={query}",
    "brave": "https://search.brave.com/search?q={query}",
    "yandex": "https://yandex.com/search/?text={query}",
}
TLD_COUNTRY = {
    "in": "IN", "uk": "GB", "au": "AU", "ca": "CA", "de": "DE", "fr": "FR",
    "es": "ES", "it": "IT", "nl": "NL", "br": "BR", "jp": "JP", "kr": "KR",
    "cn": "CN", "sg": "SG", "ae": "AE", "za": "ZA", "ng": "NG", "ke": "KE",
    "id": "ID", "ph": "PH", "vn": "VN", "th": "TH", "mx": "MX", "ar": "AR",
    "ch": "CH", "se": "SE", "no": "NO", "pl": "PL", "tr": "TR", "ru": "RU",
    "ua": "UA", "il": "IL", "nz": "NZ", "ie": "IE", "pt": "PT", "be": "BE",
}


def _clean_url(url: str) -> str:
    try:
        parsed = urlparse(url)
    except ValueError:
        return ""
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return ""
    host = parsed.hostname.lower().rstrip(".")
    path = parsed.path or ""
    return urlunparse((parsed.scheme, host, path, "", parsed.query, ""))


def _domain(url: str) -> str:
    return (urlparse(url).hostname or "").lower().rstrip(".")


def _is_relevant(text: str) -> bool:
    lowered = (text or "").lower()
    return any(term in lowered for term in RELEVANT_TERMS)


def _blocked(text: str, title: str = "") -> bool:
    sample = ((title or "") + " " + (text or "")[:12000]).lower()
    return any(marker in sample for marker in BLOCK_MARKERS)


def _detect_language(html_lang: str, title: str, body: str) -> str:
    lang = (html_lang or "").strip().lower().replace("_", "-")
    if lang:
        return lang.split("-")[0][:8]
    sample = f"{title} {body[:1200]}"
    if re.search(r"[\u4e00-\u9fff]", sample):
        return "zh"
    if re.search(r"[\u3040-\u30ff]", sample):
        return "ja"
    if re.search(r"[\uac00-\ud7af]", sample):
        return "ko"
    if re.search(r"[\u0600-\u06ff]", sample):
        return "ar"
    if re.search(r"[\u0900-\u097f]", sample):
        return "hi"
    if re.search(r"[\u0980-\u09ff]", sample):
        return "bn"
    if re.search(r"[\u0400-\u04ff]", sample):
        return "ru"
    return "unknown"


def _country_hint(domain: str) -> str:
    parts = [p for p in (domain or "").lower().split(".") if p]
    if len(parts) >= 2 and parts[-1] in TLD_COUNTRY:
        return TLD_COUNTRY[parts[-1]]
    if len(parts) >= 3 and parts[-2] in ("co", "com", "org", "ac", "gov", "edu") and parts[-1] in TLD_COUNTRY:
        return TLD_COUNTRY[parts[-1]]
    return "global/unknown"


def _categorize(text: str, url: str) -> str:
    sample = f"{url} {text}".lower()
    if any(k in sample for k in ("directory", "add url", "submit site", "suggest", "link exchange")):
        return "directory_or_listing"
    if any(k in sample for k in ("crowdfund", "fundraiser", "campaign platform", "gofund", "donation platform")):
        return "fundraising_platform"
    if any(k in sample for k in ("nonprofit", "ngo", "charity", "foundation")):
        return "nonprofit_or_charity"
    if any(k in sample for k in ("crypto", "bitcoin", "ethereum", "solana", "wallet", "web3")):
        return "crypto_related"
    return "general_relevant"


def _detect_submission_methods(body: str, links: list[dict], forms_count: int) -> list[str]:
    methods = set()
    sample = (body or "")[:6000].lower()
    for item in links or []:
        text = ((item.get("text") or "") + " " + (item.get("url") or "")).lower()
        href = (item.get("url") or "").lower()
        if href.startswith("mailto:"):
            methods.add("mailto_contact")
        if "api" in text or "/developers" in href or "/docs/api" in href:
            methods.add("official_api_candidate")
        if any(k in text for k in SUBMIT_HINTS) and href.startswith(("http://", "https://")):
            methods.add("external_submission_link")
    if forms_count > 0 and any(k in sample for k in SUBMIT_HINTS):
        methods.add("web_form_candidate")
    if not methods and any(k in sample for k in ("contact us", "contact", "email")):
        methods.add("contact_page_only")
    if not methods:
        methods.add("unknown_manual_review")
    return sorted(methods)


def _eligibility_assessment(title: str, body: str, forms_count: int, submission_methods: list[str]) -> tuple[str, list[str]]:
    sample = f"{title} {body[:8000]}".lower()
    reasons = []
    if _blocked(sample, title):
        reasons.append("challenge_or_access_control_observed")
        return "blocked_needs_manual_review", reasons
    if any(k in sample for k in LOGIN_MARKERS):
        reasons.append("login_or_account_likely_required")
    if any(k in sample for k in PAYMENT_MARKERS):
        reasons.append("payment_or_subscription_may_be_required")
    if forms_count > 0:
        reasons.append("form_detected_public_page")
    if "official_api_candidate" in submission_methods:
        reasons.append("possible_api_or_developer_docs")
    if "mailto_contact" in submission_methods:
        reasons.append("contact_channel_detected")
    if not reasons:
        reasons.append("insufficient_public_evidence")
    status = "research_only_needs_review"
    if "challenge_or_access_control_observed" in reasons:
        status = "blocked_needs_manual_review"
    elif "login_or_account_likely_required" in reasons or "payment_or_subscription_may_be_required" in reasons:
        status = "restricted_needs_permission_review"
    elif "form_detected_public_page" in reasons or "external_submission_link" in submission_methods:
        status = "candidate_needs_permission_review"
    return status, reasons


def parse_rss(xml_bytes: bytes, query: str, seen_at: str, limit: int = 8) -> list[dict]:
    """Compatibility parser retained for unit tests and offline fixtures."""
    root = ET.fromstring(xml_bytes)
    found = []
    for item in root.findall(".//item")[:limit]:
        title = (item.findtext("title") or "").strip()
        link = _clean_url((item.findtext("link") or "").strip())
        description = re.sub(r"\s+", " ", (item.findtext("description") or "").strip())
        if not title or not link or not _is_relevant(title + " " + description):
            continue
        domain = _domain(link)
        found.append({
            "title": title[:300], "url": link[:2000],
            "domain": domain,
            "country_hint": _country_hint(domain),
            "language": _detect_language("", title, description),
            "category": _categorize(title + " " + description, link),
            "source_query": query[:300], "first_seen_utc": seen_at,
            "last_seen_utc": seen_at, "verification_status": "UNVERIFIED_RESEARCH_LEAD",
            "snippet": description[:700],
            "automation_permission": "NOT_VERIFIED",
            "submission_method_hints": ["unknown_manual_review"],
            "eligibility_status": "research_only_needs_review",
            "status_reasons": ["offline_fixture_uninspected"],
            "eligibility_evidence": {"source": "rss_fixture", "official_rules_or_submission_urls": []},
        })
    return found


def merge_leads(existing: list[dict], discovered: list[dict], limit: int = 100) -> list[dict]:
    by_url = {}
    for lead in existing + discovered:
        if not isinstance(lead, dict):
            continue
        url = _clean_url(str(lead.get("url", "")).strip())
        relevance_text = str(lead.get("title", "")) + " " + str(lead.get("snippet", ""))
        if not url or not _is_relevant(relevance_text):
            continue
        domain = _domain(url)
        normalized = dict(lead)
        normalized["url"] = url
        normalized["domain"] = normalized.get("domain") or domain
        normalized.setdefault("country_hint", _country_hint(domain))
        normalized.setdefault("language", _detect_language("", str(lead.get("title", "")), str(lead.get("snippet", ""))))
        normalized.setdefault("category", _categorize(relevance_text, url))
        normalized.setdefault("verification_status", "UNVERIFIED_RESEARCH_LEAD")
        normalized.setdefault("automation_permission", "NOT_VERIFIED")
        normalized.setdefault("submission_method_hints", ["unknown_manual_review"])
        normalized.setdefault("eligibility_status", "research_only_needs_review")
        normalized.setdefault("status_reasons", [])
        normalized.setdefault("eligibility_evidence", {})
        if url in by_url:
            merged_item = by_url[url]
            merged_item["last_seen_utc"] = normalized.get("last_seen_utc", merged_item.get("last_seen_utc", ""))
            if normalized.get("first_seen_utc") and not merged_item.get("first_seen_utc"):
                merged_item["first_seen_utc"] = normalized["first_seen_utc"]
            for key in ("official_page_inspected", "rules_or_submission_links", "page_title", "meta_description",
                        "submission_method_hints", "eligibility_status", "status_reasons", "eligibility_evidence",
                        "category", "country_hint", "language", "http_status", "requires_login", "requires_captcha",
                        "requires_payment"):
                if normalized.get(key) not in (None, "", [], {}):
                    merged_item[key] = normalized[key]
            if normalized.get("snippet") and len(str(normalized.get("snippet", ""))) >= len(str(merged_item.get("snippet", ""))):
                merged_item["snippet"] = normalized["snippet"]
        else:
            by_url[url] = normalized
    items = list(by_url.values())
    items.sort(key=lambda x: (str(x.get("last_seen_utc", "")), str(x.get("url", ""))))
    return items[-max(1, int(limit)):]


_SEARCH_HOST_BLOCK = {
    "duckduckgo.com", "bing.com", "google.com", "mojeek.com", "startpage.com",
    "search.yahoo.com", "yahoo.com", "qwant.com", "brave.com", "yandex.com",
    "yandex.ru", "youtube.com", "facebook.com", "twitter.com", "x.com",
    "instagram.com", "linkedin.com", "wikipedia.org", "play.google.com",
    "apps.apple.com",
}


def _search_links(page, engine: str, query: str, timeout_ms: int) -> tuple[list[dict], str | None]:
    url = SEARCH_ENGINES[engine].format(query=quote_plus(query))
    try:
        response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(400)
        title = ""
        body = ""
        try:
            title = page.title() or ""
        except Exception:
            pass
        try:
            body = page.locator("body").inner_text(timeout=3000)
        except Exception:
            body = ""
        status = response.status if response else None
        if status in (401, 403, 429) or _blocked(body, title):
            return [], f"{engine}: search page blocked/challenged; skipped"
        links = page.locator("a[href]").evaluate_all(
            """els => els.map(a => ({title:(a.innerText||a.getAttribute('aria-label')||'').trim(),
            url:a.href, snippet:(a.parentElement?.innerText||'').trim()}))"""
        )
        results = []
        seen = set()
        for item in links or []:
            clean = _clean_url(str(item.get("url", "")))
            if not clean:
                continue
            host = (urlparse(clean).hostname or "").lower()
            if not host or any(host == b or host.endswith("." + b) for b in _SEARCH_HOST_BLOCK):
                continue
            if clean in seen:
                continue
            seen.add(clean)
            title_text = re.sub(r"\s+", " ", str(item.get("title", ""))).strip()[:300]
            snippet = re.sub(r"\s+", " ", str(item.get("snippet", ""))).strip()[:700]
            if not title_text and not snippet:
                continue
            results.append({"url": clean, "title": title_text, "snippet": snippet})
        return results, None
    except Exception as exc:
        return [], f"{engine}: page/query skipped ({type(exc).__name__})"


def _inspect_candidate(page, candidate: dict, query: str, seen_at: str, timeout_ms: int) -> dict | None:
    url = _clean_url(str(candidate.get("url", "")))
    if not url:
        return None
    try:
        response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(250)
        title = ""
        body = ""
        html_lang = ""
        try:
            title = (page.title() or "")[:300]
        except Exception:
            pass
        try:
            body = page.locator("body").inner_text(timeout=3000) or ""
        except Exception:
            body = ""
        try:
            html_lang = page.evaluate("() => document.documentElement.lang || ''") or ""
        except Exception:
            html_lang = ""
        status = response.status if response else None
        if status in (401, 403, 429) or _blocked(body, title):
            return None
        description = ""
        try:
            description = page.locator('meta[name="description"]').get_attribute("content", timeout=1000) or ""
        except Exception:
            description = ""
        description = re.sub(r"\s+", " ", description).strip()
        combined = " ".join((str(candidate.get("title", "")), title, description, body[:5000]))
        if not _is_relevant(combined):
            return None
        links = []
        try:
            links = page.locator("a[href]").evaluate_all(
                """els => els.map(a => ({text:(a.innerText||a.getAttribute('aria-label')||'').trim(),url:a.href}))"""
            ) or []
        except Exception:
            links = []
        forms_count = 0
        try:
            forms_count = int(page.locator("form").count())
        except Exception:
            forms_count = 0
        rule_links = []
        submit_links = []
        for item in links:
            href = _clean_url(str(item.get("url", "")))
            if not href:
                continue
            text = re.sub(r"\s+", " ", str(item.get("text", ""))).strip()
            blob = (text + " " + href).lower()
            if any(word in blob for word in RULE_HINTS):
                if href not in rule_links:
                    rule_links.append(href)
            if any(word in blob for word in SUBMIT_HINTS):
                if href not in submit_links:
                    submit_links.append(href)
        rule_links = rule_links[:12]
        submit_links = submit_links[:12]
        submission_methods = _detect_submission_methods(body, links, forms_count)
        eligibility_status, status_reasons = _eligibility_assessment(title, body, forms_count, submission_methods)
        final_url = _clean_url(page.url) or url
        domain = _domain(final_url)
        page_title = title or re.sub(r"\s+", " ", str(candidate.get("title", ""))).strip()[:300]
        snippet = description or re.sub(r"\s+", " ", body[:700]).strip()
        evidence = {
            "source": "playwright_browser_inspection",
            "inspected_url": final_url,
            "http_status": status,
            "official_rules_or_submission_urls": rule_links[:5],
            "submission_links": submit_links[:5],
            "form_count": forms_count,
            "notes": "Research-only public page inspection. No permission or automation eligibility is inferred as granted.",
        }
        lower_sample = f"{title} {body[:8000]}".lower()
        return {
            "title": page_title,
            "page_title": page_title,
            "meta_description": description[:700],
            "url": final_url,
            "domain": domain,
            "country_hint": _country_hint(domain),
            "language": _detect_language(html_lang, title, body),
            "category": _categorize(combined, final_url),
            "source_query": str(query)[:300],
            "first_seen_utc": seen_at,
            "last_seen_utc": seen_at,
            "snippet": snippet[:700],
            "official_page_inspected": True,
            "http_status": status,
            "rules_or_submission_links": rule_links,
            "submission_links": submit_links,
            "submission_method_hints": submission_methods,
            "eligibility_status": eligibility_status,
            "status_reasons": status_reasons,
            "eligibility_evidence": evidence,
            "requires_login": any(k in lower_sample for k in LOGIN_MARKERS),
            "requires_captcha": _blocked(body, title) or ("captcha" in lower_sample),
            "requires_payment": any(k in lower_sample for k in PAYMENT_MARKERS),
            "verification_status": "UNVERIFIED_RESEARCH_LEAD",
            "automation_permission": "NOT_VERIFIED",
        }
    except Exception:
        return None


def run_research_discovery(settings: dict, state_dir: Path) -> dict:
    if not settings.get("enabled") or settings.get("mode") != "research_only":
        return {"enabled": False, "mode": "disabled", "queries_completed": 0, "lead_count": 0, "errors": []}

    state_dir.mkdir(parents=True, exist_ok=True)
    leads_path = state_dir / "discovery_leads.json"
    try:
        existing = json.loads(leads_path.read_text(encoding="utf-8")) if leads_path.exists() else []
        if not isinstance(existing, list):
            existing = []
    except (OSError, json.JSONDecodeError):
        existing = []

    queries = [q for q in settings.get("queries", []) if isinstance(q, str) and q.strip()]
    configured_engines = settings.get("search_engines", list(SEARCH_ENGINES))
    engines = [x for x in configured_engines if x in SEARCH_ENGINES]
    if not engines:
        engines = list(SEARCH_ENGINES.keys())
    timeout_ms = max(3000, min(20000, int(settings.get("browser_timeout_seconds", 12)) * 1000))
    max_pages = max(1, min(80, int(settings.get("max_pages_per_run", 18))))
    max_leads = max(10, min(1000, int(settings.get("max_stored_leads", 150))))
    per_query_inspect = max(1, min(20, int(settings.get("max_inspections_per_query", 6))))
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
                if inspected >= max_pages:
                    break
                query_results = []
                for engine in engines:
                    results, error = _search_links(search_page, engine, query, timeout_ms)
                    if error:
                        errors.append(error)
                    else:
                        completed += 1
                    query_results.extend(results)
                deduped_query = []
                seen_query = set()
                for item in query_results:
                    u = item.get("url", "")
                    if u and u not in seen_query:
                        seen_query.add(u)
                        deduped_query.append(item)
                deduped_query.sort(
                    key=lambda x: (
                        0 if _is_relevant((x.get("title", "") or "") + " " + (x.get("snippet", "") or "")) else 1,
                        len(str(x.get("url", ""))),
                    )
                )
                inspected_for_query = 0
                for candidate in deduped_query:
                    if inspected >= max_pages or inspected_for_query >= per_query_inspect:
                        break
                    url = candidate.get("url", "")
                    if not url or url in visited:
                        continue
                    visited.add(url)
                    inspected += 1
                    inspected_for_query += 1
                    lead = _inspect_candidate(inspect_page, candidate, query, seen_at, timeout_ms)
                    if lead:
                        discovered.append(lead)
            browser.close()
    except Exception as exc:
        errors.append(f"Browser discovery unavailable ({type(exc).__name__}); no fallback scraping used")

    merged = merge_leads(existing, discovered, max_leads)
    temp = leads_path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(leads_path)
    # keep bounded unique errors for health readability
    uniq_errors = []
    for e in errors:
        if e not in uniq_errors:
            uniq_errors.append(e)
    return {
        "enabled": True,
        "provider": "playwright_chromium",
        "mode": "research_only",
        "search_engines": engines,
        "queries_configured": len(queries),
        "search_pages_completed": completed,
        "candidate_pages_inspected": inspected,
        "new_relevant_leads_this_run": len(discovered),
        "lead_count": len(merged),
        "errors": uniq_errors[:50],
        "storage": "state/discovery_leads.json",
    }

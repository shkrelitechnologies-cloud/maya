#!/usr/bin/env python3
"""Hourly Maya watchdog.

Checks the maintenance workflow through the GitHub Actions API. If the
maintenance workflow is disabled, attempts the documented enable action.
If no successful maintenance run completed in the last 45 minutes and no
run is active, dispatches one recovery run. It never edits campaign data,
code, wallet addresses, or site permissions.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = "https://api.github.com"
WORKFLOW = "maya-maintenance.yml"
REPORT = Path("state/watchdog.json")


def api_request(method, url, token, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "Maya-Repository-Watchdog",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        body = response.read()
        return json.loads(body) if body else {"http_status": response.status}


def main():
    token = os.environ.get("GITHUB_TOKEN", "")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    branch = os.environ.get("MAYA_BRANCH", "main")
    now = datetime.now(timezone.utc)
    result = {
        "checked_at_utc": now.isoformat(),
        "repository": repository,
        "workflow": WORKFLOW,
        "status": "unknown",
        "actions": [],
        "errors": [],
    }

    try:
        if not token or "/" not in repository:
            raise RuntimeError("GITHUB_TOKEN or GITHUB_REPOSITORY is unavailable")

        base = f"{API}/repos/{repository}/actions/workflows/{WORKFLOW}"
        workflow = api_request("GET", base, token)
        if workflow.get("state") != "active":
            api_request("PUT", base + "/enable", token)
            result["actions"].append("Re-enabled disabled maintenance workflow")
        else:
            result["actions"].append("Maintenance workflow is active")

        runs_url = f"{base}/runs?branch={branch}&per_page=20"
        runs = api_request("GET", runs_url, token).get("workflow_runs", [])
        active = [r for r in runs if r.get("status") in {"queued", "in_progress"}]
        successes = []
        for run in runs:
            if run.get("conclusion") != "success":
                continue
            stamp = run.get("updated_at") or run.get("completed_at") or run.get("created_at")
            if stamp:
                successes.append(datetime.fromisoformat(stamp.replace("Z", "+00:00")))

        last_success = max(successes) if successes else None
        age_minutes = (now - last_success).total_seconds() / 60 if last_success else None
        result["last_success_age_minutes"] = round(age_minutes, 1) if age_minutes is not None else None
        result["active_runs"] = len(active)

        if active:
            result["status"] = "healthy"
            result["actions"].append("A maintenance run is already active; no duplicate dispatch")
        elif last_success is None or age_minutes > 45:
            api_request("POST", base + "/dispatches", token, {"ref": branch})
            result["status"] = "recovery_dispatched"
            result["actions"].append("Dispatched one maintenance recovery run because the last success is stale")
        else:
            result["status"] = "healthy"
            result["actions"].append("Recent successful maintenance run found")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:2000]
        result["status"] = "blocked"
        result["errors"].append(f"GitHub API HTTP {exc.code}: {body}")
    except Exception as exc:
        result["status"] = "blocked"
        result["errors"].append(f"{type(exc).__name__}: {exc}")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 1 if result["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())

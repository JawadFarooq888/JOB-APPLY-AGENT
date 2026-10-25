"""Arbeitnow jobs (free API, mostly Europe). Only remote jobs are kept here."""

from .common import Job, get_json, html_to_text, parse_date

API = "https://www.arbeitnow.com/api/job-board-api"
PAGES = 3  # newest 3 pages (up to 300 jobs each) is plenty


def fetch(config):
    jobs = []
    for page in range(1, PAGES + 1):
        data = get_json(API, params={"page": page}) or {}
        for item in data.get("data", []):
            if not item.get("remote"):
                continue  # onsite jobs here are in Europe, never in Pakistan
            jobs.append(Job(
                source="Arbeitnow",
                company=item.get("company_name", ""),
                title=item.get("title", ""),
                location=item.get("location", "") or "Remote",
                remote_type="Remote",
                url=item.get("url", ""),
                description=html_to_text(item.get("description", "")),
                posted_at=parse_date(item.get("created_at")),
            ))
        if not (data.get("links") or {}).get("next"):
            break
    return jobs

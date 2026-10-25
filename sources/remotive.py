"""Remotive remote jobs (free API). Terms: link back to Remotive, only a few calls per day.
Note (checked 2026-10-25): the free API returns only ~10 recent jobs and ignores search
words, so we make a single call per run."""

from .common import Job, get_json, html_to_text, parse_date

API = "https://remotive.com/api/remote-jobs"


def fetch(config):
    data = get_json(API) or {}
    jobs = []
    for item in data.get("jobs", []):
        jobs.append(Job(
            source="Remotive",
            company=item.get("company_name", ""),
            title=item.get("title", ""),
            location=item.get("candidate_required_location", "") or "Remote",
            remote_type="Remote",
            url=item.get("url", ""),  # Remotive page; it links to the company apply page
            description=html_to_text(item.get("description", "")),
            posted_at=parse_date(item.get("publication_date")),
        ))
    return jobs

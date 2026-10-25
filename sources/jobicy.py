"""Jobicy remote jobs (free API). Please do not call it more than once an hour."""

from .common import Job, get_json, html_to_text, parse_date

API = "https://jobicy.com/api/v2/remote-jobs"
TAGS = ["sql", "etl", "data engineer", "database", "data warehouse"]


def fetch(config):
    jobs, seen = [], set()
    for tag in TAGS:
        try:
            data = get_json(API, params={"count": 50, "tag": tag}) or {}
        except Exception as e:
            print(f"    ! jobicy tag={tag}: {e}")
            continue
        for item in data.get("jobs", []):
            if item.get("id") in seen:
                continue
            seen.add(item.get("id"))
            jobs.append(Job(
                source="Jobicy",
                company=item.get("companyName", ""),
                title=html_to_text(item.get("jobTitle", "")),
                location=item.get("jobGeo", "") or "Remote",
                remote_type="Remote",
                url=item.get("url", ""),
                description=html_to_text(item.get("jobDescription", "")),
                posted_at=parse_date(item.get("pubDate")),
            ))
    return jobs

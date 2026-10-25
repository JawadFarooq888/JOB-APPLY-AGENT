"""RemoteOK remote jobs (free API). Terms: link back to Remote OK as the source."""

from .common import Job, get_json, html_to_text, parse_date

API = "https://remoteok.com/api"


def fetch(config):
    data = get_json(API) or []
    jobs = []
    for item in data[1:]:  # the first item is the legal notice, not a job
        if not isinstance(item, dict) or not item.get("position"):
            continue
        jobs.append(Job(
            source="RemoteOK",
            company=item.get("company", ""),
            title=item.get("position", ""),
            location=item.get("location", "") or "Remote",
            remote_type="Remote",
            url=item.get("url") or item.get("apply_url", ""),
            description=html_to_text(item.get("description", "")),
            posted_at=parse_date(item.get("epoch") or item.get("date")),
        ))
    return jobs

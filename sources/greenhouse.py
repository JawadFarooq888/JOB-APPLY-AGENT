"""Greenhouse company job boards (public API, no key needed)."""

from .common import Job, get_json, html_to_text, parse_date, guess_remote_type

API = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"


def fetch(config):
    jobs = []
    for slug in config["companies"].get("greenhouse") or []:
        try:
            data = get_json(API.format(slug=slug))
        except Exception as e:  # one broken company never stops the run
            print(f"    ! greenhouse/{slug}: {e}")
            continue
        if not data:
            print(f"    ! greenhouse/{slug}: board not found (check companies.yaml)")
            continue
        for item in data.get("jobs", []):
            location = (item.get("location") or {}).get("name", "")
            offices = ", ".join(o.get("name", "") for o in item.get("offices") or [])
            if offices and offices not in location:
                location = f"{location} | {offices}"
            jobs.append(Job(
                source="Greenhouse",
                company=item.get("company_name") or slug.title(),
                title=item.get("title", ""),
                location=location,
                remote_type=guess_remote_type(location),
                url=item.get("absolute_url", ""),  # company's own careers page
                description=html_to_text(item.get("content", "")),
                posted_at=parse_date(item.get("first_published") or item.get("updated_at")),
            ))
    return jobs

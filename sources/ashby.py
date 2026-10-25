"""Ashby company job boards (public API, no key needed)."""

from .common import Job, get_json, parse_date, guess_remote_type

API = "https://api.ashbyhq.com/posting-api/job-board/{slug}"

WORKPLACE = {"remote": "Remote", "hybrid": "Hybrid", "onsite": "Onsite"}


def fetch(config):
    jobs = []
    for slug in config["companies"].get("ashby") or []:
        try:
            data = get_json(API.format(slug=slug))
        except Exception as e:
            print(f"    ! ashby/{slug}: {e}")
            continue
        if not data:
            print(f"    ! ashby/{slug}: board not found (check companies.yaml)")
            continue
        for item in data.get("jobs", []):
            if item.get("isListed") is False:
                continue
            places = [item.get("location", "")]
            places += [s.get("location", "") for s in item.get("secondaryLocations") or []]
            location = ", ".join(p for p in places if p)
            address = (item.get("address") or {}).get("postalAddress") or {}
            country = address.get("addressCountry")
            if country and country.lower() not in location.lower():
                location += f" ({country})"
            workplace = (item.get("workplaceType") or "").lower()
            remote_type = WORKPLACE.get(workplace) or (
                "Remote" if item.get("isRemote") else guess_remote_type(location))
            jobs.append(Job(
                source="Ashby",
                company=slug.replace("-", " ").title(),
                title=item.get("title", ""),
                location=location,
                remote_type=remote_type,
                url=item.get("applyUrl") or item.get("jobUrl", ""),
                description=item.get("descriptionPlain", ""),
                posted_at=parse_date(item.get("publishedAt")),
            ))
    return jobs

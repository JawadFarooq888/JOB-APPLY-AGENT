"""Lever company job boards (public API, no key needed)."""

from .common import Job, get_json, html_to_text, parse_date, guess_remote_type

API = "https://api.lever.co/v0/postings/{slug}?mode=json"

WORKPLACE = {"remote": "Remote", "hybrid": "Hybrid", "onsite": "Onsite", "on-site": "Onsite"}


def fetch(config):
    jobs = []
    for slug in config["companies"].get("lever") or []:
        try:
            data = get_json(API.format(slug=slug))
        except Exception as e:
            print(f"    ! lever/{slug}: {e}")
            continue
        if not isinstance(data, list):
            print(f"    ! lever/{slug}: board not found (check companies.yaml)")
            continue
        for item in data:
            cats = item.get("categories") or {}
            places = cats.get("allLocations") or [cats.get("location", "")]
            location = ", ".join(p for p in places if p)
            if item.get("country"):
                location += f" ({item['country']})"
            workplace = (item.get("workplaceType") or "").lower()
            # Full description = intro + bullet lists + closing text
            parts = [item.get("descriptionPlain", "")]
            for block in item.get("lists") or []:
                parts.append(block.get("text", ""))
                parts.append(html_to_text(block.get("content", "")))
            parts.append(item.get("additionalPlain", ""))
            jobs.append(Job(
                source="Lever",
                company=slug.replace("-", " ").title(),
                title=item.get("text", ""),
                location=location,
                remote_type=WORKPLACE.get(workplace) or guess_remote_type(location),
                url=item.get("applyUrl") or item.get("hostedUrl", ""),
                description="\n".join(p for p in parts if p),
                posted_at=parse_date(item.get("createdAt")),
            ))
    return jobs

"""Adzuna jobs (free API key: https://developer.adzuna.com/).
Note: Adzuna has no Pakistan site, so this mainly finds remote jobs listed abroad."""

from settings import env
from .common import Job, get_json, html_to_text, parse_date, guess_remote_type

API = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"


def fetch(config):
    app_id, app_key = env("ADZUNA_APP_ID"), env("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        print("    (Adzuna keys not set - skipping)")
        return []
    jobs = []
    for country in config.get("adzuna_countries", []):
        for term in config.get("search_terms", []):
            params = {
                "app_id": app_id, "app_key": app_key,
                "what": term, "what_and": "remote",
                "results_per_page": 50, "max_days_old": 14,
                "content-type": "application/json",
            }
            try:
                data = get_json(API.format(country=country), params=params) or {}
            except Exception as e:
                print(f"    ! adzuna {country}/{term}: {e}")
                continue
            for item in data.get("results", []):
                location = (item.get("location") or {}).get("display_name", "")
                title = html_to_text(item.get("title", ""))
                desc = html_to_text(item.get("description", ""))
                jobs.append(Job(
                    source="Adzuna",
                    company=(item.get("company") or {}).get("display_name", ""),
                    title=title,
                    location=f"{location} ({country.upper()})",
                    remote_type=guess_remote_type(title, desc[:300]),
                    url=item.get("redirect_url", ""),
                    description=desc,
                    posted_at=parse_date(item.get("created")),
                ))
    return jobs

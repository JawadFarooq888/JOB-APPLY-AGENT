"""Checks every company in companies.yaml and tells you which slugs are broken.

    python check_companies.py
"""

from settings import load_config
from sources import common

URLS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
    "lever": "https://api.lever.co/v0/postings/{slug}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{slug}",
}


def main():
    config = load_config()
    common.configure({"request_delay_seconds": 0.5, "request_timeout_seconds": 20})
    broken = []
    for ats, url in URLS.items():
        for slug in config["companies"].get(ats) or []:
            try:
                data = common.get_json(url.format(slug=slug), retries=0)
                count = len(data) if isinstance(data, list) else len((data or {}).get("jobs", []))
                status = f"OK  ({count} open jobs)" if data is not None else "NOT FOUND"
            except Exception as e:
                data, status = None, f"ERROR ({type(e).__name__})"
            print(f"{ats:11s} {slug:22s} {status}")
            if data is None:
                broken.append(f"{ats}/{slug}")
    print("\nBroken - remove these from companies.yaml:" if broken else "\nAll slugs work.")
    for b in broken:
        print("  ", b)


if __name__ == "__main__":
    main()

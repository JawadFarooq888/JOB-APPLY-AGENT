"""Job Search Agent - finds jobs, scores them with AI, saves them to Google Sheets.

Examples (run inside the virtual environment):
    python main.py                          full run: all sources, AI, sheet, email
    python main.py --dry-run --source remotive   test one source: no AI, no sheet
    python main.py --source remotive        one source, with AI + sheet
    python main.py --no-email               full run without the email
"""

import argparse
import csv
import importlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

from filters import apply_filters, remove_duplicates
from settings import load_config, load_resume
from sources import common

SOURCE_NAMES = ["greenhouse", "lever", "ashby", "remotive", "remoteok", "arbeitnow", "jobicy", "adzuna"]
COMPANY_SOURCES = {"greenhouse", "lever", "ashby"}  # direct company links -> score these first
PAKISTAN_TZ = timezone(timedelta(hours=5))


def fetch_all(config, only):
    """Run every enabled source. A broken source is reported and skipped."""
    all_jobs = []
    for name in SOURCE_NAMES:
        if only and name not in only:
            continue
        if not only and not config["sources"].get(name, False):
            continue
        print(f"  - {name} ...", flush=True)
        try:
            module = importlib.import_module(f"sources.{name}")
            jobs = module.fetch(config)
            print(f"    {len(jobs)} jobs")
            all_jobs.extend(jobs)
        except Exception as e:
            print(f"    ! {name} failed, skipping it: {type(e).__name__}: {e}")
    return all_jobs


def save_preview(jobs):
    """Dry run: write the filtered jobs to output/preview.csv so you can look at them."""
    Path("output").mkdir(exist_ok=True)
    path = Path("output") / "preview.csv"
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Company", "Title", "Location", "Remote/Onsite", "Source", "Posted", "Link"])
        for j in jobs:
            posted = j.posted_at.date().isoformat() if j.posted_at else ""
            writer.writerow([j.company, j.title, j.location, j.remote_type, j.source, posted, j.url])
    print(f"\nSaved preview to {path} (open it in Excel).")


def main():
    parser = argparse.ArgumentParser(description="Daily job search agent")
    parser.add_argument("--source", action="append", choices=SOURCE_NAMES,
                        help="only use this source (can repeat)")
    parser.add_argument("--dry-run", action="store_true",
                        help="fetch + filter only. No AI, no Google Sheet, no email")
    parser.add_argument("--no-email", action="store_true", help="do not send the summary email")
    args = parser.parse_args()

    config = load_config()
    common.configure(config)

    print("1) Fetching jobs")
    jobs = fetch_all(config, args.source)
    print(f"   Total fetched: {len(jobs)}")

    print("2) Filtering (title, seniority, years, location)")
    jobs, reasons = apply_filters(jobs, config)
    for reason, count in reasons.most_common():
        print(f"   skipped {count:5d}: {reason}")
    print(f"   Passed filters: {len(jobs)}")

    if args.dry_run:
        jobs = remove_duplicates(jobs, set(), set())
        for j in jobs:
            print(f"   * {j.title} | {j.company} | {j.location} | {j.source}")
        save_preview(jobs)
        return

    # Imported here so --dry-run works even before Gemini/Sheets are set up
    import sheet
    from scorer import DailyQuotaUsed, Scorer

    print("3) Removing jobs already in the Google Sheet")
    ws = sheet.connect(config)
    seen_keys, seen_links = sheet.already_saved(ws)
    jobs = remove_duplicates(jobs, seen_keys, seen_links)
    print(f"   New jobs: {len(jobs)}")

    # Company career pages first (direct links), then newest first
    oldest = datetime.min.replace(tzinfo=timezone.utc)
    jobs.sort(key=lambda j: (j.source.lower() in COMPANY_SOURCES, j.posted_at or oldest), reverse=True)

    limit = int(config["max_ai_calls_per_run"])
    print(f"4) AI scoring with {config['gemini_model']} (max {limit} jobs this run)")
    scorer = Scorer(config, load_resume())
    today = datetime.now(PAKISTAN_TZ).date().isoformat()
    rows = []
    for job in jobs[:limit]:
        try:
            r = scorer.score(job)
        except DailyQuotaUsed:
            print("   Gemini free quota for today is used up. The rest will be scored tomorrow.")
            break
        except Exception as e:
            print(f"   ! could not score '{job.title}' ({job.company}): {e}")
            continue  # not saved, so it is tried again next run
        print(f"   [{r['score']:3d}] {r['decision']:5s} {job.title} - {job.company}")
        rows.append([
            today, job.company, job.title, job.location, job.remote_type, job.source,
            job.url, r["score"], r["decision"], r["matching"], r["missing"],
            r["cover_letter"], r["keywords"], "",  # Status: empty, you fill it in
        ])
    if len(jobs) > limit:
        print(f"   {len(jobs) - limit} jobs left for the next run (AI limit reached).")

    print("5) Saving to Google Sheet")
    sheet.add_rows(ws, rows)
    print(f"   Added {len(rows)} rows. Apply: {sum(r[8] == 'Apply' for r in rows)}")

    if not args.no_email:
        print("6) Email summary")
        try:
            from emailer import send_summary
            send_summary(rows, config)
        except Exception as e:
            print(f"   ! email failed: {e}")
    print("Done.")


if __name__ == "__main__":
    main()

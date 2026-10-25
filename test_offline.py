"""Offline test with DUMMY data only. No internet, no Gemini, no Google Sheet, no email.

    python test_offline.py

It runs the whole agent (fetch -> filter -> dedupe -> score -> save -> sort) using fake jobs,
a fake AI and a fake sheet kept in memory, and checks the results.
"""

import sys
from datetime import datetime, timedelta, timezone

import main
import scorer
import sheet
from sources.common import Job

NOW = datetime.now(timezone.utc)

# ---------- Dummy jobs (made-up companies) ----------
DUMMY_JOBS = [
    # should PASS the filters
    Job("Greenhouse", "Demo Corp", "SQL Server Developer", "Remote - Worldwide", "Remote",
        "https://example.com/jobs/1", "2+ years of experience with T-SQL and ETL.", NOW),
    Job("Ashby", "Test Data Ltd", "ETL Developer", "Lahore, Pakistan", "Hybrid",
        "https://example.com/jobs/2", "SSIS, stored procedures, data warehouse.", NOW),
    Job("Jobicy", "Sample Inc", "Data Engineer", "Remote", "Remote",
        "https://example.com/jobs/3", "Python, SQL, Airflow. 1-3 years experience.", NOW),
    Job("Lever", "Already Saved Co", "Database Developer", "Remote, Global", "Remote",
        "https://example.com/jobs/old", "SQL Server.", NOW),
    # should be SKIPPED by the filters
    Job("Greenhouse", "Demo Corp", "Senior Data Engineer", "Remote", "Remote",
        "https://example.com/jobs/4", "", NOW),
    Job("Remotive", "Sample Inc", "Data Engineer", "Remote - US", "Remote",
        "https://example.com/jobs/5", "", NOW),
    Job("Greenhouse", "Demo Corp", "BI Developer", "Faisalabad, Pakistan", "Onsite",
        "https://example.com/jobs/6", "", NOW),
    Job("Ashby", "Test Data Ltd", "Data Engineer", "Remote", "Remote",
        "https://example.com/jobs/7", "Requires 5+ years of experience.", NOW),
    Job("RemoteOK", "Sample Inc", "Database Engineer", "Worldwide", "Remote",
        "https://example.com/jobs/8", "Active security clearance required.", NOW),
    Job("Jobicy", "Old Jobs Inc", "SQL Developer", "Worldwide", "Remote",
        "https://example.com/jobs/9", "", NOW - timedelta(days=60)),
    Job("Arbeitnow", "Demo Corp", "Frontend Developer", "Remote", "Remote",
        "https://example.com/jobs/10", "", NOW),
    # duplicate of job 1 from another source -> removed
    Job("Remotive", "Demo Corp", "SQL Server Developer", "Worldwide", "Remote",
        "https://remotive.example/1", "", NOW),
]


# ---------- Fake Gemini ----------
class FakeScorer(scorer.Scorer):
    """Uses the real cleanup rules, but makes up the AI answer instead of calling Gemini."""
    def __init__(self, config, resume):
        self.threshold, self.resume, self.calls = int(config["apply_threshold"]), resume, 0

    def score(self, job):
        self.calls += 1
        fake_score = {"SQL Server Developer": 85, "ETL Developer": 70}.get(job.title, 40)
        answer = scorer.JobScore(
            relevancy_score=fake_score, matching_skills=["SQL Server", "T-SQL"],
            missing_skills=["Airflow"], apply_or_skip="Apply",  # wrong on purpose: code must fix it
            short_cover_letter="Dear hiring team, " + "test " * 200,
            resume_keywords_to_add=["stored procedures", "Snowflake"],  # Snowflake is not in resume
        )
        return self._clean(answer)


# ---------- Fake Google Sheet ----------
class FakeSheet:
    def __init__(self):
        old = ["2026-01-01", "Already Saved Co", "Database Developer", "Remote", "Remote", "Lever",
               "https://example.com/jobs/old", 90, "Apply", "", "", "", "", "Applied"]
        self.rows = [list(sheet.HEADERS), old]
        self.col_count = len(sheet.HEADERS)

    def get_all_values(self):
        return [[str(c) for c in r] for r in self.rows]

    def append_rows(self, rows, **kwargs):
        self.rows += [list(r) for r in rows]

    def col_values(self, col):
        return [r[col - 1] for r in self.rows]

    def sort(self, *specs, range=None):
        body = self.rows[1:]
        for col, order in reversed(specs):
            body.sort(key=lambda r: r[col - 1], reverse=(order == "des"))
        self.rows = [self.rows[0]] + body


def check(name, condition):
    print(("  PASS  " if condition else "  FAIL  ") + name)
    return condition


def run():
    fake_sheet = FakeSheet()
    holder = {}

    def fake_scorer(config, resume):
        holder["s"] = FakeScorer(config, resume)
        return holder["s"]

    # Swap the real internet parts for the fakes
    main.fetch_all = lambda config, only: list(DUMMY_JOBS)
    sheet.connect = lambda config: fake_sheet
    scorer.Scorer = fake_scorer
    sys.argv = ["main.py", "--no-email"]
    main.main()

    rows = fake_sheet.rows[1:]
    titles = [r[2] for r in rows]
    by_title = {r[2]: r for r in rows}
    print("\nResult sheet:")
    for r in rows:
        print(f"  {r[0]} | {r[1]:17s} | {r[2]:21s} | score {r[7]} | {r[8]} | status '{r[13]}'")
    print("\nChecks:")
    ok = all([
        check("3 new jobs saved + 1 old row kept", len(rows) == 4),
        check("Senior / US-only / Faisalabad / 5+ yrs / clearance / old / frontend skipped",
              not {"Senior Data Engineer", "Frontend Developer", "BI Developer", "SQL Developer"} & set(titles)),
        check("Duplicate job saved only once", titles.count("SQL Server Developer") == 1),
        check("Job already in sheet not scored again", holder["s"].calls == 3),
        check("Score 85 -> Apply, 40 -> Skip (threshold 65)",
              by_title["SQL Server Developer"][8] == "Apply" and by_title["Data Engineer"][8] == "Skip"),
        check("Cover letter cut to 120 words", len(by_title["SQL Server Developer"][11].split()) <= 120),
        check("Invented keyword 'Snowflake' removed", "Snowflake" not in by_title["ETL Developer"][12]),
        check("Sorted: newest first, then highest score", titles[:3] == [
            "SQL Server Developer", "ETL Developer", "Data Engineer"]),
        check("Your 'Applied' status kept on the old row", by_title["Database Developer"][13] == "Applied"),
        check("Direct company link saved", by_title["SQL Server Developer"][6] == "https://example.com/jobs/1"),
    ])
    print("\nALL TESTS PASSED" if ok else "\nSOME TESTS FAILED")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)

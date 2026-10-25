"""Free rule-based filters (no AI). They remove most jobs before we spend any AI quota."""

import re
from collections import Counter
from datetime import datetime, timedelta, timezone


def has_word(text, word):
    """True if `word` appears in `text` as a whole word/phrase (case-insensitive)."""
    return re.search(rf"(?<![a-z0-9]){re.escape(word.lower())}(?![a-z0-9])", text) is not None


def any_word(text, words):
    return next((w for w in words if has_word(text, w)), None)


# "3+ years", "2-4 years", "5 yrs", "minimum 4 years" ... followed by "experience"
YEARS_RE = re.compile(
    r"(\d{1,2})\s*(?:\+|plus)?\s*(?:(?:-|–|to)\s*\d{1,2}\s*\+?\s*)?(?:years?|yrs?)\b(.{0,60})",
    re.I | re.S,
)


def years_required(description):
    """Highest 'minimum years of experience' mentioned in the job text (0 if none)."""
    found = 0
    for match in YEARS_RE.finditer(description):
        years, after = int(match.group(1)), match.group(2).lower()
        if "experience" in after or "exp " in after:
            if years <= 15:  # ignore things like "over 20 years in business"
                found = max(found, years)
    return found


def title_ok(title, config):
    t = title.lower()
    if not any_word(t, config["title_keywords"]):
        return False, "title not a target role"
    bad = any_word(t, config["exclude_title_words"])
    if bad:
        return False, f"seniority word '{bad}'"
    return True, ""


def location_ok(job, config):
    loc = job.location.lower()
    cities = config["allowed_cities"]

    is_remote = job.remote_type == "Remote" or "remote" in loc

    # 1) One of my cities -> keep (remote, hybrid or onsite)
    if any_word(loc, cities):
        return True, ""

    # 2) Pakistan: remote -> keep. Onsite -> keep only if no other city is named.
    if has_word(loc, "pakistan") or has_word(loc, "pk"):
        other_text = re.sub(r"pakistan|\bpk\b|onsite|on-site|hybrid|[^a-z]", "", loc)
        if is_remote or not other_text:
            return True, ""
        return False, "onsite/hybrid outside my cities"

    if not is_remote:
        return False, "onsite/hybrid outside my cities"

    # 3) Remote and open worldwide / Asia / EMEA -> keep
    if any_word(loc, config["remote_ok_words"]):
        return True, ""

    # 4) Remote but limited to another country/region -> skip
    place = any_word(loc, config["blocked_places"])
    if place:
        return False, f"remote only in '{place}'"

    # 5) Just "Remote" with no country -> keep (the AI checks the description)
    return True, ""


def description_ok(job, config):
    text = job.description.lower()
    phrase = next((p for p in config["exclude_description_phrases"] if p in text), None)
    if phrase:
        return False, f"description says '{phrase}'"
    years = years_required(job.description)
    if years > config["max_years_required"]:
        return False, f"needs {years}+ years"
    return True, ""


COMPANY_SOURCES = {"Greenhouse", "Lever", "Ashby"}


def age_ok(job, config):
    if job.posted_at is None:
        return True, ""
    # Company career pages only list jobs that are still open, so allow older posts there
    key = "max_job_age_days_company" if job.source in COMPANY_SOURCES else "max_job_age_days"
    limit = datetime.now(timezone.utc) - timedelta(days=config.get(key, config["max_job_age_days"]))
    return (job.posted_at >= limit), "too old"


def apply_filters(jobs, config):
    """Return (kept_jobs, Counter of skip reasons)."""
    kept, reasons = [], Counter()
    for job in jobs:
        for check in (lambda j, c: title_ok(j.title, c), age_ok, location_ok, description_ok):
            ok, why = check(job, config)
            if not ok:
                # Group similar reasons together so the summary stays short
                reasons[re.sub(r"'.*'|\d+\+", "...", why)] += 1
                break
        else:
            kept.append(job)
    return kept, reasons


# ---------- Duplicates ----------

def job_key(company, title):
    clean = lambda s: re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()
    return f"{clean(company)}|{clean(title)}"


def remove_duplicates(jobs, seen_keys, seen_links):
    """Drop jobs already in the sheet (same link, or same company + title) or repeated in this run."""
    unique = []
    for job in jobs:
        key = job_key(job.company, job.title)
        if key in seen_keys or job.url in seen_links:
            continue
        seen_keys.add(key)
        seen_links.add(job.url)
        unique.append(job)
    return unique

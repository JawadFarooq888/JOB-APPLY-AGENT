"""Shared helpers for all job sources: the Job record, polite HTTP, text cleanup."""

import html
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import requests


@dataclass
class Job:
    source: str            # e.g. "Greenhouse", "Remotive"
    company: str
    title: str
    location: str          # location text as the job shows it
    remote_type: str       # "Remote", "Hybrid", "Onsite" or "Unknown"
    url: str               # best apply link (company site when available)
    description: str = ""  # plain text
    posted_at: datetime | None = None


# One shared connection with a clear, honest User-Agent
session = requests.Session()
session.headers.update({
    "User-Agent": "PersonalJobSearchAgent/1.0 (personal job search, 1 run per day)",
    "Accept": "application/json",
})

_settings = {"delay": 1.5, "timeout": 25}


def configure(config):
    _settings["delay"] = float(config.get("request_delay_seconds", 1.5))
    _settings["timeout"] = float(config.get("request_timeout_seconds", 25))


def get_json(url, params=None, retries=2):
    """GET a URL and return JSON. Waits politely and retries on busy/rate-limit errors.
    Returns None if the page does not exist (404)."""
    for attempt in range(retries + 1):
        time.sleep(_settings["delay"])  # polite pause before every request
        try:
            resp = session.get(url, params=params, timeout=_settings["timeout"])
        except requests.RequestException:
            if attempt == retries:
                raise
            time.sleep(10 * (attempt + 1))  # internet hiccup: wait 10s, then 20s
            continue
        if resp.status_code == 404:
            return None
        if resp.status_code in (429, 500, 502, 503, 504) and attempt < retries:
            wait = int(resp.headers.get("Retry-After", "0") or 0) or 10 * (attempt + 1)
            time.sleep(min(wait, 60))
            continue
        resp.raise_for_status()
        return resp.json()


def html_to_text(raw):
    """Turn job description HTML into plain text."""
    if not raw:
        return ""
    text = html.unescape(raw)          # Greenhouse sends escaped HTML
    text = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n", text).strip()


def parse_date(value):
    """Accepts ISO text ('2026-10-20T10:00:00Z'), epoch seconds or epoch milliseconds."""
    if value in (None, ""):
        return None
    try:
        if isinstance(value, (int, float)) or str(value).isdigit():
            num = float(value)
            if num > 1e12:  # milliseconds
                num /= 1000
            return datetime.fromtimestamp(num, tz=timezone.utc)
        text = str(value).strip().replace("Z", "+00:00")
        if " " in text and "T" not in text:
            text = text.replace(" ", "T", 1)
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, OSError):
        return None


def guess_remote_type(*texts):
    """Guess Remote / Hybrid / Onsite from location or workplace text."""
    joined = " ".join(t for t in texts if t).lower()
    if "hybrid" in joined:
        return "Hybrid"
    if "remote" in joined or "anywhere" in joined or "worldwide" in joined:
        return "Remote"
    if joined.strip():
        return "Onsite"
    return "Unknown"

"""Scores jobs against your resume with Google Gemini (free tier) and writes the cover letter."""

import re
import time

from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from settings import env


class JobScore(BaseModel):
    """The exact JSON shape we ask Gemini to return."""
    relevancy_score: int
    matching_skills: list[str]
    missing_skills: list[str]
    apply_or_skip: str
    short_cover_letter: str
    resume_keywords_to_add: list[str]


class DailyQuotaUsed(Exception):
    """Gemini says the free quota for today is used up."""


PROMPT = """You are a careful career assistant. Judge how well this job fits the candidate.

CANDIDATE PROFILE
- Junior to mid level: about 1-2 years of database/data work (plus earlier Android/Kotlin work).
- Lives in Muzaffarabad, Pakistan. Can work remote (if open to Pakistan or worldwide)
  or onsite/hybrid in Islamabad, Rawalpindi, Lahore or Karachi.
- Has no work authorization outside Pakistan and no security clearance.

CANDIDATE RESUME
\"\"\"
{resume}
\"\"\"

JOB
Title: {title}
Company: {company}
Location: {location} ({remote_type})
Description:
\"\"\"
{description}
\"\"\"

SCORING RULES
- relevancy_score 0-100 = how well the RESUME matches this job, including experience level.
- If the job needs 4+ years, a senior level, or is only open to people in other countries
  (not Pakistan), give a score below 40.
- matching_skills: skills the job asks for that ARE in the resume.
- missing_skills: important skills the job asks for that are NOT in the resume.
- apply_or_skip: "Apply" if relevancy_score >= {threshold}, else "Skip".
- short_cover_letter: max 120 words, simple clear English, first person, addressed to the
  hiring team. Use ONLY real experience from the resume. Never invent skills, tools,
  numbers, degrees or years of experience. No placeholders like [Company].
- resume_keywords_to_add: words from the job ad that the candidate truly has (they appear
  in or are clearly proven by the resume) but should mention more clearly. Never list a
  skill the candidate does not have.
Return only JSON."""


class Scorer:
    def __init__(self, config, resume):
        key = env("GEMINI_API_KEY")
        if not key:
            raise SystemExit("GEMINI_API_KEY is missing. Add it to .env (or GitHub Secrets).")
        self.client = genai.Client(api_key=key)
        self.model = config["gemini_model"]
        self.threshold = int(config["apply_threshold"])
        self.delay = float(config["ai_delay_seconds"])
        self.retries = int(config["ai_max_retries"])
        self.resume = resume

    def score(self, job):
        """Return a dict with the score fields, or raise DailyQuotaUsed."""
        prompt = PROMPT.format(
            resume=self.resume[:8000],
            title=job.title, company=job.company,
            location=job.location, remote_type=job.remote_type,
            description=job.description[:7000] or "(no description given)",
            threshold=self.threshold,
        )
        for attempt in range(self.retries + 1):
            time.sleep(self.delay)  # stay under the free "requests per minute" limit
            try:
                resp = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=JobScore,
                        temperature=0.2,
                    ),
                )
                result = resp.parsed or JobScore.model_validate_json(resp.text)
                return self._clean(result)
            except errors.APIError as e:
                message = str(e)
                if e.code == 429 and "PerDay" in message:
                    raise DailyQuotaUsed(message[:200])
                if e.code in (429, 500, 503) and attempt < self.retries:
                    wait = _retry_delay(message, default=30 * (attempt + 1))
                    print(f"    Gemini busy/rate limit ({e.code}). Waiting {wait}s...")
                    time.sleep(wait)
                    continue
                raise

    def _clean(self, r):
        """Enforce our own rules instead of trusting the AI blindly."""
        score = max(0, min(100, int(r.relevancy_score)))
        resume_lower = self.resume.lower()
        words = r.short_cover_letter.split()
        letter = " ".join(words[:120])
        return {
            "score": score,
            "decision": "Apply" if score >= self.threshold else "Skip",
            "matching": ", ".join(r.matching_skills),
            "missing": ", ".join(r.missing_skills),
            "cover_letter": letter,
            # keep only keywords that really appear in the resume (never invent skills)
            "keywords": ", ".join(k for k in r.resume_keywords_to_add if _in_resume(k, resume_lower)),
        }


def _in_resume(keyword, resume_lower):
    """True if the keyword (or every word in it) appears in the resume."""
    kw = keyword.lower().strip()
    if not kw:
        return False
    if kw in resume_lower:
        return True
    parts = [p for p in re.split(r"[\s/,&-]+", kw) if len(p) > 2]
    return bool(parts) and all(p in resume_lower for p in parts)


def _retry_delay(message, default):
    """Gemini errors often say how long to wait, e.g. 'retryDelay': '37s'."""
    m = re.search(r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+)", message)
    return min(int(m.group(1)) + 2, 120) if m else default

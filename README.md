# Job Search Agent (free)

Every day this agent:

1. Gets new jobs from **company career pages** (Greenhouse, Lever, Ashby) and **free job APIs**
   (Remotive, RemoteOK, Arbeitnow, Jobicy, Adzuna).
2. Removes jobs that don't fit: wrong title, senior roles, 4+ years, locations you can't
   work from, clearance/citizenship roles, internships. (No AI is used here, so this step is free.)
3. Removes duplicates and jobs already in your Google Sheet.
4. Sends the remaining jobs to **Google Gemini (free)**, which gives each one a score from 0 to 100, lists matching and missing skills, and writes a short cover letter.
5. Saves everything to your **Google Sheet** and can email you the top 10.

It never applies for you and never logs in to or scrapes LinkedIn, Indeed or similar sites.
**Everything is free.**

---

## Project files

| File | What it does |
|---|---|
| `main.py` | Runs everything, in order |
| `sources/` | One file per job source |
| `filters.py` | Free rule filters (title, seniority, years, location) |
| `scorer.py` | Gemini AI scoring + cover letter |
| `sheet.py` | Google Sheet read/write (never touches your Status column) |
| `emailer.py` | Optional daily email |
| `config.yaml` | **Your settings** (keywords, threshold, AI limits…) |
| `companies.yaml` | **Company list** — add more here |
| `check_companies.py` | Tests every company slug |
| `resume.txt` | Your resume text (private, not uploaded) |
| `.env` | Your keys (private, not uploaded) |
| `.github/workflows/daily.yml` | Daily run on GitHub at 9 AM Pakistan time |

---

## Step 1 — Set up on your PC (Windows, VS Code)

Open the folder in VS Code → menu **Terminal → New Terminal** (PowerShell) and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If `Activate.ps1` gives a red "running scripts is disabled" error, run this once, then try again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

You'll know the environment is active when you see `(.venv)` at the start of the line. Every time you open a new terminal, run `.\.venv\Scripts\Activate.ps1` again.

A `.env` file already exists (it was copied from `.env.example`). You'll fill it in during Steps 3–6.

Open `resume.txt` and **paste your full resume text** over the sample text.

## Step 2a — Safe test with dummy data (no internet, no keys)

```powershell
python test_offline.py
```

This runs the whole agent with fake jobs, a fake AI and a fake Sheet. Nothing is sent anywhere.
It should end with `ALL TESTS PASSED`.

> `resume.txt` currently holds a **dummy test resume**. Replace it with your real resume only
> when you are ready to use the agent for real.

## Step 2b — Test one real source (public job data only, no keys needed)

```powershell
python main.py --dry-run --source remotive
```

This only fetches and filters. You'll see the jobs that passed in the terminal and in
`output\preview.csv`. Then try the other sources one at a time:

```powershell
python main.py --dry-run --source greenhouse
python main.py --dry-run --source ashby
python main.py --dry-run
```

> Some internet providers in Pakistan block `api.lever.co` and `api.adzuna.com`. If those show
> "failed / timed out" on your PC, that's fine. The agent skips them and moves on, and they work
> on GitHub's servers.

## Step 3 — Get a free Gemini API key

1. Go to <https://aistudio.google.com/apikey> and sign in with Google.
2. Click **Create API key**, then copy it.
3. In `.env`, set `GEMINI_API_KEY=your_key_here`.

The free tier limits how many calls you can make per minute and per day, and Google changes these limits sometimes. The agent waits
`ai_delay_seconds` between calls and makes at most `max_ai_calls_per_run` calls (default 20).
Jobs that don't get scored today are scored tomorrow. If you see "model not found", change
`gemini_model` in `config.yaml` to the current Flash model listed in AI Studio.

## Step 4 — Google Sheet + service account (free)

1. Go to <https://console.cloud.google.com/> → top bar → **New Project** (name: `job-agent`) → Create.
2. Make sure the new project is selected. Search **"Google Sheets API"** → **Enable**.
   Then search **"Google Drive API"** → **Enable**.
3. Menu → **IAM & Admin → Service Accounts → Create service account**. Name: `job-agent` →
   **Done** (you can skip the role steps).
4. Click the new service account → **Keys** tab → **Add key → Create new key → JSON**.
   A file downloads. Rename it to `credentials.json` and move it into this project folder.
   (It's in `.gitignore`, so it is never uploaded.)
5. Open `credentials.json` and copy the `client_email` value
   (looks like `job-agent@job-agent-12345.iam.gserviceaccount.com`).
6. Create a new Google Sheet at <https://sheets.new>. Click **Share**, paste that email,
   choose **Editor**, untick "Notify", then click **Share**.
7. Copy the Sheet ID from the link: `https://docs.google.com/spreadsheets/d/`**`THIS_PART`**`/edit`
   and put it in `.env`: `GOOGLE_SHEET_ID=THIS_PART`

Now run the real thing with one source:

```powershell
python main.py --source remotive --no-email
```

Open your Sheet. A **Jobs** tab will have appeared with the results.

## Step 5 — (Optional) Adzuna key

1. Sign up at <https://developer.adzuna.com/signup>.
2. Copy your **Application ID** and **Application Key** into `.env`
   (`ADZUNA_APP_ID`, `ADZUNA_APP_KEY`).

Adzuna has no Pakistan site, so it finds few jobs that fit. That's expected.

## Step 6 — (Optional) Daily email

1. Your Google account must have **2-Step Verification** turned on.
2. Go to <https://myaccount.google.com/apppasswords>, create an app password named "job agent"
   and copy the 16 letters.
3. In `.env`: `EMAIL_ADDRESS=you@gmail.com`, `EMAIL_APP_PASSWORD=the16letters`,
   `EMAIL_TO=you@gmail.com`

Full run:

```powershell
python main.py
```

## Step 7 — Put it on GitHub (private repo)

1. Go to <https://github.com/new>, name it `job-agent`, choose **Private**, and click **Create**.
   (A private repo gets 2,000 free Action minutes a month. This agent uses about 5–15 minutes a day.)
2. In the VS Code terminal (replace `YOUR_USERNAME`):

```powershell
git add .
git status
```

(The folder is already a git repository, so you don't need `git init`.)

**Check the `git status` list.** `.env`, `credentials.json` and `resume.txt` must NOT be in it.
If they're missing from the list, `.gitignore` is working. Then:

```powershell
git commit -m "Job search agent"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/job-agent.git
git push -u origin main
```

## Step 8 — Add GitHub Secrets

On GitHub, open your repo → **Settings → Secrets and variables → Actions → New repository secret**.
Add each one (the name must match exactly):

| Secret name | Value |
|---|---|
| `GEMINI_API_KEY` | your Gemini key |
| `GOOGLE_SHEET_ID` | your Sheet ID |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | open `credentials.json`, copy **all** of it (from `{` to `}`) |
| `RESUME_TEXT` | copy **all** of `resume.txt` |
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | optional |
| `EMAIL_ADDRESS`, `EMAIL_APP_PASSWORD`, `EMAIL_TO` | optional |

## Step 9 — Test the GitHub Action

Repo → **Actions** tab → **Daily job search** → **Run workflow** → **Run workflow**.
Click the run to watch the log. A green tick means it worked. Check your Sheet.

After that it runs on its own every day at **9:00 AM Pakistan time**. GitHub may start it
5–30 minutes late, which is normal. GitHub also pauses schedules in repos with no activity
for 60 days. If that happens, click "Enable workflow" in the Actions tab.

---

## Daily use

- Open the Sheet, look at the rows marked **Apply**, open the **Direct apply link**, and use the cover letter.
- Type **Applied** in the **Status** column. The agent never changes that column.
- Rows are sorted with the newest date first, then the highest score.

## Changing things

- **More/less AI calls:** `max_ai_calls_per_run` in `config.yaml`
- **Stricter/looser:** `apply_threshold` (default 65)
- **Titles:** `title_keywords`, `exclude_title_words`
- **Add a company:** add its slug to `companies.yaml`, then run `python check_companies.py`
- **After you change `resume.txt`:** update the `RESUME_TEXT` secret on GitHub too

## Common errors

| Error | Meaning / fix |
|---|---|
| `ModuleNotFoundError` | The virtual environment is not active. Run `.\.venv\Scripts\Activate.ps1` |
| `GEMINI_API_KEY is missing` | `.env` is missing the key (or the secret is missing on GitHub) |
| `SpreadsheetNotFound` / `PermissionError` (403) | Share the Sheet with the service account email as **Editor** |
| `APIError: [403] Google Sheets API has not been used` | Enable the Sheets API **and** the Drive API (Step 4.2) |
| `429 RESOURCE_EXHAUSTED` | Gemini free limit reached. The agent waits and retries, and the rest are scored tomorrow |
| `SMTPAuthenticationError` | Use a Gmail **App Password**, not your normal password |

## Source terms

Remotive, RemoteOK, Arbeitnow and Jobicy ask that you credit them and link back to them. The Sheet keeps their
job links and names them in the "Source" column. The agent only uses public, free APIs, waits
between requests, and runs once a day.

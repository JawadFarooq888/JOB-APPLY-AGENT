"""Optional: email yourself the top jobs of the day (Gmail + App Password, free)."""

import smtplib
from email.message import EmailMessage

from settings import env


def send_summary(rows, config):
    """rows = the new sheet rows of this run. Sends the best ones (by score)."""
    sender, password = env("EMAIL_ADDRESS"), env("EMAIL_APP_PASSWORD")
    to = env("EMAIL_TO") or sender
    if not sender or not password:
        print("Email not set up (EMAIL_ADDRESS / EMAIL_APP_PASSWORD) - skipping email.")
        return
    top = sorted(rows, key=lambda r: r[7], reverse=True)[: int(config.get("email_top_n", 10))]
    if not top:
        print("No new jobs today - no email sent.")
        return

    lines = [f"Top {len(top)} new jobs today:\n"]
    for i, r in enumerate(top, 1):
        date, company, title, location, remote, source, link, score, decision = r[:9]
        lines.append(f"{i}. [{score}] {decision} - {title} at {company}")
        lines.append(f"   {location} ({remote}) - via {source}")
        lines.append(f"   {link}\n")
    lines.append("Cover letters and details are in your Google Sheet.")

    msg = EmailMessage()
    msg["Subject"] = f"Job Agent: {len(top)} new jobs (best score {top[0][7]})"
    msg["From"], msg["To"] = sender, to
    msg.set_content("\n".join(lines))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
        smtp.login(sender, password.replace(" ", ""))
        smtp.send_message(msg)
    print(f"Summary email sent to {to}.")

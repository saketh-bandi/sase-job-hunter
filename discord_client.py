# discord_client.py
import os, sys, requests
from urllib.parse import urlparse
from pathlib import Path
from dotenv import load_dotenv


# Loads .env from the project root 
DOTENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=DOTENV_PATH, override=True)

webhook_url = (os.getenv("DISCORD_WEBHOOK_URL") or "").strip()


def mask(url: str) -> str:
    try:
        p = urlparse(url)
        token = url.split("/")[-1]
        return f"{p.scheme}://{p.netloc}/.../{token[:8]}***"
    except Exception:
        return "<invalid>"


def send_to_discord(jobs, limit=10):
    """
    Post jobs to Discord via webhook using embeds (nicer & avoids 2000-char content limit).
    Sends up to 10 embeds per message (Discord limit). Handles rate limits.
    """
    import time
    import math
    import requests
    from datetime import datetime

    if not webhook_url:
        print(" No Discord webhook found in .env")
        return

    jobs = (jobs or [])[:max(0, int(limit))]

    if not jobs:
        print("No jobs to send to Discord.")
        return

    def job_to_embed(job: dict) -> dict:
        title = str(job.get("title", "Untitled"))[:256]  # embed title limit
        url   = str(job.get("url", ""))
        loc   = ", ".join(job.get("locations", []) or []) or "N/A"
        desc  = f"**Source:** {job.get('source','N/A')} • **Location:** {loc}\n**Details:** {title}"

        return {
            "title": title,
            "url": url,
            "description": desc[:4000],  # headroom under 4096
        }

    embeds = [job_to_embed(j) for j in jobs]

    # Discord allows max 10 embeds per message:
    BATCH = 10
    batches = math.ceil(len(embeds) / BATCH)
    print(f"🛰️  send_to_discord(): sending {batches} message chunk(s) for {len(embeds)} job(s)")

    for i in range(0, len(embeds), BATCH):
        chunk = embeds[i:i+BATCH]
        today_str = datetime.utcnow().strftime("%B %d, %Y")
        payload = {
            # Put a short header only on the first chunk
            "content": f"**SASE Job Hunter: Top Opportunities for {today_str}**" if i == 0 else None,
            "embeds": chunk,
        }
        # Remove None to avoid API complaints
        if payload["content"] is None:
            payload.pop("content")

        try:
            resp = requests.post(webhook_url, json=payload, timeout=12)
            if resp.status_code == 204 or resp.status_code == 200:
                print(f"chunk {i//BATCH+1}/{batches} sent")
            elif resp.status_code == 429:
                retry = int(resp.headers.get("Retry-After", "1"))
                print(f"⏳  Rate limited. Sleeping {retry}s…")
                time.sleep(retry)
                # retry once
                resp2 = requests.post(webhook_url, json=payload, timeout=12)
                if resp2.status_code in (200, 204):
                    print(f"chunk {i//BATCH+1}/{batches} sent after retry")
                else:
                    print(f"⚠️  Discord 429 retry failed: {resp2.status_code} - {resp2.text[:300]}")
            else:
                print(f"⚠️  Discord response: {resp.status_code} - {resp.text[:300]}")
        except requests.RequestException as e:
            print(f"⚠️  Network error posting chunk {i//BATCH+1}: {e}")

    print("Job listings sent to Discord.")


# ⬇️ Run this only when executing directly, not when importing
if __name__ == "__main__":
    print(f"Using .env at: {DOTENV_PATH}")
    if not webhook_url:
        print("DISCORD_WEBHOOK_URL missing in .env")
        sys.exit(1)
    if webhook_url.startswith("httpshttps://"):
        print("Found 'httpshttps://'. Fixing automatically for this run.")
        webhook_url = webhook_url.replace("httpshttps://", "https://", 1)
    print(f"Attempting to send a test message to {mask(webhook_url)}")
    payload = {"content": "SASE job hunter bot test", "username": "SASE Job Hunter Bot"}
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        print("HTTP status:", resp.status_code)
        if resp.status_code == 204:
            print("test message was sent")
        else:
            print("Response (first 300 chars):", resp.text[:300])
    except requests.RequestException as e:
        print(f" network error: {e}")
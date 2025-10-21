# github_feed.py (Final, High-Speed, zero per-URL network)

import time
import hashlib
import re
from urllib.parse import urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

from config import SIMPLIFY_GITHUB_RAW, STUDENT_FRIENDLY_TOKENS

def _canonicalize_url(u: str) -> str:
    """
    Local-only canonicalization: strip query/fragment, trim trailing slash.
    No network calls.
    """
    try:
        p = urlparse(u.strip())
        # keep scheme, netloc, path; drop params/query/fragment
        clean = urlunparse((p.scheme, p.netloc.lower(), p.path.rstrip("/"), "", "", ""))
        return clean
    except Exception:
        return u.strip()

def fetch_simplify_jobs():
    """Fetch and parse jobs from the SimplifyJobs GitHub repository (fast path)."""
    t0 = time.time()
    print("🌐 Fetching SimplifyJobs feed...")

    try:
        resp = requests.get(
            SIMPLIFY_GITHUB_RAW,
            timeout=(5, 15),  # connect, read
            headers={"User-Agent": "SASE Job Hunter Bot"},
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"⚠️  Error fetching SimplifyJobs GitHub: {e}")
        return [], {}

    soup = BeautifulSoup(resp.text, "lxml")
    jobs = []
    skip = {"no_link": 0, "not_student_friendly": 0, "invalid_link": 0}

    tbody = soup.find("tbody")
    if not tbody:
        print("⚠️  No <tbody> found in SimplifyJobs README.")
        return [], skip

    for row in tbody.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        company = cells[0].get_text(strip=True).replace("🔥", "").strip()
        role = cells[1].get_text(strip=True)

        # Locations (we keep them; main.py does CA/Remote filtering)
        loc_text = cells[2].get_text(separator="|", strip=True)
        locations = [loc.strip() for loc in re.split(r"\|+|/+", loc_text) if loc.strip()]

        a = cells[3].find("a")
        if not a or not a.has_attr("href"):
            skip["no_link"] += 1
            continue

        apply_url = a["href"].strip()
        if not apply_url or "error=true" in apply_url:
            skip["invalid_link"] += 1
            continue

        # Relevance: keep only student-friendly roles
        title_lower = f"{company} {role}".lower()
        if not any(tok in title_lower for tok in STUDENT_FRIENDLY_TOKENS):
            skip["not_student_friendly"] += 1
            continue

        # Zero-network canonicalization (no unwrap/validate)
        final_url = _canonicalize_url(apply_url)

        job_id = hashlib.sha1(f"{company}{role}{final_url}".encode()).hexdigest()
        jobs.append({
            "id": job_id,
            "title": f"{company} — {role}",
            "url": final_url,
            "source": "SimplifyJobs",
            "created_utc": time.time(),
            "locations": locations,
            "description": "",
        })

    t1 = time.time()
    print(
        f"Parsed {len(jobs)} SimplifyJobs listings "
        f"({skip['not_student_friendly']} skipped for relevance, "
        f"{skip['invalid_link']} invalid links). "
        f"⏱️ {t1 - t0:.2f}s"
    )
    return jobs, skip

# In github_feed.py

import requests
import time
import hashlib
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# --- CORRECTED IMPORTS ---
# Gets all settings from the central config file
from config import (
    SIMPLIFY_GITHUB_RAW,
    ATS_DOMAINS,
    STUDENT_FRIENDLY_TOKENS,
    VALID_LOCATIONS,
)
# Gets all shared tools from the central utils file
from utils import validate_job_url, unwrap_shorteners


def fetch_simplify_jobs():
    """Fetch and parse jobs from the SimplifyJobs GitHub repository."""
    try:
        response = requests.get(
            SIMPLIFY_GITHUB_RAW,
            timeout=15,
            headers={"User-Agent": "SASE Job Hunter Bot"},
        )
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"⚠️  Error fetching SimplifyJobs GitHub: {e}")
        return [], {}

    soup = BeautifulSoup(response.text, "lxml")
    jobs = []
    skip_reasons = {
        "no_link": 0,
        "not_student_friendly": 0,
        "invalid_link": 0,
        "skipped_for_location": 0,
    }

    table_body = soup.find("tbody")
    if not table_body:
        print("⚠️ No <tbody> found in SimplifyJobs README.")
        return [], skip_reasons

    for row in table_body.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        company = cells[0].get_text(strip=True).replace("🔥", "").strip()
        role = cells[1].get_text(strip=True)

        loc_text = cells[2].get_text(separator="|", strip=True)
        locations = [
            loc.strip() for loc in re.split(r"\|+|/+", loc_text) if loc.strip()
        ]

        link_anchor = cells[3].find("a")
        if not link_anchor or not link_anchor.has_attr("href"):
            skip_reasons["no_link"] += 1
            continue

        apply_url = link_anchor["href"]
        if "error=true" in apply_url:
            skip_reasons["invalid_link"] += 1
            continue

        title_lower = f"{company} {role}".lower()
        # FIXED: Uses the correct variable from config.py
        if not any(t in title_lower for t in STUDENT_FRIENDLY_TOKENS):
            skip_reasons["not_student_friendly"] += 1
            continue

        # --- NEW: Location Keyword Filter ---
        # Job is only valid if a location keyword is in the title OR locations list
        location_check_string = (title_lower + " " + " ".join(locations)).lower()
        if not any(loc in location_check_string for loc in VALID_LOCATIONS):
            skip_reasons["skipped_for_location"] += 1
            continue

        unwrapped_url = unwrap_shorteners(apply_url)
        is_valid, final_url = validate_job_url(unwrapped_url)
        if not is_valid:
            skip_reasons["invalid_link"] += 1
            continue

        job_id = hashlib.sha1(f"{company}{role}{final_url}".encode()).hexdigest()
        jobs.append(
            {
                "id": job_id,
                "title": f"{company} — {role}",
                "url": final_url,
                "source": "SimplifyJobs",
                "created_utc": time.time(),
                "locations": locations,
                "description": "",  # Empty description to match Reddit schema
            }
        )

    print(
        f"✅ Parsed {len(jobs)} SimplifyJobs listings "
        f"({skip_reasons['not_student_friendly']} skipped for relevance, "
        f"{skip_reasons['invalid_link']} invalid links)."
    )

    return jobs, skip_reasons
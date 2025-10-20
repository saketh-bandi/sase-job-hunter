import requests
import time
import hashlib
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from reddit_client import validate_job_url, unwrap_shorteners, STUDENT_FRIENDLY_TOKENS, extract_experience_requirements
from config import SIMPLIFY_GITHUB_RAW, ATS_DOMAINS

def fetch_simplify_jobs():
    """Fetch and parse jobs from the SimplifyJobs GitHub repository (HTML-based table)."""
    try:
        response = requests.get(
            SIMPLIFY_GITHUB_RAW,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        response.raise_for_status()
    except requests.RequestException as e:
        print(f" Error fetching SimplifyJobs GitHub: {e}")
        return [], {}

    html = response.text
    soup = BeautifulSoup(html, "lxml")
    jobs = []
    skip_reasons = {"no_link": 0, "not_student_friendly": 0, "invalid_link": 0}

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
        locations = [loc.strip() for loc in re.split(r"\|+|/+", loc_text) if loc.strip()]

        link_cell = cells[3]
        link_anchor = link_cell.find("a")
        if not link_anchor or not link_anchor.has_attr("href"):
            skip_reasons["no_link"] += 1
            continue

        apply_url = link_anchor["href"]
        if "error=true" in apply_url:
            skip_reasons["invalid_link"] += 1
            continue

        title_lower = f"{company} {role}".lower()
        if not any(t in title_lower for t in STUDENT_FRIENDLY_TOKENS):
            skip_reasons["not_student_friendly"] += 1
            continue

        unwrapped_url = unwrap_shorteners(apply_url)
        is_valid, final_url = validate_job_url(unwrapped_url)
        if not is_valid:
            skip_reasons["invalid_link"] += 1
            continue

        tags = []
        if any(k in title_lower for k in ["intern", "internship"]):
            tags.append("internship")
        if any(k in title_lower for k in ["new grad", "new-grad", "entry level", "entry-level", "early career"]):
            tags.append("new grad")
        if any(k in title_lower for k in ["sophomore", "freshman", "junior"]):
            tags.append("undergraduate")
        if any(k in title_lower for k in ["summer", "co-op", "coop"]):
            tags.append("summer")
        if any(k in title_lower for k in ["research", "fellowship"]):
            tags.append("research")

        experience = extract_experience_requirements(final_url)

        job_id = hashlib.sha1(f"{company}{role}{final_url}".encode()).hexdigest()
        jobs.append({
            "id": job_id,
            "title": f"{company} — {role}",
            "url": final_url,
            "source": "SimplifyJobs",
            "created_utc": time.time(),
            "locations": locations,
            "tags": tags,
            "experience": experience,
            "description": ""
        })

    print(f"✅ Parsed {len(jobs)} SimplifyJobs listings "
          f"({skip_reasons['not_student_friendly']} skipped for relevance, "
          f"{skip_reasons['invalid_link']} invalid links).")

    return jobs, skip_reasons
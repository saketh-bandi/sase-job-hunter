# main.py (hardened + strict PhD/MS filter + summary + flags)

import argparse
import re
import time
from pathlib import Path
from typing import List, Dict

# --- Config & clients ---
from config import MAX_POSTS_PER_RUN, UNDESIRABLE_KEYWORDS
from reddit_client import fetch_ranked_cs_jobs
from github_feed import fetch_simplify_jobs
from discord_client import send_to_discord

POSTED_JOBS_FILE = "posted_jobs.txt"

# ------------------------------
# Utilities
# ------------------------------

def _norm_url(u: str) -> str:
    return (u or "").split("?")[0].rstrip("/")

def deduplicate_jobs(jobs: List[Dict]) -> List[Dict]:
    """Remove duplicates by canonicalized URL, keep first occurrence."""
    seen = set()
    out = []
    for job in jobs or []:
        key = _norm_url(job.get("url", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(job)
    return out

# ------------------------------
# Location filtering (CA or Remote only)
# ------------------------------

REMOTE_SYNONYMS = {
    "remote", "remote-friendly", "remotefriendly", "work from home",
    "wfh", "anywhere in usa", "anywhere in us", "us remote", "usa remote",
    "north america remote", "fully remote", "hybrid (remote"
}

CA_CITIES = {
    "san francisco", "sf", "oakland", "berkeley", "san jose", "sj",
    "palo alto", "mountain view", "mv", "cupertino", "sunnyvale",
    "santa clara", "menlo park", "redwood city", "fremont",
    "los angeles", "la", "santa monica", "pasadena", "irvine",
    "san diego", "sd", "sacramento"
}

RE_STATE_CA = re.compile(r"(?:,|\b)\s*CA(?:\b|,|$)", re.I)  # matches ", CA" / " CA " / end

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())

def _is_remote(text: str) -> bool:
    t = _norm(text)
    return any(word in t for word in REMOTE_SYNONYMS)

def _is_california_location(blob: str) -> bool:
    """True if the blob clearly indicates California (cities or state), token-aware."""
    t = _norm(blob)

    # city tokens
    for city in CA_CITIES:
        if re.search(rf"(?:^|[\s,;\/\-\|·•]){re.escape(city)}(?:$|[\s,;\/\-\|·•])", t):
            return True

    # 'California'
    if re.search(r"(?:^|[\s,;\/\-\|·•])california(?:$|[\s,;\/\-\|·•])", t):
        return True

    # state code 'CA' as its own token
    if RE_STATE_CA.search(t):
        return True

    return False

def filter_by_location(jobs: List[Dict]) -> List[Dict]:
    """
    Keep jobs that are clearly California or Remote.
    - Build a haystack from title + locations.
    - Accept if remote OR California is detected.
    - If locations list is empty, only keep if title suggests remote.
    """
    kept = []
    for job in jobs or []:
        title = job.get("title", "")
        locs = job.get("locations") or []

        if not isinstance(locs, list):
            locs = [str(locs)]

        haystack = " | ".join([title] + [str(x) for x in locs if x])

        if _is_remote(haystack) or _is_california_location(haystack):
            kept.append(job)
            continue

        if not locs and _is_remote(title):
            kept.append(job)

    return kept

# ------------------------------
# Final Quality Filter
# ------------------------------

def filter_by_undesirables(jobs: List[Dict]) -> List[Dict]:
    """
    Strictest and final filter. Rejects a job if its title contains any
    undesirable keyword (e.g., "PhD", "Master's", "Senior").
    Case-insensitive. No exceptions.
    """
    kept = []
    for job in jobs or []:
        title_lower = job.get("title", "").lower()
        if any(keyword in title_lower for keyword in UNDESIRABLE_KEYWORDS):
            continue  # Reject immediately
        kept.append(job)
    return kept


# ------------------------------
# Main
# ------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true",
                        help="Ignore posted_jobs.txt and treat all as new.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Do everything except send to Discord / write file.")
    args = parser.parse_args()

    overall_start_time = time.time()
    print("SASE Job Hunter v2 - Starting Run")

    # --- 1) Setup ---
    posted_jobs_file = Path(POSTED_JOBS_FILE)
    posted_jobs_file.touch(exist_ok=True)
    posted_urls = set()
    if not args.force:
        posted_urls = {
            line.strip()
            for line in posted_jobs_file.read_text().splitlines()
            if line.strip()
        }
    print(f"Found {len(posted_urls)} previously posted jobs. (force={args.force})")

    # --- 2) Fetch ---
    reddit_jobs, _ = fetch_ranked_cs_jobs()
    simplify_jobs, _ = fetch_simplify_jobs()

    # --- 3) Process ---
    all_jobs = (reddit_jobs or []) + (simplify_jobs or [])
    unique_jobs_in_run = deduplicate_jobs(all_jobs)
    location_filtered_jobs = filter_by_location(unique_jobs_in_run)
    final_filtered_jobs = filter_by_undesirables(location_filtered_jobs)

    if args.force:
        new_jobs = final_filtered_jobs
    else:
        new_jobs = [
            j for j in final_filtered_jobs
            if _norm_url(j.get("url", "")) not in posted_urls
        ]

    # --- 4) Prepare & Post ---
    jobs_to_post = new_jobs[:MAX_POSTS_PER_RUN]

    # Summary line (always prints)
    print(
        f"SUMMARY — total:{len(all_jobs)} | unique:{len(unique_jobs_in_run)} "
        f"| loc_ok:{len(location_filtered_jobs)} "
        f"| final_ok:{len(final_filtered_jobs)} | new:{len(new_jobs)} | posting:{len(jobs_to_post)}"
    )

    if not jobs_to_post:
        print("\nNo new, relevant job posts found in this run.")
    else:
        if args.dry_run:
            print("\nDRY RUN — would post:")
            for j in jobs_to_post:
                locs = " / ".join(j.get("locations") or [])
                print(f"• {j.get('title')} | {locs} | {j.get('source')}")
        else:
            print(f"\nPosting {len(jobs_to_post)} new, relevant jobs to Discord…")
            send_to_discord(jobs_to_post)
            with posted_jobs_file.open("a") as f:
                for job in jobs_to_post:
                    f.write(_norm_url(job.get("url", "")) + "\n")

    overall_end_time = time.time()
    print(f"\n--- Total run completed in {overall_end_time - overall_start_time:.2f}s ---")

# call guard (helps surface hidden errors)
if __name__ == "__main__":
    print("BOOT — entering main.py")
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()

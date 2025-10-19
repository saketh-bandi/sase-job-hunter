import time
from config import SUBREDDITS, FETCH_LIMIT, MAX_POSTS_PER_RUN
from reddit_client import fetch_ranked_cs_jobs
from github_feed import fetch_simplify_jobs
from discord_client import send_to_discord

POSTED_JOBS_FILE = "posted_jobs.txt"

def format_age(seconds):
    if seconds < 3600:
        return f"{int(seconds / 60)}m"
    elif seconds < 86400:
        return f"{int(seconds / 3600)}h"
    else:
        return f"{int(seconds / 86400)}d"

def deduplicate_jobs_in_run(jobs: list[dict]) -> list[dict]:
    """Removes duplicate jobs from a single run based on their URL."""
    seen_urls = set()
    deduped_jobs = []
    for job in jobs:
        url_key = job['url'].split('?')[0].rstrip('/')
        if url_key not in seen_urls:
            seen_urls.add(url_key)
            deduped_jobs.append(job)
    return deduped_jobs

def filter_already_posted(jobs: list[dict], posted_urls: set) -> list[dict]:
    """Filters out jobs that have already been posted in previous runs."""
    new_jobs = []
    for job in jobs:
        url_key = job['url'].split('?')[0].rstrip('/')
        if url_key not in posted_urls:
            new_jobs.append(job)
    return new_jobs

def main():
    print("SASE Job Hunter v2 - Starting Run")
    start_time = time.time()

    # --- Load already posted jobs ---
    try:
        with open(POSTED_JOBS_FILE, "r") as f:
            posted_urls = set(line.strip() for line in f)
        print(f"Found {len(posted_urls)} previously posted jobs in '{POSTED_JOBS_FILE}'.")
    except FileNotFoundError:
        posted_urls = set()
        print(f"'{POSTED_JOBS_FILE}' not found. Starting with a clean slate.")

    # --- Fetch from all sources ---
    reddit_jobs, reddit_stats = fetch_ranked_cs_jobs(SUBREDDITS, FETCH_LIMIT)
    print(f"Fetched {len(reddit_jobs)} ranked jobs from Reddit.")

    simplify_jobs, simplify_stats = fetch_simplify_jobs()
    if simplify_jobs:
        print("\n--- 1. DATA AT SOURCE ---")
        print(simplify_jobs[0])
    print("-------------------------\n")
    print(f"Fetched {len(simplify_jobs)} jobs from SimplifyJobs GitHub.")

    # --- Merge and Process ---
    # De-duplicate and filter jobs from each source individually
    new_reddit_jobs = filter_already_posted(deduplicate_jobs_in_run(reddit_jobs), posted_urls)
    new_simplify_jobs = filter_already_posted(deduplicate_jobs_in_run(simplify_jobs), posted_urls)

    # For summary purposes, get a list of all unique new jobs found
    new_jobs = deduplicate_jobs_in_run(new_reddit_jobs + new_simplify_jobs)

    # --- Priority-based merging ---
    final_jobs = []
    seen_urls = set()

    # 1. Add all new Reddit jobs (priority)
    for job in new_reddit_jobs:
        url_key = job['url'].split('?')[0].rstrip('/')
        if url_key not in seen_urls:
            final_jobs.append(job)
            seen_urls.add(url_key)

    # 2. Add new Simplify jobs until the limit is reached
    for job in new_simplify_jobs:
        if len(final_jobs) >= MAX_POSTS_PER_RUN:
            break
        url_key = job['url'].split('?')[0].rstrip('/')
        if url_key not in seen_urls:
            final_jobs.append(job)
            seen_urls.add(url_key)
    
    # Ensure the final list does not exceed the maximum number of posts
    final_jobs = final_jobs[:MAX_POSTS_PER_RUN]

    # Sort the final list by date for display
    final_jobs.sort(key=lambda x: x["created_utc"], reverse=True)

    # --- Display Results ---
    print("\n--- Summary ---")
    if "internship_pass" in reddit_stats:
        print("Reddit - Internship Pass:")
        intern_stats = reddit_stats["internship_pass"]
        print(f"  - Fetched {intern_stats.get('fetched', 0)} posts, Found {intern_stats.get('filtered', 0)} jobs")
        for reason, count in intern_stats.get('skipped', {}).items():
            if count > 0:
                print(f"    - Skipped {count} posts (reason: {reason})")

    if "new_grad_pass" in reddit_stats:
        print("Reddit - New Grad Pass:")
        new_grad_stats = reddit_stats["new_grad_pass"]
        print(f"  - Fetched {new_grad_stats.get('fetched', 0)} posts, Found {new_grad_stats.get('filtered', 0)} jobs")
        for reason, count in new_grad_stats.get('skipped', {}).items():
            if count > 0:
                print(f"    - Skipped {count} posts (reason: {reason})")

    print(f"SimplifyJobs: Found {len(simplify_jobs)} jobs")
    for reason, count in simplify_stats.items():
        if count > 0:
            print(f"  - Skipped {count} SimplifyJobs rows (reason: {reason})")

    print(f"Total new jobs found: {len(new_jobs)}")
    print(f"Displayed top {len(final_jobs)} jobs.")
    print(f"Run completed in {time.time() - start_time:.2f}s")
    print("---------------")

    if not final_jobs:
        print("\nNo suitable job posts found in this run.")
        return

    print(f"\n--- Top {len(final_jobs)} Student-Friendly Job Postings ---")
    current_time = time.time()
    for i, job in enumerate(final_jobs, 1):
        age_seconds = current_time - job["created_utc"]
        age_str = format_age(age_seconds)
        location_str = ", ".join(job['locations']) if job['locations'] else "N/A"

        print(f"\n{i}) {job['title']}")
        print(f"   Source: {job['source']} | Age: {age_str}")
        print(f"   Location: {location_str}")
        print(f"   Link: {job['url']}")
        if job.get('description'):
            snippet = job['description'][:200]
            if len(job['description']) > 200:
                snippet += "..."
            print(f"   About: {snippet}")

    # >>> POST to Discord (INSIDE main) <<<
    print(f"\nPosting {len(final_jobs)} jobs to Discord…")
        # Inside main.py

   

    send_to_discord(final_jobs, limit=10)
    print("Posted to Discord call returned.")

    # --- Save newly posted jobs ---
    with open(POSTED_JOBS_FILE, "a") as f:
        for job in final_jobs:
            f.write(job['url'].split('?')[0].rstrip('/') + "\n")


if __name__ == "__main__":
    main()

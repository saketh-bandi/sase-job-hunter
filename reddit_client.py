import os
import praw
import time
import re
import requests
from dotenv import load_dotenv, find_dotenv
from requests.exceptions import RequestException, Timeout
from praw.exceptions import PRAWException
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from utils import (
    unwrap_shorteners, is_external_job_link, validate_job_url, 
    extract_experience_requirements
)

from config import (
    ATS_DOMAINS, INTERNSHIP_KEYWORDS, INTERNSHIP_BLOCKLIST, 
    NEW_GRAD_KEYWORDS, NEW_GRAD_BLOCKLIST, HIRING_KEYWORDS
)

# --- Constants ---
MAX_VALIDATIONS_PER_RUN = 50
VALIDATION_COUNTER = 0

# Patterns to identify and block megathreads
MEGATHREAD_PATTERNS = [
    r'^Daily', r'^Weekly', r'^Megathread'
]

BLOCK_DOMAINS = [
    "medium.com", "substack.com", "youtube.com", "news.ycombinator.com",
    "reddit.com", "redd.it", "imgur.com", "i.redd.it"
]

# Domains to skip full HTTP validation for
ATS_SKIP_VALIDATION_DOMAINS = [
    "greenhouse.io", "lever.co", "myworkdayjobs.com", "ashbyhq.com",
    "smartrecruiters.com", "workable.com", "icims.com"
]

# --- Reddit Client Initialization ---
def get_reddit_client():
    """Loads credentials from .env and returns a PRAW client."""
    load_dotenv(find_dotenv())
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent="SASE Job Hunter Bot v1 by u/SASE_Job_Hunter"
    )
    return reddit

# --- URL Validation and Handling ---
def unwrap_shorteners(url: str) -> str:
    """Unwraps shortened URLs like bit.ly, t.co, etc., with a timeout."""
    try:
        response = requests.head(url, allow_redirects=True, timeout=4)
        return response.url
    except (RequestException, Timeout):
        return url

def is_external_job_link(url: str) -> bool:
    """
    Checks if a URL is a likely external job link based on domain and path.
    Excludes common non-job sites.
    """
    if not url or not url.startswith('http'):
        return False

    try:
        parsed_url = urlparse(url)
    except ValueError:
        print(f" Could not parse URL: {url}")
        return False
        
    domain = parsed_url.netloc.lower()
    path = parsed_url.path.lower()

    if any(d in domain for d in BLOCK_DOMAINS):
        return False
    if any(path.endswith(ext) for ext in ['.jpg', '.png', '.gif', '.jpeg']):
        return False

    if any(ats in domain for ats in ATS_DOMAINS):
        return True

    if re.search(r'careers|jobs|join-?us|/careers/|/jobs/', f"{domain}{path}"):
        return True

    return False

def validate_job_url(url: str) -> tuple[bool, str]:
    """
    Validates if a job URL is active. Skips full validation for known ATS domains.
    Returns (is_valid, final_url).
    """
    global VALIDATION_COUNTER
    if VALIDATION_COUNTER >= MAX_VALIDATIONS_PER_RUN:
        return False, url

    VALIDATION_COUNTER += 1
    
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36'}
    
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        if any(ats_domain in domain for ats_domain in ATS_SKIP_VALIDATION_DOMAINS) or \
           domain.startswith(('boards.', 'careers.', 'jobs.')):
            return True, url

        response = requests.head(url, headers=headers, allow_redirects=True, timeout=4)
        final_url = response.url
        if response.status_code >= 400:
            get_response = requests.get(url, headers=headers, timeout=4)
            final_url = get_response.url
            if get_response.status_code >= 400:
                return False, final_url
        
        return True, final_url

    except (RequestException, Timeout):
        return False, url

# --- Core Fetching and Filtering Logic ---
def fetch_raw_posts(subreddits: list[str], limit: int, keywords: list[str]) -> list[dict]:
    """For each subreddit, pull the newest posts based on a keyword search."""
    reddit = get_reddit_client()
    all_posts = []
    print(f"Fetching raw posts from {len(subreddits)} subreddits for keywords: {', '.join(keywords)}...")
    for sub in subreddits:
        try:
            subreddit = reddit.subreddit(sub)
            # Using search instead of new
            query = ' OR '.join(f'title:"{k}"' for k in keywords)
            posts = list(subreddit.search(query, sort='new', limit=limit))
            print(f"  - Fetched {len(posts)} posts from r/{sub}")
            for post in posts:
                all_posts.append({
                    "id": post.id, "title": post.title, "selftext": post.selftext,
                    "url": post.url, "permalink": f"https://reddit.com{post.permalink}",
                    "subreddit": sub, "created_utc": post.created_utc,
                    "is_self": post.is_self, "stickied": post.stickied,
                    "ups": post.ups,
                })
        except (RequestException, PRAWException) as e:
            print(f"Error fetching from r/{sub}: {e}. Skipping...")
    return all_posts

def filter_and_rank_jobs(posts: list[dict], title_blocklist: list[str], job_keywords: list[str]) -> tuple[list[dict], dict]:
    """
    Filters posts for valid, student-friendly jobs.
    """
    valid_jobs = []
    url_pattern = r'https?://[^\s()<>]+(?<![.,!?:;])'
    
    counters = {
        "matched_by_keyword": 0,
        "blocked_megathread": 0,
        "blocked_title": 0,
        "blocked_no_hiring_intent": 0,
        "invalid_link": 0,
        "stickied": 0,
        "no_link": 0,
    }

    for post in posts:
        if post["stickied"]:
            counters["stickied"] += 1
            continue

        title = post['title']
        selftext = post['selftext']
        title_lower = title.lower()

        # Combined keyword and hiring intent check
        if not (any(job_kw in title_lower for job_kw in job_keywords) and \
                any(hiring_kw in title_lower for hiring_kw in HIRING_KEYWORDS)):
            counters["blocked_no_hiring_intent"] += 1
            continue

        if any(word in title_lower for word in title_blocklist):
            counters["blocked_title"] += 1
            continue

        if any(re.search(p, title, re.IGNORECASE) for p in MEGATHREAD_PATTERNS):
            counters["blocked_megathread"] += 1
            continue

        found_urls = re.findall(url_pattern, selftext)
        if post['url'] and not post['is_self']:
             found_urls.insert(0, post['url'])
        
        unwrapped_urls = [unwrap_shorteners(url) for url in found_urls]
        external_urls = [url for url in unwrapped_urls if is_external_job_link(url)]
        
        counters["matched_by_keyword"] += 1

        url_to_validate = None
        if external_urls:
            url_to_validate = external_urls[0]
        
        if not url_to_validate:
            counters["no_link"] += 1
            continue

        is_valid, final_url = validate_job_url(url_to_validate)
        if not is_valid:
            counters["invalid_link"] += 1
            continue
        
        post['url'] = final_url
        valid_jobs.append(post)

    return valid_jobs, counters

# --- Enrichment and Normalization ---
def normalize_to_jobposts(posts: list[dict]) -> list[dict]:
    """Maps filtered posts to the final JobPost schema."""
    job_posts = []
    for post in posts:
        title = post["title"].strip()
        # Remove [Hiring] tag for cleaner output
        if "[hiring]" in title.lower():
            title = re.sub(r'\[hiring\]', '', title, flags=re.IGNORECASE).strip()

        all_keywords = INTERNSHIP_KEYWORDS + NEW_GRAD_KEYWORDS
        tags = [kw for kw in all_keywords if kw in post["title"].lower()]
        
        experience = extract_experience_requirements(post["url"])
        
        job_posts.append({
            "id": post["id"],
            "title": title,
            "url": post["url"],
            "source": f"r/{post['subreddit']}",
            "created_utc": post["created_utc"],
            "locations": re.findall(r'\[(.*?)\]', post["title"]),
            "tags": list(set(tags)),
            "experience": experience,
        })
    return job_posts

# --- Main Orchestrator ---
def fetch_ranked_cs_jobs(subreddits: list[str], limit: int) -> tuple[list[dict], dict]:
    """Orchestrates the full job fetching, filtering, and ranking pipeline with a two-pass strategy."""
    global VALIDATION_COUNTER
    VALIDATION_COUNTER = 0
    
    stats = {"internship_pass": {}, "new_grad_pass": {}}
    
    # --- Pass 1: Internship Hunt ---
    print("--- Starting Internship Hunt ---")
    internship_posts = fetch_raw_posts(subreddits, limit, INTERNSHIP_KEYWORDS)
    stats["internship_pass"]['fetched'] = len(internship_posts)

    valid_internships, intern_filter_stats = filter_and_rank_jobs(internship_posts, INTERNSHIP_BLOCKLIST, INTERNSHIP_KEYWORDS)
    stats["internship_pass"]['filtered'] = len(valid_internships)
    stats["internship_pass"]['skipped'] = intern_filter_stats

    # --- Pass 2: New-Grad Hunt ---
    print("\n--- Starting New-Grad Hunt ---")
    new_grad_posts = fetch_raw_posts(subreddits, limit, NEW_GRAD_KEYWORDS)
    stats["new_grad_pass"]['fetched'] = len(new_grad_posts)

    valid_new_grad, new_grad_filter_stats = filter_and_rank_jobs(new_grad_posts, NEW_GRAD_BLOCKLIST, NEW_GRAD_KEYWORDS)
    stats["new_grad_pass"]['filtered'] = len(valid_new_grad)
    stats["new_grad_pass"]['skipped'] = new_grad_filter_stats
    
    # --- Merge, De-duplicate, and Normalize ---
    combined_valid_posts = valid_internships + valid_new_grad
    
    # De-duplicate based on post ID
    seen_ids = set()
    unique_posts = []
    for post in combined_valid_posts:
        if post['id'] not in seen_ids:
            unique_posts.append(post)
            seen_ids.add(post['id'])
            
    stats['total_unique_posts'] = len(unique_posts)

    final_jobs = normalize_to_jobposts(unique_posts)
    
    final_jobs.sort(key=lambda x: x["created_utc"], reverse=True)

    return final_jobs, stats
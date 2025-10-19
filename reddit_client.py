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

from config import ATS_DOMAINS

# --- Constants ---
MAX_VALIDATIONS_PER_RUN = 50
VALIDATION_COUNTER = 0

# Keywords for student-friendly job posts
STUDENT_FRIENDLY_TOKENS = [
    'intern', 'internship', 'new grad', 'new-grad', 'entry level',
    'junior', 'university', 'campus', 'early career', 'undergrad',
    'undergraduate', 'freshman', 'sophomore', 'co-op'
]

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
        user_agent=os.getenv("REDDIT_USER_AGENT"),
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

    parsed_url = urlparse(url)
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

def extract_experience_requirements(url: str) -> str:
    """
    Fetches the job page and tries to extract experience requirements.
    Returns a string with the findings.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        text = soup.get_text().lower()
        
        patterns = [
            r'(\d+\+?)\s+years? of experience',
            r'graduating between (\w+\s+\d{4}) and (\w+\s+\d{4})',
            r'pursuing a degree in .* and graduating in (\d{4})',
            r'class of (\d{4})',
            r'(freshman|sophomore|junior|senior|undergraduate|undergrad|masters|phd)',
            r'co-op'
        ]
        
        found_requirements = []
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                for match in matches:
                    if isinstance(match, tuple):
                        found_requirements.append(" ".join(match))
                    else:
                        found_requirements.append(match)

        if found_requirements:
            return ", ".join(list(set(found_requirements)))
            
        return "N/A"
        
    except (RequestException, Timeout):
        return "Could not fetch."
    except Exception:
        return "Error parsing."

# --- Core Fetching and Filtering Logic ---
def fetch_raw_posts(subreddits: list[str], limit: int) -> list[dict]:
    """For each subreddit, pull the newest posts."""
    reddit = get_reddit_client()
    all_posts = []
    print(f"Fetching raw posts from {len(subreddits)} subreddits...")
    for sub in subreddits:
        try:
            subreddit = reddit.subreddit(sub)
            posts = list(subreddit.new(limit=limit))
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

def filter_and_rank_jobs(posts: list[dict]) -> tuple[list[dict], dict]:
    """
    Filters posts for valid, student-friendly jobs.
    """
    valid_jobs = []
    url_pattern = r'https?://[^\s()<>]+(?<![.,!?:;])'
    
    counters = {
        "matched_by_title": 0,
        "matched_by_body": 0,
        "matched_by_ats_link": 0,
        "blocked_megathread": 0,
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

        if any(re.search(p, title, re.IGNORECASE) for p in MEGATHREAD_PATTERNS):
            counters["blocked_megathread"] += 1
            continue

        found_urls = re.findall(url_pattern, selftext)
        if post['url'] and not post['is_self']:
             found_urls.insert(0, post['url'])
        
        unwrapped_urls = [unwrap_shorteners(url) for url in found_urls]
        external_urls = [url for url in unwrapped_urls if is_external_job_link(url)]
        
        matched_title = any(token in title_lower for token in STUDENT_FRIENDLY_TOKENS)
        matched_body = any(token in selftext.lower() for token in STUDENT_FRIENDLY_TOKENS)
        
        ats_links = [url for url in external_urls if any(ats in urlparse(url).netloc for ats in ATS_DOMAINS)]
        matched_ats = bool(ats_links)

        if matched_title:
            counters["matched_by_title"] += 1
        if matched_body:
            counters["matched_by_body"] += 1
        if matched_ats:
            counters["matched_by_ats_link"] += 1

        if not (matched_title or matched_body or matched_ats):
            continue

        url_to_validate = None
        if ats_links:
            url_to_validate = ats_links[0]
        elif external_urls:
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
        tags = [kw for kw in STUDENT_FRIENDLY_TOKENS if kw in post["title"].lower()]
        
        experience = extract_experience_requirements(post["url"])
        
        job_posts.append({
            "id": post["id"],
            "title": post["title"].strip(),
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
    """Orchestrates the full job fetching, filtering, and ranking pipeline."""
    global VALIDATION_COUNTER
    VALIDATION_COUNTER = 0
    
    stats = {}
    raw_posts = fetch_raw_posts(subreddits, limit)
    stats['fetched'] = len(raw_posts)

    valid_jobs, filter_stats = filter_and_rank_jobs(raw_posts)
    stats['filtered'] = len(valid_jobs)
    stats['skipped'] = filter_stats

    final_jobs = normalize_to_jobposts(valid_jobs)
    
    final_jobs.sort(key=lambda x: x["created_utc"], reverse=True)

    return final_jobs, stats

# reddit_client.py (hardened, still high-speed)
import os
import re
import time
from typing import List, Dict, Tuple
import praw
from dotenv import load_dotenv, find_dotenv

from config import SUBREDDITS, FETCH_LIMIT, INTERNSHIP_KEYWORDS, HIRING_KEYWORDS, REDDIT_BLOCKLIST
from utils import unwrap_shorteners, is_external_job_link

# Precompiled patterns
MEGATHREAD_RES = [
    re.compile(r"^(daily|weekly).*(thread|hiring)", re.I),
    re.compile(r"\bmega(thread)?\b", re.I),
]
WORDY_HIRE = re.compile(r"\b(hiring|hire|opening|positions?|opportunit(y|ies))\b", re.I)
WORDY_INTERN = re.compile(r"\b(intern(ship)?|co-?op|coop|university\s+program)\b", re.I)
BLOCKLIST_RE = re.compile("|".join(re.escape(w) for w in REDDIT_BLOCKLIST), re.I)

# URL pattern also catches markdown links: [text](url)
URL_RE = re.compile(r"""
    (?:
      \[ [^\]]+ \] \( (?P<md>https?://[^\s)]+) \)   # markdown link
      |
      (?P<bare>https?://[^\s()<>]+(?<![.,!?:;]))
    )
""", re.X | re.I)

TITLE_TAG_RE = re.compile(r"(?i)\[(hiring|remote|us|usa|ca|onsite|sf|bay|nyc)\]")

def get_reddit_client() -> praw.Reddit:
    """Initializes and returns the PRAW client."""
    load_dotenv(find_dotenv())
    cid = os.getenv("REDDIT_CLIENT_ID")
    csec = os.getenv("REDDIT_CLIENT_SECRET")
    if not cid or not csec:
        raise RuntimeError("Missing REDDIT_CLIENT_ID/REDDIT_CLIENT_SECRET")
    reddit = praw.Reddit(
        client_id=cid,
        client_secret=csec,
        user_agent="SASE Job Hunter Bot v1.1 (contact: your_email@example.com)"
    )
    reddit.read_only = True
    return reddit

def _extract_urls(text: str) -> List[str]:
    urls = []
    for m in URL_RE.finditer(text or ""):
        u = m.group("md") or m.group("bare")
        if u:
            urls.append(u)
    return urls

def _clean_title(t: str) -> str:
    t = TITLE_TAG_RE.sub("", t).strip()
    # Remove repeated spaces and leading punctuation artifacts
    return re.sub(r"\s{2,}", " ", t).strip(" -|·•")

def _locations_from_title(t: str) -> List[str]:
    # Grab bracketed items then split on common separators
    locs = []
    for raw in re.findall(r"\[(.*?)\]", t):
        for piece in re.split(r"[|/,·•]+", raw):
            p = piece.strip()
            if p and p.lower() not in {"hiring", "remote", "onsite", "us", "usa"}:
                locs.append(p)
    return locs

def fetch_raw_posts(subreddits: List[str], limit: int, keywords: List[str]) -> List[Dict]:
    """
    Faster strategy: fetch 'new' and filter locally with regex/keywords.
    Avoids Reddit search quirks and reduces misses.
    """
    reddit = get_reddit_client()
    all_posts: List[Dict] = []
    print(f"Scanning {len(subreddits)} subreddits (latest posts)…")
    for sub in subreddits:
        try:
            sr = reddit.subreddit(sub)
            # Fetch more than limit so filtering still leaves enough
            candidates = list(sr.new(limit=limit * 3))
            print(f"  - Pulled {len(candidates)} from r/{sub}")
            for p in candidates:
                all_posts.append({
                    "id": p.id,
                    "title": p.title or "",
                    "selftext": p.selftext or "",
                    "url": getattr(p, "url", "") or "",
                    "subreddit": sub,
                    "created_utc": getattr(p, "created_utc", 0) or 0,
                    "is_self": getattr(p, "is_self", False),
                    "stickied": getattr(p, "stickied", False),
                    # Optional: p.link_flair_text if you want flair-based rules
                    "flair": getattr(p, "link_flair_text", None),
                })
        except Exception as e:
            print(f"⚠️  Error fetching r/{sub}: {e} — skipping")
            continue
    return all_posts

def filter_and_process_posts(posts: List[Dict]) -> Tuple[List[Dict], Dict]:
    """
    Text-only, high-speed filtering. No network validation of links.
    """
    valid_jobs: List[Dict] = []
    counters = {
        "stickied": 0,
        "blocked_megathread": 0,
        "blocked_title": 0,
        "blocked_no_hiring_intent": 0,
        "no_link": 0,
        "kept": 0,
        "scanned": len(posts),
    }

    for post in posts:
        title = post.get("title", "")
        title_lower = title.lower()

        if post.get("stickied"):
            counters["stickied"] += 1
            continue

        if any(r.search(title) for r in MEGATHREAD_RES):
            counters["blocked_megathread"] += 1
            continue

        if BLOCKLIST_RE.search(title):
            counters["blocked_title"] += 1
            continue

        # Hiring intent: require both a hiring word and an intern/coop word
        if not (WORDY_HIRE.search(title) and WORDY_INTERN.search(title)):
            counters["blocked_no_hiring_intent"] += 1
            continue

        found_urls = _extract_urls(post.get("selftext", ""))
        # If it's a link post, prioritize that URL first
        if post.get("url") and not post.get("is_self"):
            found_urls.insert(0, post["url"])

        potential = []
        for u in found_urls:
            if is_external_job_link(u):
                try:
                    potential.append(unwrap_shorteners(u))
                except Exception:
                    # If unwrap fails, still consider the raw url
                    potential.append(u)

        if not potential:
            counters["no_link"] += 1
            continue

        post["url"] = potential[0]
        valid_jobs.append(post)
        counters["kept"] += 1

    return valid_jobs, counters

def normalize_to_job_schema(posts: List[Dict]) -> List[Dict]:
    """Map filtered Reddit posts to your Job schema."""
    jobs = []
    for post in posts:
        clean = _clean_title(post["title"])
        jobs.append({
            "id": post["id"],
            "title": clean,
            "url": post["url"],
            "source": f"r/{post['subreddit']}",
            "created_utc": post["created_utc"],
            "locations": _locations_from_title(post["title"]),  # parse from original
            "description": "",
        })
    return jobs

def fetch_ranked_cs_jobs() -> Tuple[List[Dict], Dict]:
    """Orchestrates the full, high-speed internship fetching pipeline."""
    stats = {"skipped": {}, "totals": {}}
    print("--- Starting Reddit Internship Hunt ---")

    t0 = time.time()
    raw_posts = fetch_raw_posts(SUBREDDITS, FETCH_LIMIT, INTERNSHIP_KEYWORDS)
    t1 = time.time()
    print(f"--- Raw fetch took {t1 - t0:.2f}s ---")

    valid_posts, filter_stats = filter_and_process_posts(raw_posts)
    t2 = time.time()
    print(f"--- Filter (text-only) took {t2 - t1:.2f}s ---")

    # Dedupe by normalized URL here as an extra guard (crossposts)
    seen_urls = set()
    deduped = []
    for p in valid_posts:
        key = (p.get("url") or "").split("?")[0].rstrip("/")
        if key and key not in seen_urls:
            seen_urls.add(key)
            deduped.append(p)

    final_jobs = normalize_to_job_schema(deduped)
    final_jobs.sort(key=lambda x: x["created_utc"], reverse=True)

    stats["skipped"] = filter_stats
    stats["totals"] = {"raw": len(raw_posts), "valid": len(valid_posts), "deduped": len(final_jobs)}
    print(f"Fetched {len(final_jobs)} ranked jobs from Reddit.")
    return final_jobs, stats

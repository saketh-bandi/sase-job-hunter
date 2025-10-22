# config.py

# =============================================================================
# Subreddit Configuration
# =============================================================================
# High-quality, focused subreddits for finding internships.
SUBREDDITS = [
    "internships",
    "DataScienceJobs",
    "MLJobs",
]
2
# =============================================================================
# Reddit Search & Filtering Strategy (Internship-Only)
# =============================================================================
# The bot will ONLY search for posts containing these keywords on Reddit.
INTERNSHIP_KEYWORDS = [
    "intern", "internship", "co-op", "summer 2026", "sophomore", "freshman"
]

# A post must ALSO contain one of these to be considered a real job posting.
HIRING_KEYWORDS = ["hiring", "apply", "job", "position", "opening"]
FULL_TIME_INDICATORS = ["new grad", "bachelor's degree", "bs degree"]
# Aggressive blocklist for rejecting low-quality discussion posts on Reddit.
REDDIT_BLOCKLIST = [
    "list", "sharing", "compilation", "collection", "resources",
    "mega-thread", "discussion", "study", "find jobs", "my list"
]

# =============================================================================
# General & Location Filtering
# =============================================================================
# Keywords for filtering relevant locations for UC Merced students (case-insensitive).
VALID_LOCATIONS = [
    "remote", "california", "ca", "sf", "san francisco",
    "los angeles", "la", "san diego", "irvine", "mountain view",
    "palo alto", "sunnyvale", "san jose"
]

# General keywords for identifying student-friendly roles across ALL sources.
STUDENT_FRIENDLY_TOKENS = [
    "intern", "internship", "new grad", "new-grad", "entry level", "junior",
    "university", "campus", "early career", "sophomore", "freshman",
    "summer", "co-op", "coop", "research", "undergraduate", "student"
]

# =============================================================================
# Final Quality Filter
# =============================================================================
# Aggressive, "no exceptions" filter to reject jobs requiring a completed degree.
# If a job title contains any of these, it is IMMEDIATELY REJECTED.
UNDESIRABLE_KEYWORDS = [
    "phd", "master's", "masters", "ms", "bachelor's", "bachelors", "bs",
    "senior", "sr.", "lead", "principal"
]

# =============================================================================
# URL Validation & Scraping Settings
# =============================================================================
# Domains for common non-job sites that should be ignored.
BLOCK_DOMAINS = [
    "medium.com", "substack.com", "youtube.com", "news.ycombinator.com",
    "reddit.com", "redd.it", "imgur.com", "i.redd.it"
]

# Domains for trusted Applicant Tracking Systems (ATS) for link validation.
ATS_DOMAINS = [
    "boards.greenhouse.io", "lever.co", "myworkdayjobs.com", "ashbyhq.com",
    "smartrecruiters.com", "workable.com", "icims.com", "jobs.lever.co",
]

# "Express Lane": Domains to skip slow HTTP validation for, improving reliability.
ATS_SKIP_VALIDATION_DOMAINS = [
    "greenhouse.io", "lever.co", "myworkdayjobs.com", "ashbyhq.com",
    "smartrecruiters.com", "workable.com", "icims.com", "oraclecloud.com",
    "eightfold.ai", "careerpuck.com", "wd1.myworkdayjobs.com",
    "wd5.myworkdayjobs.com", "wd12.myworkdayjobs.com"
]

# =============================================================================
# Script Limits & Sources
# =============================================================================
FETCH_LIMIT = 75
MAX_POSTS_PER_RUN = 10
MAX_VALIDATIONS_PER_RUN = 50

# URL for the Simplify Summer 2026 Internships list.
SIMPLIFY_GITHUB_RAW = "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/README.md"
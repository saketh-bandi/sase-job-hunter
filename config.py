SUBREDDITS = [
    "csmajors", "cscareerquestions", "internships", "EngineeringStudents",
    "ComputerEngineering", "datascience", "MLJobs", "DataScienceJobs"
]

# Case-insensitive tokens to identify student-friendly roles
MUST_HAVE_TOKENS = [
    "intern", "internship", "new grad", "new-grad", "entry level", "junior",
    "university", "campus", "early career", "sophomore", "freshman", "junior",
    "summer", "co-op", "coop", "research", "undergraduate", "student",
    "part-time", "part time", "fellowship"
]

# Case-insensitive tokens to filter out senior roles
BLOCK_TOKENS = [
    "senior", "sr.", "staff", "principal", "lead", "manager", "director",
    "iii", "iv", "v", "megathread", "daily", "weekly", "question", "faq"
]

# Domains for trusted Applicant Tracking Systems (ATS)
ATS_DOMAINS = [
    "boards.greenhouse.io", "lever.co", "myworkdayjobs.com", "ashbyhq.com",
    "smartrecruiters.com", "workable.com", "icims.com", "jobs.lever.co",
    "careers.", "jobs.", "workday"
]

# --- Flags ---
REQUIRE_EXTERNAL_LINK = True
REQUIRE_STUDENT_FRIENDLY = True
MAX_YEARS_EXPERIENCE = 1  # Reject roles requiring >= 2 years

# --- Limits ---
FETCH_LIMIT = 75  # Max posts to fetch from each subreddit
MAX_POSTS_PER_RUN = 10  # Final number of posts to display

# --- GitHub Feed ---
SIMPLIFY_GITHUB_RAW = "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/README.md"

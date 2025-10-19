SUBREDDITS = [
    "csmajors", "cscareerquestions", "internships", "EngineeringStudents",
    "ComputerEngineering", "datascience", "MLJobs", "DataScienceJobs","internships"
]

# --- Reddit Search Strategy ---

# Pass 1: Internship Hunt
INTERNSHIP_KEYWORDS = ["intern", "internship", "co-op"]
INTERNSHIP_BLOCKLIST = ["list", "sharing", "my list"]

# Pass 2: New-Grad Hunt
NEW_GRAD_KEYWORDS = ["new grad", "entry level", "junior"]
NEW_GRAD_BLOCKLIST = [
    "list", "sharing", "share", "find jobs", "remote jobs", 
    "my list", "hiring", "for hire"
]

HIRING_KEYWORDS = ["hiring", "apply", "job", "position", "opening"]

# --- GitHub Feed Keywords ---
SIMPLIFY_KEYWORDS = [
    "intern", "internship", "new grad", "new-grad", "entry level", "junior",
    "university", "campus", "early career", "sophomore", "freshman", "junior",
    "summer", "co-op", "coop", "research", "undergraduate", "student",
    "part-time", "part time", "fellowship"
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

import re
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from requests.exceptions import RequestException, Timeout

from config import ATS_DOMAINS

# --- Constants ---
MAX_VALIDATIONS_PER_RUN = 50
VALIDATION_COUNTER = 0

BLOCK_DOMAINS = [
    "medium.com", "substack.com", "youtube.com", "news.ycombinator.com",
    "reddit.com", "redd.it", "imgur.com", "i.redd.it"
]

ATS_SKIP_VALIDATION_DOMAINS = [
    "greenhouse.io", "lever.co", "myworkdayjobs.com", "ashbyhq.com",
    "smartrecruiters.com", "workable.com", "icims.com"
]

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
        print(f"⚠️  Could not parse URL: {url}")
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

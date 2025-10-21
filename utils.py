# utils.py

import re
import requests
from urllib.parse import urlparse
from requests.exceptions import RequestException, Timeout

# All configuration is now imported from the central config file.
from config import ATS_DOMAINS, ATS_SKIP_VALIDATION_DOMAINS, BLOCK_DOMAINS

def unwrap_shorteners(url: str) -> str:
    """Unwraps shortened URLs like bit.ly, t.co, etc., with a timeout."""
    try:
        # CORRECTED: Timeout is now 2 seconds
        response = requests.head(url, allow_redirects=True, timeout=3)
        return response.url
    except (RequestException, Timeout):
        return url

def is_external_job_link(url: str) -> bool:
    """Checks if a URL is a likely external job link based on domain and path."""
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
    Validates if a job URL is active by making a HEAD request.
    This function is now 'stateless' (it doesn't use a global counter).
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36'}

    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()

        # Skip full validation for known, reliable ATS domains for speed.
        if any(ats_domain in domain for ats_domain in ATS_SKIP_VALIDATION_DOMAINS):
            return True, url

        # CORRECTED: Timeout is now 2 seconds
        response = requests.head(url, headers=headers, allow_redirects=True, timeout=2)
        final_url = response.url

        # If HEAD fails, try a GET request as a fallback.
        if response.status_code >= 400:
            # CORRECTED: Timeout is now 2 seconds
            get_response = requests.get(url, headers=headers, timeout=2)
            final_url = get_response.url
            if get_response.status_code >= 400:
                return False, final_url

        return True, final_url

    except (RequestException, Timeout):
        return False, url
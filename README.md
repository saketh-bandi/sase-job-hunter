**UC Merced SASE Job Hunter Bot**

A Python bot that finds and posts relevant engineering internships and new grad job opportunities from Reddit and Simplify's curated list directly to the UC Merced Society of Asian Scientists and Engineers Discord server.

**Key Features**

- Automated Daily Posts: Runs automatically every day at 9:00 AM using GitHub Actions. This allows for complete automation and fresh opportunities each and everyday. 
- Multiple Sources: Pulls high quality job links from SimplifyJobs's curated list and new openings posted in Reddit communities.
- Intelligent Filtering: Uses a multi-layered filtering system that prioritizes internships, identifies "hiring intent" in post titles, and blocks low quality threads.
- De-Duplication: Uses a text file for long-term memory to ensure that a job already posted inside the channel isn't reposted.
- Formatting: Job listings posted in a professional and clean format.

**Technology**

- Language: Python
- Main Libraries:
    - PRAW: Python Reddit API Wrapper to handle API authentication and fetch posts from subreddits using keyword search.
    - Requests: Used for HTTP operations such as posting the jobs to discord and validating link URLs.
    - Beautifulsoup4: For HTML parsing and webscraping for job data.
    - python-dotenv: For secure credential management to prevent hardcoding API keys and Webhook URLs.
- Automation: GitHub Actions 
- Collaboration: GitHub



**Setup**

1.  Clone the repository:
    ```bash
    git clone https://github.com/saketh-bandi/sase-job-hunter.git
    ```
    
2.  Navigate into the project directory:
    ```bash
    cd sase-job-hunter
    ```

3.  Create and activate a virtual environment:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

4.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

5.  Create a .env file in the root directory and add your secret keys:
    ```env
    REDDIT_CLIENT_ID="YOUR_CLIENT_ID"
    REDDIT_CLIENT_SECRET="YOUR_CLIENT_SECRET"
    DISCORD_WEBHOOK_URL="YOUR_WEBHOOK_URL"
    ```

6.  Run the bot manually:
    ```bash
    python3 main.py
    ```


**Project Team**

- **Project Lead:** Saketh Bandi

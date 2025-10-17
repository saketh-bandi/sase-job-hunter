import os
import praw
from dotenv import load_dotenv

load_dotenv()
#authenticating using reddit keys
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent="SASE Job Hunter Bot v1 by u/SASE_Job_Hunter"
)

#testing authentication
print("Authentication w/ reddit working")


subreddit = reddit.subreddit("csmajors")
print(f"Retrieving newest posts from r/{subreddit.display_name}")

#gets 5 newest posts and prints their title
for post in subreddit.new(limit=5):
    print(f"  - {post.title}")
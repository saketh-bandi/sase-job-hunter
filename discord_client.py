import os
import requests
from dotenv import load_dotenv


load_dotenv()
webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

if not webhook_url:
    print("Add discord webhook url to env file.")
else:
    message_data = {
        "content": "SASE job hunter bot test",
        "username": "SASE Job Hunter Bot"
    }

    print("Attempting sending a message to discord")

    #sends message to webhoob url channel
    response = requests.post(webhook_url, json=message_data)

    if response.status_code == 204:
        print("Message was sent")
    else:
        print(f"Message didn't send")
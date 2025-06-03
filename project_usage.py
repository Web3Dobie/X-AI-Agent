from dotenv import load_dotenv
import os, sys
import requests

load_dotenv()

BEARER_TOKEN = os.environ.get("X_BEARER_TOKEN")

if not BEARER_TOKEN:
    print(">> No token found in X_BEARER_TOKEN! Exiting.", file=sys.stderr)
    sys.exit(1)
print(f"Token looks like: {BEARER_TOKEN[:10]}… (length {len(BEARER_TOKEN)})")
# …then proceed with the request

url = "https://api.x.com/2/usage/tweets"
headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}

resp = requests.get(url, headers=headers)
resp.raise_for_status()
data = resp.json()["data"]
usage = int(data["project_usage"])
cap   = int(data["project_cap"])
reset = int(data["cap_reset_day"])

print(f"Used {usage} of {cap} Posts. Resets on day {reset}.")

r = requests.get("https://api.x.com/2/users/me", headers=headers)
remaining = int(r.headers.get("x-rate-limit-remaining", 0))
reset_ts  = int(r.headers.get("x-rate-limit-reset", 0))
print(f"{remaining} calls left in this window. Window resets at {reset_ts} (epoch).")

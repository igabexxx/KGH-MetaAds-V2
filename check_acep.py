import urllib.request
import json
import time

SC_KEY = 'MTI0NjExMzgxNl9TeWhLc2dDdUlUVGcwQTdWTkZpVg=='
SC_BASE = 'https://api.socialchat.id/partner'

def sc_get(path):
    url = f"{SC_BASE}/{path.lstrip('/')}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {SC_KEY}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

print("Searching across all conversations...")
matches = []
page = 1
while page <= 10: # Fetch up to 5000 records
    try:
        data = sc_get(f'conversation?page={page}&limit=500')
        docs = data.get("docs", [])
        if not docs:
            break
        print(f"Page {page}: Fetched {len(docs)} conversations.")
        for c in docs:
            name = str(c.get('senderName', '')).lower()
            if 'acep' in name or 'byd' in name:
                matches.append(c)
        page += 1
    except Exception as e:
        print(f"Error on page {page}: {e}")
        break

if not matches:
    print("No matches found for 'Acep' or 'BYD'.")
else:
    print(f"\nFound {len(matches)} match(es):")
    for m in matches:
        agent = (m.get('agentBy') or {}).get('name', 'Unassigned')
        last_msg = (m.get('lastMessage') or {}).get('text', '')
        print(f"Name: {m.get('senderName')}")
        print(f"Agent/Channel: {agent}")
        print(f"Last Message: {last_msg}")
        print("-" * 30)

import urllib.request
import json
import urllib.parse

SC_KEY = "MTI0NjExMzgxNl9TeWhLc2dDdUlUVGcwQTdWTkZpVg=="
phone = "6281316917728"
search_url = f"https://api.socialchat.id/partner/conversation?page=1&limit=10&search={phone}"

req = urllib.request.Request(search_url)
req.add_header("Authorization", f"Bearer {SC_KEY}")

try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
        print(f"Docs found for phone '{phone}': {len(data.get('docs', []))}")
except Exception as e:
    print(f"Error: {e}")

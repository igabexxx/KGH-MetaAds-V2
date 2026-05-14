import urllib.request
import json
import urllib.parse
import sys

SC_KEY = "MTI0NjExMzgxNl9TeWhLc2dDdUlUVGcwQTdWTkZpVg=="
name = "aurawedding"
search_url = f"https://api.socialchat.id/partner/conversation?page=1&limit=10&search={urllib.parse.quote(name)}"

req = urllib.request.Request(search_url)
req.add_header("Authorization", f"Bearer {SC_KEY}")

try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
        print(f"Docs found for '{name}': {len(data.get('docs', []))}")
        for doc in data.get('docs', []):
            print(f"ID: {doc.get('_id')} | Name: {doc.get('senderName')} | Phone: {doc.get('senderId')}")
except Exception as e:
    print(f"Error fetching: {e}")

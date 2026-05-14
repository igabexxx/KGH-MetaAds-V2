import urllib.request
import json

SC_KEY = "MTI0NjExMzgxNl9TeWhLc2dDdUlUVGcwQTdWTkZpVg=="
convId = "69f462c07b21201de6b9ec8e"
msg_url = f"https://api.socialchat.id/partner/message/{convId}"

req = urllib.request.Request(msg_url)
req.add_header("Authorization", f"Bearer {SC_KEY}")

try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
        msgs = data.get('messages', [])
        print(f"Messages found: {len(msgs)}")
        if len(msgs) > 0:
            for m in msgs[:2]:
                print(f"From: {m.get('senderName')} - {m.get('text')}")
except Exception as e:
    print(f"Error fetching messages: {e}")

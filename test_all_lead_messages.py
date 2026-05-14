import urllib.request
import json

# Test messages for the lead with phone 6281316917728
for lead_id in [1041, 819, 603, 194]:
    url = f"https://api.kayanagreenhills.com/api/leads/{lead_id}/messages"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            msgs = data.get('messages', [])
            error = data.get('error', '')
            print(f"ID {lead_id}: {len(msgs)} messages | {error}")
            if msgs:
                print(f"  First: {msgs[0].get('text','[no text]')[:60]}")
                break
    except Exception as e:
        print(f"ID {lead_id}: Error - {e}")

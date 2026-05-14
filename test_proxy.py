import urllib.request
import json

# Test the backend proxy endpoint for aurawedding leads
# First find a lead ID from the leads list
url = "https://api.kayanagreenhills.com/api/leads?search=aurawedding&limit=1"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as resp:
        leads = json.loads(resp.read())
        if leads:
            lead_id = leads[0]['id']
            print(f"Found lead ID: {lead_id}")
            
            # Now test the messages proxy endpoint
            msg_url = f"https://api.kayanagreenhills.com/api/leads/{lead_id}/messages"
            msg_req = urllib.request.Request(msg_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(msg_req) as msg_resp:
                data = json.loads(msg_resp.read())
                msgs = data.get('messages', [])
                error = data.get('error', '')
                print(f"Messages found: {len(msgs)}")
                if error:
                    print(f"Error: {error}")
                if msgs:
                    print(f"First message: {msgs[0].get('text', '[no text]')[:80]}")
        else:
            print("No leads found for aurawedding")
except Exception as e:
    print(f"Error: {e}")

import urllib.request
import json

url = "https://api.kayanagreenhills.com/api/leads/194/analyze"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, timeout=35) as resp:
        data = json.loads(resp.read())
        print("=== AI ANALYSIS RESULT ===")
        for k, v in data.items():
            print(f"{k}: {v}")
except Exception as e:
    print(f"Error: {e}")

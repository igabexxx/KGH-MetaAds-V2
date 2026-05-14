import urllib.request
import json
import urllib.error

url = "https://api.kayanagreenhills.com/api/leads/1041"
req = urllib.request.Request(url)
try:
    with urllib.request.urlopen(req) as resp:
        print(resp.read().decode())
except urllib.error.HTTPError as e:
    print(f"HTTPError: {e.code}")
    print(e.read().decode())
except Exception as e:
    print(e)

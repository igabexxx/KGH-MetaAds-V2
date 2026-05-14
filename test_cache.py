import urllib.request

url = "https://api.kayanagreenhills.com/js/leads.js"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
try:
    with urllib.request.urlopen(req) as resp:
        content = resp.read().decode()
        if "cleanPhone" in content:
            print("YES: leads.js contains the newest phone-search logic!")
        else:
            print("NO: leads.js is stale/cached and does not contain the newest logic!")
except Exception as e:
    print(e)

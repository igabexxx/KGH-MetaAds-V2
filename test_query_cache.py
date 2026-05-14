import urllib.request

url = "https://api.kayanagreenhills.com/?refresh=2"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
try:
    with urllib.request.urlopen(req) as resp:
        content = resp.read().decode()
        if "v=1.4" in content:
            print("YES: ?refresh=2 bypassed cache!")
        else:
            print("NO: Still cached!")
except Exception as e:
    print(e)

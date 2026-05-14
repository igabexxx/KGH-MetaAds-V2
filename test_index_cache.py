import urllib.request

url = "https://api.kayanagreenhills.com/"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
try:
    with urllib.request.urlopen(req) as resp:
        content = resp.read().decode()
        if "v=1.4" in content:
            print("YES: index.html is fresh and contains v=1.4")
        else:
            print("NO: index.html is stale/cached by Cloudflare!")
except Exception as e:
    print(e)

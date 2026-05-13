import urllib.request
import json
import ssl

url = "https://192.168.101.226:9443/api/endpoints/3/docker/containers/json?all=1"
api_key = "ptr_hPzUizSxcX3DK4M6ZGoiX0Si2PZLQgqrHTGv3mVhkdc="

req = urllib.request.Request(url)
req.add_header("X-API-Key", api_key)
context = ssl._create_unverified_context()

try:
    with urllib.request.urlopen(req, context=context) as response:
        data = json.loads(response.read().decode("utf-8"))
        for c in data:
            name = c.get("Names", [""])[0]
            if "kgh" in name.lower():
                print(f"Name: {name}, State: {c.get('State')}, Status: {c.get('Status')}")
except Exception as e:
    print("Error:", e)

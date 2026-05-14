import urllib.request
import json
import ssl

portainer_url = "https://192.168.101.226:9443/api/endpoints/3/docker/containers/json?all=true&filters=%7B%22name%22%3A%5B%22kgh%22%5D%7D"
api_key = "ptr_hPzUizSxcX3DK4M6ZGoiX0Si2PZLQgqrHTGv3mVhkdc="

req = urllib.request.Request(portainer_url)
req.add_header("X-API-Key", api_key)

context = ssl._create_unverified_context()

try:
    with urllib.request.urlopen(req, context=context) as response:
        containers = json.loads(response.read().decode("utf-8"))
        for c in containers:
            name = c.get("Names", ["?"])[0]
            state = c.get("State", "?")
            status = c.get("Status", "?")
            print(f"{name}: State={state}, Status={status}")
except Exception as e:
    print(f"ERROR: {e}")

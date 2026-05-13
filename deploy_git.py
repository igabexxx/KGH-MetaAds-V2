import urllib.request
import urllib.parse
import json
import ssl

portainer_url = "https://192.168.101.226:9443/api/stacks/create/standalone/repository?endpointId=3"
api_key = "ptr_hPzUizSxcX3DK4M6ZGoiX0Si2PZLQgqrHTGv3mVhkdc="

payload = {
    "Name": "kgh-metads",
    "RepositoryURL": "https://github.com/igabexxx/KGH-MetaAds-V2.git",
    "RepositoryReferenceName": "refs/heads/main",
    "ComposeFile": "docker-compose.yml"
}

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(portainer_url, data=data, method="POST")
req.add_header("X-API-Key", api_key)
req.add_header("Content-Type", "application/json")

context = ssl._create_unverified_context()

try:
    with urllib.request.urlopen(req, context=context) as response:
        res = response.read()
        print("Success:", res.decode("utf-8"))
except urllib.error.HTTPError as e:
    print("Error HTTP", e.code, ":", e.read().decode("utf-8"))
except Exception as e:
    print("Error Exception:", str(e))

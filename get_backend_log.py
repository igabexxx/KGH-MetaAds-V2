import urllib.request
import json
import ssl

# Get logs from kgh_backend_v2 container
portainer_url = "https://192.168.101.226:9443/api/endpoints/3/docker/containers/kgh_backend_v2/logs?stdout=1&stderr=1&tail=50"
api_key = "ptr_hPzUizSxcX3DK4M6ZGoiX0Si2PZLQgqrHTGv3mVhkdc="

req = urllib.request.Request(portainer_url)
req.add_header("X-API-Key", api_key)

context = ssl._create_unverified_context()

try:
    with urllib.request.urlopen(req, context=context) as response:
        logs = response.read().decode("utf-8", errors='replace')
        # Strip docker log header bytes (8 bytes per line)
        clean_lines = []
        for line in logs.split('\n'):
            if len(line) > 8:
                clean_lines.append(line[8:])
        print('\n'.join(clean_lines[-30:]))
except Exception as e:
    print(f"ERROR: {e}")

import urllib.request
import json
import ssl

url = "https://192.168.101.226:9443/api/endpoints/3/docker/containers/kgh_postgres/logs?stdout=1&stderr=1&tail=50"
api_key = "ptr_hPzUizSxcX3DK4M6ZGoiX0Si2PZLQgqrHTGv3mVhkdc="

req = urllib.request.Request(url)
req.add_header("X-API-Key", api_key)
context = ssl._create_unverified_context()

try:
    with urllib.request.urlopen(req, context=context) as response:
        # Logs from docker API are multiplexed. We will just decode them ignoring the 8-byte headers for a quick look.
        raw = response.read()
        print("Logs:")
        # Skip every 8 byte header (dirty parse)
        text = ""
        i = 0
        while i < len(raw):
            if i + 8 <= len(raw):
                size = int.from_bytes(raw[i+4:i+8], byteorder='big')
                text += raw[i+8:i+8+size].decode('utf-8', errors='replace')
                i += 8 + size
            else:
                break
        print(text)
except Exception as e:
    print("Error:", e)

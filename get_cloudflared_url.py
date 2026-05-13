import urllib.request
import re
import ssl
import time

url = "https://192.168.101.226:9443/api/endpoints/3/docker/containers/kgh_cloudflared/logs?stdout=1&stderr=1&tail=100"
api_key = "ptr_hPzUizSxcX3DK4M6ZGoiX0Si2PZLQgqrHTGv3mVhkdc="

req = urllib.request.Request(url)
req.add_header("X-API-Key", api_key)
context = ssl._create_unverified_context()

max_retries = 10
for i in range(max_retries):
    try:
        with urllib.request.urlopen(req, context=context) as response:
            raw = response.read()
            text = ""
            idx = 0
            while idx < len(raw):
                if idx + 8 <= len(raw):
                    size = int.from_bytes(raw[idx+4:idx+8], byteorder='big')
                    text += raw[idx+8:idx+8+size].decode('utf-8', errors='replace')
                    idx += 8 + size
                else:
                    break
            
            # Find the Cloudflare URL
            match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', text)
            if match:
                print(f"FOUND_URL: {match.group(0)}")
                break
            else:
                if i == max_retries - 1:
                    print("URL not found in logs yet. Raw logs:")
                    print(text)
                else:
                    time.sleep(2)
    except Exception as e:
        print("Error:", e)
        time.sleep(2)

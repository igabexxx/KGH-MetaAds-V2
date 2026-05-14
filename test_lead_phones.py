import urllib.request
import json

# Get all aurawedding leads to see which one has phone set
url = "https://api.kayanagreenhills.com/api/leads?search=aurawedding&limit=10"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as resp:
        leads = json.loads(resp.read())
        for lead in leads:
            print(f"ID: {lead['id']} | Phone: {lead.get('phone', 'N/A')} | Name: {lead.get('full_name','N/A')}")
except Exception as e:
    print(f"Error: {e}")

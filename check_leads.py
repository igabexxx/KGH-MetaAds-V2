"""Check leads in KGH database with AI scoring data"""
import urllib.request, json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

urls = [
    'http://192.168.101.226:8005/api/leads?limit=5',
    'http://192.168.101.226:8005/api/leads?skip=400&limit=5',
    'http://192.168.101.226:8005/api/leads?skip=600&limit=5',
]

for url in urls:
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        if isinstance(data, list):
            print(f"URL: {url} -> {len(data)} leads")
            for l in data[:3]:
                cf = l.get("custom_fields", {}) or {}
                name = l.get("full_name", "?")
                status = l.get("status", "?")
                score = cf.get("ai_score", "N/A")
                temp = cf.get("ai_temp", "N/A")
                summary = cf.get("ai_summary", "")[:60]
                print(f"  {name} | status={status} | ai_score={score} | ai_temp={temp}")
                if summary:
                    print(f"    summary: {summary}")
        else:
            keys = list(data.keys()) if isinstance(data, dict) else "?"
            print(f"URL: {url} -> type={type(data).__name__} keys={keys}")
    except Exception as e:
        print(f"URL: {url} -> Error: {e}")
    print()

# Also check total count
try:
    with urllib.request.urlopen('http://192.168.101.226:8005/api/leads', timeout=10) as resp:
        data = json.loads(resp.read())
    if isinstance(data, list):
        total = len(data)
        statuses = {}
        for l in data:
            s = l.get("status", "?")
            statuses[s] = statuses.get(s, 0) + 1
        print(f"Default /api/leads: {total} leads")
        print(f"Status breakdown: {statuses}")
        
        # Check how many have ai_score
        with_ai = sum(1 for l in data if (l.get("custom_fields") or {}).get("ai_score") is not None)
        print(f"With AI score: {with_ai}")
except Exception as e:
    print(f"Error: {e}")

"""Push scoring results from n8n execution #1 directly to KGH API"""
import urllib.request, json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

N8N = 'http://192.168.101.226:5680'
N8N_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMTI5NjgwNS1iOGRlLTRiOGYtYjUwMy1jOWQ3M2U1MzJhYTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMzc3N2M3MzAtY2ExZC00YzQxLWE4NjktYjk0YWFjOWJkNmJhIiwiaWF0IjoxNzc4NzE5MTI1LCJleHAiOjE3ODEyODM2MDB9.tvL7MrDA5QRc8QEtHeM9JS0x_RtgP7JoARXgeiORG2E'
KGH_URL = 'http://192.168.101.226:8005/api/v1/socialchat/scoring/bulk'

# 1. Get execution data
print("[1/2] Extracting scoring results from n8n execution #1...")
req = urllib.request.Request(N8N + '/api/v1/executions/1?includeData=true')
req.add_header('X-N8N-API-KEY', N8N_KEY)
with urllib.request.urlopen(req, timeout=15) as resp:
    data = json.loads(resp.read())

run_data = data.get('data', {}).get('resultData', {}).get('runData', {})
analyze_runs = run_data.get('Analyze & Build Report', [])

results = []
for run in analyze_runs:
    if run.get('data') and run['data'].get('main'):
        outputs = run['data']['main'][0]
        for item in outputs:
            j = item.get('json', {})
            r = j.get('results', [])
            if r:
                results = r
                break

hot = [r for r in results if r.get('temp') == 'HOT']
warm = [r for r in results if r.get('temp') == 'WARM']
cold = [r for r in results if r.get('temp') == 'COLD']
print(f"  Total: {len(results)} | HOT={len(hot)} WARM={len(warm)} COLD={len(cold)}")
print()

# Show top HOT leads
print("TOP HOT LEADS:")
for h in hot[:10]:
    cn = h.get('contactName', '?')
    sc = h.get('score', 0)
    act = h.get('action', '')[:60]
    msg = h.get('msgCount', 0)
    bf = h.get('bf', 0)
    print(f"  🔥 {cn:25s} score={sc:3d} | msgs={msg} dialog={bf}x | {act}")
print()

# 2. Push to KGH
print(f"[2/2] Pushing {len(results)} leads to KGH dashboard...")
batch_size = 50
total_created = total_updated = total_errors = 0

for i in range(0, len(results), batch_size):
    batch = results[i:i+batch_size]
    payload = json.dumps({"leads": batch}).encode("utf-8")
    
    req = urllib.request.Request(KGH_URL, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            c = result.get("created", 0)
            u = result.get("updated", 0)
            e = result.get("errors", 0)
            total_created += c
            total_updated += u
            total_errors += e
            print(f"  Batch {i//batch_size + 1}: created={c}, updated={u}, errors={e}")
    except urllib.error.HTTPError as err:
        body = err.read().decode()[:200]
        print(f"  Batch {i//batch_size + 1}: HTTP {err.code} - {body}")
        total_errors += len(batch)
    except Exception as ex:
        print(f"  Batch {i//batch_size + 1}: Error - {ex}")
        total_errors += len(batch)

print(f"\nDone! Created: {total_created}, Updated: {total_updated}, Errors: {total_errors}")

# Verify
print("\nVerifying...")
for s in ['HOT', 'WARM', 'COLD']:
    url = f'http://192.168.101.226:8005/api/leads?status={s}&limit=200'
    with urllib.request.urlopen(url, timeout=10) as resp:
        d = json.loads(resp.read())
    print(f"  {s}: {len(d)} leads in dashboard")

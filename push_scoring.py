"""Push AI scoring results to KGH via /scoring/bulk endpoint (upsert by phone)"""
import json, sys, io, urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

KGH_API = "http://192.168.101.226:8005"

# Load scored data
with open("socialchat_leads_scored.json", "r", encoding="utf-8") as f:
    scored = json.load(f)

print(f"Loaded {len(scored)} scored leads")

# Transform to scoring/bulk format
leads_payload = []
for item in scored:
    ai = item.get("ai") or item.get("score")
    if not ai or not isinstance(ai, dict):
        continue
    
    leads_payload.append({
        "contactName": item.get("name", "Unknown"),
        "contactPhone": item.get("phone", ""),
        "agentName": item.get("agent", ""),
        "score": ai.get("score", 0),
        "temp": ai.get("temp", "COLD"),
        "summary": ai.get("summary", ""),
        "posSignals": ai.get("posSignals", ""),
        "negStr": ai.get("negStr", ""),
        "urgLabel": ai.get("urgLabel", ""),
        "bdgLabel": ai.get("bdgLabel", ""),
        "action": ai.get("action", ""),
        "reasons": ai.get("reasons", ""),
        "ghostCount": ai.get("ghostCount", 0),
        "ghostLabel": ai.get("ghostLabel", ""),
        "bofuHits": ai.get("bofuHits", 0),
        "mofuHits": ai.get("mofuHits", 0),
        "negHits": ai.get("negHits", 0),
        "msgCount": ai.get("msgCount", 0),
        "leadMsgCount": ai.get("leadMsgCount", 0),
        "bf": ai.get("bf", 0),
        "daysDiff": ai.get("daysDiff", 0),
        "recencyLabel": ai.get("recencyLabel", ""),
    })

print(f"Prepared {len(leads_payload)} leads with AI scoring")

# Send in batches of 50
batch_size = 50
total_created = total_updated = total_errors = 0

for i in range(0, len(leads_payload), batch_size):
    batch = leads_payload[i:i+batch_size]
    payload = json.dumps({"leads": batch}).encode("utf-8")
    
    url = f"{KGH_API}/api/v1/socialchat/scoring/bulk"
    req = urllib.request.Request(url, data=payload, method="POST")
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

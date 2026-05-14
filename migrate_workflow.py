"""
Export workflow from old n8n (192.168.86.158) and import to KGH n8n (192.168.101.226:5680)
Updates Push to KGH URL to use Docker internal network (http://backend:8000)
"""
import urllib.request
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

OLD_N8N = "http://192.168.86.158:5678"
OLD_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJiMTIwZDJkMC1lMTU1LTQ5MjYtYjg4Yi1jYmI1YWZiMmE5ODUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiNDAzZmNjZWEtMDljYy00NGYzLWE3OWYtYzdiY2E1ZDllZWM4IiwiaWF0IjoxNzc4MzgzMzg0LCJleHAiOjE3ODYwNzUyMDB9.K7rAi6uMskJTcH5jyEpdwTOsO9tHvUpry9rlgw5khRA"
OLD_WF_ID = "XqlehS9OhjW2cNuG"

NEW_N8N = "http://192.168.101.226:5680"
NEW_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMTI5NjgwNS1iOGRlLTRiOGYtYjUwMy1jOWQ3M2U1MzJhYTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMzc3N2M3MzAtY2ExZC00YzQxLWE4NjktYjk0YWFjOWJkNmJhIiwiaWF0IjoxNzc4NzE5MTI1LCJleHAiOjE3ODEyODM2MDB9.tvL7MrDA5QRc8QEtHeM9JS0x_RtgP7JoARXgeiORG2E"

def api_get(base_url, api_key, path):
    req = urllib.request.Request(f"{base_url}/api/v1{path}")
    req.add_header("X-N8N-API-KEY", api_key)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

def api_post(base_url, api_key, path, data):
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(f"{base_url}/api/v1{path}", data=payload, method="POST")
    req.add_header("X-N8N-API-KEY", api_key)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

# 1. Export workflow from old n8n
print("[1/3] Exporting workflow from old n8n (192.168.86.158)...")
wf = api_get(OLD_N8N, OLD_KEY, f"/workflows/{OLD_WF_ID}")
print(f"  Name: {wf.get('name')}")
print(f"  Nodes: {len(wf.get('nodes', []))}")
node_names = [n['name'] for n in wf.get('nodes', [])]
print(f"  Node names: {node_names}")

# 2. Fix Push to KGH URL to use Docker internal network
print("\n[2/3] Updating Push to KGH URL for Docker network...")
nodes = wf.get('nodes', [])
for node in nodes:
    if node['name'] == 'Push to KGH':
        code = node.get('parameters', {}).get('jsCode', '')
        old_url = 'https://api.kayanagreenhills.com/api/v1/socialchat/scoring/bulk'
        new_url = 'http://backend:8000/api/v1/socialchat/scoring/bulk'
        if old_url in code:
            code = code.replace(old_url, new_url)
            node['parameters']['jsCode'] = code
            print(f"  Updated URL: {old_url} -> {new_url}")
        else:
            print(f"  URL not found in code, checking other patterns...")
            # Try alternate URL patterns
            for alt in ['http://192.168.101.226:8005/api/v1/socialchat/scoring/bulk']:
                if alt in code:
                    code = code.replace(alt, new_url)
                    node['parameters']['jsCode'] = code
                    print(f"  Updated URL: {alt} -> {new_url}")
                    break
            else:
                print(f"  Warning: Could not find URL to replace in Push to KGH code")
        break
else:
    print("  Warning: Push to KGH node not found!")

# 3. Import workflow to new n8n
print("\n[3/3] Importing workflow to KGH n8n (192.168.101.226:5680)...")

# Prepare import payload - remove ID and other server-specific fields
import_data = {
    "name": wf.get("name", "SocialChat LEADS AI Report - Daily"),
    "nodes": nodes,
    "connections": wf.get("connections", {}),
    "settings": {"executionOrder": "v1"},
}

try:
    result = api_post(NEW_N8N, NEW_KEY, "/workflows", import_data)
    new_id = result.get("id", "?")
    print(f"  Success! New workflow ID: {new_id}")
    print(f"  Name: {result.get('name')}")
    print(f"  Nodes: {len(result.get('nodes', []))}")
    new_node_names = [n['name'] for n in result.get('nodes', [])]
    print(f"  Nodes: {new_node_names}")
    
    # Activate the workflow
    print("\n  Activating workflow...")
    activate_data = json.dumps({"active": True}).encode("utf-8")
    req = urllib.request.Request(
        f"{NEW_N8N}/api/v1/workflows/{new_id}",
        data=json.dumps({"name": result['name'], "nodes": result['nodes'], "connections": result['connections'], "settings": result.get('settings', {}), "active": True}).encode("utf-8"),
        method="PUT"
    )
    req.add_header("X-N8N-API-KEY", NEW_KEY)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=15) as resp:
        act_result = json.loads(resp.read())
        print(f"  Active: {act_result.get('active')}")
    
    print(f"\n  Open workflow: http://192.168.101.226:5680/workflow/{new_id}")
    
except urllib.error.HTTPError as e:
    body = e.read().decode()[:500]
    print(f"  Error {e.code}: {body}")
except Exception as ex:
    print(f"  Error: {ex}")

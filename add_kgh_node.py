"""
Add 'Push to KGH' node to n8n workflow
Connects after 'Analyze & Build Report' → pushes scoring to KGH dashboard
"""
import urllib.request
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

N8N_URL = "http://192.168.86.158:5678"
N8N_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJiMTIwZDJkMC1lMTU1LTQ5MjYtYjg4Yi1jYmI1YWZiMmE5ODUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiNDAzZmNjZWEtMDljYy00NGYzLWE3OWYtYzdiY2E1ZDllZWM4IiwiaWF0IjoxNzc4MzgzMzg0LCJleHAiOjE3ODYwNzUyMDB9.K7rAi6uMskJTcH5jyEpdwTOsO9tHvUpry9rlgw5khRA"
WF_ID = "XqlehS9OhjW2cNuG"
KGH_URL = "https://api.kayanagreenhills.com/api/v1/socialchat/scoring/bulk"

# 1. Get current workflow
req = urllib.request.Request(f"{N8N_URL}/api/v1/workflows/{WF_ID}")
req.add_header("X-N8N-API-KEY", N8N_KEY)
with urllib.request.urlopen(req, timeout=10) as resp:
    wf = json.loads(resp.read())

nodes = wf.get("nodes", [])
connections = wf.get("connections", {})

# Find Analyze node position for placement
analyze_node = None
for n in nodes:
    if n["name"] == "Analyze & Build Report":
        analyze_node = n
        break

if not analyze_node:
    print("ERROR: 'Analyze & Build Report' node not found!")
    sys.exit(1)

pos = analyze_node.get("position", [0, 0])
print(f"Analyze node position: {pos}")

# 2. Create "Push to KGH" code node
# This node receives the first output item from Analyze (which contains results array)
# and POSTs it to KGH scoring/bulk endpoint
push_node = {
    "parameters": {
        "jsCode": """// Push scoring results to KGH Dashboard
const results = $input.first().json.results || [];
if (!results.length) {
  return [{ json: { status: 'skip', message: 'No results to push' } }];
}

// POST to KGH scoring/bulk endpoint
const KGH_URL = '""" + KGH_URL + """';
const batchSize = 50;
let created = 0, updated = 0, errors = 0;

for (let i = 0; i < results.length; i += batchSize) {
  const batch = results.slice(i, i + batchSize);
  try {
    const response = await this.helpers.httpRequest({
      method: 'POST',
      url: KGH_URL,
      body: { leads: batch },
      headers: { 'Content-Type': 'application/json' },
      timeout: 30000,
    });
    created += response.created || 0;
    updated += response.updated || 0;
    errors += response.errors || 0;
  } catch (e) {
    errors += batch.length;
  }
}

return [{
  json: {
    status: 'done',
    totalPushed: results.length,
    created,
    updated,
    errors,
  }
}];"""
    },
    "name": "Push to KGH",
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [pos[0] + 300, pos[1] + 250],
    "id": "push-to-kgh-node",
}

# Check if node already exists
existing = [n for n in nodes if n["name"] == "Push to KGH"]
if existing:
    print("Node 'Push to KGH' already exists — updating...")
    for i, n in enumerate(nodes):
        if n["name"] == "Push to KGH":
            nodes[i] = push_node
            break
else:
    print("Adding new 'Push to KGH' node...")
    nodes.append(push_node)

# 3. Add connection: "Analyze & Build Report" -> "Push to KGH"
analyze_conns = connections.get("Analyze & Build Report", {})
main_conns = analyze_conns.get("main", [[]])

# Check if connection already exists
already_connected = False
for target_list in main_conns:
    for target in target_list:
        if target.get("node") == "Push to KGH":
            already_connected = True
            break

if not already_connected:
    # Add to existing connections (alongside Telegram, Merge, Agent Reports)
    if main_conns and main_conns[0]:
        main_conns[0].append({"node": "Push to KGH", "type": "main", "index": 0})
    else:
        main_conns = [[{"node": "Push to KGH", "type": "main", "index": 0}]]

    analyze_conns["main"] = main_conns
    connections["Analyze & Build Report"] = analyze_conns
    print("Connected: Analyze & Build Report -> Push to KGH")
else:
    print("Connection already exists")

# 4. Update workflow
payload = json.dumps({
    "nodes": nodes,
    "connections": connections,
}).encode("utf-8")

req2 = urllib.request.Request(
    f"{N8N_URL}/api/v1/workflows/{WF_ID}",
    data=payload,
    method="PUT",
)
req2.add_header("X-N8N-API-KEY", N8N_KEY)
req2.add_header("Content-Type", "application/json")

with urllib.request.urlopen(req2, timeout=15) as resp2:
    result = json.loads(resp2.read())
    print(f"Workflow updated! Name: {result.get('name', '?')}")
    print(f"Nodes: {len(result.get('nodes', []))}")

print("\nDone! n8n workflow will now push scoring to KGH dashboard on every execution.")

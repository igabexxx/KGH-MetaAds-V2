"""Test page 3 message fetch - where data was found before"""
import urllib.request, json, sys, io
from datetime import datetime, timedelta, timezone
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

API_KEY = 'MTI0NjExMzgxNl9TeWhLc2dDdUlUVGcwQTdWTkZpVg=='
BASE = 'https://api.socialchat.id/partner'

from_d = (datetime.now(timezone.utc) - timedelta(days=14)).strftime('%Y-%m-%dT00:00:00.000Z')
to_d = datetime.now(timezone.utc).strftime('%Y-%m-%dT23:59:59.999Z')

# Page 3 worked before
url = f'{BASE}/conversation?page=3&limit=10&fromDate={from_d}&toDate={to_d}'
req = urllib.request.Request(url)
req.add_header('Authorization', f'Bearer {API_KEY}')
with urllib.request.urlopen(req, timeout=15) as resp:
    data = json.loads(resp.read())

for conv in data['docs'][:10]:
    cid = conv['_id']
    name = conv.get('senderName', '?')
    
    msg_url = f'{BASE}/message/{cid}'
    req2 = urllib.request.Request(msg_url)
    req2.add_header('Authorization', f'Bearer {API_KEY}')
    with urllib.request.urlopen(req2, timeout=15) as resp2:
        md = json.loads(resp2.read())
    
    docs = md.get('docs', [])
    total = md.get('totalDocs', len(docs))
    
    status = f'{total} msgs'
    if docs:
        m = docs[0]
        text = (m.get('text') or '[no text]')[:50]
        sid = m.get('senderId', '?')[:30]
        sname = m.get('senderName', '?')
        status += f' | {sname}: {text}'
    
    print(f'{name[:25]:25s} | {status}')

# Also try getting the latest execution from n8n to see the data it got
print('\n--- Checking n8n latest execution for comparison ---')
n8n_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJiMTIwZDJkMC1lMTU1LTQ5MjYtYjg4Yi1jYmI1YWZiMmE5ODUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiNDAzZmNjZWEtMDljYy00NGYzLWE3OWYtYzdiY2E1ZDllZWM4IiwiaWF0IjoxNzc4MzgzMzg0LCJleHAiOjE3ODYwNzUyMDB9.K7rAi6uMskJTcH5jyEpdwTOsO9tHvUpry9rlgw5khRA'
exec_url = f'http://192.168.86.158:5678/api/v1/executions?workflowId=XqlehS9OhjW2cNuG&limit=1&status=success'
req3 = urllib.request.Request(exec_url)
req3.add_header('X-N8N-API-KEY', n8n_key)
try:
    with urllib.request.urlopen(req3, timeout=10) as resp3:
        exec_data = json.loads(resp3.read())
    execs = exec_data.get('data', [])
    if execs:
        last_exec = execs[0]
        print(f'Last execution: {last_exec.get("startedAt", "?")}')
        print(f'Status: {last_exec.get("status", "?")}')
        print(f'Finished: {last_exec.get("stoppedAt", "?")}')
except Exception as e:
    print(f'n8n error: {e}')

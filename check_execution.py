"""Analyze n8n execution result for Push to KGH"""
import urllib.request, json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

N8N = 'http://192.168.101.226:5680'
KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMTI5NjgwNS1iOGRlLTRiOGYtYjUwMy1jOWQ3M2U1MzJhYTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMzc3N2M3MzAtY2ExZC00YzQxLWE4NjktYjk0YWFjOWJkNmJhIiwiaWF0IjoxNzc4NzE5MTI1LCJleHAiOjE3ODEyODM2MDB9.tvL7MrDA5QRc8QEtHeM9JS0x_RtgP7JoARXgeiORG2E'

req = urllib.request.Request(N8N + '/api/v1/executions/1?includeData=true')
req.add_header('X-N8N-API-KEY', KEY)
with urllib.request.urlopen(req, timeout=15) as resp:
    data = json.loads(resp.read())

run_data = data.get('data', {}).get('resultData', {}).get('runData', {})

for node_name in sorted(run_data.keys()):
    runs = run_data[node_name]
    for run in runs:
        has_error = run.get('error') is not None
        output_data = []
        if run.get('data') and run['data'].get('main'):
            output_data = run['data']['main'][0] if run['data']['main'] else []
        
        items = len(output_data) if output_data else 0
        status_str = "ERROR" if has_error else "OK"
        
        print(f"[{status_str:5s}] {node_name} ({items} items)")
        
        if has_error:
            err_msg = run['error'].get('message', '?')
            print(f"        Error: {err_msg[:150]}")
        
        if node_name == 'Push to KGH' and output_data:
            for item in output_data:
                j = item.get('json', {})
                print(f"        Output: {json.dumps(j, ensure_ascii=False)}")
        
        if node_name == 'Analyze & Build Report' and output_data:
            first_json = output_data[0].get('json', {})
            results = first_json.get('results', [])
            if results:
                hot = [r for r in results if r.get('temp') == 'HOT']
                warm = [r for r in results if r.get('temp') == 'WARM']
                cold = [r for r in results if r.get('temp') == 'COLD']
                print(f"        Results: {len(results)} total | HOT={len(hot)} WARM={len(warm)} COLD={len(cold)}")
                for h in hot[:5]:
                    cn = h.get('contactName', '?')
                    sc = h.get('score', 0)
                    ph = h.get('contactPhone', '?')
                    act = h.get('action', '')[:60]
                    print(f"        🔥 {cn} ({ph}) score={sc} | {act}")

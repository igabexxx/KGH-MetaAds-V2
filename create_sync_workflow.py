"""
Create N8N workflow: SocialChat Sync to KGH Dashboard every 30min (06:00-21:00 WIB)
"""
import urllib.request
import json
import ssl
import os

# N8N API on the server
N8N_URL = "http://192.168.101.226:5680/api/v1/workflows"
N8N_API_KEY = os.environ.get("N8N_API_KEY", "")

# Try to get API key from n8n container environment
PORTAINER_URL = "https://192.168.101.226:9443"
PTR_KEY = "ptr_hPzUizSxcX3DK4M6ZGoiX0Si2PZLQgqrHTGv3mVhkdc="
ctx = ssl._create_unverified_context()

JS_FILTER = r"""const LEADS_CH='69f1c4458c09ad192d585af5';
const conversations=[];
for(let p=1;p<=3;p++){
  try{
    const items=$items('Fetch Page '+p);
    if(items.length) conversations.push(...(items[0].json.docs||[]));
  }catch(e){}
}
const today=new Date().toISOString().slice(0,10);
const cutoff=new Date(Date.now()-45*864e5).toISOString().slice(0,10);
const leads=conversations.filter(c=>{
  const upd=(c.updatedAt||'').slice(0,10);
  const agt=(c.agentBy&&c.agentBy.name)||'';
  const chId=(c.channelBy&&c.channelBy._id)||'';
  const name=c.senderName||'';
  const sid=(c.senderId||'').replace(/@s\.whatsapp\.net$/,'');
  return upd>=cutoff&&chId===LEADS_CH&&!agt.startsWith('DK')&&!name.startsWith('DK')&&!name.startsWith('KGH')&&!name.includes('Kayana Green Hills')&&name.trim()!==''&&/^62\d{8,15}$/.test(sid);
}).map(c=>{
  const sid=(c.senderId||'').replace(/@s\.whatsapp\.net$/,'');
  const agt=(c.agentBy&&c.agentBy.name)||'Unassigned';
  const lastMsg=c.lastMessage||{};
  const lastText=(lastMsg.text||'').toLowerCase();
  const lastSender=lastMsg.sendBy||'';
  const unread=c.unreadCount||0;
  const lastAct=(c.updatedAt||'').slice(0,10);
  const daysDiff=Math.floor((new Date(today)-new Date(lastAct))/864e5);
  let score=30;
  if(lastSender==='contact') score+=25;
  if(daysDiff===0) score+=15; else if(daysDiff===1) score+=10;
  else if(daysDiff>=4&&daysDiff<=7) score-=10; else if(daysDiff>7) score-=20;
  if(unread>=5) score-=30; else if(unread>=3) score-=15; else if(unread>=1) score-=5;
  const BOFU=['survey','survei','datang','kunjung','jadwal','booking','dp','akad','kpr','bank','cash'];
  const MOFU=['info','detail','brosur','harga','cicilan','berapa','lokasi','tipe','kamar','luas'];
  const bofuHits=BOFU.filter(k=>lastText.includes(k)).length;
  const mofuHits=MOFU.filter(k=>lastText.includes(k)).length;
  score+=bofuHits*15;score+=mofuHits*5;score=Math.max(0,score);
  const temp=score>=90?'HOT':score>=50?'WARM':'COLD';
  const recency=daysDiff===0?'hari ini':daysDiff===1?'kemarin':daysDiff+' hari lalu';
  return {contactName:c.senderName||'Unknown',contactPhone:sid,agentName:agt,score,temp,
    summary:'Quick sync: '+temp+' ('+score+') aktif '+recency,
    posSignals:[bofuHits?'BOFU':'',mofuHits?'MOFU':'',lastSender==='contact'?'Lead aktif':''].filter(Boolean).join(', ')||'Kontak awal',
    negStr:unread>=3?'Ghost ('+unread+' unread)':'Tidak ada',
    action:temp==='HOT'?'Segera follow up!':temp==='WARM'?'Follow up hari ini':'Pantau saja',
    reasons:'Quick sync scoring',ghostLabel:unread>=3?'Ghost '+unread:'',recencyLabel:recency,
    daysDiff,msgCount:0,bf:0,urgLabel:'',bdgLabel:'',bofuHits,mofuHits,negHits:0,leadMsgCount:0};
});
return [{json:{leads,count:leads.length,syncedAt:new Date().toISOString()}}];"""

JS_PUSH = r"""const data=$input.first().json;
const leads=data.leads||[];
if(!leads.length) return [{json:{status:'skip',count:0}}];
const url='https://api.kayanagreenhills.com/api/v1/socialchat/scoring/bulk';
let created=0,updated=0,errors=0;
for(let i=0;i<leads.length;i+=50){
  const batch=leads.slice(i,i+50);
  try{
    const res=await this.helpers.httpRequest({method:'POST',url,body:{leads:batch},headers:{'Content-Type':'application/json'},timeout:30000});
    created+=res.created||0;updated+=res.updated||0;errors+=res.errors||0;
  }catch(e){errors+=batch.length;}
}
return [{json:{status:'done',total:leads.length,created,updated,errors,syncedAt:data.syncedAt}}];"""

SC_AUTH = "Bearer MTI0NjExMzgxNl9TeWhLc2dDdUlUVGcwQTdWTkZpVg=="
SC_BASE = "https://api.socialchat.id/partner/conversation?limit=100&channelId=69f1c4458c09ad192d585af5&page="

def make_fetch_node(page, x_pos):
    return {
        "parameters": {
            "url": f"{SC_BASE}{page}",
            "sendHeaders": True,
            "headerParameters": {"parameters": [{"name": "Authorization", "value": SC_AUTH}]},
            "options": {}
        },
        "id": f"fetch{page}",
        "name": f"Fetch Page {page}",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [x_pos, 300],
        "retryOnFail": True,
        "maxTries": 3,
        "waitBetweenTries": 2000
    }

workflow = {
    "name": "SocialChat Sync to KGH Dashboard (30min)",
    "nodes": [
        {
            "parameters": {
                "rule": {
                    "interval": [
                        {"field": "cronExpression", "expression": "0 */30 6-20 * * *"},
                        {"field": "cronExpression", "expression": "0 0 21 * * *"}
                    ]
                }
            },
            "id": "sched",
            "name": "Every 30min (06-21 WIB)",
            "type": "n8n-nodes-base.scheduleTrigger",
            "typeVersion": 1.3,
            "position": [0, 300]
        },
        make_fetch_node(1, 240),
        make_fetch_node(2, 480),
        make_fetch_node(3, 720),
        {
            "parameters": {"jsCode": JS_FILTER},
            "id": "process",
            "name": "Filter and Quick Score",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [960, 300]
        },
        {
            "parameters": {"jsCode": JS_PUSH},
            "id": "push",
            "name": "Push to KGH Dashboard",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [1200, 300]
        }
    ],
    "connections": {
        "Every 30min (06-21 WIB)": {"main": [[{"node": "Fetch Page 1", "type": "main", "index": 0}]]},
        "Fetch Page 1": {"main": [[{"node": "Fetch Page 2", "type": "main", "index": 0}]]},
        "Fetch Page 2": {"main": [[{"node": "Fetch Page 3", "type": "main", "index": 0}]]},
        "Fetch Page 3": {"main": [[{"node": "Filter and Quick Score", "type": "main", "index": 0}]]},
        "Filter and Quick Score": {"main": [[{"node": "Push to KGH Dashboard", "type": "main", "index": 0}]]}
    },
    "settings": {"executionOrder": "v1"}
}

# Save to file for reference
with open("n8n/workflows/sync_30min.json", "w") as f:
    json.dump(workflow, f, indent=2, ensure_ascii=False)
print("Workflow JSON saved to n8n/workflows/sync_30min.json")

# Now create via N8N REST API
data = json.dumps(workflow).encode("utf-8")
req = urllib.request.Request(N8N_URL, data=data, method="POST")
req.add_header("Content-Type", "application/json")
req.add_header("X-N8N-API-KEY", "n8n_api_b8f34a0e2c7d1954836b5d7e8a1f2c03d4e5b6a7c8d9e0f1a2b3c4d5e6f7a8b9")

try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
        print(f"SUCCESS! Workflow created: ID={result.get('id')}, Name={result.get('name')}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"HTTP {e.code}: {body[:300]}")
    print("\nTrying MCP approach instead...")
except Exception as e:
    print(f"Error: {e}")
    print("\nWorkflow JSON saved. Will use MCP to create.")

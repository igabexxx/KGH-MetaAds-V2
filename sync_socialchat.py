"""
SocialChat → KGH Lead Sync Script
Pulls all conversations from SocialChat API and imports them into the KGH database.
"""
import urllib.request, json, sys, io
from datetime import datetime, timedelta, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

API_KEY = 'MTI0NjExMzgxNl9TeWhLc2dDdUlUVGcwQTdWTkZpVg=='
BASE_URL = 'https://api.socialchat.id/partner'
KGH_API = 'http://192.168.101.226:8005'

def fetch_all_conversations(days_back=90):
    """Fetch all conversations from SocialChat"""
    from_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime('%Y-%m-%dT00:00:00.000Z')
    to_date = datetime.now(timezone.utc).strftime('%Y-%m-%dT23:59:59.999Z')
    
    all_convs = []
    page = 1
    while True:
        url = f'{BASE_URL}/conversation?page={page}&limit=50&fromDate={from_date}&toDate={to_date}'
        req = urllib.request.Request(url)
        req.add_header('Authorization', f'Bearer {API_KEY}')
        req.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        docs = data.get('docs', [])
        all_convs.extend(docs)
        total_pages = data.get('totalPages', 1)
        print(f'  Page {page}/{total_pages} - got {len(docs)} conversations')
        if page >= total_pages:
            break
        page += 1
    return all_convs


def extract_leads(conversations):
    """Extract unique leads from conversations"""
    leads = {}
    for conv in conversations:
        sender_id = conv.get('senderId', '')
        sender_name = conv.get('senderName', 'Unknown')
        if not sender_id or conv.get('isGroup'):
            continue
        phone = sender_id.split('@')[0] if '@' in sender_id else sender_id
        
        agent = conv.get('agentBy', {}) or {}
        agent_name = agent.get('name', 'Unassigned') if isinstance(agent, dict) else 'Unassigned'
        
        last_msg = conv.get('lastMessage', {}) or {}
        msg_text = last_msg.get('text', '') if isinstance(last_msg, dict) else ''
        
        if phone not in leads:
            leads[phone] = {
                'name': sender_name,
                'phone': phone,
                'agent': agent_name,
                'createdAt': conv.get('createdAt', ''),
                'updatedAt': conv.get('updatedAt', ''),
                'lastMessage': msg_text,
                'conversationId': conv.get('_id', ''),
                'labels': conv.get('labels', []),
                'socialchat_id': conv.get('_id', ''),
            }
        else:
            # Update with newer data
            if conv.get('updatedAt', '') > leads[phone].get('updatedAt', ''):
                leads[phone]['updatedAt'] = conv.get('updatedAt', '')
                leads[phone]['lastMessage'] = msg_text
                leads[phone]['agent'] = agent_name
    return leads


def push_to_kgh(leads):
    """Push leads to KGH backend API"""
    created = 0
    skipped = 0
    errors = 0
    
    for phone, lead in leads.items():
        payload = json.dumps({
            "full_name": lead['name'],
            "phone": lead['phone'],
            "source": "WhatsApp (SocialChat)",
            "status": "NEW",
            "assigned_to": lead['agent'] if lead['agent'] != 'Unassigned' else None,
            "notes": f"Last message: {lead['lastMessage'][:200]}" if lead['lastMessage'] else None,
            "custom_fields": {
                "socialchat_conversation_id": lead['conversationId'],
                "socialchat_labels": lead['labels'],
                "socialchat_last_update": lead['updatedAt'],
            }
        }).encode('utf-8')
        
        req = urllib.request.Request(
            f'{KGH_API}/api/leads',
            data=payload,
            method='POST'
        )
        req.add_header('Content-Type', 'application/json')
        
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                created += 1
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            if '409' in str(e.code) or 'duplicate' in body.lower():
                skipped += 1
            else:
                errors += 1
                if errors <= 3:
                    print(f'  Error pushing {lead["name"]}: HTTP {e.code} - {body[:100]}')
        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f'  Error pushing {lead["name"]}: {e}')
    
    return created, skipped, errors


if __name__ == '__main__':
    print("=" * 60)
    print("SocialChat -> KGH Lead Sync")
    print("=" * 60)
    
    print("\n[1/3] Fetching conversations from SocialChat API...")
    conversations = fetch_all_conversations(days_back=90)
    print(f"  Total conversations: {len(conversations)}")
    
    print("\n[2/3] Extracting unique leads...")
    leads = extract_leads(conversations)
    print(f"  Unique leads: {len(leads)}")
    
    # Show preview
    print("\n  Preview (first 15):")
    for i, (phone, lead) in enumerate(list(leads.items())[:15]):
        print(f"  {i+1:3d}. {lead['name'][:30]:30s} | {phone:15s} | Agent: {lead['agent']}")
    
    # Save JSON backup
    with open('socialchat_leads.json', 'w', encoding='utf-8') as f:
        json.dump(list(leads.values()), f, ensure_ascii=False, indent=2, default=str)
    print(f"\n  Backup saved to socialchat_leads.json")
    
    print("\n[3/3] Pushing leads to KGH database...")
    created, skipped, errors = push_to_kgh(leads)
    print(f"\n  Results:")
    print(f"    Created: {created}")
    print(f"    Skipped: {skipped}")
    print(f"    Errors:  {errors}")
    print("\n" + "=" * 60)
    print("Sync complete!")

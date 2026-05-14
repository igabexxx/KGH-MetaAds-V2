"""Analyze score distribution to understand why no HOT leads"""
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open('socialchat_leads_scored.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Collect scores
items = []
for d in data:
    ai = d.get('ai') or d.get('score')
    if ai and isinstance(ai, dict):
        items.append({
            'name': d.get('name', '?'),
            'score': ai.get('score', 0),
            'temp': ai.get('temp', '?'),
            'pos': ai.get('posSignals', ''),
            'neg': ai.get('negStr', ''),
            'action': ai.get('action', ''),
            'summary': ai.get('summary', ''),
            'reasons': ai.get('reasons', ''),
            'msgCount': ai.get('msgCount', 0),
            'leadMsgCount': ai.get('leadMsgCount', 0),
            'bf': ai.get('bf', 0),
            'ghost': ai.get('ghostLabel', ''),
            'mofu': ai.get('mofuHits', 0),
            'bofu': ai.get('bofuHits', 0),
            'daysDiff': ai.get('daysDiff', 999),
            'recency': ai.get('recencyLabel', ''),
        })

scores = [i['score'] for i in items]
scores.sort(reverse=True)

print('=' * 60)
print('  ANALISIS: Mengapa Tidak Ada HOT Lead?')
print('=' * 60)
print()
print('DISTRIBUSI SKOR:')
print(f'  Total scored   : {len(scores)}')
print(f'  Max score      : {max(scores) if scores else 0}')
print(f'  Score >= 90 HOT: {sum(1 for s in scores if s >= 90)}')
print(f'  Score 80-89    : {sum(1 for s in scores if 80 <= s < 90)}')
print(f'  Score 70-79    : {sum(1 for s in scores if 70 <= s < 90)}')
print(f'  Score 50-69    : {sum(1 for s in scores if 50 <= s < 70)}')
print(f'  Score < 50     : {sum(1 for s in scores if s < 50)}')
print()

# Top 15 leads
items.sort(key=lambda x: x['score'], reverse=True)
print('TOP 15 LEADS (skor tertinggi):')
print('-' * 60)
for i, t in enumerate(items[:15]):
    name = t['name'][:25]
    score = t['score']
    temp = t['temp']
    pos = t['pos'][:70]
    neg = t['neg'][:70]
    summary = t['summary'][:80]
    reasons = t['reasons'][:80]
    mofu = t['mofu']
    bofu = t['bofu']
    bf = t['bf']
    mc = t['msgCount']
    lmc = t['leadMsgCount']
    dd = t['daysDiff']
    
    print(f'{i+1:2d}. {name:25s} | {score:3d} ({temp})')
    print(f'    MOFU={mofu} BOFU={bofu} BF={bf} msgs={mc} leadMsgs={lmc} days={dd}')
    print(f'    +: {pos}')
    if neg:
        print(f'    -: {neg}')
    print(f'    => {summary}')
    print()

# Root cause analysis
print('=' * 60)
print('  ROOT CAUSE ANALYSIS')
print('=' * 60)
print()
print('Kenapa tidak ada HOT (>=90)?')
print()

# Check data richness
total_with_1_msg = sum(1 for i in items if i['msgCount'] <= 1)
total_with_0_msg = sum(1 for i in items if i['msgCount'] == 0)
total_with_mofu = sum(1 for i in items if i['mofu'] > 0)
total_with_bofu = sum(1 for i in items if i['bofu'] > 0)

print(f'1. DATA TERBATAS:')
print(f'   - Leads dengan 0 pesan   : {total_with_0_msg}/{len(items)} ({total_with_0_msg*100//len(items)}%)')
print(f'   - Leads dengan <=1 pesan : {total_with_1_msg}/{len(items)} ({total_with_1_msg*100//len(items)}%)')
print(f'   - Leads dengan MOFU hit  : {total_with_mofu}/{len(items)}')
print(f'   - Leads dengan BOFU hit  : {total_with_bofu}/{len(items)}')
print()
print('2. SUMBER DATA:')
print('   AI hanya mendapat "lastMessage" dari metadata conversation.')
print('   BUKAN transkrip lengkap percakapan WhatsApp.')
print('   Tanpa transkrip, AI tidak bisa mendeteksi:')
print('   - BOFU signals (survey, booking, DP, KPR)')
print('   - Budget signals (DP siap, KPR ACC)')
print('   - Urgency signals (segera, bulan ini)')
print('   - Conversation depth (bolak-balik)')
print()
print('3. SOLUSI:')
print('   a) Hubungkan n8n workflow ke /scoring/bulk endpoint')
print('      n8n sudah punya akses FULL message history')
print('      Scoring n8n jauh lebih akurat (14+ dimensi penuh)')
print()
print('   b) SocialChat Message API tidak reliabel dari luar')
print('      API mengembalikan 0 pesan (rate limit/quota)')
print('      n8n di jaringan lokal bisa akses message API')

import json

with open('k:/AntiGravity/KGH-MetaAds V2/new_wf_clean.json', 'r', encoding='utf-8') as f:
    wf = json.load(f)

# Force empty settings
wf['settings'] = {}

with open('k:/AntiGravity/KGH-MetaAds V2/new_wf_minimal.json', 'w', encoding='utf-8') as f:
    json.dump(wf, f)

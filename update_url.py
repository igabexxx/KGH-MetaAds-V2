import json

with open('k:/AntiGravity/KGH-MetaAds V2/new_wf_clean.json', 'r', encoding='utf-8') as f:
    wf = json.load(f)

# Find the "Push to KGH Dashboard" node (it should be the last one, index 5)
push_node = next(n for n in wf['nodes'] if n['name'] == 'Push to KGH Dashboard')

# Update the URL inside its jsCode
old_code = push_node['parameters']['jsCode']
new_code = old_code.replace(
    "const url='https://api.kayanagreenhills.com/api/v1/socialchat/scoring/bulk';",
    "const url='http://backend:8000/api/v1/socialchat/scoring/bulk';"
)
push_node['parameters']['jsCode'] = new_code

# Make sure settings is empty
wf['settings'] = {}

with open('k:/AntiGravity/KGH-MetaAds V2/new_wf_minimal.json', 'w', encoding='utf-8') as f:
    json.dump(wf, f)

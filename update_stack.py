import urllib.request
import json
import ssl

portainer_url = "https://192.168.101.226:9443/api/stacks/11/git/redeploy?endpointId=3"
api_key = "ptr_hPzUizSxcX3DK4M6ZGoiX0Si2PZLQgqrHTGv3mVhkdc="

payload = {
    "RepositoryReferenceName": "refs/heads/main",
    "Env": [
        {"name": "DB_PASSWORD", "value": "kgh_admin_secure123!"},
        {"name": "DB_NAME", "value": "kgh_metads"},
        {"name": "META_APP_ID", "value": "demo_meta_app_id"},
        {"name": "META_APP_SECRET", "value": "demo_meta_secret"},
        {"name": "META_ACCESS_TOKEN", "value": "demo_meta_token"},
        {"name": "META_AD_ACCOUNT_ID", "value": "act_12345"},
        {"name": "META_PAGE_ID", "value": "demo_page_id"},
        {"name": "N8N_USER", "value": "admin"},
        {"name": "N8N_PASSWORD", "value": "admin123"},
        {"name": "N8N_ENCRYPTION_KEY", "value": "demo_n8n_key_12345"},
        {"name": "LLM_PROVIDER", "value": "openai"},
        {"name": "LLM_MODEL", "value": "gpt-4o"},
        {"name": "LLM_API_KEY", "value": "sk-demo-key"},
        {"name": "TELEGRAM_BOT_TOKEN", "value": "demo-bot-token"},
        {"name": "TELEGRAM_CHAT_ID", "value": "demo-chat-id"},
        {"name": "WHATSAPP_TOKEN", "value": "demo-wa-token"},
        {"name": "WHATSAPP_NUMBER_ID", "value": "demo-wa-number"},
        {"name": "API_SECRET_KEY", "value": "secret12345"},
        {"name": "WEBHOOK_VERIFY_TOKEN", "value": "kgh_webhook_verify_123"},
        {"name": "SOCIALCHAT_API_KEY", "value": "MTI0NjExMzgxNl9TeWhLc2dDdUlUVGcwQTdWTkZpVg=="},
        {"name": "SOCIALCHAT_APP_ID", "value": "1246113816"},
        {"name": "SOCIALCHAT_SECRET_KEY", "value": "SyhKsgCuITTg0A7VNFiV"},
        {"name": "SOCIALCHAT_BASE_URL", "value": "https://api.socialchat.id/partner"},
        {"name": "CLOUDFLARE_TUNNEL_TOKEN", "value": "eyJhIjoiZDNmZDViZGVlZTRlYzY2NjVmYTQwYWM1MjFhOTc1MGUiLCJ0IjoiMThiYTYwMDMtZmUzNi00YmRlLTgyNDEtMzBhNjgyMjExOWYwIiwicyI6Ik5tSTNabVF5T0RBdE56WTNNeTAwT1RKaUxUZzROR010TjJZd1pETmlNbVV5TlRjeiJ9"}
    ]
}

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(portainer_url, data=data, method="PUT")
req.add_header("X-API-Key", api_key)
req.add_header("Content-Type", "application/json")

context = ssl._create_unverified_context()

try:
    with urllib.request.urlopen(req, context=context) as response:
        res = response.read()
        print("Success:", res.decode("utf-8"))
except urllib.error.HTTPError as e:
    print("Error HTTP", e.code, ":", e.read().decode("utf-8"))
except Exception as e:
    print("Error Exception:", str(e))

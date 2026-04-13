"""Quick verification: Check index doc count and test backend health + chat"""
import requests
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

print("=" * 60)
print("VERIFICATION: Index + Backend Health")
print("=" * 60)

# Get creds from Key Vault
cred = DefaultAzureCredential()
kv = SecretClient(vault_url="https://kv-chubb-mcp-9342.vault.azure.net", credential=cred)
search_endpoint = kv.get_secret("aisearch-endpoint").value
search_key = kv.get_secret("aisearch-key").value

# 1. Check index document count
print("\n[1] AI Search Index:")
sc = SearchClient(
    endpoint=search_endpoint,
    index_name="index-chubb-ai-governance",
    credential=AzureKeyCredential(search_key),
)
count = sc.get_document_count()
print(f"  Documents in index: {count}")

# 2. Health check on backend
print("\n[2] Backend Health Check:")
try:
    r = requests.get("https://app-chubb-backend-poc.azurewebsites.net/health", timeout=30)
    print(f"  HTTP {r.status_code}: {r.text[:200]}")
except Exception as e:
    print(f"  ERROR: {e}")

# 3. Health check on MCP server
print("\n[3] MCP Server Health Check:")
try:
    r = requests.get("https://app-chubb-mcp-poc.azurewebsites.net/health", timeout=30)
    print(f"  HTTP {r.status_code}: {r.text[:200]}")
except Exception as e:
    print(f"  ERROR: {e}")

# 4. Quick chat test
print("\n[4] Quick Chat Test:")
try:
    r = requests.post(
        "https://app-chubb-backend-poc.azurewebsites.net/chat",
        json={"message": "What is Chubb AI governance?", "user_id": "test@chubb.com"},
        timeout=60,
    )
    print(f"  HTTP {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        resp = data.get("response", "")
        print(f"  Response: {resp[:200]}...")
    else:
        print(f"  Body: {r.text[:300]}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\nDone!")

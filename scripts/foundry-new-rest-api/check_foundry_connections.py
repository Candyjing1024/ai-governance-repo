"""Check new Foundry connection capabilities - can it connect to KV and Cosmos?"""
import requests, json
from azure.identity import DefaultAzureCredential

cred = DefaultAzureCredential()
token = cred.get_token("https://management.azure.com/.default").token
h = {"Authorization": f"Bearer {token}"}
SUB = "a3223db3-76f2-4a7c-8684-57b835dc77e7"
RG = "rg-chubb-mcp-poc"
ARM = "https://management.azure.com"
ACCOUNT = "proj-chubb-storage-val-resource"

# 1) List existing connections
print("=" * 60)
print("EXISTING CONNECTIONS")
print("=" * 60)
url = f"{ARM}/subscriptions/{SUB}/resourceGroups/{RG}/providers/Microsoft.CognitiveServices/accounts/{ACCOUNT}/connections?api-version=2025-06-01"
r = requests.get(url, headers=h)
if r.status_code == 200:
    for c in r.json().get("value", []):
        cp = c.get("properties", {})
        print(f"  {c['name']}")
        print(f"    category: {cp.get('category')}")
        print(f"    target: {cp.get('target')}")
        print(f"    authType: {cp.get('authType')}")
        print(f"    metadata: {cp.get('metadata', {})}")
        print()

# 2) Try adding a Key Vault connection
print("=" * 60)
print("ATTEMPT: Add Key Vault connection")
print("=" * 60)
kv_url = "https://kv-chubb-mcp-9342.vault.azure.net/"
kv_rid = f"/subscriptions/{SUB}/resourceGroups/{RG}/providers/Microsoft.KeyVault/vaults/kv-chubb-mcp-9342"

kv_body = {
    "properties": {
        "category": "AzureKeyVault",
        "target": kv_url,
        "authType": "AAD",
        "metadata": {"ResourceId": kv_rid},
    }
}
conn_url = f"{ARM}/subscriptions/{SUB}/resourceGroups/{RG}/providers/Microsoft.CognitiveServices/accounts/{ACCOUNT}/connections/kv-connection?api-version=2025-06-01"
r = requests.put(conn_url, headers=h, json=kv_body)
print(f"  HTTP {r.status_code}")
if r.status_code in (200, 201):
    print(f"  SUCCESS: Key Vault connection created!")
    print(f"  Response: {json.dumps(r.json().get('properties', {}), indent=2)[:300]}")
else:
    print(f"  Response: {r.text[:400]}")
    # Try alternate category name
    print()
    print("  Retrying with category='KeyVault'...")
    kv_body["properties"]["category"] = "KeyVault"
    r2 = requests.put(conn_url, headers=h, json=kv_body)
    print(f"  HTTP {r2.status_code}")
    if r2.status_code in (200, 201):
        print(f"  SUCCESS with 'KeyVault' category!")
    else:
        print(f"  Response: {r2.text[:400]}")

# 3) Check Cosmos connection details (already exists)
print()
print("=" * 60)
print("EXISTING Cosmos DB connection details")
print("=" * 60)
cosmos_url = f"{ARM}/subscriptions/{SUB}/resourceGroups/{RG}/providers/Microsoft.CognitiveServices/accounts/{ACCOUNT}/connections/cosmos-agent-store?api-version=2025-06-01"
r = requests.get(cosmos_url, headers=h)
if r.status_code == 200:
    cp = r.json().get("properties", {})
    print(f"  category: {cp.get('category')}")
    print(f"  target: {cp.get('target')}")
    print(f"  authType: {cp.get('authType')}")
    print(f"  metadata: {json.dumps(cp.get('metadata', {}), indent=2)}")
    print(f"  isSharedToAll: {cp.get('isSharedToAll')}")
    print(f"  provisioningState: {cp.get('provisioningState')}")
else:
    print(f"  HTTP {r.status_code}")

# 4) Check full account properties including encryption options
print()
print("=" * 60)
print("FULL ACCOUNT PROPERTIES (encryption, CMK, storage)")
print("=" * 60)

# Try latest preview API
for api in ["2025-06-01", "2026-01-15-preview"]:
    print(f"\n  --- API {api} ---")
    url = f"{ARM}/subscriptions/{SUB}/resourceGroups/{RG}/providers/Microsoft.CognitiveServices/accounts/{ACCOUNT}?api-version={api}"
    r = requests.get(url, headers=h)
    if r.status_code == 200:
        data = r.json()
        props = data.get("properties", {})
        print(f"  encryption: {props.get('encryption', 'NONE')}")
        print(f"  userOwnedStorage: {props.get('userOwnedStorage', 'NONE')}")
        print(f"  keyVaultProperties: {props.get('keyVaultProperties', 'NONE')}")
        # Check if there are any storage/kv related fields
        for k, v in props.items():
            kl = k.lower()
            if any(word in kl for word in ['key', 'vault', 'storage', 'cosmos', 'encrypt', 'store', 'cmk']):
                print(f"  {k}: {json.dumps(v, indent=2)[:200]}")
    else:
        print(f"  HTTP {r.status_code}")

# 5) List ALL connections after adding KV
print()
print("=" * 60)
print("ALL CONNECTIONS (after KV attempt)")
print("=" * 60)
url = f"{ARM}/subscriptions/{SUB}/resourceGroups/{RG}/providers/Microsoft.CognitiveServices/accounts/{ACCOUNT}/connections?api-version=2025-06-01"
r = requests.get(url, headers=h)
if r.status_code == 200:
    for c in r.json().get("value", []):
        cp = c.get("properties", {})
        print(f"  {c['name']:30s} category={cp.get('category'):20s} target={cp.get('target', '')[:50]}")

print("\nDONE")

"""Check new Foundry (CogSvc) resource connections and try adding Key Vault."""
import requests, json
from azure.identity import DefaultAzureCredential

cred = DefaultAzureCredential()
token = cred.get_token("https://management.azure.com/.default").token
h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
SUB = "a3223db3-76f2-4a7c-8684-57b835dc77e7"
RG = "rg-chubb-mcp-poc"
ARM = "https://management.azure.com"
ACCOUNT = "proj-chubb-storage-val-resource"
base = f"{ARM}/subscriptions/{SUB}/resourceGroups/{RG}/providers/Microsoft.CognitiveServices/accounts/{ACCOUNT}"

# 1) List ALL existing connections
print("=" * 60)
print("EXISTING CONNECTIONS")
print("=" * 60)
r = requests.get(f"{base}/connections?api-version=2025-06-01", headers=h)
if r.status_code == 200:
    conns = r.json().get("value", [])
    print(f"  Total: {len(conns)}")
    for c in conns:
        cp = c.get("properties", {})
        print(f"\n  Name: {c['name']}")
        print(f"    category: {cp.get('category', '?')}")
        print(f"    target: {cp.get('target', '?')}")
        print(f"    authType: {cp.get('authType', '?')}")
        meta = cp.get("metadata", {})
        if meta:
            print(f"    metadata: {json.dumps(meta, indent=6)}")
else:
    print(f"  HTTP {r.status_code}: {r.text[:300]}")

# 2) Try adding Key Vault connection
print("\n" + "=" * 60)
print("ADDING KEY VAULT CONNECTION")
print("=" * 60)
kv_body = {
    "properties": {
        "category": "AzureKeyVault",
        "target": "https://kv-chubb-mcp-9342.vault.azure.net/",
        "authType": "AAD",
        "metadata": {
            "ResourceId": f"/subscriptions/{SUB}/resourceGroups/{RG}/providers/Microsoft.KeyVault/vaults/kv-chubb-mcp-9342"
        }
    }
}
r = requests.put(f"{base}/connections/kv-connection?api-version=2025-06-01", headers=h, json=kv_body)
print(f"  HTTP {r.status_code}")
if r.status_code in (200, 201):
    print("  SUCCESS - Key Vault connected!")
    print(f"  Response: {json.dumps(r.json().get('properties', {}), indent=4)}")
else:
    print(f"  Response: {r.text[:500]}")
    # Try alternative category names
    for cat in ["KeyVault", "AzureKeyVault", "CustomKeys"]:
        kv_body["properties"]["category"] = cat
        r2 = requests.put(f"{base}/connections/kv-connection-{cat.lower()}?api-version=2025-06-01", headers=h, json=kv_body)
        print(f"  Retry category='{cat}': HTTP {r2.status_code}")
        if r2.status_code in (200, 201):
            print(f"    SUCCESS with category={cat}")
            break

# 3) Verify Cosmos connection details
print("\n" + "=" * 60)
print("COSMOS DB CONNECTION DETAILS")
print("=" * 60)
r = requests.get(f"{base}/connections/cosmos-agent-store?api-version=2025-06-01", headers=h)
if r.status_code == 200:
    cp = r.json().get("properties", {})
    print(f"  category: {cp.get('category')}")
    print(f"  target: {cp.get('target')}")
    print(f"  authType: {cp.get('authType')}")
    print(f"  isSharedToAll: {cp.get('isSharedToAll')}")
    print(f"  metadata: {json.dumps(cp.get('metadata', {}), indent=4)}")
else:
    print(f"  HTTP {r.status_code}")

# 4) List connections again to see final state
print("\n" + "=" * 60)
print("FINAL CONNECTION LIST")
print("=" * 60)
r = requests.get(f"{base}/connections?api-version=2025-06-01", headers=h)
if r.status_code == 200:
    conns = r.json().get("value", [])
    for c in conns:
        cp = c.get("properties", {})
        print(f"  {c['name']:30s} category={cp.get('category', '?'):20s} target={cp.get('target', '?')[:50]}")

# 5) Check if there's an encryption/CMK option on the account
print("\n" + "=" * 60)
print("ENCRYPTION / CMK CONFIG")
print("=" * 60)
r = requests.get(f"{base}?api-version=2025-06-01", headers=h)
if r.status_code == 200:
    data = r.json()
    props = data.get("properties", {})
    print(f"  encryption: {props.get('encryption', 'NOT SET')}")
    print(f"  userOwnedStorage: {props.get('userOwnedStorage', 'NOT SET')}")
    # Check if there's a way to PATCH encryption with CMK
    print(f"  disableLocalAuth: {props.get('disableLocalAuth')}")
    print(f"  publicNetworkAccess: {props.get('publicNetworkAccess')}")

print("\nDONE")

"""Check if new Foundry resources are connected to Key Vault."""
import requests, json
from azure.identity import DefaultAzureCredential

cred = DefaultAzureCredential()
token = cred.get_token("https://management.azure.com/.default").token
h = {"Authorization": f"Bearer {token}"}
SUB = "a3223db3-76f2-4a7c-8684-57b835dc77e7"
RG = "rg-chubb-mcp-poc"
ARM = "https://management.azure.com"

# 1) CogSvc account (new Foundry)
print("=" * 60)
print("proj-chubb-storage-val-resource (CognitiveServices)")
print("=" * 60)
url = f"{ARM}/subscriptions/{SUB}/resourceGroups/{RG}/providers/Microsoft.CognitiveServices/accounts/proj-chubb-storage-val-resource?api-version=2025-06-01"
r = requests.get(url, headers=h)
if r.status_code == 200:
    props = r.json().get("properties", {})
    enc = props.get("encryption", "NONE")
    print(f"  encryption: {json.dumps(enc, indent=2)}")
    print(f"  userOwnedStorage: {props.get('userOwnedStorage', 'NONE')}")
    kvp = props.get("keyVaultProperties", "NONE")
    print(f"  keyVaultProperties: {kvp}")
    print(f"  All property keys: {sorted(props.keys())}")
else:
    print(f"  HTTP {r.status_code}")

# 2) CogSvc project
print()
print("=" * 60)
print("proj-chubb-storage-val (CogSvc project)")
print("=" * 60)
url2 = f"{ARM}/subscriptions/{SUB}/resourceGroups/{RG}/providers/Microsoft.CognitiveServices/accounts/proj-chubb-storage-val-resource/projects/proj-chubb-storage-val?api-version=2025-06-01"
r2 = requests.get(url2, headers=h)
if r2.status_code == 200:
    props2 = r2.json().get("properties", {})
    print(f"  All property keys: {sorted(props2.keys())}")
else:
    print(f"  HTTP {r2.status_code}")

# 3) ML workspace Hub (old architecture)
print()
print("=" * 60)
print("hub-chubb-cosmos-val (ML workspace Hub)")
print("=" * 60)
url3 = f"{ARM}/subscriptions/{SUB}/resourceGroups/{RG}/providers/Microsoft.MachineLearningServices/workspaces/hub-chubb-cosmos-val?api-version=2025-01-01-preview"
r3 = requests.get(url3, headers=h)
if r3.status_code == 200:
    props3 = r3.json().get("properties", {})
    print(f"  keyVault: {props3.get('keyVault', 'NONE')}")
    print(f"  storageAccount: {props3.get('storageAccount', 'NONE')}")
    print(f"  agentStoreSettings: {props3.get('agentStoreSettings', 'NONE')}")
    print(f"  provisioningState: {props3.get('provisioningState', '?')}")
elif r3.status_code == 404:
    print("  NOT FOUND (hub not created yet)")
else:
    print(f"  HTTP {r3.status_code}: {r3.text[:200]}")

# 4) Also check connections on CogSvc account
print()
print("=" * 60)
print("Connections on proj-chubb-storage-val-resource")
print("=" * 60)
url4 = f"{ARM}/subscriptions/{SUB}/resourceGroups/{RG}/providers/Microsoft.CognitiveServices/accounts/proj-chubb-storage-val-resource/connections?api-version=2025-06-01"
r4 = requests.get(url4, headers=h)
if r4.status_code == 200:
    conns = r4.json().get("value", [])
    for c in conns:
        cp = c.get("properties", {})
        print(f"  {c['name']:30s} category={cp.get('category', '?'):15s} target={cp.get('target', '?')[:60]}")
else:
    print(f"  HTTP {r4.status_code}")

print("\nDONE")

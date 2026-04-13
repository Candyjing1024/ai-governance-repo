"""Compare mcp-poc-010 vs proj-chubb-storage-val to find storage config differences."""
import json
import requests
from azure.identity import DefaultAzureCredential

SUB_ID = "a3223db3-76f2-4a7c-8684-57b835dc77e7"
RG = "rg-chubb-mcp-poc"
ARM = "https://management.azure.com"
API = "2026-01-15-preview"

cred = DefaultAzureCredential()


def get_headers():
    token = cred.get_token("https://management.azure.com/.default").token
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def inspect_account(account_name):
    print("=" * 60)
    print(f"ACCOUNT: {account_name}")
    print("=" * 60)
    headers = get_headers()
    base = f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}/providers/Microsoft.CognitiveServices/accounts/{account_name}"

    # Get account
    r = requests.get(f"{base}?api-version={API}", headers=headers)
    if r.status_code != 200:
        print(f"  ERROR: HTTP {r.status_code}")
        return
    acct = r.json()
    props = acct.get("properties", {})

    print(f"  Kind: {acct.get('kind')}")
    print(f"  Location: {acct.get('location')}")
    print(f"  SKU: {acct.get('sku')}")
    print(f"  Identity: {acct.get('identity', {}).get('type')}")
    print(f"  PrincipalId: {acct.get('identity', {}).get('principalId')}")
    print(f"\n  Properties keys: {sorted(props.keys())}")

    # Print ALL properties
    for k in sorted(props.keys()):
        v = props[k]
        sv = json.dumps(v, default=str) if not isinstance(v, str) else v
        if len(sv) > 300:
            sv = sv[:300] + "..."
        print(f"    {k}: {sv}")

    # Check connections
    print(f"\n  --- Connections ---")
    r = requests.get(f"{base}/connections?api-version={API}", headers=headers)
    if r.status_code == 200:
        conns = r.json().get("value", [])
        print(f"  {len(conns)} connection(s):")
        for c in conns:
            name = c.get("name", "?")
            cat = c.get("properties", {}).get("category", "?")
            auth = c.get("properties", {}).get("authType", "?")
            target = c.get("properties", {}).get("target", "?")
            print(f"    {name}: cat={cat} auth={auth} target={target[:80]}")
    else:
        print(f"  Connections: HTTP {r.status_code}")

    # Check deployments
    print(f"\n  --- Deployments ---")
    r = requests.get(f"{base}/deployments?api-version=2024-10-01", headers=headers)
    if r.status_code == 200:
        deps = r.json().get("value", [])
        print(f"  {len(deps)} deployment(s):")
        for d in deps:
            name = d.get("name", "?")
            model = d.get("properties", {}).get("model", {})
            model_name = model.get("name", "?") if isinstance(model, dict) else str(model)
            print(f"    {name}: model={model_name}")
    else:
        print(f"  Deployments: HTTP {r.status_code}")

    # List projects
    print(f"\n  --- Projects ---")
    r = requests.get(f"{base}/projects?api-version={API}", headers=headers)
    if r.status_code == 200:
        projs = r.json().get("value", [])
        print(f"  {len(projs)} project(s):")
        for p in projs:
            pname = p.get("name", "?")
            pprops = p.get("properties", {})
            print(f"    {pname}:")
            print(f"      Keys: {sorted(pprops.keys())}")
            for pk in sorted(pprops.keys()):
                pv = json.dumps(pprops[pk], default=str) if not isinstance(pprops[pk], str) else pprops[pk]
                if len(pv) > 200:
                    pv = pv[:200] + "..."
                print(f"      {pk}: {pv}")
    else:
        print(f"  Projects: HTTP {r.status_code}")


# Also check if mcp-poc-010 has an ML workspace counterpart
def check_ml_workspaces():
    print("\n" + "=" * 60)
    print("ML WORKSPACES (for comparison)")
    print("=" * 60)
    headers = get_headers()
    url = (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
           f"/providers/Microsoft.MachineLearningServices/workspaces"
           f"?api-version=2025-01-01-preview")
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        ws = r.json().get("value", [])
        print(f"  {len(ws)} workspace(s):")
        for w in ws:
            name = w.get("name", "?")
            kind = w.get("kind", "?")
            loc = w.get("location", "?")
            wprops = w.get("properties", {})
            kv = wprops.get("keyVault", "N/A")
            sa = wprops.get("storageAccount", "N/A")
            agents = wprops.get("agentsEndpointUri", "N/A")
            hub = wprops.get("hubResourceId", "N/A")
            agent_store = wprops.get("agentStoreSettings", "N/A")
            print(f"\n    {name} (kind={kind}, loc={loc}):")
            print(f"      keyVault: {kv}")
            print(f"      storageAccount: {sa}")
            print(f"      agentsEndpoint: {agents[:100] if agents != 'N/A' else 'N/A'}")
            print(f"      hubResourceId: {hub}")
            print(f"      agentStoreSettings: {agent_store}")


if __name__ == "__main__":
    inspect_account("mcp-poc-010-resource")
    print("\n\n")
    inspect_account("proj-chubb-storage-val-resource")
    check_ml_workspaces()

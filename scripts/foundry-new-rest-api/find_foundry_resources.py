"""
Find the new Foundry resources - search broadly across resource types.
"""
import json
import requests
from azure.identity import DefaultAzureCredential

SUB_ID = "a3223db3-76f2-4a7c-8684-57b835dc77e7"
RG = "rg-chubb-mcp-poc"
ARM = "https://management.azure.com"


def get_headers():
    cred = DefaultAzureCredential()
    token = cred.get_token("https://management.azure.com/.default").token
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def main():
    headers = get_headers()

    # 1. List ALL resources in the resource group
    print("=" * 60)
    print("ALL RESOURCES IN rg-chubb-mcp-poc")
    print("=" * 60)
    url = f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}/resources?api-version=2021-04-01"
    r = requests.get(url, headers=headers)
    resources = r.json().get("value", [])
    for res in sorted(resources, key=lambda x: x.get("type", "")):
        name = res.get("name", "?")
        rtype = res.get("type", "?")
        location = res.get("location", "?")
        kind = res.get("kind", "")
        kind_str = f" (kind={kind})" if kind else ""
        print(f"  {rtype}: {name} [{location}]{kind_str}")

    # 2. Specifically search for anything with "chubb-storage" or "proj-chubb" in name
    print("\n" + "=" * 60)
    print("MATCHING 'proj-chubb' or 'storage-val'")
    print("=" * 60)
    for res in resources:
        name = res.get("name", "")
        if "chubb-storage" in name.lower() or "proj-chubb" in name.lower() or "storage-val" in name.lower():
            print(f"  MATCH: {res.get('type')}: {name} [{res.get('location')}]")
            # Get details
            rid = res.get("id", "")
            if rid:
                for api_ver in ["2025-01-01-preview", "2024-10-01", "2024-01-01-preview", "2023-10-01"]:
                    dr = requests.get(f"{ARM}{rid}?api-version={api_ver}", headers=headers)
                    if dr.status_code == 200:
                        data = dr.json()
                        props = data.get("properties", {})
                        print(f"    API {api_ver}: OK")
                        print(f"    Kind: {data.get('kind', 'N/A')}")
                        for key in sorted(props.keys()):
                            kl = key.lower()
                            if any(kw in kl for kw in ["endpoint", "hub", "keyvault", "storage", "cosmos", "agent", "workspace", "portal", "url"]):
                                val = props[key]
                                if isinstance(val, (dict, list)):
                                    val = json.dumps(val)[:200]
                                elif isinstance(val, str) and len(val) > 200:
                                    val = val[:200]
                                print(f"    {key}: {val}")
                        break

    # 3. Check ML workspaces specifically with multiple API versions
    print("\n" + "=" * 60)
    print("ML WORKSPACES (all API versions)")
    print("=" * 60)
    for api_ver in ["2025-01-01-preview", "2024-10-01-preview", "2024-10-01", "2024-04-01"]:
        url = (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
               f"/providers/Microsoft.MachineLearningServices/workspaces"
               f"?api-version={api_ver}")
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            ws = r.json().get("value", [])
            print(f"  API {api_ver}: {len(ws)} workspace(s)")
            for w in ws:
                print(f"    {w.get('name')} (kind={w.get('kind', '?')}, "
                      f"location={w.get('location', '?')})")

    # 4. Check if there's a new resource provider for Foundry
    print("\n" + "=" * 60)
    print("CHECK FOR NEW FOUNDRY RESOURCE TYPES")
    print("=" * 60)
    # Look for anything AI-related
    for res in resources:
        rtype = res.get("type", "").lower()
        if any(kw in rtype for kw in ["ai", "foundry", "cognitive", "machinelearning", "ml"]):
            print(f"  {res.get('type')}: {res.get('name')} [{res.get('location')}] kind={res.get('kind', '')}")

    # 5. Search subscription-wide for new Foundry resource types
    print("\n" + "=" * 60)
    print("SUBSCRIPTION-WIDE SEARCH: Foundry resources")
    print("=" * 60)
    sub_url = f"{ARM}/subscriptions/{SUB_ID}/resources?api-version=2021-04-01&$filter=resourceGroup eq '{RG}'"
    r = requests.get(sub_url, headers=headers)
    if r.status_code == 200:
        for res in r.json().get("value", []):
            rtype = res.get("type", "").lower()
            name = res.get("name", "")
            if "foundry" in rtype or "foundry" in name.lower() or "proj-chubb" in name.lower():
                print(f"  {res.get('type')}: {name} [{res.get('location')}]")
                rid = res.get("id", "")
                if rid:
                    dr = requests.get(f"{ARM}{rid}?api-version=2025-01-01-preview", headers=headers)
                    if dr.status_code == 200:
                        print(f"    Properties: {json.dumps(dr.json().get('properties', {}))[:500]}")


if __name__ == "__main__":
    main()

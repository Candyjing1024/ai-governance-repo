"""
01 - Create Foundry V2 Resource (AIServices account) + Project.

Uses CognitiveServices ARM API (latest stable: 2025-12-01).
Resource type: Microsoft.CognitiveServices/accounts (kind=AIServices)
Project type:  Microsoft.CognitiveServices/accounts/projects
"""
import json, sys, os, requests
sys.path.insert(0, os.path.dirname(__file__))
from _auth import load_config, arm_headers, ARM, account_id, project_id, rg_id, poll


def run():
    cfg = load_config()
    h = arm_headers(cfg)
    api = cfg["foundry"]["api_version"]
    location = cfg["location"]
    acct_name = cfg["foundry"]["account_name"]
    proj_name = cfg["foundry"]["project_name"]

    # ---- 1. Create AIServices Account (Foundry V2 resource) ----
    print("=" * 60)
    print(f"STEP 1: Create Foundry resource '{acct_name}'")
    print("=" * 60)

    acct_url = f"{ARM}{account_id(cfg)}?api-version={api}"

    # Check if exists
    r = requests.get(acct_url, headers=h)
    if r.status_code == 200:
        state = r.json()['properties']['provisioningState']
        print(f"  Already exists (state={state})")
        # Ensure allowProjectManagement is enabled
        props = r.json().get("properties", {})
        if not props.get("allowProjectManagement"):
            print(f"  Enabling allowProjectManagement...")
            patch = {"properties": {"allowProjectManagement": True}}
            rp = requests.patch(acct_url, headers=h, json=patch)
            if rp.status_code in (200, 201, 202):
                print(f"  Updated (HTTP {rp.status_code})")
                poll(acct_url, h, f"Account '{acct_name}'")
            else:
                print(f"  Patch error: {rp.status_code} {rp.text[:300]}")
    else:
        body = {
            "location": location,
            "kind": "AIServices",
            "identity": {"type": "SystemAssigned"},
            "sku": {"name": "S0"},
            "properties": {
                "customSubDomainName": acct_name,
                "publicNetworkAccess": "Enabled",
                "allowProjectManagement": True,
            },
        }
        r = requests.put(acct_url, headers=h, json=body)
        if r.status_code in (200, 201, 202):
            print(f"  Creating... (HTTP {r.status_code})")
        else:
            print(f"  ERROR: {r.status_code} {r.text[:400]}")
            return
        poll(acct_url, h, f"Account '{acct_name}'")

    # Show account details
    r = requests.get(acct_url, headers=h)
    acct = r.json()
    props = acct.get("properties", {})
    print(f"\n  Kind:       {acct.get('kind')}")
    print(f"  Location:   {acct.get('location')}")
    print(f"  Endpoint:   {props.get('endpoint')}")
    print(f"  MI:         {acct.get('identity', {}).get('principalId', 'N/A')}")

    # ---- 2. Create Project ----
    print(f"\n{'='*60}")
    print(f"STEP 2: Create Project '{proj_name}'")
    print("=" * 60)

    proj_url = f"{ARM}{project_id(cfg)}?api-version={api}"

    r = requests.get(proj_url, headers=h)
    if r.status_code == 200:
        print(f"  Already exists (state={r.json()['properties']['provisioningState']})")
    else:
        body = {
            "location": location,
            "identity": {"type": "SystemAssigned"},
            "properties": {
                "displayName": proj_name,
                "description": "Foundry V2 E2E POC project",
            },
        }
        r = requests.put(proj_url, headers=h, json=body)
        if r.status_code in (200, 201, 202):
            print(f"  Creating... (HTTP {r.status_code})")
        else:
            print(f"  ERROR: {r.status_code} {r.text[:400]}")
            return
        poll(proj_url, h, f"Project '{proj_name}'")

    # Show project details
    r = requests.get(proj_url, headers=h)
    proj = r.json()
    pprops = proj.get("properties", {})
    print(f"\n  Location:   {proj.get('location')}")
    print(f"  MI:         {proj.get('identity', {}).get('principalId', 'N/A')}")
    endpoints = pprops.get("endpoints", {})
    if isinstance(endpoints, dict):
        for k, v in endpoints.items():
            print(f"  {k}: {v}")

    print(f"\nDone. Run 02-deploy-model.py next.")


if __name__ == "__main__":
    run()

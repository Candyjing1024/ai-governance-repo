"""
POC: Azure Policy for Limiting AI Model Deployments in Foundry.

This script uses the Azure REST API (ARM) to:
1. Find the built-in policy definition for approved registry models
2. Assign the policy to a resource group with allowed model list
3. Test deploying a BLOCKED model (expects Deny)
4. Test deploying an ALLOWED model (expects success)
5. Check compliance status

Built-in policy: "Cognitive Services Deployments should only use approved Registry Models"

Reference: https://learn.microsoft.com/en-us/azure/foundry/how-to/model-deployment-policy

Prerequisites:
  - pip install azure-identity requests
  - Owner or Resource Policy Contributor role on target resource group
"""
import json
import time
import requests
from azure.identity import DefaultAzureCredential

# ============================================================
# CONFIGURATION — Update for your environment
# ============================================================
SUB_ID       = "<your-subscription-id>"
RG           = "<your-resource-group>"
ACCOUNT_NAME = "<your-foundry-account-name>"    # CognitiveServices/AIServices account
LOCATION     = "eastus"
ARM          = "https://management.azure.com"

# Policy assignment settings
POLICY_ASSIGNMENT_NAME = "limit-foundry-model-deployments"
POLICY_DISPLAY_NAME    = "Limit Foundry Model Deployments - POC"

# Approved models — only these should be deployable
# IMPORTANT: The policy uses AND logic: publisher NOT in allowedPublishers AND
# assetId NOT in allowedAssetIds. Setting allowedPublishers=["OpenAI"] would
# allow ALL OpenAI models regardless of assetIds. Use empty publishers and
# rely on allowedAssetIds for fine-grained control.
ALLOWED_PUBLISHERS = []
ALLOWED_ASSET_IDS  = [
    "azureml://registries/azure-openai/models/gpt-4o/versions/2024-11-20",
    "azureml://registries/azure-openai/models/gpt-4o-mini/versions/2024-07-18",
]

# Test models
ALLOWED_MODEL   = {"name": "gpt-4o",       "version": "2024-11-20"}
BLOCKED_MODEL   = {"name": "gpt-35-turbo", "version": "0125"}

# API versions
API_POLICY  = "2023-04-01"
API_DEPLOY  = "2024-10-01"

# ============================================================
# AUTH
# ============================================================
_credential = None

def get_headers():
    global _credential
    if _credential is None:
        _credential = DefaultAzureCredential()
    token = _credential.get_token("https://management.azure.com/.default").token
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ============================================================
# STEP 1: Find the built-in policy definition
# ============================================================
def find_policy_definition():
    print("=" * 60)
    print("STEP 1: Find built-in policy definition")
    print("=" * 60)

    headers = get_headers()
    url = f"{ARM}/subscriptions/{SUB_ID}/providers/Microsoft.Authorization/policyDefinitions?api-version={API_POLICY}&$filter=policyType eq 'BuiltIn'"

    # Search through built-in policies
    target_name = "Cognitive Services Deployments should only use approved Registry Models"
    next_url = url
    found = None

    while next_url and not found:
        r = requests.get(next_url, headers=headers)
        if r.status_code != 200:
            print(f"  ERROR: HTTP {r.status_code}")
            print(f"  {r.text[:300]}")
            return None

        data = r.json()
        for p in data.get("value", []):
            display = p.get("properties", {}).get("displayName", "")
            if "approved Registry Models" in display or "approved registry models" in display.lower():
                found = p
                break

        next_url = data.get("nextLink")

    if not found:
        print("  ERROR: Built-in policy not found!")
        print("  Searching for similar policies...")
        # Broader search
        r = requests.get(url, headers=headers)
        for p in r.json().get("value", [])[:500]:
            dn = p.get("properties", {}).get("displayName", "")
            if "cognitive" in dn.lower() and "model" in dn.lower():
                print(f"    - {dn}")
        return None

    policy_id = found["id"]
    policy_name = found["name"]
    display_name = found["properties"]["displayName"]
    params = found["properties"].get("parameters", {})

    print(f"  Found: {display_name}")
    print(f"  ID: {policy_id}")
    print(f"  Name: {policy_name}")
    print(f"  Parameters: {list(params.keys())}")

    return policy_id


# ============================================================
# STEP 2: Assign the policy to the resource group
# ============================================================
def assign_policy(policy_def_id):
    print("\n" + "=" * 60)
    print("STEP 2: Assign policy to resource group")
    print("=" * 60)

    headers = get_headers()
    rg_scope = f"/subscriptions/{SUB_ID}/resourceGroups/{RG}"
    assignment_url = (
        f"{ARM}{rg_scope}/providers/Microsoft.Authorization"
        f"/policyAssignments/{POLICY_ASSIGNMENT_NAME}?api-version={API_POLICY}"
    )

    # Check if already exists
    r = requests.get(assignment_url, headers=headers)
    if r.status_code == 200:
        print(f"  Policy assignment already exists. Deleting and recreating...")
        requests.delete(assignment_url, headers=headers)
        time.sleep(5)

    # Create assignment
    body = {
        "properties": {
            "displayName": POLICY_DISPLAY_NAME,
            "description": "POC: Limit AI model deployments to approved models only",
            "policyDefinitionId": policy_def_id,
            "scope": rg_scope,
            "enforcementMode": "Default",
            "parameters": {
                "effect": {"value": "Deny"},
                "allowedPublishers": {"value": ALLOWED_PUBLISHERS},
                "allowedAssetIds": {"value": ALLOWED_ASSET_IDS},
            },
        }
    }

    print(f"  Scope: {rg_scope}")
    print(f"  Effect: Deny")
    print(f"  Allowed Publishers: {ALLOWED_PUBLISHERS}")
    print(f"  Allowed Asset IDs:")
    for aid in ALLOWED_ASSET_IDS:
        print(f"    - {aid}")

    r = requests.put(assignment_url, headers=headers, json=body)
    if r.status_code in (200, 201):
        result = r.json()
        print(f"\n  SUCCESS: Policy assigned")
        print(f"  Assignment ID: {result.get('id')}")
        print(f"  Enforcement: {result['properties'].get('enforcementMode')}")
        return True
    else:
        print(f"\n  ERROR: HTTP {r.status_code}")
        print(f"  {r.text[:500]}")
        return False


# ============================================================
# STEP 3: Test BLOCKED model deployment (should fail)
# ============================================================
def test_blocked_deployment():
    print("\n" + "=" * 60)
    print(f"STEP 3: Test BLOCKED model ({BLOCKED_MODEL['name']})")
    print("=" * 60)
    print(f"  Deploying: {BLOCKED_MODEL['name']} v{BLOCKED_MODEL['version']}")
    print(f"  Expected: DENIED by policy\n")

    headers = get_headers()
    deploy_name = f"test-blocked-{BLOCKED_MODEL['name']}"
    account_rid = (
        f"/subscriptions/{SUB_ID}/resourceGroups/{RG}"
        f"/providers/Microsoft.CognitiveServices/accounts/{ACCOUNT_NAME}"
    )
    url = f"{ARM}{account_rid}/deployments/{deploy_name}?api-version={API_DEPLOY}"

    body = {
        "sku": {"name": "GlobalStandard", "capacity": 1},
        "properties": {
            "model": {
                "format": "OpenAI",
                "name": BLOCKED_MODEL["name"],
                "version": BLOCKED_MODEL["version"],
            }
        },
    }

    r = requests.put(url, headers=headers, json=body)

    if r.status_code == 403 or "RequestDisallowedByPolicy" in r.text or "PolicyViolation" in r.text:
        print(f"  PASS: Deployment correctly BLOCKED by policy!")
        print(f"  HTTP {r.status_code}")
        # Extract policy error
        try:
            err = r.json().get("error", {})
            print(f"  Code: {err.get('code', 'N/A')}")
            msg = err.get("message", "")[:300]
            print(f"  Message: {msg}")
        except Exception:
            pass
        return True
    elif r.status_code in (200, 201, 202):
        print(f"  WARNING: Deployment was NOT blocked! (HTTP {r.status_code})")
        print(f"  Policy may not have propagated. Wait 15 minutes and retry.")
        # Cleanup
        print(f"  Cleaning up test deployment...")
        requests.delete(url, headers=headers)
        return False
    else:
        print(f"  HTTP {r.status_code}")
        print(f"  Response: {r.text[:500]}")
        if "disallowed by policy" in r.text.lower():
            print(f"\n  PASS: Policy blocked the deployment!")
            return True
        print(f"\n  INCONCLUSIVE: Check response above.")
        return False


# ============================================================
# STEP 4: Test ALLOWED model deployment (should succeed)
# ============================================================
def test_allowed_deployment():
    print("\n" + "=" * 60)
    print(f"STEP 4: Test ALLOWED model ({ALLOWED_MODEL['name']})")
    print("=" * 60)
    print(f"  Deploying: {ALLOWED_MODEL['name']} v{ALLOWED_MODEL['version']}")
    print(f"  Expected: ALLOWED by policy\n")

    headers = get_headers()
    deploy_name = f"test-allowed-{ALLOWED_MODEL['name']}"
    account_rid = (
        f"/subscriptions/{SUB_ID}/resourceGroups/{RG}"
        f"/providers/Microsoft.CognitiveServices/accounts/{ACCOUNT_NAME}"
    )
    url = f"{ARM}{account_rid}/deployments/{deploy_name}?api-version={API_DEPLOY}"

    body = {
        "sku": {"name": "GlobalStandard", "capacity": 1},
        "properties": {
            "model": {
                "format": "OpenAI",
                "name": ALLOWED_MODEL["name"],
                "version": ALLOWED_MODEL["version"],
            }
        },
    }

    r = requests.put(url, headers=headers, json=body)

    if r.status_code in (200, 201, 202):
        print(f"  PASS: Allowed model deployed successfully! (HTTP {r.status_code})")
        # Cleanup
        print(f"  Cleaning up test deployment...")
        time.sleep(5)
        requests.delete(url, headers=headers)
        return True
    elif "RequestDisallowedByPolicy" in r.text:
        print(f"  FAIL: Allowed model was blocked by policy! (HTTP {r.status_code})")
        print(f"  Check that allowedAssetIds includes this exact model+version.")
        return False
    else:
        print(f"  HTTP {r.status_code}")
        print(f"  Response: {r.text[:500]}")
        return False


# ============================================================
# STEP 5: Check compliance status
# ============================================================
def check_compliance():
    print("\n" + "=" * 60)
    print("STEP 5: Check policy compliance")
    print("=" * 60)

    headers = get_headers()
    rg_scope = f"/subscriptions/{SUB_ID}/resourceGroups/{RG}"

    # Get assignment details
    url = (
        f"{ARM}{rg_scope}/providers/Microsoft.Authorization"
        f"/policyAssignments/{POLICY_ASSIGNMENT_NAME}?api-version={API_POLICY}"
    )
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        a = r.json()["properties"]
        print(f"  Assignment: {a.get('displayName')}")
        print(f"  Enforcement: {a.get('enforcementMode')}")
        print(f"  Effect: {a['parameters']['effect']['value']}")
    else:
        print(f"  Assignment not found (HTTP {r.status_code})")
        return

    # Trigger compliance scan
    print("\n  Triggering on-demand compliance scan...")
    scan_url = (
        f"{ARM}{rg_scope}/providers/Microsoft.PolicyInsights"
        f"/policyStates/latest/triggerEvaluation?api-version=2019-10-01"
    )
    r = requests.post(scan_url, headers=headers)
    if r.status_code == 202:
        print(f"  Compliance scan triggered (runs async).")
    else:
        print(f"  Scan trigger: HTTP {r.status_code} (may require PolicyInsights RP)")

    # Check compliance state
    print("\n  Note: Full compliance results take up to 24 hours.")
    compliance_url = (
        f"{ARM}{rg_scope}/providers/Microsoft.PolicyInsights"
        f"/policyStates/latest/summarize?api-version=2019-10-01"
    )
    r = requests.post(compliance_url, headers=headers)
    if r.status_code == 200:
        summary = r.json().get("value", [{}])[0].get("results", {})
        print(f"  Compliant: {summary.get('resourceDetails', [{}])[0].get('count', 'N/A') if summary.get('resourceDetails') else 'N/A'}")
    else:
        print(f"  Compliance summary: HTTP {r.status_code}")


# ============================================================
# CLEANUP: Remove the policy assignment
# ============================================================
def cleanup():
    print("\n" + "=" * 60)
    print("CLEANUP: Remove policy assignment")
    print("=" * 60)

    headers = get_headers()
    rg_scope = f"/subscriptions/{SUB_ID}/resourceGroups/{RG}"
    url = (
        f"{ARM}{rg_scope}/providers/Microsoft.Authorization"
        f"/policyAssignments/{POLICY_ASSIGNMENT_NAME}?api-version={API_POLICY}"
    )

    r = requests.delete(url, headers=headers)
    if r.status_code in (200, 204):
        print(f"  Policy assignment removed.")
    elif r.status_code == 404:
        print(f"  Assignment not found (already removed).")
    else:
        print(f"  HTTP {r.status_code}: {r.text[:300]}")


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print("POC: Azure Policy — Limit Foundry Model Deployments")
    print("=" * 60)
    print(f"  Subscription: {SUB_ID}")
    print(f"  Resource Group: {RG}")
    print(f"  Account: {ACCOUNT_NAME}")
    print(f"  Allowed Models: {[m for m in ALLOWED_ASSET_IDS]}")
    print(f"  Blocked Test: {BLOCKED_MODEL['name']}")
    print()

    # Step 1: Find policy
    policy_def_id = find_policy_definition()
    if not policy_def_id:
        return

    # Step 2: Assign policy
    if not assign_policy(policy_def_id):
        return

    # Step 3: Test blocked model
    print("\n  Note: Policy may take up to 15 minutes to propagate.")
    input("  Press ENTER to proceed with deployment tests...\n")

    blocked_ok = test_blocked_deployment()

    # Step 4: Test allowed model
    allowed_ok = test_allowed_deployment()

    # Step 5: Compliance
    check_compliance()

    # Summary
    print("\n" + "=" * 60)
    print("POC RESULTS")
    print("=" * 60)
    print(f"  Blocked model denied:  {'PASS' if blocked_ok else 'FAIL/PENDING'}")
    print(f"  Allowed model deployed: {'PASS' if allowed_ok else 'FAIL/PENDING'}")
    print()
    print("  To cleanup (remove policy assignment):")
    print("    python 02-Validate-Model-Policy.py --cleanup")
    print()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--cleanup":
        cleanup()
    else:
        main()

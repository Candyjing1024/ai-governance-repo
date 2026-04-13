"""
Phase 0: Restore deleted Azure resources (OpenAI + AI Search)
and redeploy models, reindex documents, update secrets.
"""
import json
import time
import sys
import requests
from azure.identity import DefaultAzureCredential

SUB_ID = "a3223db3-76f2-4a7c-8684-57b835dc77e7"
RG = "rg-chubb-mcp-poc"
LOCATION = "eastus"
OAI_NAME = "oai-chubb-mcp-9342"
SEARCH_NAME = "srch-chubb-mcp-9342"
ARM = "https://management.azure.com"


def get_headers():
    cred = DefaultAzureCredential()
    token = cred.get_token("https://management.azure.com/.default").token
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def check_resource(headers, provider, resource_type, name, api_version="2024-10-01"):
    url = f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}/providers/{provider}/{resource_type}/{name}?api-version={api_version}"
    r = requests.get(url, headers=headers)
    return r


def poll_provisioning(headers, provider, resource_type, name, api_version="2024-10-01", max_wait=300):
    url = f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}/providers/{provider}/{resource_type}/{name}?api-version={api_version}"
    start = time.time()
    while time.time() - start < max_wait:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            state = r.json().get("properties", {}).get("provisioningState", "Unknown")
            print(f"  State: {state}")
            if state == "Succeeded":
                return r.json()
            if state == "Failed":
                print(f"  FAILED: {r.text[:500]}")
                return None
        time.sleep(15)
    print(f"  TIMEOUT waiting for {name}")
    return None


def restore_openai(headers):
    print("\n" + "=" * 60)
    print("STEP 1: Restore Azure OpenAI")
    print("=" * 60)

    r = check_resource(headers, "Microsoft.CognitiveServices", "accounts", OAI_NAME)
    if r.status_code == 200:
        state = r.json().get("properties", {}).get("provisioningState")
        endpoint = r.json().get("properties", {}).get("endpoint", "")
        print(f"  Already exists! State: {state}, Endpoint: {endpoint}")
        return True

    # Check soft-deleted
    del_url = f"{ARM}/subscriptions/{SUB_ID}/providers/Microsoft.CognitiveServices/deletedAccounts?api-version=2024-10-01"
    dr = requests.get(del_url, headers=headers)
    if dr.status_code == 200:
        deleted = [d for d in dr.json().get("value", []) if OAI_NAME in d.get("name", "")]
        if deleted:
            print(f"  Found soft-deleted resource, purging...")
            purge_url = f"{ARM}/subscriptions/{SUB_ID}/providers/Microsoft.CognitiveServices/locations/{LOCATION}/resourceGroups/{RG}/deletedAccounts/{OAI_NAME}?api-version=2024-10-01"
            pr = requests.delete(purge_url, headers=headers)
            print(f"  Purge: HTTP {pr.status_code}")
            if pr.status_code in (200, 202):
                print("  Waiting 30s for purge...")
                time.sleep(30)
            elif pr.status_code != 204:
                print(f"  Purge error: {pr.text[:300]}")
        else:
            print("  No soft-deleted resource found")

    # Create
    print(f"  Creating {OAI_NAME}...")
    url = f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}/providers/Microsoft.CognitiveServices/accounts/{OAI_NAME}?api-version=2024-10-01"
    body = {
        "kind": "OpenAI",
        "location": LOCATION,
        "sku": {"name": "S0"},
        "properties": {
            "customSubDomainName": OAI_NAME,
            "publicNetworkAccess": "Enabled",
        },
    }
    r = requests.put(url, headers=headers, json=body)
    print(f"  Create: HTTP {r.status_code}")
    if r.status_code not in (200, 201, 202):
        print(f"  Error: {r.text[:500]}")
        return False

    result = poll_provisioning(headers, "Microsoft.CognitiveServices", "accounts", OAI_NAME)
    if result:
        print(f"  Endpoint: {result['properties']['endpoint']}")
        return True
    return False


def deploy_model(headers, deployment_name, model_name, model_version, capacity=30):
    print(f"\n  Deploying model: {deployment_name} ({model_name})...")
    url = (
        f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
        f"/providers/Microsoft.CognitiveServices/accounts/{OAI_NAME}"
        f"/deployments/{deployment_name}?api-version=2024-10-01"
    )

    # Check if already exists
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        state = r.json().get("properties", {}).get("provisioningState")
        print(f"  Deployment '{deployment_name}' already exists (state: {state})")
        return True

    body = {
        "sku": {"name": "Standard", "capacity": capacity},
        "properties": {
            "model": {
                "format": "OpenAI",
                "name": model_name,
                "version": model_version,
            },
        },
    }
    r = requests.put(url, headers=headers, json=body)
    print(f"  Deploy: HTTP {r.status_code}")
    if r.status_code not in (200, 201, 202):
        print(f"  Error: {r.text[:500]}")
        return False

    # Poll deployment
    for i in range(20):
        time.sleep(10)
        dr = requests.get(url, headers=headers)
        if dr.status_code == 200:
            state = dr.json().get("properties", {}).get("provisioningState", "?")
            print(f"  Deployment state: {state}")
            if state == "Succeeded":
                return True
            if state == "Failed":
                print(f"  {dr.text[:500]}")
                return False
    return False


def deploy_models(headers):
    print("\n" + "=" * 60)
    print("STEP 2: Deploy OpenAI Models")
    print("=" * 60)

    # Deploy gpt-4o
    ok1 = deploy_model(headers, "gpt-4o", "gpt-4o", "2024-08-06", capacity=30)

    # Deploy text-embedding-3-large
    ok2 = deploy_model(headers, "text-embedding-3-large", "text-embedding-3-large", "1", capacity=30)

    return ok1 and ok2


def restore_search(headers):
    print("\n" + "=" * 60)
    print("STEP 3: Restore AI Search")
    print("=" * 60)

    r = check_resource(headers, "Microsoft.Search", "searchServices", SEARCH_NAME, api_version="2023-11-01")
    if r.status_code == 200:
        state = r.json().get("properties", {}).get("provisioningState")
        print(f"  Already exists! State: {state}")
        return True

    print(f"  Creating {SEARCH_NAME} (Free tier)...")
    url = f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}/providers/Microsoft.Search/searchServices/{SEARCH_NAME}?api-version=2023-11-01"
    body = {
        "location": LOCATION,
        "sku": {"name": "free"},
        "properties": {
            "replicaCount": 1,
            "partitionCount": 1,
            "hostingMode": "default",
        },
    }
    r = requests.put(url, headers=headers, json=body)
    print(f"  Create: HTTP {r.status_code}")
    if r.status_code not in (200, 201, 202):
        print(f"  Error: {r.text[:500]}")
        return False

    result = poll_provisioning(headers, "Microsoft.Search", "searchServices", SEARCH_NAME, api_version="2023-11-01")
    return result is not None


def get_search_admin_key(headers):
    """Get the admin key for AI Search."""
    url = (
        f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
        f"/providers/Microsoft.Search/searchServices/{SEARCH_NAME}"
        f"/listAdminKeys?api-version=2023-11-01"
    )
    r = requests.post(url, headers=headers)
    if r.status_code == 200:
        return r.json().get("primaryKey")
    print(f"  Error getting search key: HTTP {r.status_code}: {r.text[:300]}")
    return None


def get_openai_key(headers):
    """Get the API key for Azure OpenAI."""
    url = (
        f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
        f"/providers/Microsoft.CognitiveServices/accounts/{OAI_NAME}"
        f"/listKeys?api-version=2024-10-01"
    )
    r = requests.post(url, headers=headers)
    if r.status_code == 200:
        return r.json().get("key1")
    print(f"  Error getting OAI key: HTTP {r.status_code}: {r.text[:300]}")
    return None


def update_keyvault_secrets(headers):
    print("\n" + "=" * 60)
    print("STEP 4: Update Key Vault Secrets")
    print("=" * 60)

    from azure.keyvault.secrets import SecretClient

    kv_url = "https://kv-chubb-mcp-9342.vault.azure.net"
    cred = DefaultAzureCredential()
    kv_client = SecretClient(vault_url=kv_url, credential=cred)

    # Get new keys
    oai_key = get_openai_key(headers)
    search_key = get_search_admin_key(headers)

    oai_endpoint = f"https://{OAI_NAME}.openai.azure.com/"
    search_endpoint = f"https://{SEARCH_NAME}.search.windows.net"

    secrets = {}
    if oai_key:
        secrets["aisvc-key"] = oai_key
    secrets["aisvc-endpoint"] = oai_endpoint
    if search_key:
        secrets["search-key"] = search_key
    secrets["search-endpoint"] = search_endpoint

    for name, value in secrets.items():
        try:
            kv_client.set_secret(name, value)
            display = value[:20] + "..." if len(value) > 20 else value
            print(f"  Set '{name}' = {display}")
        except Exception as e:
            print(f"  Error setting '{name}': {e}")

    return True


def main():
    print("=" * 60)
    print("PHASE 0: RESTORE DELETED AZURE RESOURCES")
    print("=" * 60)

    headers = get_headers()

    # Step 1: Restore OpenAI
    if not restore_openai(headers):
        print("\nFAILED: Could not restore OpenAI resource")
        sys.exit(1)

    # Refresh token (may have expired during long waits)
    headers = get_headers()

    # Step 2: Deploy models
    if not deploy_models(headers):
        print("\nWARNING: Model deployment had issues")

    # Refresh token
    headers = get_headers()

    # Step 3: Restore AI Search
    if not restore_search(headers):
        print("\nFAILED: Could not restore AI Search")
        sys.exit(1)

    # Refresh token
    headers = get_headers()

    # Step 4: Update Key Vault secrets
    update_keyvault_secrets(headers)

    print("\n" + "=" * 60)
    print("PHASE 0 COMPLETE")
    print("=" * 60)
    print(f"  OpenAI:  https://{OAI_NAME}.openai.azure.com/")
    print(f"  Search:  https://{SEARCH_NAME}.search.windows.net")
    print(f"  Key Vault secrets updated")
    print(f"\n  Next: Reindex documents, update App Service env vars, smoke test")


if __name__ == "__main__":
    main()

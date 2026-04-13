"""
Phase 1: Verify existing resources (Key Vault, Cosmos DB) and create Storage Account.
Phase 2: Create new Foundry Hub+Project with customer-managed backend storage.
"""
import json
import time
import uuid
import requests
from azure.identity import DefaultAzureCredential

SUB_ID = "a3223db3-76f2-4a7c-8684-57b835dc77e7"
RG = "rg-chubb-mcp-poc"
LOCATION = "eastus"
ARM = "https://management.azure.com"
API_ML = "2024-10-01"

# Existing resources
KV_NAME = "kv-chubb-mcp-9342"
COSMOS_NAME = "cosmos-chubb-mcp-poc"
OAI_NAME = "oai-chubb-mcp-9342"

# New resources
STORAGE_NAME = "stchubbmcppoc"
HUB_NAME = "hub-chubb-storage-val"
PROJECT_NAME = "proj-chubb-storage-val"


def get_headers():
    cred = DefaultAzureCredential()
    token = cred.get_token("https://management.azure.com/.default").token
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def poll(headers, url, label, max_wait=300):
    start = time.time()
    while time.time() - start < max_wait:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            state = r.json().get("properties", {}).get("provisioningState", "Unknown")
            print(f"  {label} state: {state}")
            if state in ("Succeeded", "succeeded"):
                return r.json()
            if state in ("Failed", "failed"):
                print(f"  FAILED: {r.text[:500]}")
                return None
        time.sleep(15)
    print(f"  TIMEOUT")
    return None


# ============================================================
# PHASE 1: Verify existing resources + create Storage Account
# ============================================================

def phase1(headers):
    print("=" * 60)
    print("PHASE 1: Verify Resources + Create Storage Account")
    print("=" * 60)

    # 1a. Key Vault
    print("\n[1a] Checking Key Vault...")
    url = f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}/providers/Microsoft.KeyVault/vaults/{KV_NAME}?api-version=2023-07-01"
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        kv_id = r.json()["id"]
        print(f"  OK: {KV_NAME}")
        print(f"  Resource ID: {kv_id}")
    else:
        print(f"  ERROR: HTTP {r.status_code}")
        return None, None, None

    # 1b. Cosmos DB
    print("\n[1b] Checking Cosmos DB...")
    url = f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}/providers/Microsoft.DocumentDB/databaseAccounts/{COSMOS_NAME}?api-version=2024-05-15"
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        cosmos_id = r.json()["id"]
        cosmos_endpoint = r.json()["properties"]["documentEndpoint"]
        print(f"  OK: {COSMOS_NAME}")
        print(f"  Resource ID: {cosmos_id}")
        print(f"  Endpoint: {cosmos_endpoint}")
    else:
        print(f"  ERROR: HTTP {r.status_code}")
        return None, None, None

    # List existing Cosmos DB databases
    print("\n  Listing Cosmos DB databases (before Foundry)...")
    db_url = f"{ARM}{cosmos_id}/sqlDatabases?api-version=2024-05-15"
    r = requests.get(db_url, headers=headers)
    if r.status_code == 200:
        dbs = r.json().get("value", [])
        for db in dbs:
            db_name = db["name"]
            print(f"    Database: {db_name}")
            # List containers
            cont_url = f"{ARM}{db['id']}/containers?api-version=2024-05-15"
            cr = requests.get(cont_url, headers=headers)
            if cr.status_code == 200:
                for c in cr.json().get("value", []):
                    print(f"      Container: {c['name']}")

    # 1c. Create Storage Account
    print(f"\n[1c] Creating Storage Account: {STORAGE_NAME}...")
    st_url = f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}/providers/Microsoft.Storage/storageAccounts/{STORAGE_NAME}?api-version=2023-05-01"
    r = requests.get(st_url, headers=headers)
    if r.status_code == 200:
        storage_id = r.json()["id"]
        print(f"  Already exists! ID: {storage_id}")
    else:
        body = {
            "location": LOCATION,
            "kind": "StorageV2",
            "sku": {"name": "Standard_LRS"},
            "properties": {
                "supportsHttpsTrafficOnly": True,
                "minimumTlsVersion": "TLS1_2",
                "allowBlobPublicAccess": False,
            },
        }
        r = requests.put(st_url, headers=headers, json=body)
        print(f"  Create: HTTP {r.status_code}")
        if r.status_code not in (200, 201, 202):
            print(f"  Error: {r.text[:500]}")
            return None, None, None
        result = poll(headers, st_url, "Storage")
        if not result:
            return None, None, None
        storage_id = result["id"]
        print(f"  Created! ID: {storage_id}")

    return kv_id, cosmos_id, storage_id


# ============================================================
# PHASE 2: Create Foundry Hub + Project with customer storage
# ============================================================

def phase2(headers, kv_id, cosmos_id, storage_id):
    print("\n" + "=" * 60)
    print("PHASE 2: Create Foundry Hub + Project with Customer Storage")
    print("=" * 60)

    # 2a. Create Hub with customer-managed Key Vault + Storage
    print(f"\n[2a] Creating Hub: {HUB_NAME}...")
    hub_url = (
        f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
        f"/providers/Microsoft.MachineLearningServices/workspaces/{HUB_NAME}"
        f"?api-version={API_ML}"
    )

    r = requests.get(hub_url, headers=headers)
    if r.status_code == 200:
        print(f"  Hub already exists! State: {r.json()['properties']['provisioningState']}")
    else:
        body = {
            "location": LOCATION,
            "kind": "Hub",
            "identity": {"type": "SystemAssigned"},
            "properties": {
                "friendlyName": "Chubb Storage Validation Hub",
                "description": "Hub with customer-managed Key Vault, Storage, and Cosmos DB",
                "keyVault": kv_id,
                "storageAccount": storage_id,
            },
            "sku": {"name": "Basic", "tier": "Basic"},
        }
        r = requests.put(hub_url, headers=headers, json=body)
        print(f"  Create: HTTP {r.status_code}")
        if r.status_code not in (200, 201, 202):
            print(f"  Error: {r.text[:500]}")
            return False
        result = poll(headers, hub_url, "Hub")
        if not result:
            return False

    # 2b. Add OpenAI connection to Hub
    print(f"\n[2b] Adding OpenAI connection...")
    conn_url = (
        f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
        f"/providers/Microsoft.MachineLearningServices/workspaces/{HUB_NAME}"
        f"/connections/oai-storage-val-conn?api-version={API_ML}"
    )
    r = requests.get(conn_url, headers=headers)
    if r.status_code == 200:
        print("  Connection already exists")
    else:
        oai_id = f"/subscriptions/{SUB_ID}/resourceGroups/{RG}/providers/Microsoft.CognitiveServices/accounts/{OAI_NAME}"
        body = {
            "properties": {
                "category": "AzureOpenAI",
                "target": f"https://{OAI_NAME}.openai.azure.com/",
                "authType": "AAD",
                "metadata": {"ApiType": "Azure", "ResourceId": oai_id},
            }
        }
        r = requests.put(conn_url, headers=headers, json=body)
        print(f"  Connection: HTTP {r.status_code}")
        if r.status_code not in (200, 201):
            print(f"  Warning: {r.text[:300]}")

    # 2c. Add Cosmos DB connection to Hub (for agent thread storage)
    print(f"\n[2c] Adding Cosmos DB connection...")
    cosmos_conn_url = (
        f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
        f"/providers/Microsoft.MachineLearningServices/workspaces/{HUB_NAME}"
        f"/connections/cosmos-storage-val-conn?api-version={API_ML}"
    )
    r = requests.get(cosmos_conn_url, headers=headers)
    if r.status_code == 200:
        print("  Cosmos connection already exists")
    else:
        cosmos_endpoint = f"https://{COSMOS_NAME}.documents.azure.com:443/"
        body = {
            "properties": {
                "category": "CosmosDB",
                "target": cosmos_endpoint,
                "authType": "AAD",
                "metadata": {
                    "ResourceId": cosmos_id,
                },
            }
        }
        r = requests.put(cosmos_conn_url, headers=headers, json=body)
        print(f"  Cosmos connection: HTTP {r.status_code}")
        if r.status_code not in (200, 201):
            print(f"  Response: {r.text[:500]}")

    # 2d. Create Project under Hub
    print(f"\n[2d] Creating Project: {PROJECT_NAME}...")
    proj_url = (
        f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
        f"/providers/Microsoft.MachineLearningServices/workspaces/{PROJECT_NAME}"
        f"?api-version={API_ML}"
    )
    r = requests.get(proj_url, headers=headers)
    if r.status_code == 200:
        print(f"  Project already exists! State: {r.json()['properties']['provisioningState']}")
    else:
        hub_resource_id = f"/subscriptions/{SUB_ID}/resourceGroups/{RG}/providers/Microsoft.MachineLearningServices/workspaces/{HUB_NAME}"
        body = {
            "location": LOCATION,
            "kind": "Project",
            "identity": {"type": "SystemAssigned"},
            "properties": {
                "friendlyName": "Chubb Storage Validation Project",
                "description": "Project for validating Foundry backend storage",
                "hubResourceId": hub_resource_id,
            },
            "sku": {"name": "Basic", "tier": "Basic"},
        }
        r = requests.put(proj_url, headers=headers, json=body)
        print(f"  Create: HTTP {r.status_code}")
        if r.status_code not in (200, 201, 202):
            print(f"  Error: {r.text[:500]}")
            return False
        result = poll(headers, proj_url, "Project")
        if not result:
            return False

    # 2e. Assign RBAC to project managed identity
    print(f"\n[2e] Assigning RBAC permissions...")
    # Get project identity
    headers = get_headers()  # refresh token
    r = requests.get(proj_url, headers=headers)
    if r.status_code != 200:
        print(f"  Error getting project: HTTP {r.status_code}")
        return False
    proj_data = r.json()
    principal_id = proj_data.get("identity", {}).get("principalId")
    print(f"  Project principal ID: {principal_id}")

    if principal_id:
        oai_scope = f"/subscriptions/{SUB_ID}/resourceGroups/{RG}/providers/Microsoft.CognitiveServices/accounts/{OAI_NAME}"
        roles = [
            ("5e0bd9bd-7b93-4f28-af87-19fc36ad61bd", "Cognitive Services OpenAI Contributor"),
            ("a97b65f3-24c7-4388-baec-2e87135dc908", "Cognitive Services User"),
        ]
        for role_id, role_name in roles:
            assign_url = f"{ARM}{oai_scope}/providers/Microsoft.Authorization/roleAssignments/{uuid.uuid4()}?api-version=2022-04-01"
            body = {
                "properties": {
                    "roleDefinitionId": f"{oai_scope}/providers/Microsoft.Authorization/roleDefinitions/{role_id}",
                    "principalId": principal_id,
                    "principalType": "ServicePrincipal",
                }
            }
            r = requests.put(assign_url, headers=headers, json=body)
            status = "OK" if r.status_code in (200, 201) else f"HTTP {r.status_code}"
            if r.status_code == 409:
                status = "Already assigned"
            print(f"  {role_name}: {status}")

    # Print summary
    print(f"\n{'='*60}")
    print("PHASE 1+2 COMPLETE")
    print(f"{'='*60}")
    print(f"  Hub:     {HUB_NAME}")
    print(f"  Project: {PROJECT_NAME}")
    print(f"  Key Vault:  {KV_NAME} (customer-managed)")
    print(f"  Storage:    {STORAGE_NAME} (customer-managed)")
    print(f"  Cosmos DB:  {COSMOS_NAME} (connected)")
    print(f"  OpenAI:     {OAI_NAME} (connected)")

    # Get agents endpoint
    agents_uri = proj_data.get("properties", {}).get("agentsEndpointUri", "N/A")
    print(f"  Agents Endpoint: {agents_uri}")

    return True


def main():
    headers = get_headers()
    kv_id, cosmos_id, storage_id = phase1(headers)
    if not kv_id:
        print("Phase 1 failed!")
        return

    headers = get_headers()  # refresh
    if not phase2(headers, kv_id, cosmos_id, storage_id):
        print("Phase 2 failed!")
        return

    print("\nReady for Phase 3 (Agent creation)!")


if __name__ == "__main__":
    main()

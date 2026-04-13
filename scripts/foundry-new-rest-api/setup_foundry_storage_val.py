"""
Phase 1-2: Create Foundry Hub with customer-managed backend resources.

This script:
1. Creates a Storage Account (new)
2. Verifies Key Vault and Cosmos DB exist
3. Creates a new Foundry Hub linked to: Key Vault, Storage Account
4. Adds Cosmos DB connection for Agent service thread storage
5. Adds OpenAI connection
6. Creates a Project under the Hub
7. Assigns RBAC roles
"""
import json
import time
import uuid
import requests
from azure.identity import DefaultAzureCredential

# Configuration
SUB_ID = "a3223db3-76f2-4a7c-8684-57b835dc77e7"
RG = "rg-chubb-mcp-poc"
LOCATION = "eastus"
ARM = "https://management.azure.com"
API_ML = "2024-10-01"

# Existing resources to link
KV_NAME = "kv-chubb-mcp-9342"
COSMOS_NAME = "cosmos-chubb-mcp-poc"
OAI_NAME = "oai-chubb-mcp-9342"

# New resources
STORAGE_NAME = "stchubbmcppoc"  # lowercase, no hyphens (Storage naming rules)
HUB_NAME = "hub-chubb-storage-val"
PROJECT_NAME = "proj-chubb-storage-val"


def get_headers():
    cred = DefaultAzureCredential()
    token = cred.get_token("https://management.azure.com/.default").token
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def resource_id(provider, rtype, name):
    return f"/subscriptions/{SUB_ID}/resourceGroups/{RG}/providers/{provider}/{rtype}/{name}"


def check_exists(headers, rid, api_version):
    r = requests.get(f"{ARM}{rid}?api-version={api_version}", headers=headers)
    return r.status_code == 200, r


def poll_until(headers, rid, api_version, max_wait=600):
    start = time.time()
    while time.time() - start < max_wait:
        r = requests.get(f"{ARM}{rid}?api-version={api_version}", headers=headers)
        if r.status_code == 200:
            state = r.json().get("properties", {}).get("provisioningState", "Unknown")
            print(f"  State: {state}")
            if state in ("Succeeded", "succeeded"):
                return r.json()
            if state in ("Failed", "failed"):
                print(f"  FAILED: {r.text[:500]}")
                return None
        time.sleep(15)
    print("  TIMEOUT")
    return None


# ============================================================
# STEP 1: Create Storage Account
# ============================================================
def create_storage_account(headers):
    print("\n" + "=" * 60)
    print("STEP 1: Create Storage Account")
    print("=" * 60)

    rid = resource_id("Microsoft.Storage", "storageAccounts", STORAGE_NAME)
    exists, r = check_exists(headers, rid, "2023-05-01")
    if exists:
        print(f"  Already exists: {STORAGE_NAME}")
        return rid

    print(f"  Creating {STORAGE_NAME}...")
    body = {
        "location": LOCATION,
        "kind": "StorageV2",
        "sku": {"name": "Standard_LRS"},
        "properties": {
            "supportsHttpsTrafficOnly": True,
            "allowBlobPublicAccess": False,
            "minimumTlsVersion": "TLS1_2",
        },
    }
    r = requests.put(f"{ARM}{rid}?api-version=2023-05-01", headers=headers, json=body)
    print(f"  Create: HTTP {r.status_code}")
    if r.status_code not in (200, 201, 202):
        print(f"  Error: {r.text[:500]}")
        return None

    result = poll_until(headers, rid, "2023-05-01")
    if result:
        print(f"  Storage Account created: {STORAGE_NAME}")
        return rid
    return None


# ============================================================
# STEP 2: Verify Key Vault and Cosmos DB
# ============================================================
def verify_existing_resources(headers):
    print("\n" + "=" * 60)
    print("STEP 2: Verify Key Vault and Cosmos DB")
    print("=" * 60)

    kv_rid = resource_id("Microsoft.KeyVault", "vaults", KV_NAME)
    exists, r = check_exists(headers, kv_rid, "2023-07-01")
    if exists:
        print(f"  Key Vault OK: {KV_NAME}")
    else:
        print(f"  ERROR: Key Vault {KV_NAME} not found!")
        return None, None

    cosmos_rid = resource_id("Microsoft.DocumentDB", "databaseAccounts", COSMOS_NAME)
    exists, r = check_exists(headers, cosmos_rid, "2024-05-15")
    if exists:
        print(f"  Cosmos DB OK: {COSMOS_NAME}")
    else:
        print(f"  ERROR: Cosmos DB {COSMOS_NAME} not found!")
        return kv_rid, None

    return kv_rid, cosmos_rid


# ============================================================
# STEP 3: Create Foundry Hub with linked resources
# ============================================================
def create_hub(headers, kv_rid, storage_rid):
    print("\n" + "=" * 60)
    print("STEP 3: Create Foundry Hub with customer-managed resources")
    print("=" * 60)

    hub_rid = resource_id("Microsoft.MachineLearningServices", "workspaces", HUB_NAME)
    exists, r = check_exists(headers, hub_rid, API_ML)
    if exists:
        state = r.json().get("properties", {}).get("provisioningState", "?")
        print(f"  Hub already exists! State: {state}")
        return hub_rid

    print(f"  Creating hub '{HUB_NAME}' linked to:")
    print(f"    Key Vault:       {kv_rid}")
    print(f"    Storage Account: {storage_rid}")

    body = {
        "location": LOCATION,
        "kind": "Hub",
        "identity": {"type": "SystemAssigned"},
        "properties": {
            "friendlyName": "Chubb Storage Validation Hub",
            "description": "AI Foundry Hub with customer-managed Key Vault, Storage, and Cosmos DB",
            "keyVault": kv_rid,
            "storageAccount": storage_rid,
        },
        "sku": {"name": "Basic", "tier": "Basic"},
    }

    r = requests.put(f"{ARM}{hub_rid}?api-version={API_ML}", headers=headers, json=body)
    print(f"  Create: HTTP {r.status_code}")
    if r.status_code not in (200, 201, 202):
        print(f"  Error: {r.text[:500]}")
        return None

    result = poll_until(headers, hub_rid, API_ML, max_wait=600)
    if result:
        print(f"  Hub created: {HUB_NAME}")
        props = result.get("properties", {})
        print(f"    keyVault: {props.get('keyVault', 'N/A')}")
        print(f"    storageAccount: {props.get('storageAccount', 'N/A')}")
        return hub_rid
    return None


# ============================================================
# STEP 4: Add Cosmos DB connection for Agent service
# ============================================================
def add_cosmos_connection(headers, cosmos_rid):
    print("\n" + "=" * 60)
    print("STEP 4: Add Cosmos DB connection to Hub (Agent service)")
    print("=" * 60)

    hub_rid = resource_id("Microsoft.MachineLearningServices", "workspaces", HUB_NAME)
    conn_name = "cosmos-agent-store"
    conn_url = f"{ARM}{hub_rid}/connections/{conn_name}?api-version={API_ML}"

    # Check if exists
    r = requests.get(conn_url, headers=headers)
    if r.status_code == 200:
        print(f"  Connection '{conn_name}' already exists")
        return True

    # Get Cosmos endpoint and key
    cosmos_url = f"{ARM}{cosmos_rid}?api-version=2024-05-15"
    cr = requests.get(cosmos_url, headers=headers)
    cosmos_endpoint = cr.json().get("properties", {}).get("documentEndpoint", "")

    keys_url = f"{ARM}{cosmos_rid}/listKeys?api-version=2024-05-15"
    kr = requests.post(keys_url, headers=headers)
    cosmos_key = kr.json().get("primaryMasterKey", "") if kr.status_code == 200 else ""

    print(f"  Cosmos endpoint: {cosmos_endpoint}")
    print(f"  Adding connection '{conn_name}'...")

    body = {
        "properties": {
            "category": "CosmosDB",
            "target": cosmos_endpoint,
            "authType": "CustomKeys",
            "credentials": {
                "keys": {
                    "key": cosmos_key,
                }
            },
            "metadata": {
                "ResourceId": cosmos_rid,
            },
        }
    }

    r = requests.put(conn_url, headers=headers, json=body)
    print(f"  Create: HTTP {r.status_code}")
    if r.status_code in (200, 201):
        print(f"  Cosmos DB connection added")
        return True
    else:
        print(f"  Response: {r.text[:500]}")
        # Try alternative: ApiKey auth
        print("  Trying ApiKey auth type...")
        body["properties"]["authType"] = "ApiKey"
        body["properties"]["credentials"] = {"key": cosmos_key}
        r2 = requests.put(conn_url, headers=headers, json=body)
        print(f"  Retry: HTTP {r2.status_code}")
        if r2.status_code in (200, 201):
            print(f"  Cosmos DB connection added (ApiKey)")
            return True
        print(f"  Retry response: {r2.text[:500]}")
        return False


# ============================================================
# STEP 5: Add OpenAI connection
# ============================================================
def add_openai_connection(headers):
    print("\n" + "=" * 60)
    print("STEP 5: Add OpenAI connection to Hub")
    print("=" * 60)

    hub_rid = resource_id("Microsoft.MachineLearningServices", "workspaces", HUB_NAME)
    oai_rid = resource_id("Microsoft.CognitiveServices", "accounts", OAI_NAME)
    conn_name = "oai-chubb-connection"
    conn_url = f"{ARM}{hub_rid}/connections/{conn_name}?api-version={API_ML}"

    r = requests.get(conn_url, headers=headers)
    if r.status_code == 200:
        print(f"  Connection '{conn_name}' already exists")
        return True

    body = {
        "properties": {
            "category": "AzureOpenAI",
            "target": f"https://{OAI_NAME}.openai.azure.com/",
            "authType": "AAD",
            "metadata": {
                "ApiType": "Azure",
                "ResourceId": oai_rid,
            },
        }
    }

    print(f"  Adding OpenAI connection...")
    r = requests.put(conn_url, headers=headers, json=body)
    print(f"  Create: HTTP {r.status_code}")
    if r.status_code in (200, 201):
        print(f"  OpenAI connection added")
        return True
    print(f"  Error: {r.text[:300]}")
    return False


# ============================================================
# STEP 6: Create Project under Hub
# ============================================================
def create_project(headers):
    print("\n" + "=" * 60)
    print("STEP 6: Create Project under Hub")
    print("=" * 60)

    proj_rid = resource_id("Microsoft.MachineLearningServices", "workspaces", PROJECT_NAME)
    exists, r = check_exists(headers, proj_rid, API_ML)
    if exists:
        state = r.json().get("properties", {}).get("provisioningState", "?")
        print(f"  Project already exists! State: {state}")
        return proj_rid

    hub_rid = resource_id("Microsoft.MachineLearningServices", "workspaces", HUB_NAME)

    body = {
        "location": LOCATION,
        "kind": "Project",
        "identity": {"type": "SystemAssigned"},
        "properties": {
            "friendlyName": "Chubb Storage Validation Project",
            "description": "Project for validating Foundry backend storage integration",
            "hubResourceId": hub_rid,
        },
        "sku": {"name": "Basic", "tier": "Basic"},
    }

    print(f"  Creating project '{PROJECT_NAME}'...")
    r = requests.put(f"{ARM}{proj_rid}?api-version={API_ML}", headers=headers, json=body)
    print(f"  Create: HTTP {r.status_code}")
    if r.status_code not in (200, 201, 202):
        print(f"  Error: {r.text[:500]}")
        return None

    result = poll_until(headers, proj_rid, API_ML)
    if result:
        print(f"  Project created: {PROJECT_NAME}")
        props = result.get("properties", {})
        print(f"    agentsEndpointUri: {props.get('agentsEndpointUri', 'N/A')}")
        return proj_rid
    return None


# ============================================================
# STEP 7: Assign RBAC roles
# ============================================================
def assign_rbac(headers):
    print("\n" + "=" * 60)
    print("STEP 7: Assign RBAC roles")
    print("=" * 60)

    # Get the project's managed identity principal ID
    proj_rid = resource_id("Microsoft.MachineLearningServices", "workspaces", PROJECT_NAME)
    r = requests.get(f"{ARM}{proj_rid}?api-version={API_ML}", headers=headers)
    if r.status_code != 200:
        print(f"  ERROR: Cannot get project: HTTP {r.status_code}")
        return False

    principal_id = r.json().get("identity", {}).get("principalId", "")
    print(f"  Project principal ID: {principal_id}")

    if not principal_id:
        print("  ERROR: No principal ID found")
        return False

    oai_rid = resource_id("Microsoft.CognitiveServices", "accounts", OAI_NAME)

    roles = [
        ("Cognitive Services OpenAI Contributor", "5e0bd9bd-7b93-4f28-af87-19fc36ad61bd"),
        ("Cognitive Services User", "a97b65f3-24c7-4388-baec-2e87135dc908"),
    ]

    for role_name, role_id in roles:
        assign_id = str(uuid.uuid4())
        url = f"{ARM}{oai_rid}/providers/Microsoft.Authorization/roleAssignments/{assign_id}?api-version=2022-04-01"
        body = {
            "properties": {
                "roleDefinitionId": f"{oai_rid}/providers/Microsoft.Authorization/roleDefinitions/{role_id}",
                "principalId": principal_id,
                "principalType": "ServicePrincipal",
            }
        }
        r = requests.put(url, headers=headers, json=body)
        if r.status_code in (200, 201):
            print(f"  Assigned: {role_name}")
        elif r.status_code == 409:
            print(f"  Already assigned: {role_name}")
        else:
            print(f"  {role_name}: HTTP {r.status_code}: {r.text[:200]}")

    # Also get current user and assign
    print("  Getting current user...")
    cred = DefaultAzureCredential()
    graph_token = cred.get_token("https://graph.microsoft.com/.default").token
    gr = requests.get("https://graph.microsoft.com/v1.0/me", headers={"Authorization": f"Bearer {graph_token}"})
    if gr.status_code == 200:
        user_id = gr.json().get("id", "")
        print(f"  User ID: {user_id}")
        assign_id = str(uuid.uuid4())
        url = f"{ARM}{oai_rid}/providers/Microsoft.Authorization/roleAssignments/{assign_id}?api-version=2022-04-01"
        body = {
            "properties": {
                "roleDefinitionId": f"{oai_rid}/providers/Microsoft.Authorization/roleDefinitions/5e0bd9bd-7b93-4f28-af87-19fc36ad61bd",
                "principalId": user_id,
                "principalType": "User",
            }
        }
        r = requests.put(url, headers=headers, json=body)
        if r.status_code in (200, 201):
            print(f"  Assigned OpenAI Contributor to current user")
        elif r.status_code == 409:
            print(f"  Already assigned to current user")
        else:
            print(f"  User role: HTTP {r.status_code}: {r.text[:200]}")

    print("  Waiting 15s for RBAC propagation...")
    time.sleep(15)
    return True


def main():
    print("=" * 60)
    print("FOUNDRY STORAGE VALIDATION - SETUP")
    print("=" * 60)

    headers = get_headers()

    # Step 1: Create Storage Account
    storage_rid = create_storage_account(headers)
    if not storage_rid:
        print("FAILED: Storage Account")
        return

    headers = get_headers()

    # Step 2: Verify KV + Cosmos
    kv_rid, cosmos_rid = verify_existing_resources(headers)
    if not kv_rid or not cosmos_rid:
        print("FAILED: Missing resources")
        return

    headers = get_headers()

    # Step 3: Create Hub with KV + Storage
    hub_rid = create_hub(headers, kv_rid, storage_rid)
    if not hub_rid:
        print("FAILED: Hub creation")
        return

    headers = get_headers()

    # Step 4: Add Cosmos connection
    add_cosmos_connection(headers, cosmos_rid)

    headers = get_headers()

    # Step 5: Add OpenAI connection
    add_openai_connection(headers)

    headers = get_headers()

    # Step 6: Create Project
    proj_rid = create_project(headers)
    if not proj_rid:
        print("FAILED: Project creation")
        return

    headers = get_headers()

    # Step 7: RBAC
    assign_rbac(headers)

    print("\n" + "=" * 60)
    print("SETUP COMPLETE")
    print("=" * 60)
    print(f"  Hub:     {HUB_NAME}")
    print(f"  Project: {PROJECT_NAME}")
    print(f"  Key Vault: {KV_NAME} (linked)")
    print(f"  Storage:   {STORAGE_NAME} (linked)")
    print(f"  Cosmos DB: {COSMOS_NAME} (connected)")
    print(f"  OpenAI:    {OAI_NAME} (connected)")
    print(f"\nReady for Phase 3: Agent creation")


if __name__ == "__main__":
    main()

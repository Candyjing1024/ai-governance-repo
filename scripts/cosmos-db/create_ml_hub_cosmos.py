"""
Create ML workspace Hub+Project (old architecture) with Cosmos DB thread storage.
This uses Microsoft.MachineLearningServices/workspaces which supports agentStoreSettings.
Won't show in new Foundry portal, but threads WILL go to Cosmos DB.
"""
import json
import time
import uuid
import requests
from azure.identity import DefaultAzureCredential

SUB_ID = "a3223db3-76f2-4a7c-8684-57b835dc77e7"
RG = "rg-chubb-mcp-poc"
ARM = "https://management.azure.com"
API_ML = "2025-01-01-preview"
LOCATION = "eastus"

# Names
HUB_NAME = "hub-chubb-cosmos-val"
PROJECT_NAME = "proj-chubb-cosmos-val"

# Existing resources
COSMOS_NAME = "cosmos-chubb-mcp-poc"
OAI_NAME = "oai-chubb-mcp-9342"
KV_NAME = "kv-chubb-mcp-9342"
STORAGE_NAME = "stchubbmcppoc"

cred = DefaultAzureCredential()


def get_headers():
    token = cred.get_token("https://management.azure.com/.default").token
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def rid(provider, rtype, name):
    return f"/subscriptions/{SUB_ID}/resourceGroups/{RG}/providers/{provider}/{rtype}/{name}"


def wait_for_provisioning(url, headers, timeout=300):
    """Poll until provisioningState is terminal."""
    for i in range(timeout // 10):
        time.sleep(10)
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            state = r.json().get("properties", {}).get("provisioningState", "")
            print(f"    {i*10}s: {state}")
            if state in ("Succeeded", "Failed", "Canceled"):
                return state
    return "Timeout"


# ============================================================
# STEP 1: Create Hub with linked resources + agentStoreSettings
# ============================================================
def create_hub():
    print("=" * 60)
    print(f"STEP 1: Create Hub '{HUB_NAME}'")
    print("=" * 60)

    headers = get_headers()
    url = (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
           f"/providers/Microsoft.MachineLearningServices/workspaces/{HUB_NAME}"
           f"?api-version={API_ML}")

    # Check if exists
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        state = r.json().get("properties", {}).get("provisioningState", "")
        print(f"  Hub already exists (state={state})")
        if state == "Succeeded":
            return True
        # Wait if in progress
        if state in ("Creating", "Updating", "Accepted"):
            state = wait_for_provisioning(url, headers)
            return state == "Succeeded"

    kv_rid = rid("Microsoft.KeyVault", "vaults", KV_NAME)
    sa_rid = rid("Microsoft.Storage", "storageAccounts", STORAGE_NAME)
    cosmos_rid = rid("Microsoft.DocumentDB", "databaseAccounts", COSMOS_NAME)

    body = {
        "location": LOCATION,
        "kind": "Hub",
        "identity": {"type": "SystemAssigned"},
        "sku": {"name": "Basic", "tier": "Basic"},
        "properties": {
            "friendlyName": "Chubb Cosmos Validation Hub",
            "description": "Hub with Cosmos DB agent thread storage",
            "keyVault": kv_rid,
            "storageAccount": sa_rid,
            "hbiWorkspace": False,
            "v1LegacyMode": False,
            "publicNetworkAccess": "Enabled",
        }
    }

    print(f"  Creating hub...")
    print(f"    KeyVault: {KV_NAME}")
    print(f"    Storage: {STORAGE_NAME}")
    r = requests.put(url, headers=headers, json=body)
    print(f"  HTTP {r.status_code}")

    if r.status_code not in (200, 201, 202):
        print(f"  Error: {r.text[:500]}")
        return False

    state = r.json().get("properties", {}).get("provisioningState", "?")
    print(f"  Initial state: {state}")

    if state not in ("Succeeded",):
        print("  Waiting for provisioning...")
        state = wait_for_provisioning(url, headers, timeout=600)

    print(f"  Final state: {state}")
    return state == "Succeeded"


# ============================================================
# STEP 2: Configure agentStoreSettings on the Hub
# ============================================================
def configure_agent_store():
    print("\n" + "=" * 60)
    print("STEP 2: Configure agentStoreSettings with Cosmos DB")
    print("=" * 60)

    headers = get_headers()
    hub_url = (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
               f"/providers/Microsoft.MachineLearningServices/workspaces/{HUB_NAME}"
               f"?api-version={API_ML}")

    # First add Cosmos connection to Hub
    print("  Adding Cosmos DB connection to hub...")
    cosmos_rid = rid("Microsoft.DocumentDB", "databaseAccounts", COSMOS_NAME)
    cosmos_endpoint = f"https://{COSMOS_NAME}.documents.azure.com:443/"

    # Get Cosmos key
    keys_url = f"{ARM}{cosmos_rid}/listKeys?api-version=2024-05-15"
    kr = requests.post(keys_url, headers=headers)
    cosmos_key = kr.json().get("primaryMasterKey", "") if kr.status_code == 200 else ""

    hub_base = (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
                f"/providers/Microsoft.MachineLearningServices/workspaces/{HUB_NAME}")

    # Add Cosmos connection
    conn_body = {
        "properties": {
            "category": "CosmosDB",
            "target": cosmos_endpoint,
            "authType": "ApiKey",
            "credentials": {"key": cosmos_key},
            "metadata": {"ResourceId": cosmos_rid},
        }
    }
    r = requests.put(f"{hub_base}/connections/cosmos-agent-store?api-version={API_ML}",
                     headers=headers, json=conn_body)
    print(f"    Cosmos connection: HTTP {r.status_code}")
    if r.status_code not in (200, 201):
        # Try CustomKeys
        conn_body["properties"]["authType"] = "CustomKeys"
        conn_body["properties"]["credentials"] = {"keys": {"key": cosmos_key}}
        r = requests.put(f"{hub_base}/connections/cosmos-agent-store?api-version={API_ML}",
                         headers=headers, json=conn_body)
        print(f"    Cosmos (CustomKeys): HTTP {r.status_code}")

    # Add OpenAI connection
    print("  Adding OpenAI connection to hub...")
    oai_rid = rid("Microsoft.CognitiveServices", "accounts", OAI_NAME)
    oai_body = {
        "properties": {
            "category": "AzureOpenAI",
            "target": f"https://{OAI_NAME}.openai.azure.com/",
            "authType": "AAD",
            "metadata": {"ApiType": "Azure", "ResourceId": oai_rid},
        }
    }
    r = requests.put(f"{hub_base}/connections/oai-connection?api-version={API_ML}",
                     headers=headers, json=oai_body)
    print(f"    OpenAI connection: HTTP {r.status_code}")

    # Now PATCH hub with agentStoreSettings
    print("\n  Setting agentStoreSettings...")
    patch_body = {
        "properties": {
            "agentStoreSettings": {
                "storeType": "CosmosDB",
                "connectionName": "cosmos-agent-store"
            }
        }
    }
    r = requests.patch(hub_url, headers=headers, json=patch_body)
    print(f"    PATCH: HTTP {r.status_code}")

    if r.status_code in (200, 201, 202):
        props = r.json().get("properties", {})
        agent_store = props.get("agentStoreSettings", "NOT FOUND")
        state = props.get("provisioningState", "?")
        print(f"    agentStoreSettings: {agent_store}")
        print(f"    Provisioning state: {state}")

        if state not in ("Succeeded",):
            print("    Waiting for provisioning...")
            state = wait_for_provisioning(hub_url, headers)
            print(f"    Final state: {state}")
    else:
        print(f"    Error: {r.text[:500]}")

    # Verify
    r = requests.get(hub_url, headers=headers)
    if r.status_code == 200:
        props = r.json().get("properties", {})
        print(f"\n  Verified agentStoreSettings: {props.get('agentStoreSettings', 'NOT FOUND')}")
        print(f"  Agents endpoint: {props.get('agentsEndpointUri', 'N/A')}")

    return True


# ============================================================
# STEP 3: Create Project under Hub
# ============================================================
def create_project():
    print("\n" + "=" * 60)
    print(f"STEP 3: Create Project '{PROJECT_NAME}'")
    print("=" * 60)

    headers = get_headers()
    hub_rid = (f"/subscriptions/{SUB_ID}/resourceGroups/{RG}"
               f"/providers/Microsoft.MachineLearningServices/workspaces/{HUB_NAME}")
    url = (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
           f"/providers/Microsoft.MachineLearningServices/workspaces/{PROJECT_NAME}"
           f"?api-version={API_ML}")

    # Check if exists
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        state = r.json().get("properties", {}).get("provisioningState", "")
        print(f"  Project already exists (state={state})")
        if state == "Succeeded":
            return True

    body = {
        "location": LOCATION,
        "kind": "Project",
        "identity": {"type": "SystemAssigned"},
        "sku": {"name": "Basic", "tier": "Basic"},
        "properties": {
            "friendlyName": "Chubb Cosmos Validation Project",
            "description": "Project for validating Cosmos DB thread storage",
            "hubResourceId": hub_rid,
            "hbiWorkspace": False,
            "v1LegacyMode": False,
            "publicNetworkAccess": "Enabled",
        }
    }

    print(f"  Creating project (hub={HUB_NAME})...")
    r = requests.put(url, headers=headers, json=body)
    print(f"  HTTP {r.status_code}")

    if r.status_code not in (200, 201, 202):
        print(f"  Error: {r.text[:500]}")
        return False

    state = r.json().get("properties", {}).get("provisioningState", "?")
    print(f"  Initial state: {state}")

    if state not in ("Succeeded",):
        print("  Waiting for provisioning...")
        state = wait_for_provisioning(url, headers, timeout=600)

    # Get project details
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        props = r.json().get("properties", {})
        print(f"\n  Agents endpoint: {props.get('agentsEndpointUri', 'N/A')}")
        print(f"  Hub ref: {props.get('hubResourceId', 'N/A')}")

    return state == "Succeeded"


# ============================================================
# STEP 4: Assign RBAC
# ============================================================
def assign_rbac():
    print("\n" + "=" * 60)
    print("STEP 4: Assign RBAC roles")
    print("=" * 60)

    headers = get_headers()

    # Get project principal
    proj_url = (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
                f"/providers/Microsoft.MachineLearningServices/workspaces/{PROJECT_NAME}"
                f"?api-version={API_ML}")
    r = requests.get(proj_url, headers=headers)
    proj_principal = r.json().get("identity", {}).get("principalId", "")

    # Get hub principal
    hub_url = (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
               f"/providers/Microsoft.MachineLearningServices/workspaces/{HUB_NAME}"
               f"?api-version={API_ML}")
    r = requests.get(hub_url, headers=headers)
    hub_principal = r.json().get("identity", {}).get("principalId", "")

    # Get user
    graph_token = cred.get_token("https://graph.microsoft.com/.default").token
    gr = requests.get("https://graph.microsoft.com/v1.0/me",
                       headers={"Authorization": f"Bearer {graph_token}"})
    user_id = gr.json().get("id", "")

    print(f"  Hub principal: {hub_principal}")
    print(f"  Project principal: {proj_principal}")
    print(f"  User: {user_id}")

    oai_rid = rid("Microsoft.CognitiveServices", "accounts", OAI_NAME)

    assignments = []
    for pid, ptype in [(proj_principal, "ServicePrincipal"),
                       (hub_principal, "ServicePrincipal"),
                       (user_id, "User")]:
        if pid:
            # Cognitive Services OpenAI Contributor
            assignments.append((oai_rid, pid, ptype, "CogSvc OpenAI Contributor",
                                "a001fd3d-188f-4b5d-821b-7da978bf7442"))
            # Cognitive Services OpenAI User
            assignments.append((oai_rid, pid, ptype, "CogSvc OpenAI User",
                                "5e0bd9bd-7b93-4f28-af87-19fc36ad61bd"))

    for scope, pid, ptype, role_name, role_id in assignments:
        assign_id = str(uuid.uuid4())
        url = (f"{ARM}{scope}/providers/Microsoft.Authorization"
               f"/roleAssignments/{assign_id}?api-version=2022-04-01")
        body = {
            "properties": {
                "roleDefinitionId": f"{scope}/providers/Microsoft.Authorization/roleDefinitions/{role_id}",
                "principalId": pid,
                "principalType": ptype,
            }
        }
        r = requests.put(url, headers=headers, json=body)
        status = ("OK" if r.status_code in (200, 201) else
                  "Exists" if r.status_code == 409 else f"HTTP {r.status_code}")
        print(f"  {role_name} -> {ptype[:4]}..{pid[-4:]}: {status}")

    print("  Waiting 15s for RBAC propagation...")
    time.sleep(15)


# ============================================================
# STEP 5: Create agent and test
# ============================================================
def create_agent_and_test():
    print("\n" + "=" * 60)
    print("STEP 5: Create agent + test + check Cosmos DB")
    print("=" * 60)

    from azure.ai.agents import AgentsClient
    from azure.ai.agents.models import MessageRole
    from azure.cosmos import CosmosClient

    headers = get_headers()

    # Get project agents endpoint
    proj_url = (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
                f"/providers/Microsoft.MachineLearningServices/workspaces/{PROJECT_NAME}"
                f"?api-version={API_ML}")
    r = requests.get(proj_url, headers=headers)
    endpoint = r.json().get("properties", {}).get("agentsEndpointUri", "")
    print(f"  Agents endpoint: {endpoint}")

    if not endpoint:
        print("  ERROR: No agents endpoint")
        return

    client = AgentsClient(
        endpoint=endpoint,
        credential=cred,
    )

    # Create simple agent (no OpenAPI tool, just test thread storage)
    agent = client.create_agent(
        model="gpt-4o",
        name="cosmos-thread-test-agent",
        instructions="You are a helpful test agent. Answer questions briefly.",
    )
    print(f"  Agent: {agent.id} ({agent.name})")

    # Snapshot Cosmos BEFORE
    cosmos = CosmosClient(f"https://{COSMOS_NAME}.documents.azure.com:443/", credential=cred)
    dbs_before = sorted([d["id"] for d in cosmos.list_databases()])
    counts_before = {}
    for db in cosmos.list_databases():
        dbc = cosmos.get_database_client(db["id"])
        for cont in dbc.list_containers():
            key = f"{db['id']}/{cont['id']}"
            cnt = list(dbc.get_container_client(cont["id"]).query_items(
                "SELECT VALUE COUNT(1) FROM c", enable_cross_partition_query=True))[0]
            counts_before[key] = cnt
    print(f"\n  Cosmos BEFORE: DBs={dbs_before}")
    print(f"  Counts: {counts_before}")

    # Test conversation
    thread = client.threads.create()
    print(f"\n  Thread: {thread.id}")
    client.messages.create(thread_id=thread.id, role=MessageRole.USER,
                           content="Hello, what is 2+2?")
    start = time.time()
    run = client.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)
    elapsed = time.time() - start
    print(f"  Run: {run.id}  Status: {run.status}  Time: {elapsed:.1f}s")

    if hasattr(run, "last_error") and run.last_error:
        print(f"  Error: {run.last_error.code} - {run.last_error.message}")

    # Wait for data to land
    print("  Waiting 15s for Cosmos propagation...")
    time.sleep(15)

    # Snapshot Cosmos AFTER
    dbs_after = sorted([d["id"] for d in cosmos.list_databases()])
    counts_after = {}
    for db in cosmos.list_databases():
        dbc = cosmos.get_database_client(db["id"])
        for cont in dbc.list_containers():
            key = f"{db['id']}/{cont['id']}"
            cnt = list(dbc.get_container_client(cont["id"]).query_items(
                "SELECT VALUE COUNT(1) FROM c", enable_cross_partition_query=True))[0]
            counts_after[key] = cnt

    print(f"\n  Cosmos AFTER: DBs={dbs_after}")
    print(f"  Counts: {counts_after}")

    new_dbs = set(dbs_after) - set(dbs_before)
    if new_dbs:
        print(f"\n  ** NEW DATABASES: {new_dbs} **")
        for db_name in new_dbs:
            dbc = cosmos.get_database_client(db_name)
            containers = list(dbc.list_containers())
            print(f"    {db_name}: {[c['id'] for c in containers]}")
            for cont in containers:
                cc = dbc.get_container_client(cont["id"])
                items = list(cc.query_items(
                    "SELECT TOP 5 c.id, c._ts FROM c ORDER BY c._ts DESC",
                    enable_cross_partition_query=True))
                print(f"      {cont['id']}: {items}")

    changed = {k: (counts_before.get(k, 0), v)
               for k, v in counts_after.items()
               if v != counts_before.get(k, 0)}
    if changed:
        print(f"  Changed: {changed}")

    # Search for thread ID
    print(f"\n  Searching for thread '{thread.id}'...")
    for db in cosmos.list_databases():
        dbc = cosmos.get_database_client(db["id"])
        for cont in dbc.list_containers():
            cc = dbc.get_container_client(cont["id"])
            hits = list(cc.query_items(
                f"SELECT TOP 3 c.id FROM c WHERE CONTAINS(c.id, '{thread.id}')",
                enable_cross_partition_query=True))
            if hits:
                print(f"    FOUND in {db['id']}/{cont['id']}: {hits}")

    print(f"\n  Done. Thread storage in Cosmos: {'YES' if new_dbs or any('thread' in str(changed).lower() for _ in [1]) else 'CHECK ABOVE'}")


def main():
    if not create_hub():
        print("\nFAILED: Hub creation failed")
        return

    if not configure_agent_store():
        print("\nWARN: Agent store config may have failed, continuing...")

    if not create_project():
        print("\nFAILED: Project creation failed")
        return

    assign_rbac()
    create_agent_and_test()

    print("\n" + "=" * 60)
    print("COMPLETE")
    print("=" * 60)
    print(f"  Hub: {HUB_NAME}")
    print(f"  Project: {PROJECT_NAME}")
    print("  NOTE: These won't show in the new Foundry portal")
    print("  They use the old ML workspace architecture")


if __name__ == "__main__":
    main()

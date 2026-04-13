"""
Configure Cosmos DB as Agent Service thread storage via CognitiveServices API,
then test and verify.
"""
import json
import time
import requests
from azure.identity import DefaultAzureCredential

SUB_ID = "a3223db3-76f2-4a7c-8684-57b835dc77e7"
RG = "rg-chubb-mcp-poc"
ARM = "https://management.azure.com"
ACCOUNT_NAME = "proj-chubb-storage-val-resource"
PROJECT_NAME = "proj-chubb-storage-val"
COSMOS_NAME = "cosmos-chubb-mcp-poc"
AGENT_ID = "asst_jRfE1bi4RV39diHnbL5k0FdI"

cred = DefaultAzureCredential()


def get_headers():
    token = cred.get_token("https://management.azure.com/.default").token
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def account_base():
    return (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
            f"/providers/Microsoft.CognitiveServices/accounts/{ACCOUNT_NAME}")


# ============================================================
# STEP 1: Check current account properties for agent store settings
# ============================================================
def check_current_config():
    print("=" * 60)
    print("STEP 1: Check current account config for agent store settings")
    print("=" * 60)
    headers = get_headers()

    for api in ["2026-01-15-preview", "2025-06-01", "2025-04-01-preview"]:
        url = f"{account_base()}?api-version={api}"
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            props = r.json().get("properties", {})
            print(f"\n  API {api} - property keys: {list(props.keys())}")
            # Look for anything agent/store/cosmos related
            for k, v in props.items():
                kl = k.lower()
                if any(word in kl for word in ["agent", "store", "cosmos", "thread", "storage"]):
                    print(f"    {k}: {json.dumps(v, default=str)[:300]}")
            # Also check full properties dump for patterns
            full = json.dumps(props, default=str)
            for pattern in ["agentStore", "threadStore", "cosmosDb", "dataStore"]:
                if pattern.lower() in full.lower():
                    print(f"    Found '{pattern}' in properties!")
            break


# ============================================================
# STEP 2: Try to configure agent store via PATCH
# ============================================================
def configure_agent_store():
    print("\n" + "=" * 60)
    print("STEP 2: Configure Cosmos DB as agent thread store")
    print("=" * 60)
    headers = get_headers()

    cosmos_rid = (f"/subscriptions/{SUB_ID}/resourceGroups/{RG}"
                  f"/providers/Microsoft.DocumentDB/databaseAccounts/{COSMOS_NAME}")
    cosmos_endpoint = f"https://{COSMOS_NAME}.documents.azure.com:443/"

    # Get Cosmos key
    keys_url = f"{ARM}{cosmos_rid}/listKeys?api-version=2024-05-15"
    kr = requests.post(keys_url, headers=headers)
    cosmos_key = kr.json().get("primaryMasterKey", "") if kr.status_code == 200 else ""

    # Try multiple API versions and property shapes
    attempts = [
        # Attempt 1: agentStoreSettings (used in ML workspaces)
        {
            "api": "2026-01-15-preview",
            "body": {
                "properties": {
                    "agentStoreSettings": {
                        "storeType": "CosmosDB",
                        "connectionName": "cosmos-agent-store"
                    }
                }
            }
        },
        # Attempt 2: agentStorageConfiguration
        {
            "api": "2026-01-15-preview",
            "body": {
                "properties": {
                    "agentStorageConfiguration": {
                        "storageType": "CosmosDB",
                        "connectionName": "cosmos-agent-store",
                        "cosmosDbResourceId": cosmos_rid
                    }
                }
            }
        },
        # Attempt 3: agentSettings with cosmosDb
        {
            "api": "2026-01-15-preview",
            "body": {
                "properties": {
                    "agentSettings": {
                        "threadStorage": {
                            "type": "CosmosDB",
                            "cosmosDbConnectionName": "cosmos-agent-store"
                        }
                    }
                }
            }
        },
        # Attempt 4: dataConnections approach
        {
            "api": "2025-04-01-preview",
            "body": {
                "properties": {
                    "agentStoreSettings": {
                        "storeType": "CosmosDB",
                        "connectionName": "cosmos-agent-store"
                    }
                }
            }
        },
    ]

    for i, attempt in enumerate(attempts):
        api = attempt["api"]
        body = attempt["body"]
        url = f"{account_base()}?api-version={api}"
        prop_key = list(body["properties"].keys())[0]
        print(f"\n  Attempt {i+1}: PATCH {prop_key} (api={api})")

        r = requests.patch(url, headers=headers, json=body)
        print(f"    HTTP {r.status_code}")
        if r.status_code in (200, 201, 202):
            resp_props = r.json().get("properties", {})
            # Check if our property was accepted
            if prop_key in resp_props:
                print(f"    Accepted! {prop_key}: {json.dumps(resp_props[prop_key], default=str)[:200]}")
            else:
                print(f"    Property accepted but not in response (may need time)")
            # Check provisioning state
            state = resp_props.get("provisioningState", "?")
            print(f"    Provisioning state: {state}")
        else:
            err = r.text[:300]
            print(f"    Error: {err}")


# ============================================================
# STEP 3: Check project properties too
# ============================================================
def check_project_config():
    print("\n" + "=" * 60)
    print("STEP 3: Check project properties")
    print("=" * 60)
    headers = get_headers()

    url = (f"{account_base()}/projects/{PROJECT_NAME}"
           f"?api-version=2026-01-15-preview")
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        proj = r.json()
        props = proj.get("properties", {})
        print(f"  Property keys: {list(props.keys())}")
        for k, v in props.items():
            print(f"    {k}: {json.dumps(v, default=str)[:200]}")
    else:
        print(f"  HTTP {r.status_code}: {r.text[:300]}")


# ============================================================
# STEP 4: Run a test conversation and check Cosmos immediately
# ============================================================
def test_and_check_cosmos():
    print("\n" + "=" * 60)
    print("STEP 4: Test conversation then check Cosmos DB")
    print("=" * 60)

    from azure.ai.agents import AgentsClient
    from azure.ai.agents.models import MessageRole
    from azure.cosmos import CosmosClient

    endpoint = f"https://{ACCOUNT_NAME}.services.ai.azure.com/api/projects/{PROJECT_NAME}"
    client = AgentsClient(endpoint=endpoint, credential=cred)

    # Get Cosmos state BEFORE
    cosmos = CosmosClient(f"https://{COSMOS_NAME}.documents.azure.com:443/", credential=cred)
    dbs_before = [d["id"] for d in cosmos.list_databases()]
    counts_before = {}
    for db in cosmos.list_databases():
        db_client = cosmos.get_database_client(db["id"])
        for cont in db_client.list_containers():
            key = f"{db['id']}/{cont['id']}"
            count = list(db_client.get_container_client(cont["id"]).query_items(
                "SELECT VALUE COUNT(1) FROM c", enable_cross_partition_query=True))[0]
            counts_before[key] = count
    print(f"  Cosmos BEFORE: DBs={dbs_before}, counts={counts_before}")

    # Run test
    thread = client.threads.create()
    print(f"\n  Thread: {thread.id}")
    client.messages.create(thread_id=thread.id, role=MessageRole.USER,
                           content="What are Chubb's AI governance principles?")
    run = client.runs.create_and_process(thread_id=thread.id, agent_id=AGENT_ID)
    print(f"  Run: {run.id}  Status: {run.status}")

    # Wait a moment for data to land
    print("  Waiting 10s for data propagation...")
    time.sleep(10)

    # Get Cosmos state AFTER
    dbs_after = [d["id"] for d in cosmos.list_databases()]
    counts_after = {}
    for db in cosmos.list_databases():
        db_client = cosmos.get_database_client(db["id"])
        for cont in db_client.list_containers():
            key = f"{db['id']}/{cont['id']}"
            count = list(db_client.get_container_client(cont["id"]).query_items(
                "SELECT VALUE COUNT(1) FROM c", enable_cross_partition_query=True))[0]
            counts_after[key] = count

    print(f"\n  Cosmos AFTER: DBs={dbs_after}, counts={counts_after}")

    # Compare
    new_dbs = set(dbs_after) - set(dbs_before)
    if new_dbs:
        print(f"\n  NEW DATABASES: {new_dbs}")
    changed = {k: (counts_before.get(k, 0), v)
               for k, v in counts_after.items()
               if v != counts_before.get(k, 0)}
    if changed:
        print(f"  CHANGED containers: {changed}")
    else:
        print(f"  No changes in Cosmos DB item counts.")
        print(f"  Thread data is NOT going to Cosmos DB.")

    # Search for thread ID in all containers
    print(f"\n  Searching for thread {thread.id}...")
    for db in cosmos.list_databases():
        db_client = cosmos.get_database_client(db["id"])
        for cont in db_client.list_containers():
            cont_client = db_client.get_container_client(cont["id"])
            results = list(cont_client.query_items(
                f"SELECT TOP 1 c.id FROM c WHERE CONTAINS(c.id, '{thread.id}')",
                enable_cross_partition_query=True))
            if results:
                print(f"    FOUND in {db['id']}/{cont['id']}: {results}")


if __name__ == "__main__":
    check_current_config()
    configure_agent_store()
    check_project_config()
    test_and_check_cosmos()

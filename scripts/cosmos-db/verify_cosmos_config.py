"""Check if agentStoreSettings provisioning completed, then re-test."""
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


def account_url():
    return (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
            f"/providers/Microsoft.CognitiveServices/accounts/{ACCOUNT_NAME}")


# Check provisioning state and agentStoreSettings
print("=" * 60)
print("CHECK 1: Account provisioning state + agentStoreSettings")
print("=" * 60)
headers = get_headers()
r = requests.get(f"{account_url()}?api-version=2026-01-15-preview", headers=headers)
if r.status_code == 200:
    data = r.json()
    props = data.get("properties", {})
    state = props.get("provisioningState", "?")
    print(f"  Provisioning state: {state}")
    print(f"  Property keys: {list(props.keys())}")

    # Check for agentStoreSettings or similar
    for k, v in props.items():
        kl = k.lower()
        if any(word in kl for word in ["agent", "store", "cosmos", "thread", "storage"]):
            print(f"  {k}: {json.dumps(v, default=str)[:300]}")

    # Full dump to find it
    full = json.dumps(props, default=str)
    for pattern in ["agentStore", "storeType", "CosmosDB", "cosmos-agent-store"]:
        if pattern.lower() in full.lower():
            # Find the key containing it
            print(f"  Found '{pattern}' in properties!")

# Check project too
print("\n" + "=" * 60)
print("CHECK 2: Project properties")
print("=" * 60)
r = requests.get(
    f"{account_url()}/projects/{PROJECT_NAME}?api-version=2026-01-15-preview",
    headers=headers)
if r.status_code == 200:
    pprops = r.json().get("properties", {})
    print(f"  Keys: {list(pprops.keys())}")
    for k, v in pprops.items():
        print(f"    {k}: {json.dumps(v, default=str)[:200]}")

# Test conversation
print("\n" + "=" * 60)
print("CHECK 3: Test conversation + Cosmos DB check")
print("=" * 60)

from azure.ai.agents import AgentsClient
from azure.ai.agents.models import MessageRole
from azure.cosmos import CosmosClient

endpoint = f"https://{ACCOUNT_NAME}.services.ai.azure.com/api/projects/{PROJECT_NAME}"
client = AgentsClient(endpoint=endpoint, credential=cred)
cosmos = CosmosClient(f"https://{COSMOS_NAME}.documents.azure.com:443/", credential=cred)

# DB list before
dbs_before = sorted([d["id"] for d in cosmos.list_databases()])
print(f"  DBs before: {dbs_before}")

# Run test
thread = client.threads.create()
print(f"  Thread: {thread.id}")
client.messages.create(thread_id=thread.id, role=MessageRole.USER,
                       content="Hello, test message for storage validation")
run = client.runs.create_and_process(thread_id=thread.id, agent_id=AGENT_ID)
print(f"  Run: {run.id}  Status: {run.status}")

time.sleep(15)

# DB list after
dbs_after = sorted([d["id"] for d in cosmos.list_databases()])
print(f"  DBs after: {dbs_after}")
new_dbs = set(dbs_after) - set(dbs_before)
if new_dbs:
    print(f"  ** NEW DATABASES: {new_dbs} **")
    for db_name in new_dbs:
        db_client = cosmos.get_database_client(db_name)
        containers = list(db_client.list_containers())
        print(f"    {db_name} containers: {[c['id'] for c in containers]}")
        for cont in containers:
            cc = db_client.get_container_client(cont["id"])
            items = list(cc.query_items("SELECT TOP 5 c.id, c._ts FROM c ORDER BY c._ts DESC",
                                        enable_cross_partition_query=True))
            print(f"      {cont['id']}: {items}")
else:
    print("  No new databases created.")

# Search ALL containers for thread ID
print(f"\n  Searching all containers for '{thread.id}'...")
for db in cosmos.list_databases():
    db_client = cosmos.get_database_client(db["id"])
    for cont in db_client.list_containers():
        cc = db_client.get_container_client(cont["id"])
        hits = list(cc.query_items(
            f"SELECT c.id, c.type FROM c WHERE CONTAINS(c.id, '{thread.id}') OR CONTAINS(ToString(c), '{thread.id}')",
            enable_cross_partition_query=True))
        if hits:
            print(f"    FOUND in {db['id']}/{cont['id']}: {hits}")
print("  Search complete.")

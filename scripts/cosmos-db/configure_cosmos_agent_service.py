"""
Configure Cosmos DB directly as the Agent Service backing store for Foundry,
connect to the EXISTING agent (asst_tlb3LSNpxfV8zPY7gT8bR3GB), test, and verify.

Steps:
1. Discover available API versions and inspect current project properties
2. Configure Agent Service to use customer Cosmos DB via ARM API
3. Connect to the existing agent and run a test conversation
4. Verify new data appears in Cosmos DB
"""
import json
import time
import requests
from azure.identity import DefaultAzureCredential

SUB_ID = "a3223db3-76f2-4a7c-8684-57b835dc77e7"
RG = "rg-chubb-mcp-poc"
LOCATION = "eastus"
ARM = "https://management.azure.com"

HUB_NAME = "hub-chubb-storage-val"
PROJECT_NAME = "proj-chubb-storage-val"
COSMOS_NAME = "cosmos-chubb-mcp-poc"
COSMOS_CONNECTION = "cosmos-agent-store"
OAI_NAME = "oai-chubb-mcp-9342"
STORAGE_NAME = "stchubbmcppoc"

EXISTING_AGENT_ID = "asst_tlb3LSNpxfV8zPY7gT8bR3GB"

# API versions to try (newest first)
API_VERSIONS = [
    "2025-01-01-preview",
    "2024-10-01-preview",
    "2024-10-01",
    "2024-07-01-preview",
    "2024-04-01-preview",
    "2024-04-01",
    "2024-01-01-preview",
]


def get_headers():
    cred = DefaultAzureCredential()
    token = cred.get_token("https://management.azure.com/.default").token
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def proj_url(api_version):
    return (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
            f"/providers/Microsoft.MachineLearningServices/workspaces/{PROJECT_NAME}"
            f"?api-version={api_version}")


def hub_url(api_version):
    return (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
            f"/providers/Microsoft.MachineLearningServices/workspaces/{HUB_NAME}"
            f"?api-version={api_version}")


# ============================================================
# STEP 1: Discover API versions and dump all agent-related props
# ============================================================
def discover_api_and_config():
    print("=" * 60)
    print("STEP 1: Discover API versions & current agent configuration")
    print("=" * 60)

    headers = get_headers()
    best_api = None
    all_agent_props = {}

    # Try each API version, find the newest one that works and dump agent-related properties
    for api_ver in API_VERSIONS:
        r = requests.get(proj_url(api_ver), headers=headers)
        if r.status_code == 200:
            if best_api is None:
                best_api = api_ver
            props = r.json().get("properties", {})
            # Collect ALL property keys that might relate to agents/cosmos/storage
            for key in sorted(props.keys()):
                kl = key.lower()
                if any(kw in kl for kw in ["agent", "cosmos", "store", "endpoint", "setup"]):
                    val = props[key]
                    val_str = json.dumps(val) if isinstance(val, (dict, list)) else str(val)
                    if val_str and val_str != "null" and val_str != "None" and val_str != "{}":
                        all_agent_props[f"{api_ver}/{key}"] = val_str[:300]
            print(f"  API {api_ver}: OK (project found)")
        else:
            print(f"  API {api_ver}: HTTP {r.status_code}")

    # Also check Hub properties
    print(f"\n  Checking Hub properties...")
    if best_api:
        r = requests.get(hub_url(best_api), headers=headers)
        if r.status_code == 200:
            props = r.json().get("properties", {})
            for key in sorted(props.keys()):
                kl = key.lower()
                if any(kw in kl for kw in ["agent", "cosmos", "store", "endpoint", "setup"]):
                    val = props[key]
                    val_str = json.dumps(val) if isinstance(val, (dict, list)) else str(val)
                    if val_str and val_str != "null" and val_str != "None" and val_str != "{}":
                        all_agent_props[f"HUB/{best_api}/{key}"] = val_str[:300]

    print(f"\n  Best API version: {best_api}")
    print(f"\n  Agent-related properties found:")
    if all_agent_props:
        for k, v in sorted(all_agent_props.items()):
            print(f"    {k} = {v}")
    else:
        print("    (none found)")

    # List hub connections
    print(f"\n  Hub connections:")
    conns_url = (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
                 f"/providers/Microsoft.MachineLearningServices/workspaces/{HUB_NAME}"
                 f"/connections?api-version={best_api}")
    r = requests.get(conns_url, headers=headers)
    if r.status_code == 200:
        for c in r.json().get("value", []):
            name = c.get("name", "?")
            cat = c.get("properties", {}).get("category", "?")
            auth = c.get("properties", {}).get("authType", "?")
            target = c.get("properties", {}).get("target", "?")
            print(f"    {name}: category={cat}, auth={auth}, target={target[:80]}")

    return best_api


# ============================================================
# STEP 2: Configure Agent Service with Cosmos DB
# ============================================================
def configure_agent_service(best_api):
    print("\n" + "=" * 60)
    print("STEP 2: Configure Agent Service to use customer Cosmos DB")
    print("=" * 60)

    headers = get_headers()
    cosmos_rid = (f"/subscriptions/{SUB_ID}/resourceGroups/{RG}"
                  f"/providers/Microsoft.DocumentDB/databaseAccounts/{COSMOS_NAME}")
    storage_rid = (f"/subscriptions/{SUB_ID}/resourceGroups/{RG}"
                   f"/providers/Microsoft.Storage/storageAccounts/{STORAGE_NAME}")

    configured = False

    # ---- Approach A: PATCH project with various property shapes ----
    property_variants = [
        # Variant 1: agentStoreSettings
        {
            "agentStoreSettings": {
                "cosmosDbResourceId": cosmos_rid,
                "cosmosDbConnectionName": COSMOS_CONNECTION,
                "storageAccountResourceId": storage_rid,
            }
        },
        # Variant 2: agentConfiguration (seen in some docs)
        {
            "agentConfiguration": {
                "cosmosDbConnection": COSMOS_CONNECTION,
                "storageConnection": STORAGE_NAME,
            }
        },
        # Variant 3: agents block with connectionReferences (newer pattern)
        {
            "agents": {
                "connectionReferences": {
                    "aoai_connection": {"id": f"/subscriptions/{SUB_ID}/resourceGroups/{RG}/providers/Microsoft.MachineLearningServices/workspaces/{HUB_NAME}/connections/oai-chubb-connection"},
                    "cosmos_db": {"id": f"/subscriptions/{SUB_ID}/resourceGroups/{RG}/providers/Microsoft.MachineLearningServices/workspaces/{HUB_NAME}/connections/{COSMOS_CONNECTION}"},
                    "storage": {"id": f"/subscriptions/{SUB_ID}/resourceGroups/{RG}/providers/Microsoft.MachineLearningServices/workspaces/{HUB_NAME}/connections/{STORAGE_NAME}"},
                }
            }
        },
    ]

    # Try with best API and also preview APIs
    apis_to_try = [best_api] if best_api else []
    for v in API_VERSIONS:
        if v not in apis_to_try and "preview" in v:
            apis_to_try.append(v)

    for api_ver in apis_to_try[:3]:
        for i, variant in enumerate(property_variants, 1):
            body = {"properties": variant}
            print(f"\n  [{api_ver}] Variant {i}: {list(variant.keys())[0]}...")
            r = requests.patch(proj_url(api_ver), headers=headers, json=body)
            print(f"    PATCH: HTTP {r.status_code}")
            if r.status_code in (200, 201):
                # Check if property stuck
                r2 = requests.get(proj_url(api_ver), headers=headers)
                new_props = r2.json().get("properties", {})
                key = list(variant.keys())[0]
                if new_props.get(key):
                    print(f"    SUCCESS: {key} is set!")
                    configured = True
                    break
                else:
                    print(f"    Property accepted but not reflected in GET")
            elif r.status_code == 202:
                print(f"    Accepted (async) - waiting...")
                for _ in range(12):
                    time.sleep(15)
                    r2 = requests.get(proj_url(api_ver), headers=headers)
                    state = r2.json().get("properties", {}).get("provisioningState", "?")
                    print(f"    State: {state}")
                    if state in ("Succeeded", "succeeded"):
                        configured = True
                        break
                    if state in ("Failed", "failed"):
                        break
                if configured:
                    break
            else:
                resp = r.text[:200]
                print(f"    Error: {resp}")

        if configured:
            break

    # ---- Approach B: PUT to Hub with updated agent store properties ----
    if not configured:
        print(f"\n  [Approach B] Trying Hub-level update...")
        api_ver = best_api or "2025-01-01-preview"
        r = requests.get(hub_url(api_ver), headers=headers)
        if r.status_code == 200:
            hub_body = r.json()
            hub_props = hub_body.get("properties", {})

            # Add agent store configuration to hub
            hub_props["agentStoreSettings"] = {
                "cosmosDbResourceId": cosmos_rid,
                "cosmosDbConnectionName": COSMOS_CONNECTION,
            }
            hub_body["properties"] = hub_props

            r2 = requests.put(hub_url(api_ver), headers=headers, json=hub_body)
            print(f"    PUT Hub: HTTP {r2.status_code}")
            if r2.status_code in (200, 201, 202):
                print(f"    Hub updated!")
                if r2.status_code == 202:
                    for _ in range(20):
                        time.sleep(15)
                        r3 = requests.get(hub_url(api_ver), headers=headers)
                        state = r3.json().get("properties", {}).get("provisioningState", "?")
                        print(f"    State: {state}")
                        if state in ("Succeeded", "succeeded"):
                            configured = True
                            break
                        if state in ("Failed", "failed"):
                            break
                else:
                    configured = True
            else:
                print(f"    Error: {r2.text[:300]}")

    if not configured:
        print("\n  API configuration did not confirm success.")
        print("  Falling back: will still test the existing agent and check Cosmos.")

    return configured


# ============================================================
# STEP 3: Inspect Cosmos DB for any Foundry agent data
# ============================================================
def check_cosmos_for_foundry_data():
    print("\n" + "=" * 60)
    print("STEP 3: Inspect Cosmos DB for Foundry agent data")
    print("=" * 60)

    from azure.cosmos import CosmosClient

    cred = DefaultAzureCredential()
    cosmos_url = f"https://{COSMOS_NAME}.documents.azure.com:443/"
    client = CosmosClient(cosmos_url, credential=cred)

    databases = list(client.list_databases())
    print(f"\n  Databases found: {[d['id'] for d in databases]}")

    foundry_data = False
    for db in databases:
        db_name = db["id"]
        db_client = client.get_database_client(db_name)
        containers = list(db_client.list_containers())
        print(f"\n  Database: {db_name} ({len(containers)} containers)")

        for cont in containers:
            cont_name = cont["id"]
            cont_client = db_client.get_container_client(cont_name)
            try:
                items = list(cont_client.query_items(
                    query="SELECT VALUE COUNT(1) FROM c",
                    enable_cross_partition_query=True,
                ))
                count = items[0] if items else "?"
            except Exception as e:
                count = f"error: {str(e)[:60]}"
            print(f"    {cont_name}: {count} items")

            # Check if this looks like Foundry agent data
            if any(kw in cont_name.lower() for kw in
                   ["thread", "message", "agent", "run", "file", "vector"]):
                foundry_data = True
                print(f"    ^ FOUNDRY AGENT DATA DETECTED!")

        # Any DB besides agentic-framework is potentially Foundry-created
        if db_name != "agentic-framework":
            foundry_data = True
            print(f"  ^ NEW DATABASE (not agentic-framework)")
            # Sample documents from first container
            if containers:
                first_cont = containers[0]["id"]
                c = db_client.get_container_client(first_cont)
                try:
                    sample = list(c.query_items(
                        query="SELECT TOP 3 * FROM c",
                        enable_cross_partition_query=True,
                    ))
                    for doc in sample[:2]:
                        print(f"\n    Sample from {first_cont}:")
                        print(f"      Keys: {list(doc.keys())}")
                        for k in list(doc.keys())[:10]:
                            v = doc[k]
                            if isinstance(v, str) and len(v) > 120:
                                v = v[:120] + "..."
                            elif isinstance(v, (dict, list)):
                                v = json.dumps(v)[:120] + "..."
                            print(f"        {k}: {v}")
                except Exception as e:
                    print(f"    Sample error: {str(e)[:100]}")

    if not foundry_data:
        print(f"\n  No Foundry-specific data found yet.")
        print("  Only the pre-existing 'agentic-framework' DB (Astra backend).")

    return foundry_data


# ============================================================
# STEP 4: Connect to EXISTING agent and run test conversation
# ============================================================
def run_test_with_existing_agent():
    print("\n" + "=" * 60)
    print("STEP 4: Connect to EXISTING agent and run test")
    print("=" * 60)

    from azure.ai.agents import AgentsClient
    from azure.ai.agents.models import MessageRole

    cred = DefaultAzureCredential()
    headers = get_headers()

    # Get agents endpoint
    r = requests.get(proj_url("2024-10-01"), headers=headers)
    endpoint = r.json()["properties"].get("agentsEndpointUri")
    if not endpoint:
        print("  ERROR: No agents endpoint found")
        return None

    print(f"  Agents endpoint: {endpoint}")
    print(f"  Connecting to existing agent: {EXISTING_AGENT_ID}")

    client = AgentsClient(
        endpoint=endpoint,
        credential=cred,
        subscription_id=SUB_ID,
        resource_group_name=RG,
        project_name=PROJECT_NAME,
    )

    # Verify agent exists
    try:
        agent = client.get_agent(agent_id=EXISTING_AGENT_ID)
        print(f"  Agent verified: {agent.name} (model: {agent.model})")
    except Exception as e:
        print(f"  ERROR retrieving agent: {e}")
        return None

    # Create thread and run test
    thread = client.threads.create()
    print(f"  Created thread: {thread.id}")

    client.messages.create(
        thread_id=thread.id,
        role=MessageRole.USER,
        content="What is Chubb's AI governance policy?",
    )

    start = time.time()
    run = client.runs.create_and_process(
        thread_id=thread.id,
        agent_id=EXISTING_AGENT_ID,
    )
    elapsed = time.time() - start
    print(f"  Run: {run.id}")
    print(f"  Status: {run.status}")
    print(f"  Time: {elapsed:.1f}s")

    if hasattr(run, "usage") and run.usage:
        print(f"  Tokens: {run.usage.prompt_tokens}+{run.usage.completion_tokens}={run.usage.total_tokens}")

    response = client.messages.get_last_message_text_by_role(
        thread_id=thread.id,
        role=MessageRole.AGENT,
    )
    if response:
        text = response.text.value if hasattr(response, "text") else str(response)
        print(f"  Response ({len(text)} chars): {text[:250]}...")

    print(f"\n  Thread ID to look for in Cosmos: {thread.id}")
    return thread.id


# ============================================================
# STEP 5: Re-check Cosmos DB for new Foundry data
# ============================================================
def verify_cosmos_after_test(thread_id=None):
    print("\n" + "=" * 60)
    print("STEP 5: Re-check Cosmos DB for new Foundry data")
    print("=" * 60)

    from azure.cosmos import CosmosClient

    cred = DefaultAzureCredential()
    cosmos_url = f"https://{COSMOS_NAME}.documents.azure.com:443/"
    client = CosmosClient(cosmos_url, credential=cred)

    databases = list(client.list_databases())
    db_names = [d["id"] for d in databases]
    print(f"  Databases: {db_names}")

    for db in databases:
        db_name = db["id"]
        db_client = client.get_database_client(db_name)
        containers = list(db_client.list_containers())

        for cont in containers:
            cont_name = cont["id"]
            cont_client = db_client.get_container_client(cont_name)
            try:
                items = list(cont_client.query_items(
                    query="SELECT VALUE COUNT(1) FROM c",
                    enable_cross_partition_query=True,
                ))
                count = items[0] if items else 0
            except Exception:
                count = "?"
            print(f"  {db_name}/{cont_name}: {count} items")

            # Search for thread_id in this container
            if thread_id and count and count != "?" and count > 0:
                try:
                    search = list(cont_client.query_items(
                        query=(
                            f"SELECT TOP 5 c.id, c.thread_id FROM c "
                            f"WHERE CONTAINS(c.id, @tid) OR c.thread_id = @tid"
                        ),
                        parameters=[{"name": "@tid", "value": thread_id}],
                        enable_cross_partition_query=True,
                    ))
                    if search:
                        print(f"    ** FOUND thread {thread_id} in {cont_name}! **")
                        for doc in search:
                            print(f"      {doc}")
                except Exception as e:
                    pass  # Container may not support this query

    # Check for any NEW databases that were not there before
    non_astra = [d for d in db_names if d != "agentic-framework"]
    if non_astra:
        print(f"\n  NEW DATABASE(S) (not agentic-framework): {non_astra}")
        print("  Cosmos DB IS being used by Foundry Agent Service!")
        # Deep inspect new databases
        for db_name in non_astra:
            db_client = client.get_database_client(db_name)
            containers = list(db_client.list_containers())
            for cont in containers:
                cont_name = cont["id"]
                cont_client = db_client.get_container_client(cont_name)
                try:
                    sample = list(cont_client.query_items(
                        query="SELECT TOP 3 * FROM c",
                        enable_cross_partition_query=True,
                    ))
                    for doc in sample:
                        print(f"\n  {db_name}/{cont_name} sample:")
                        print(f"    Keys: {list(doc.keys())}")
                        for k in list(doc.keys())[:10]:
                            v = doc[k]
                            if isinstance(v, str) and len(v) > 120:
                                v = v[:120] + "..."
                            elif isinstance(v, (dict, list)):
                                v = json.dumps(v)[:120] + "..."
                            print(f"      {k}: {v}")
                except Exception:
                    pass
    else:
        print(f"\n  No new Foundry databases found.")
        print("  Agent Service is still using Foundry-managed internal storage.")
        print("\n  NEXT STEP - Configure via Azure AI Foundry Portal:")
        print("    1. Go to https://ai.azure.com")
        print("    2. Open project: proj-chubb-storage-val")
        print("    3. Settings > scroll to 'Agent service'")
        print("    4. Click '+ Select Resources'")
        print("    5. Select Cosmos DB: cosmos-chubb-mcp-poc")
        print("    6. Save, then re-run this script")


def main():
    print("=" * 70)
    print("  CONFIGURE COSMOS DB FOR FOUNDRY AGENT SERVICE")
    print("  Using existing agent: " + EXISTING_AGENT_ID)
    print("=" * 70)

    # Step 1: Discover APIs and current config
    best_api = discover_api_and_config()

    # Step 2: Try to configure Cosmos DB as agent store via API
    api_success = configure_agent_service(best_api)

    # Step 3: Check what's currently in Cosmos
    has_foundry_data = check_cosmos_for_foundry_data()

    # Step 4: Run a test with the EXISTING agent
    thread_id = run_test_with_existing_agent()

    # Step 5: Check Cosmos for new data
    if thread_id:
        print("\n  Waiting 10s for data propagation...")
        time.sleep(10)
        verify_cosmos_after_test(thread_id)

    # Final summary
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print(f"  API config succeeded:    {'YES' if api_success else 'NO (may need portal)'}")
    print(f"  Foundry data in Cosmos:  {'YES' if has_foundry_data else 'NO'}")
    print(f"  Test conversation:       {'Thread ' + thread_id if thread_id else 'FAILED'}")
    print(f"  Existing agent used:     {EXISTING_AGENT_ID}")


if __name__ == "__main__":
    main()

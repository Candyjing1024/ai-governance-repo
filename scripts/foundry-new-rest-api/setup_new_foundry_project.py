"""
Post-portal-creation setup for NEW Foundry (CognitiveServices-based).
Discovers the CognitiveServices account + project, adds connections,
assigns RBAC, creates agent, and tests.

Resource types (new Foundry portal):
  - Microsoft.CognitiveServices/accounts          (parent = "Foundry resource")
  - Microsoft.CognitiveServices/accounts/projects  (child  = "project")
"""
import json
import time
import uuid
import requests
from azure.identity import DefaultAzureCredential

SUB_ID = "a3223db3-76f2-4a7c-8684-57b835dc77e7"
RG = "rg-chubb-mcp-poc"
ARM = "https://management.azure.com"

# New Foundry (CognitiveServices) details  -- discovered by find_foundry_resources.py
ACCOUNT_NAME = "proj-chubb-storage-val-resource"   # parent AIServices account
PROJECT_NAME = "proj-chubb-storage-val"             # project under the account
API_CS = "2025-06-01"                                # CognitiveServices stable API (supports accounts/projects)
API_CS_PREVIEW = "2026-01-15-preview"                # latest preview (for connections)

# Existing shared resources
COSMOS_NAME = "cosmos-chubb-mcp-poc"
OAI_NAME = "oai-chubb-mcp-9342"
KV_NAME = "kv-chubb-mcp-9342"
STORAGE_NAME = "stchubbmcppoc"


def _cred():
    return DefaultAzureCredential()


def get_headers():
    token = _cred().get_token("https://management.azure.com/.default").token
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _account_base():
    return (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
            f"/providers/Microsoft.CognitiveServices/accounts/{ACCOUNT_NAME}")


def _project_base():
    return f"{_account_base()}/projects/{PROJECT_NAME}"


# ============================================================
# STEP 1: Discover and display CognitiveServices resources
# ============================================================
def discover_resources():
    print("=" * 60)
    print("STEP 1: Discover new Foundry resources (CognitiveServices)")
    print("=" * 60)

    headers = get_headers()

    # --- Account ---
    url = f"{_account_base()}?api-version={API_CS}"
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        print(f"  ERROR: Account GET returned {r.status_code}")
        print(f"  {r.text[:500]}")
        return None
    acct = r.json()
    props = acct.get("properties", {})
    endpoints = props.get("endpoints", {})
    print(f"\n  Account: {ACCOUNT_NAME}")
    print(f"    Kind: {acct.get('kind')}")
    print(f"    Location: {acct.get('location')}")
    print(f"    State: {props.get('provisioningState')}")
    print(f"    Endpoint: {props.get('endpoint')}")
    if isinstance(endpoints, dict):
        for k, v in endpoints.items():
            print(f"    {k}: {v}")
    elif isinstance(endpoints, str):
        try:
            ep = json.loads(endpoints)
            for k, v in ep.items():
                print(f"    {k}: {v}")
        except Exception:
            print(f"    Endpoints: {endpoints[:200]}")

    identity = acct.get("identity", {})
    acct_principal = identity.get("principalId", "")
    print(f"    Identity type: {identity.get('type')}")
    print(f"    PrincipalId: {acct_principal}")

    # --- Project ---
    url = f"{_project_base()}?api-version={API_CS}"
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        print(f"\n  ERROR: Project GET returned {r.status_code}")
        print(f"  {r.text[:500]}")
        return None
    proj = r.json()
    pprops = proj.get("properties", {})
    print(f"\n  Project: {PROJECT_NAME}")
    print(f"    Kind: {proj.get('kind')}")
    print(f"    Location: {proj.get('location')}")
    print(f"    State: {pprops.get('provisioningState')}")

    # Dump all project properties for reference
    print(f"\n  Project properties keys: {list(pprops.keys())}")
    for k, v in pprops.items():
        sv = str(v)
        if len(sv) > 200:
            sv = sv[:200] + "..."
        print(f"    {k}: {sv}")

    proj_identity = proj.get("identity", {})
    proj_principal = proj_identity.get("principalId", "")
    if proj_principal:
        print(f"    Project PrincipalId: {proj_principal}")

    return {
        "account": acct,
        "project": proj,
        "acct_principal": acct_principal,
        "proj_principal": proj_principal,
    }


# ============================================================
# STEP 2: Add connections to the CognitiveServices account
# ============================================================
def add_connections():
    print("\n" + "=" * 60)
    print("STEP 2: Add connections")
    print("=" * 60)

    headers = get_headers()
    base = _account_base()

    # Try listing existing connections (multiple API versions)
    existing = []
    conn_api = None
    conn_base = None

    # Try account-level connections with multiple API versions
    for api in [API_CS_PREVIEW, "2024-06-01-preview", API_CS]:
        r = requests.get(f"{base}/connections?api-version={api}", headers=headers)
        print(f"  List connections on account (api={api}): HTTP {r.status_code}")
        if r.status_code == 200:
            conns = r.json().get("value", [])
            existing = [c.get("name", "") for c in conns]
            print(f"    Existing: {existing}")
            conn_api = api
            conn_base = base
            break
        elif r.status_code != 404:
            print(f"    Body: {r.text[:200]}")

    # If not found at account level, try project level
    if not conn_api:
        proj_base = _project_base()
        for api in [API_CS_PREVIEW, "2024-06-01-preview", API_CS]:
            r = requests.get(f"{proj_base}/connections?api-version={api}", headers=headers)
            print(f"  List connections on project (api={api}): HTTP {r.status_code}")
            if r.status_code == 200:
                conns = r.json().get("value", [])
                existing = [c.get("name", "") for c in conns]
                print(f"    Existing: {existing}")
                conn_api = api
                conn_base = proj_base
                break
            elif r.status_code != 404:
                print(f"    Body: {r.text[:200]}")

    if not conn_api:
        print("  WARN: No working connections API found. Will skip connections.")
        print("         You may need to add connections manually in the portal.")
        return

    print(f"\n  Using connections API: {conn_api} on {conn_base.split('/')[-1]}")

    # --- Cosmos DB connection ---
    if "cosmos-agent-store" not in existing:
        print("\n  Adding Cosmos DB connection...")
        cosmos_rid = (f"/subscriptions/{SUB_ID}/resourceGroups/{RG}"
                      f"/providers/Microsoft.DocumentDB/databaseAccounts/{COSMOS_NAME}")
        cosmos_url = f"{ARM}{cosmos_rid}?api-version=2024-05-15"
        cr = requests.get(cosmos_url, headers=headers)
        cosmos_endpoint = cr.json().get("properties", {}).get("documentEndpoint", "")

        keys_url = f"{ARM}{cosmos_rid}/listKeys?api-version=2024-05-15"
        kr = requests.post(keys_url, headers=headers)
        cosmos_key = kr.json().get("primaryMasterKey", "") if kr.status_code == 200 else ""

        # Try multiple auth formats
        bodies = [
            {
                "properties": {
                    "category": "CosmosDB",
                    "target": cosmos_endpoint,
                    "authType": "ApiKey",
                    "credentials": {"key": cosmos_key},
                    "metadata": {"ResourceId": cosmos_rid},
                }
            },
            {
                "properties": {
                    "category": "CosmosDB",
                    "target": cosmos_endpoint,
                    "authType": "CustomKeys",
                    "credentials": {"keys": {"key": cosmos_key}},
                    "metadata": {"ResourceId": cosmos_rid},
                }
            },
            {
                "properties": {
                    "category": "CosmosDB",
                    "target": cosmos_endpoint,
                    "authType": "AAD",
                    "metadata": {"ResourceId": cosmos_rid},
                }
            },
        ]
        for i, body in enumerate(bodies):
            conn_url = f"{conn_base}/connections/cosmos-agent-store?api-version={conn_api}"
            rc = requests.put(conn_url, headers=headers, json=body)
            auth = body["properties"]["authType"]
            print(f"    Cosmos ({auth}): HTTP {rc.status_code}")
            if rc.status_code in (200, 201):
                break
            if i < len(bodies) - 1:
                print(f"      {rc.text[:200]}")
    else:
        print("  Cosmos DB connection already exists")

    # --- OpenAI connection ---
    has_oai = any("oai" in c.lower() or "openai" in c.lower() or "aoai" in c.lower()
                   for c in existing)
    if not has_oai:
        print("\n  Adding OpenAI connection...")
        oai_rid = (f"/subscriptions/{SUB_ID}/resourceGroups/{RG}"
                   f"/providers/Microsoft.CognitiveServices/accounts/{OAI_NAME}")
        body = {
            "properties": {
                "category": "AzureOpenAI",
                "target": f"https://{OAI_NAME}.openai.azure.com/",
                "authType": "AAD",
                "metadata": {"ApiType": "Azure", "ResourceId": oai_rid},
            }
        }
        conn_url = f"{conn_base}/connections/oai-chubb-connection?api-version={conn_api}"
        r = requests.put(conn_url, headers=headers, json=body)
        print(f"    OpenAI connection: HTTP {r.status_code}")
        if r.status_code not in (200, 201):
            print(f"      {r.text[:300]}")
    else:
        print("  OpenAI connection already exists")

    # Verify
    r = requests.get(f"{conn_base}/connections?api-version={conn_api}", headers=headers)
    if r.status_code == 200:
        conns = r.json().get("value", [])
        print(f"\n  All connections ({len(conns)}):")
        for c in conns:
            name = c.get("name", "?")
            cat = c.get("properties", {}).get("category", "?")
            print(f"    {name}: {cat}")


# ============================================================
# STEP 3: Assign RBAC roles
# ============================================================
def assign_rbac(info):
    print("\n" + "=" * 60)
    print("STEP 3: Assign RBAC roles")
    print("=" * 60)

    headers = get_headers()
    acct_principal = info.get("acct_principal", "")
    proj_principal = info.get("proj_principal", "")

    print(f"  Account principal: {acct_principal}")
    print(f"  Project principal: {proj_principal}")

    # Get current user
    graph_token = _cred().get_token("https://graph.microsoft.com/.default").token
    gr = requests.get("https://graph.microsoft.com/v1.0/me",
                       headers={"Authorization": f"Bearer {graph_token}"})
    user_id = gr.json().get("id", "")
    print(f"  User ID: {user_id}")

    oai_rid = (f"/subscriptions/{SUB_ID}/resourceGroups/{RG}"
               f"/providers/Microsoft.CognitiveServices/accounts/{OAI_NAME}")
    storage_rid = (f"/subscriptions/{SUB_ID}/resourceGroups/{RG}"
                   f"/providers/Microsoft.Storage/storageAccounts/{STORAGE_NAME}")
    account_rid = (f"/subscriptions/{SUB_ID}/resourceGroups/{RG}"
                   f"/providers/Microsoft.CognitiveServices/accounts/{ACCOUNT_NAME}")

    assignments = []
    # Cognitive Services OpenAI Contributor on OAI for account SP
    if acct_principal:
        assignments.append((oai_rid, acct_principal, "ServicePrincipal",
                            "CogSvc OpenAI Contributor", "a001fd3d-188f-4b5d-821b-7da978bf7442"))
        assignments.append((oai_rid, acct_principal, "ServicePrincipal",
                            "CogSvc OpenAI User", "5e0bd9bd-7b93-4f28-af87-19fc36ad61bd"))
    # OpenAI for project SP (if different from account)
    if proj_principal and proj_principal != acct_principal:
        assignments.append((oai_rid, proj_principal, "ServicePrincipal",
                            "CogSvc OpenAI Contributor", "a001fd3d-188f-4b5d-821b-7da978bf7442"))
        assignments.append((oai_rid, proj_principal, "ServicePrincipal",
                            "CogSvc OpenAI User", "5e0bd9bd-7b93-4f28-af87-19fc36ad61bd"))
    # OpenAI for user
    if user_id:
        assignments.append((oai_rid, user_id, "User",
                            "CogSvc OpenAI Contributor", "a001fd3d-188f-4b5d-821b-7da978bf7442"))
    # Cognitive Services Contributor on the account for user
    if user_id:
        assignments.append((account_rid, user_id, "User",
                            "CogSvc Contributor", "25fbc0a9-bd7c-42a3-aa1a-3b75d497ee68"))
    # Storage Blob Data Contributor for everyone
    for pid, ptype in [(user_id, "User"), (acct_principal, "ServicePrincipal"),
                       (proj_principal, "ServicePrincipal")]:
        if pid:
            assignments.append((storage_rid, pid, ptype,
                                "Storage Blob Data Contributor",
                                "ba92f5b4-2d11-453d-a403-e96b0029c9fe"))

    for scope, pid, ptype, role_name, role_id in assignments:
        if not pid:
            continue
        assign_id = str(uuid.uuid4())
        url = (f"{ARM}{scope}/providers/Microsoft.Authorization"
               f"/roleAssignments/{assign_id}?api-version=2022-04-01")
        body = {
            "properties": {
                "roleDefinitionId": (f"{scope}/providers/Microsoft.Authorization"
                                     f"/roleDefinitions/{role_id}"),
                "principalId": pid,
                "principalType": ptype,
            }
        }
        r = requests.put(url, headers=headers, json=body)
        status = ("OK" if r.status_code in (200, 201) else
                  "Exists" if r.status_code == 409 else
                  f"HTTP {r.status_code}")
        print(f"  {role_name} -> {ptype[:4]}..{pid[-4:]}: {status}")

    print("  Waiting 15s for RBAC propagation...")
    time.sleep(15)


# ============================================================
# STEP 4: Create agent on new project
# ============================================================
def create_agent(info):
    print("\n" + "=" * 60)
    print("STEP 4: Create agent on new project")
    print("=" * 60)

    from azure.ai.agents import AgentsClient
    from azure.ai.agents.models import OpenApiTool, OpenApiAnonymousAuthDetails

    # For new CognitiveServices-based Foundry, the project has its own endpoint
    proj = info["project"]
    proj_endpoints = proj.get("properties", {}).get("endpoints", {})
    if isinstance(proj_endpoints, str):
        try:
            proj_endpoints = json.loads(proj_endpoints)
        except Exception:
            proj_endpoints = {}

    # Use the project-level "AI Foundry API" endpoint (includes /api/projects/<name>)
    endpoint = None
    if isinstance(proj_endpoints, dict):
        endpoint = proj_endpoints.get("AI Foundry API")

    # Fallback: construct from account endpoint + project name
    if not endpoint:
        acct = info["account"]
        acct_endpoints = acct.get("properties", {}).get("endpoints", {})
        if isinstance(acct_endpoints, str):
            try:
                acct_endpoints = json.loads(acct_endpoints)
            except Exception:
                acct_endpoints = {}
        if isinstance(acct_endpoints, dict):
            base = acct_endpoints.get("AI Foundry API", "")
            if base:
                endpoint = f"{base.rstrip('/')}/api/projects/{PROJECT_NAME}"
    if not endpoint:
        endpoint = f"https://{ACCOUNT_NAME}.services.ai.azure.com/api/projects/{PROJECT_NAME}"

    print(f"  Agents endpoint: {endpoint}")

    cred = _cred()
    client = AgentsClient(endpoint=endpoint, credential=cred)

    # Load OpenAPI spec
    with open("astra_openapi.json", "r") as f:
        spec = json.load(f)
    print(f"  Loaded OpenAPI spec: {spec['info']['title']}")

    openapi_tool = OpenApiTool(
        name="astra_backend",
        description="Chubb AI Governance Astra Backend",
        spec=spec,
        auth=OpenApiAnonymousAuthDetails(),
    )

    system_instructions = """You are the Chubb AI Governance Assistant powered by the Astra multi-agent system.
Your role:
- Answer questions about Chubb's AI governance policies, frameworks, compliance requirements, and best practices.
- Use the 'askAstra' tool to query the Astra backend for any Chubb AI governance question.
- Always pass the user's question directly to the tool - do NOT try to answer from your own knowledge.
- Present the response from Astra clearly and professionally.

When the user asks a question:
1. Call the askAstra tool with the user's message
2. Return the response from Astra to the user

You should ALWAYS use the askAstra tool for any question related to Chubb AI governance.
For general conversation (greetings, clarifications), respond naturally without using tools.
"""

    agent = client.create_agent(
        model="gpt-4o",
        name="astra-storage-val-agent",
        instructions=system_instructions,
        tools=openapi_tool.definitions,
    )
    print(f"  Agent created: {agent.id} ({agent.name})")
    return client, agent


# ============================================================
# STEP 5: Test conversation
# ============================================================
def test_conversation(client, agent):
    print("\n" + "=" * 60)
    print("STEP 5: Test conversation")
    print("=" * 60)

    from azure.ai.agents.models import MessageRole

    thread = client.threads.create()
    print(f"  Thread: {thread.id}")

    client.messages.create(
        thread_id=thread.id,
        role=MessageRole.USER,
        content="What is Chubb's AI governance policy?",
    )

    start = time.time()
    run = client.runs.create_and_process(
        thread_id=thread.id,
        agent_id=agent.id,
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
        print(f"  Response ({len(text)} chars): {text[:300]}...")

    return thread.id


# ============================================================
# STEP 6: Check Cosmos DB for Foundry data
# ============================================================
def check_cosmos():
    print("\n" + "=" * 60)
    print("STEP 6: Check Cosmos DB")
    print("=" * 60)

    from azure.cosmos import CosmosClient

    cred = _cred()
    client = CosmosClient(f"https://{COSMOS_NAME}.documents.azure.com:443/", credential=cred)

    databases = list(client.list_databases())
    print(f"  Databases: {[d['id'] for d in databases]}")

    for db in databases:
        db_client = client.get_database_client(db["id"])
        containers = list(db_client.list_containers())
        print(f"\n  {db['id']} ({len(containers)} containers):")
        for cont in containers:
            cont_client = db_client.get_container_client(cont["id"])
            try:
                items = list(cont_client.query_items(
                    query="SELECT VALUE COUNT(1) FROM c",
                    enable_cross_partition_query=True))
                count = items[0] if items else "?"
            except Exception:
                count = "?"
            print(f"    {cont['id']}: {count} items")


def main():
    # Step 1: Discover
    info = discover_resources()
    if not info:
        print("\nERROR: Could not find account or project.")
        return

    # Step 2: Add connections
    add_connections()

    # Step 3: RBAC
    assign_rbac(info)

    # Step 4: Create agent
    client, agent = create_agent(info)
    if not client:
        print("\nERROR: Agent creation failed")
        return

    # Step 5: Test
    thread_id = test_conversation(client, agent)

    # Step 6: Check Cosmos
    check_cosmos()

    print("\n" + "=" * 60)
    print("SETUP COMPLETE")
    print("=" * 60)
    print(f"  Account: {ACCOUNT_NAME}")
    print(f"  Project: {PROJECT_NAME}")
    print(f"  Agent: {agent.id} ({agent.name})")
    print(f"  Test thread: {thread_id}")
    print(f"\n  Next: Open the project in the new Foundry portal")
    print(f"  Portal: https://ai.azure.com")
    print(f"  Go to Settings > Agent service > + Select Resources > Cosmos DB")


if __name__ == "__main__":
    main()

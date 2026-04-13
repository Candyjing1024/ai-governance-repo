"""
Phase 3-5: Create Foundry Agent, run test conversations, inspect backend stores.
Uses the new hub-chubb-storage-val / proj-chubb-storage-val with linked resources.
"""
import json
import time
import requests
from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import OpenApiTool, OpenApiAnonymousAuthDetails, MessageRole

SUB_ID = "a3223db3-76f2-4a7c-8684-57b835dc77e7"
RG = "rg-chubb-mcp-poc"
PROJECT_NAME = "proj-chubb-storage-val"
ARM = "https://management.azure.com"

AGENT_MODEL = "gpt-4o"
AGENT_NAME = "astra-storage-val-agent"
OPENAPI_SPEC_PATH = "astra_openapi.json"

SYSTEM_INSTRUCTIONS = """You are the Chubb AI Governance Assistant powered by the Astra multi-agent system.

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

TEST_QUERIES = [
    "What is Chubb's AI governance policy?",
    "What are the AI risk categories at Chubb?",
    "How does Chubb monitor AI models in production?",
]


def get_agents_endpoint():
    cred = DefaultAzureCredential()
    token = cred.get_token("https://management.azure.com/.default").token
    headers = {"Authorization": f"Bearer {token}"}
    url = (
        f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
        f"/providers/Microsoft.MachineLearningServices/workspaces/{PROJECT_NAME}"
        f"?api-version=2024-10-01"
    )
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    uri = r.json()["properties"].get("agentsEndpointUri")
    if not uri:
        raise RuntimeError("No agentsEndpointUri found")
    return uri


def create_agent():
    print("=" * 60)
    print("PHASE 3: CREATE FOUNDRY AGENT")
    print("=" * 60)

    print("\n[1] Loading OpenAPI spec...")
    with open(OPENAPI_SPEC_PATH, "r") as f:
        spec = json.load(f)
    print(f"  Loaded: {spec['info']['title']} v{spec['info']['version']}")

    print("\n[2] Getting agents endpoint...")
    endpoint = get_agents_endpoint()
    print(f"  Endpoint: {endpoint}")

    print("\n[3] Connecting AgentsClient...")
    cred = DefaultAzureCredential()
    client = AgentsClient(
        endpoint=endpoint,
        credential=cred,
        subscription_id=SUB_ID,
        resource_group_name=RG,
        project_name=PROJECT_NAME,
    )

    print("\n[4] Creating agent...")
    openapi_tool = OpenApiTool(
        name="astra_backend",
        description="Chubb AI Governance Astra Backend",
        spec=spec,
        auth=OpenApiAnonymousAuthDetails(),
    )

    agent = client.create_agent(
        model=AGENT_MODEL,
        name=AGENT_NAME,
        instructions=SYSTEM_INSTRUCTIONS,
        tools=openapi_tool.definitions,
    )

    print(f"  Agent created!")
    print(f"  ID:    {agent.id}")
    print(f"  Name:  {agent.name}")
    print(f"  Model: {agent.model}")
    print(f"  Tools: {len(agent.tools)}")

    return client, agent


def run_test_conversations(client, agent):
    print("\n" + "=" * 60)
    print("PHASE 4: TEST CONVERSATIONS")
    print("=" * 60)

    thread_ids = []
    run_ids = []

    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\n--- Test {i}/{len(TEST_QUERIES)}: {query}")

        start = time.time()
        thread = client.threads.create()
        thread_ids.append(thread.id)
        print(f"  Thread: {thread.id}")

        client.messages.create(
            thread_id=thread.id,
            role=MessageRole.USER,
            content=query,
        )

        run = client.runs.create_and_process(
            thread_id=thread.id,
            agent_id=agent.id,
        )
        run_ids.append(run.id)
        elapsed = time.time() - start

        print(f"  Run:    {run.id}")
        print(f"  Status: {run.status}")
        print(f"  Time:   {elapsed:.1f}s")

        if hasattr(run, "usage") and run.usage:
            print(f"  Tokens: {run.usage.prompt_tokens}+{run.usage.completion_tokens}={run.usage.total_tokens}")

        # Get response
        response = client.messages.get_last_message_text_by_role(
            thread_id=thread.id,
            role=MessageRole.AGENT,
        )
        if response:
            text = response.text.value if hasattr(response, "text") else str(response)
            print(f"  Response ({len(text)} chars): {text[:200]}...")
        else:
            print("  No response received")

    # Also test multi-turn on the first thread
    print(f"\n--- Multi-turn test on thread {thread_ids[0]}...")
    client.messages.create(
        thread_id=thread_ids[0],
        role=MessageRole.USER,
        content="Can you elaborate on the compliance framework mentioned above?",
    )
    run2 = client.runs.create_and_process(
        thread_id=thread_ids[0],
        agent_id=agent.id,
    )
    run_ids.append(run2.id)
    print(f"  Follow-up run: {run2.id}, status: {run2.status}")

    response2 = client.messages.get_last_message_text_by_role(
        thread_id=thread_ids[0],
        role=MessageRole.AGENT,
    )
    if response2:
        text2 = response2.text.value if hasattr(response2, "text") else str(response2)
        print(f"  Response ({len(text2)} chars): {text2[:200]}...")

    print(f"\n  Summary: {len(thread_ids)} threads, {len(run_ids)} runs")
    print(f"  Thread IDs: {thread_ids}")
    print(f"  Run IDs: {run_ids}")

    return thread_ids, run_ids


def inspect_cosmos_db():
    print("\n" + "=" * 60)
    print("PHASE 5a: INSPECT COSMOS DB")
    print("=" * 60)

    from azure.cosmos import CosmosClient

    cred = DefaultAzureCredential()
    cosmos_url = "https://cosmos-chubb-mcp-poc.documents.azure.com:443/"
    client = CosmosClient(cosmos_url, credential=cred)

    print("\n  Listing all databases:")
    databases = list(client.list_databases())
    for db in databases:
        db_name = db["id"]
        print(f"\n  Database: {db_name}")
        db_client = client.get_database_client(db_name)
        containers = list(db_client.list_containers())
        for cont in containers:
            cont_name = cont["id"]
            cont_client = db_client.get_container_client(cont_name)
            # Count items
            try:
                items = list(cont_client.query_items(
                    query="SELECT VALUE COUNT(1) FROM c",
                    enable_cross_partition_query=True,
                ))
                count = items[0] if items else "?"
            except Exception as e:
                count = f"error: {str(e)[:80]}"

            print(f"    Container: {cont_name} ({count} items)")

            # Sample a few documents
            try:
                sample = list(cont_client.query_items(
                    query="SELECT TOP 3 * FROM c",
                    enable_cross_partition_query=True,
                ))
                for doc in sample:
                    keys = list(doc.keys())
                    print(f"      Sample keys: {keys}")
                    # Print a compact view
                    for k in keys[:8]:
                        v = doc[k]
                        if isinstance(v, str) and len(v) > 100:
                            v = v[:100] + "..."
                        elif isinstance(v, (dict, list)):
                            v = json.dumps(v)[:100] + "..."
                        print(f"        {k}: {v}")
                    if len(sample) > 1:
                        break  # One sample is enough
            except Exception as e:
                print(f"      Sample error: {str(e)[:100]}")


def inspect_storage_account():
    print("\n" + "=" * 60)
    print("PHASE 5b: INSPECT STORAGE ACCOUNT")
    print("=" * 60)

    from azure.storage.blob import BlobServiceClient

    cred = DefaultAzureCredential()
    blob_url = "https://stchubbmcppoc.blob.core.windows.net"
    client = BlobServiceClient(blob_url, credential=cred)

    print("\n  Listing blob containers:")
    containers = list(client.list_containers())
    if not containers:
        print("    (no containers found)")

    for cont in containers:
        cont_name = cont["name"]
        cont_client = client.get_container_client(cont_name)
        blobs = list(cont_client.list_blobs())
        print(f"\n    Container: {cont_name} ({len(blobs)} blobs)")
        for blob in blobs[:10]:
            print(f"      {blob.name} ({blob.size} bytes, {blob.content_settings.content_type})")
        if len(blobs) > 10:
            print(f"      ... and {len(blobs) - 10} more")


def inspect_key_vault():
    print("\n" + "=" * 60)
    print("PHASE 5c: INSPECT KEY VAULT")
    print("=" * 60)

    from azure.keyvault.secrets import SecretClient

    cred = DefaultAzureCredential()
    kv_url = "https://kv-chubb-mcp-9342.vault.azure.net"
    client = SecretClient(vault_url=kv_url, credential=cred)

    print("\n  Listing secrets:")
    for s in client.list_properties_of_secrets():
        print(f"    {s.name} (created: {s.created_on}, updated: {s.updated_on})")


def main():
    # Phase 3: Create agent
    client, agent = create_agent()

    # Phase 4: Run test conversations
    thread_ids, run_ids = run_test_conversations(client, agent)

    # Phase 5: Inspect backend stores
    inspect_cosmos_db()
    inspect_storage_account()
    inspect_key_vault()

    print("\n" + "=" * 60)
    print("ALL PHASES COMPLETE")
    print("=" * 60)
    print(f"  Agent: {agent.id} ({agent.name})")
    print(f"  Threads tested: {len(thread_ids)}")
    print(f"  Runs completed: {len(run_ids)}")
    print("  Backend inspection done - see output above")


if __name__ == "__main__":
    main()

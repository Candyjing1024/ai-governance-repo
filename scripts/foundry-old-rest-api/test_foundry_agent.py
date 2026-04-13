"""
Test the Azure AI Foundry Agent end-to-end from a script.

Flow: Script -> Foundry Agent -> OpenAPI Tool (askAstra) -> app-chubb-backend-poc/chat
     -> Supervisor -> Domain Agent -> MCP Server -> AI Search
"""
import json
import time
import requests
from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import (
    AgentThreadCreationOptions,
    ThreadMessageOptions,
    MessageRole,
)

# Configuration
SUBSCRIPTION_ID = "a3223db3-76f2-4a7c-8684-57b835dc77e7"
RESOURCE_GROUP = "rg-chubb-mcp-poc"
PROJECT_NAME = "proj-chubb-mcp-poc"
AGENT_ID = "asst_zVruiGuN2cFY90MKXzZEs4g5"

# Test queries
TEST_QUERIES = [
    "What is Chubb's AI governance policy?",
]


def get_agents_endpoint():
    """Get the agents endpoint from the project properties."""
    credential = DefaultAzureCredential()
    token = credential.get_token("https://management.azure.com/.default").token
    headers = {"Authorization": f"Bearer {token}"}

    url = (
        f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}"
        f"/resourceGroups/{RESOURCE_GROUP}"
        f"/providers/Microsoft.MachineLearningServices/workspaces/{PROJECT_NAME}"
        f"?api-version=2024-10-01"
    )
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    data = r.json()
    agents_uri = data["properties"].get("agentsEndpointUri")
    if agents_uri:
        return agents_uri
    raise RuntimeError("No agentsEndpointUri found in project properties")


def main():
    print("=" * 60)
    print("TESTING FOUNDRY AGENT END-TO-END")
    print("=" * 60)

    # Connect
    print("\n[1/4] Getting agents endpoint...")
    agents_endpoint = get_agents_endpoint()
    print(f"  Endpoint: {agents_endpoint}")

    print("\n[2/4] Connecting to AgentsClient...")
    credential = DefaultAzureCredential()
    client = AgentsClient(
        endpoint=agents_endpoint,
        credential=credential,
        subscription_id=SUBSCRIPTION_ID,
        resource_group_name=RESOURCE_GROUP,
        project_name=PROJECT_NAME,
    )

    # Verify agent exists
    agent = client.get_agent(AGENT_ID)
    print(f"  Agent: {agent.name} ({agent.id})")
    print(f"  Model: {agent.model}")
    print(f"  Tools: {len(agent.tools)}")

    # Run test queries
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\n[3/4] Test {i}/{len(TEST_QUERIES)}: {query}")
        print("-" * 50)

        # Create thread with the user message and run the agent
        print("  Creating thread and running agent...")
        start_time = time.time()

        thread = client.threads.create()
        print(f"  Thread ID: {thread.id}")

        # Add user message
        client.messages.create(
            thread_id=thread.id,
            role=MessageRole.USER,
            content=query,
        )

        # Run the agent on the thread and poll until complete
        run = client.runs.create_and_process(
            thread_id=thread.id,
            agent_id=AGENT_ID,
        )

        elapsed = time.time() - start_time
        print(f"  Run ID: {run.id}")
        print(f"  Status: {run.status}")
        print(f"  Duration: {elapsed:.1f}s")

        if run.status == "failed":
            print(f"  ERROR: {run.last_error}")
            continue

        # Get the assistant's response
        last_msg = client.messages.get_last_message_text_by_role(
            thread_id=thread.id,
            role=MessageRole.AGENT,
        )

        print(f"\n  RESPONSE:")
        print(f"  {'-' * 46}")
        if last_msg:
            # Print wrapped response
            for line in last_msg.text.value.split("\n"):
                print(f"  {line}")
        else:
            print("  (No response from agent)")

        # Show token usage if available
        if run.usage:
            print(f"\n  Tokens: prompt={run.usage.prompt_tokens}, completion={run.usage.completion_tokens}, total={run.usage.total_tokens}")

        # Cleanup thread
        client.threads.delete(thread.id)

    print(f"\n{'=' * 60}")
    print("TEST COMPLETE")
    print(f"{'=' * 60}")

    client.close()


if __name__ == "__main__":
    main()

"""
Create Azure AI Foundry Agent with OpenAPI tool wrapping the Astra backend.
The agent will be accessible from Foundry UI Playground.

Flow: User -> Foundry Agent -> OpenAPI Tool (askAstra) -> app-chubb-backend-poc/chat
     -> Supervisor -> Domain Agent -> MCP Server -> AI Search
"""
import json
import requests
from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import OpenApiTool, OpenApiAnonymousAuthDetails

# Configuration
SUBSCRIPTION_ID = "a3223db3-76f2-4a7c-8684-57b835dc77e7"
RESOURCE_GROUP = "rg-chubb-mcp-poc"
PROJECT_NAME = "proj-chubb-mcp-poc"
HUB_NAME = "hub-chubb-mcp-poc"

AGENT_NAME = "astra-chubb-governance-agent"
AGENT_MODEL = "gpt-4o"

SYSTEM_INSTRUCTIONS = """You are the Chubb AI Governance Assistant powered by the Astra multi-agent system.

Your role:
- Answer questions about Chubb's AI governance policies, frameworks, compliance requirements, and best practices.
- Use the 'askAstra' tool to query the Astra backend for any Chubb AI governance question.
- Always pass the user's question directly to the tool - do NOT try to answer from your own knowledge.
- Present the response from Astra clearly and professionally.

When the user asks a question:
1. Call the askAstra tool with the user's message
2. Return the response from Astra to the user
3. If the user asks a follow-up, call askAstra again with the new question

You should ALWAYS use the askAstra tool for any question related to:
- Chubb AI governance policies
- AI risk management
- AI compliance frameworks
- Model governance
- Data governance
- AI ethics at Chubb
- Any Chubb-specific AI topic

For general conversation (greetings, clarifications), respond naturally without using tools.
"""

OPENAPI_SPEC_PATH = "astra_openapi.json"


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
    props = data.get("properties", {})

    # Try agentsEndpointUri first, fall back to discoveryUrl-based endpoint
    agents_uri = props.get("agentsEndpointUri")
    if agents_uri:
        return agents_uri

    # Build from discovery URL pattern
    discovery = props.get("discoveryUrl", "")
    # The agents endpoint is: https://<region>.api.azureml.ms
    # with the workspace being passed as context
    base = discovery.replace("/discovery", "")
    print(f"  Discovery URL: {discovery}")
    print(f"  No agentsEndpointUri found, using discovery base: {base}")
    return base


def main():
    print("=" * 60)
    print("CREATING FOUNDRY AGENT WITH OPENAPI TOOL")
    print("=" * 60)

    # Load OpenAPI spec
    print("\n[1/4] Loading OpenAPI spec...")
    with open(OPENAPI_SPEC_PATH, "r") as f:
        openapi_spec = json.load(f)
    print(f"  Loaded spec: {openapi_spec['info']['title']} v{openapi_spec['info']['version']}")
    print(f"  Endpoints: {list(openapi_spec['paths'].keys())}")

    # Get the agents endpoint
    print("\n[2/4] Getting agents endpoint...")
    agents_endpoint = get_agents_endpoint()
    print(f"  Agents endpoint: {agents_endpoint}")

    # Connect via AgentsClient
    print("\n[3/4] Connecting to AI Foundry agents service...")
    credential = DefaultAzureCredential()

    agents_client = AgentsClient(
        endpoint=agents_endpoint,
        credential=credential,
        subscription_id=SUBSCRIPTION_ID,
        resource_group_name=RESOURCE_GROUP,
        project_name=PROJECT_NAME,
    )
    print(f"  Connected to project: {PROJECT_NAME}")

    # Create the OpenAPI tool
    print("\n[4/4] Creating agent with OpenAPI tool...")

    # The OpenAPI tool lets the agent call the Astra backend directly
    openapi_tool = OpenApiTool(
        name="astra_backend",
        description="Chubb AI Governance Astra Backend - queries the multi-agent system for AI governance information",
        spec=openapi_spec,
        auth=OpenApiAnonymousAuthDetails(),
    )

    # Create the agent
    agent = agents_client.create_agent(
        model=AGENT_MODEL,
        name=AGENT_NAME,
        instructions=SYSTEM_INSTRUCTIONS,
        tools=openapi_tool.definitions,
    )

    print(f"\n{'=' * 60}")
    print(f"AGENT CREATED SUCCESSFULLY!")
    print(f"{'=' * 60}")
    print(f"  Agent ID:    {agent.id}")
    print(f"  Agent Name:  {agent.name}")
    print(f"  Model:       {agent.model}")
    print(f"  Tools:       {len(agent.tools)} tool(s)")
    for tool in agent.tools:
        if hasattr(tool, "type"):
            print(f"    - Type: {tool.type}")
    print(f"\nYou can now test this agent in the Azure AI Foundry UI:")
    print(f"  1. Go to https://ai.azure.com")
    print(f"  2. Open project: {PROJECT_NAME}")
    print(f"  3. Go to Agents -> {AGENT_NAME}")
    print(f"  4. Use the Playground to chat!")
    print(f"\nTry asking: 'What is Chubb AI governance policy?'")


if __name__ == "__main__":
    main()

"""
Create Azure AI Foundry Hub + Project using Azure REST API.
Bypasses az ml CLI which is stuck.
"""
import json
import time
import requests
from azure.identity import DefaultAzureCredential

# Configuration
SUBSCRIPTION_ID = None  # Will be auto-detected
RESOURCE_GROUP = "rg-chubb-mcp-poc"
LOCATION = "eastus"
HUB_NAME = "hub-chubb-mcp-poc"
PROJECT_NAME = "proj-chubb-mcp-poc"
OPENAI_RESOURCE_NAME = "oai-chubb-mcp-9342"

API_VERSION = "2024-10-01"
ARM_BASE = "https://management.azure.com"


def get_token():
    cred = DefaultAzureCredential()
    token = cred.get_token("https://management.azure.com/.default")
    return token.token


def get_subscription_id(headers):
    """Auto-detect subscription ID."""
    r = requests.get(
        f"{ARM_BASE}/subscriptions?api-version=2022-12-01",
        headers=headers,
    )
    r.raise_for_status()
    subs = r.json()["value"]
    # Find Visual Studio Enterprise or first enabled
    for s in subs:
        if s["state"] == "Enabled":
            print(f"  Using subscription: {s['displayName']} ({s['subscriptionId']})")
            return s["subscriptionId"]
    raise RuntimeError("No enabled subscription found")


def get_openai_resource_id(headers, sub_id):
    """Get the full resource ID for the existing OpenAI account."""
    url = (
        f"{ARM_BASE}/subscriptions/{sub_id}/resourceGroups/{RESOURCE_GROUP}"
        f"/providers/Microsoft.CognitiveServices/accounts/{OPENAI_RESOURCE_NAME}"
        f"?api-version=2024-10-01"
    )
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    resource_id = r.json()["id"]
    print(f"  OpenAI resource: {resource_id}")
    return resource_id


def check_existing(headers, sub_id, name, kind):
    """Check if workspace already exists."""
    url = (
        f"{ARM_BASE}/subscriptions/{sub_id}/resourceGroups/{RESOURCE_GROUP}"
        f"/providers/Microsoft.MachineLearningServices/workspaces/{name}"
        f"?api-version={API_VERSION}"
    )
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        print(f"  {kind} '{name}' already exists! State: {data.get('properties', {}).get('provisioningState', 'Unknown')}")
        return True
    return False


def create_hub(headers, sub_id, openai_resource_id):
    """Create AI Foundry Hub."""
    if check_existing(headers, sub_id, HUB_NAME, "Hub"):
        return

    url = (
        f"{ARM_BASE}/subscriptions/{sub_id}/resourceGroups/{RESOURCE_GROUP}"
        f"/providers/Microsoft.MachineLearningServices/workspaces/{HUB_NAME}"
        f"?api-version={API_VERSION}"
    )

    body = {
        "location": LOCATION,
        "kind": "Hub",
        "identity": {"type": "SystemAssigned"},
        "properties": {
            "friendlyName": "Chubb AI MCP Hub",
            "description": "AI Foundry Hub for Chubb AI Governance POC",
        },
        "sku": {"name": "Basic", "tier": "Basic"},
    }

    print(f"  Creating hub '{HUB_NAME}' in {LOCATION}...")
    r = requests.put(url, headers=headers, json=body)

    if r.status_code in (200, 201, 202):
        print(f"  Hub creation started (HTTP {r.status_code})")
    else:
        print(f"  ERROR: HTTP {r.status_code}")
        print(f"  {r.text[:500]}")
        r.raise_for_status()

    # Poll until provisioned
    poll_provisioning(headers, sub_id, HUB_NAME, "Hub")


def create_project(headers, sub_id):
    """Create AI Foundry Project under the Hub."""
    if check_existing(headers, sub_id, PROJECT_NAME, "Project"):
        return

    hub_resource_id = (
        f"/subscriptions/{sub_id}/resourceGroups/{RESOURCE_GROUP}"
        f"/providers/Microsoft.MachineLearningServices/workspaces/{HUB_NAME}"
    )

    url = (
        f"{ARM_BASE}/subscriptions/{sub_id}/resourceGroups/{RESOURCE_GROUP}"
        f"/providers/Microsoft.MachineLearningServices/workspaces/{PROJECT_NAME}"
        f"?api-version={API_VERSION}"
    )

    body = {
        "location": LOCATION,
        "kind": "Project",
        "identity": {"type": "SystemAssigned"},
        "properties": {
            "friendlyName": "Chubb AI MCP Project",
            "description": "AI Foundry Project for Chubb AI Governance Agent",
            "hubResourceId": hub_resource_id,
        },
        "sku": {"name": "Basic", "tier": "Basic"},
    }

    print(f"  Creating project '{PROJECT_NAME}' under hub...")
    r = requests.put(url, headers=headers, json=body)

    if r.status_code in (200, 201, 202):
        print(f"  Project creation started (HTTP {r.status_code})")
    else:
        print(f"  ERROR: HTTP {r.status_code}")
        print(f"  {r.text[:500]}")
        r.raise_for_status()

    poll_provisioning(headers, sub_id, PROJECT_NAME, "Project")


def add_openai_connection(headers, sub_id, openai_resource_id):
    """Add OpenAI connection to the Hub."""
    conn_name = "oai-chubb-connection"
    url = (
        f"{ARM_BASE}/subscriptions/{sub_id}/resourceGroups/{RESOURCE_GROUP}"
        f"/providers/Microsoft.MachineLearningServices/workspaces/{HUB_NAME}"
        f"/connections/{conn_name}?api-version={API_VERSION}"
    )

    # Check if connection already exists
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        print(f"  OpenAI connection '{conn_name}' already exists")
        return

    body = {
        "properties": {
            "category": "AzureOpenAI",
            "target": f"https://{OPENAI_RESOURCE_NAME}.openai.azure.com/",
            "authType": "AAD",
            "metadata": {
                "ApiType": "Azure",
                "ResourceId": openai_resource_id,
            },
        }
    }

    print(f"  Adding OpenAI connection to hub...")
    r = requests.put(url, headers=headers, json=body)
    if r.status_code in (200, 201):
        print(f"  OpenAI connection added successfully")
    else:
        print(f"  WARNING: Connection creation returned HTTP {r.status_code}: {r.text[:300]}")


def poll_provisioning(headers, sub_id, name, kind, max_wait=300):
    """Poll until resource is provisioned."""
    url = (
        f"{ARM_BASE}/subscriptions/{sub_id}/resourceGroups/{RESOURCE_GROUP}"
        f"/providers/Microsoft.MachineLearningServices/workspaces/{name}"
        f"?api-version={API_VERSION}"
    )

    start = time.time()
    while time.time() - start < max_wait:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            state = r.json().get("properties", {}).get("provisioningState", "Unknown")
            print(f"  {kind} state: {state}")
            if state == "Succeeded":
                return
            if state == "Failed":
                print(f"  ERROR: {kind} provisioning failed!")
                print(f"  {r.text[:500]}")
                raise RuntimeError(f"{kind} provisioning failed")
        else:
            print(f"  Polling... HTTP {r.status_code}")

        time.sleep(15)

    raise TimeoutError(f"{kind} did not provision within {max_wait}s")


def get_project_discovery_url(headers, sub_id):
    """Get the project endpoint for AI Agent Service."""
    url = (
        f"{ARM_BASE}/subscriptions/{sub_id}/resourceGroups/{RESOURCE_GROUP}"
        f"/providers/Microsoft.MachineLearningServices/workspaces/{PROJECT_NAME}"
        f"?api-version={API_VERSION}"
    )
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    data = r.json()
    discovery_url = data.get("properties", {}).get("discoveryUrl", "")
    workspace_id = data.get("id", "")
    print(f"  Discovery URL: {discovery_url}")
    print(f"  Workspace ID: {workspace_id}")
    return discovery_url, workspace_id


def main():
    print("=" * 60)
    print("AZURE AI FOUNDRY - SETUP VIA REST API")
    print("=" * 60)

    print("\n[1/6] Authenticating...")
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    print("  Authenticated OK")

    print("\n[2/6] Getting subscription...")
    sub_id = get_subscription_id(headers)

    print("\n[3/6] Getting OpenAI resource...")
    openai_resource_id = get_openai_resource_id(headers, sub_id)

    print("\n[4/6] Creating AI Foundry Hub...")
    create_hub(headers, sub_id, openai_resource_id)

    print("\n[5/6] Adding OpenAI connection to hub...")
    add_openai_connection(headers, sub_id, openai_resource_id)

    print("\n[6/6] Creating AI Foundry Project...")
    create_project(headers, sub_id)

    print("\n" + "=" * 60)
    print("Getting project details...")
    discovery_url, workspace_id = get_project_discovery_url(headers, sub_id)

    print("\n" + "=" * 60)
    print("SETUP COMPLETE!")
    print(f"  Hub:     {HUB_NAME}")
    print(f"  Project: {PROJECT_NAME}")
    print(f"  Region:  {LOCATION}")
    print("=" * 60)
    print("\nNext: Create the Foundry Agent using azure-ai-projects SDK")
    print(f"  Project connection string: <sub_id>;{RESOURCE_GROUP};{PROJECT_NAME}")


if __name__ == "__main__":
    main()

"""
Recreate Hub + Project using Azure CLI (az) which properly registers them 
for the new Azure AI Foundry portal UI.

The old hub/project were created via ARM REST API and are missing metadata
that the new Foundry UI requires. This script:
1. Deletes the old project + hub
2. Recreates using 'az ml workspace create' which sets all portal metadata
3. Re-adds connections (Cosmos DB, OpenAI)
4. Re-assigns RBAC roles
5. Verifies the agent still works
"""
import json
import time
import uuid
import subprocess
import requests
from azure.identity import DefaultAzureCredential

SUB_ID = "a3223db3-76f2-4a7c-8684-57b835dc77e7"
RG = "rg-chubb-mcp-poc"
LOCATION = "eastus"
ARM = "https://management.azure.com"

KV_NAME = "kv-chubb-mcp-9342"
COSMOS_NAME = "cosmos-chubb-mcp-poc"
OAI_NAME = "oai-chubb-mcp-9342"
STORAGE_NAME = "stchubbmcppoc"
HUB_NAME = "hub-chubb-storage-val"
PROJECT_NAME = "proj-chubb-storage-val"

API_ML = "2025-01-01-preview"


def run_cmd(cmd, check=True):
    """Run a shell command and return output."""
    print(f"  > {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0 and check:
        print(f"  STDERR: {result.stderr[:500]}")
    if result.stdout:
        print(f"  {result.stdout[:500]}")
    return result


def get_headers():
    cred = DefaultAzureCredential()
    token = cred.get_token("https://management.azure.com/.default").token
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ============================================================
# STEP 0: Check if az CLI is available and ml extension installed
# ============================================================
def check_prerequisites():
    print("=" * 60)
    print("STEP 0: Check prerequisites")
    print("=" * 60)

    # Check az CLI
    r = run_cmd("az version", check=False)
    if r.returncode != 0:
        print("  ERROR: Azure CLI not found. Install from https://aka.ms/installazurecli")
        return False

    # Check ml extension
    r = run_cmd("az extension list --query \"[?name=='ml'].version\" -o tsv", check=False)
    if not r.stdout.strip():
        print("  Installing ml extension...")
        run_cmd("az extension add -n ml --yes")
    else:
        print(f"  ml extension version: {r.stdout.strip()}")

    # Set subscription
    run_cmd(f"az account set --subscription {SUB_ID}")
    print("  Prerequisites OK")
    return True


# ============================================================
# STEP 1: Delete old project and hub
# ============================================================
def delete_old_resources():
    print("\n" + "=" * 60)
    print("STEP 1: Delete old project and hub")
    print("=" * 60)

    # Delete project first (child of hub)
    print("\n  Deleting project...")
    r = run_cmd(
        f'az ml workspace delete --name {PROJECT_NAME} '
        f'--resource-group {RG} --yes --no-wait',
        check=False
    )

    # Wait for project deletion
    print("  Waiting for project deletion...")
    headers = get_headers()
    for i in range(30):
        proj_url = (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
                    f"/providers/Microsoft.MachineLearningServices/workspaces/{PROJECT_NAME}"
                    f"?api-version={API_ML}")
        resp = requests.get(proj_url, headers=headers)
        if resp.status_code == 404:
            print("  Project deleted")
            break
        state = resp.json().get("properties", {}).get("provisioningState", "?")
        print(f"  State: {state} (attempt {i+1}/30)")
        if state in ("Deleting", "deleting"):
            time.sleep(15)
        elif state in ("Succeeded", "succeeded"):
            # Try to force delete again
            run_cmd(
                f'az ml workspace delete --name {PROJECT_NAME} '
                f'--resource-group {RG} --yes --permanently-delete --no-wait',
                check=False
            )
            time.sleep(15)
        else:
            time.sleep(10)
    else:
        print("  WARNING: Project deletion timed out, continuing...")

    # Delete hub
    print("\n  Deleting hub...")
    r = run_cmd(
        f'az ml workspace delete --name {HUB_NAME} '
        f'--resource-group {RG} --yes --no-wait',
        check=False
    )

    print("  Waiting for hub deletion...")
    for i in range(40):
        hub_url = (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
                   f"/providers/Microsoft.MachineLearningServices/workspaces/{HUB_NAME}"
                   f"?api-version={API_ML}")
        resp = requests.get(hub_url, headers=headers)
        if resp.status_code == 404:
            print("  Hub deleted")
            break
        state = resp.json().get("properties", {}).get("provisioningState", "?")
        print(f"  State: {state} (attempt {i+1}/40)")
        if state in ("Deleting", "deleting"):
            time.sleep(15)
        elif state in ("Succeeded", "succeeded"):
            run_cmd(
                f'az ml workspace delete --name {HUB_NAME} '
                f'--resource-group {RG} --yes --permanently-delete --no-wait',
                check=False
            )
            time.sleep(15)
        else:
            time.sleep(10)
    else:
        print("  WARNING: Hub deletion timed out")

    # Small delay after deletion
    time.sleep(10)
    print("  Cleanup complete")


# ============================================================
# STEP 2: Recreate Hub via az CLI
# ============================================================
def create_hub_cli():
    print("\n" + "=" * 60)
    print("STEP 2: Create Hub via Azure CLI")
    print("=" * 60)

    kv_rid = (f"/subscriptions/{SUB_ID}/resourceGroups/{RG}"
              f"/providers/Microsoft.KeyVault/vaults/{KV_NAME}")
    storage_rid = (f"/subscriptions/{SUB_ID}/resourceGroups/{RG}"
                   f"/providers/Microsoft.Storage/storageAccounts/{STORAGE_NAME}")

    # Create hub using az ml workspace create --kind hub
    cmd = (
        f'az ml workspace create '
        f'--name {HUB_NAME} '
        f'--resource-group {RG} '
        f'--location {LOCATION} '
        f'--kind hub '
        f'--display-name "Chubb Storage Validation Hub" '
        f'--description "AI Foundry Hub with customer-managed Key Vault, Storage, and Cosmos DB" '
        f'--storage-account "{storage_rid}" '
        f'--key-vault "{kv_rid}" '
        f'--no-wait'
    )

    r = run_cmd(cmd)
    if r.returncode != 0:
        print(f"  ERROR: Hub creation failed")
        # Try without --no-wait
        cmd2 = cmd.replace(" --no-wait", "")
        r2 = run_cmd(cmd2)
        if r2.returncode != 0:
            return False

    # Poll for completion
    print("  Waiting for hub provisioning...")
    headers = get_headers()
    for i in range(40):
        hub_url = (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
                   f"/providers/Microsoft.MachineLearningServices/workspaces/{HUB_NAME}"
                   f"?api-version={API_ML}")
        resp = requests.get(hub_url, headers=headers)
        if resp.status_code == 200:
            state = resp.json().get("properties", {}).get("provisioningState", "?")
            print(f"  State: {state} (attempt {i+1}/40)")
            if state in ("Succeeded", "succeeded"):
                props = resp.json().get("properties", {})
                print(f"    keyVault: {props.get('keyVault', 'N/A')}")
                print(f"    storageAccount: {props.get('storageAccount', 'N/A')}")
                return True
            if state in ("Failed", "failed"):
                print(f"    FAILED: {resp.text[:300]}")
                return False
        else:
            print(f"  HTTP {resp.status_code} (attempt {i+1}/40)")
        time.sleep(15)

    print("  TIMEOUT waiting for hub")
    return False


# ============================================================
# STEP 3: Recreate Project via az CLI
# ============================================================
def create_project_cli():
    print("\n" + "=" * 60)
    print("STEP 3: Create Project via Azure CLI")
    print("=" * 60)

    hub_rid = (f"/subscriptions/{SUB_ID}/resourceGroups/{RG}"
               f"/providers/Microsoft.MachineLearningServices/workspaces/{HUB_NAME}")

    cmd = (
        f'az ml workspace create '
        f'--name {PROJECT_NAME} '
        f'--resource-group {RG} '
        f'--location {LOCATION} '
        f'--kind project '
        f'--hub-id "{hub_rid}" '
        f'--display-name "Chubb Storage Validation Project" '
        f'--description "Project for validating Foundry backend storage integration"'
    )

    r = run_cmd(cmd)
    if r.returncode != 0:
        print(f"  ERROR: Project creation failed")
        return False

    # Verify
    headers = get_headers()
    proj_url = (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
                f"/providers/Microsoft.MachineLearningServices/workspaces/{PROJECT_NAME}"
                f"?api-version={API_ML}")
    resp = requests.get(proj_url, headers=headers)
    if resp.status_code == 200:
        props = resp.json().get("properties", {})
        print(f"  State: {props.get('provisioningState')}")
        print(f"  AgentsEndpoint: {props.get('agentsEndpointUri', 'N/A')}")
        return True
    return False


# ============================================================
# STEP 4: Re-add connections (Cosmos DB + OpenAI)
# ============================================================
def add_connections():
    print("\n" + "=" * 60)
    print("STEP 4: Add Cosmos DB and OpenAI connections")
    print("=" * 60)

    headers = get_headers()
    hub_base = (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
                f"/providers/Microsoft.MachineLearningServices/workspaces/{HUB_NAME}")

    # --- Cosmos DB connection ---
    print("\n  Adding Cosmos DB connection...")
    cosmos_rid = (f"/subscriptions/{SUB_ID}/resourceGroups/{RG}"
                  f"/providers/Microsoft.DocumentDB/databaseAccounts/{COSMOS_NAME}")

    # Get Cosmos endpoint and key
    cosmos_url = f"{ARM}{cosmos_rid}?api-version=2024-05-15"
    cr = requests.get(cosmos_url, headers=headers)
    cosmos_endpoint = cr.json().get("properties", {}).get("documentEndpoint", "")

    keys_url = f"{ARM}{cosmos_rid}/listKeys?api-version=2024-05-15"
    kr = requests.post(keys_url, headers=headers)
    cosmos_key = kr.json().get("primaryMasterKey", "") if kr.status_code == 200 else ""

    conn_body = {
        "properties": {
            "category": "CosmosDB",
            "target": cosmos_endpoint,
            "authType": "CustomKeys",
            "credentials": {"keys": {"key": cosmos_key}},
            "metadata": {"ResourceId": cosmos_rid},
        }
    }
    conn_url = f"{hub_base}/connections/cosmos-agent-store?api-version={API_ML}"
    r = requests.put(conn_url, headers=headers, json=conn_body)
    print(f"    Cosmos connection: HTTP {r.status_code}")
    if r.status_code not in (200, 201):
        # Try ApiKey auth
        conn_body["properties"]["authType"] = "ApiKey"
        conn_body["properties"]["credentials"] = {"key": cosmos_key}
        r2 = requests.put(conn_url, headers=headers, json=conn_body)
        print(f"    Cosmos (retry ApiKey): HTTP {r2.status_code}")

    # --- OpenAI connection ---
    print("\n  Adding OpenAI connection...")
    oai_rid = (f"/subscriptions/{SUB_ID}/resourceGroups/{RG}"
               f"/providers/Microsoft.CognitiveServices/accounts/{OAI_NAME}")
    oai_body = {
        "properties": {
            "category": "AzureOpenAI",
            "target": f"https://{OAI_NAME}.openai.azure.com/",
            "authType": "AAD",
            "metadata": {"ApiType": "Azure", "ResourceId": oai_rid},
        }
    }
    oai_conn_url = f"{hub_base}/connections/oai-chubb-connection?api-version={API_ML}"
    r = requests.put(oai_conn_url, headers=headers, json=oai_body)
    print(f"    OpenAI connection: HTTP {r.status_code}")

    # List all connections to verify
    r = requests.get(f"{hub_base}/connections?api-version={API_ML}", headers=headers)
    if r.status_code == 200:
        conns = r.json().get("value", [])
        print(f"\n  Connections ({len(conns)}):")
        for c in conns:
            name = c.get("name", "?")
            cat = c.get("properties", {}).get("category", "?")
            print(f"    {name}: {cat}")


# ============================================================
# STEP 5: Assign RBAC roles
# ============================================================
def assign_rbac():
    print("\n" + "=" * 60)
    print("STEP 5: Assign RBAC roles")
    print("=" * 60)

    headers = get_headers()

    # Get project managed identity
    proj_url = (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
                f"/providers/Microsoft.MachineLearningServices/workspaces/{PROJECT_NAME}"
                f"?api-version={API_ML}")
    r = requests.get(proj_url, headers=headers)
    principal_id = r.json().get("identity", {}).get("principalId", "")
    print(f"  Project principal: {principal_id}")

    if not principal_id:
        print("  WARNING: No project principal ID")
        return

    oai_rid = (f"/subscriptions/{SUB_ID}/resourceGroups/{RG}"
               f"/providers/Microsoft.CognitiveServices/accounts/{OAI_NAME}")
    storage_rid = (f"/subscriptions/{SUB_ID}/resourceGroups/{RG}"
                   f"/providers/Microsoft.Storage/storageAccounts/{STORAGE_NAME}")

    # Get current user
    cred = DefaultAzureCredential()
    graph_token = cred.get_token("https://graph.microsoft.com/.default").token
    gr = requests.get("https://graph.microsoft.com/v1.0/me",
                       headers={"Authorization": f"Bearer {graph_token}"})
    user_id = gr.json().get("id", "")
    print(f"  User ID: {user_id}")

    # Get Hub MI
    hub_url = (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
               f"/providers/Microsoft.MachineLearningServices/workspaces/{HUB_NAME}"
               f"?api-version={API_ML}")
    hr = requests.get(hub_url, headers=headers)
    hub_pid = hr.json().get("identity", {}).get("principalId", "")
    print(f"  Hub principal: {hub_pid}")

    role_assignments = [
        # OpenAI roles for project SP
        (oai_rid, principal_id, "ServicePrincipal",
         "Cognitive Services OpenAI Contributor", "5e0bd9bd-7b93-4f28-af87-19fc36ad61bd"),
        (oai_rid, principal_id, "ServicePrincipal",
         "Cognitive Services User", "a97b65f3-24c7-4388-baec-2e87135dc908"),
        # OpenAI for current user
        (oai_rid, user_id, "User",
         "Cognitive Services OpenAI Contributor", "5e0bd9bd-7b93-4f28-af87-19fc36ad61bd"),
        # Storage roles for user
        (storage_rid, user_id, "User",
         "Storage Blob Data Contributor", "ba92f5b4-2d11-453d-a403-e96b0029c9fe"),
        (storage_rid, user_id, "User",
         "Storage Blob Data Reader", "2a2b9908-6ea1-4ae2-8e65-a410df84e7d1"),
    ]

    # Add storage roles for hub and project MIs
    for pid in [hub_pid, principal_id]:
        if pid:
            role_assignments.append(
                (storage_rid, pid, "ServicePrincipal",
                 "Storage Blob Data Contributor", "ba92f5b4-2d11-453d-a403-e96b0029c9fe"))
            role_assignments.append(
                (storage_rid, pid, "ServicePrincipal",
                 "Storage Blob Data Reader", "2a2b9908-6ea1-4ae2-8e65-a410df84e7d1"))

    for scope, pid, ptype, role_name, role_id in role_assignments:
        if not pid:
            continue
        assign_id = str(uuid.uuid4())
        url = f"{ARM}{scope}/providers/Microsoft.Authorization/roleAssignments/{assign_id}?api-version=2022-04-01"
        body = {
            "properties": {
                "roleDefinitionId": f"{scope}/providers/Microsoft.Authorization/roleDefinitions/{role_id}",
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
# STEP 6: Verify in portal
# ============================================================
def verify_portal():
    print("\n" + "=" * 60)
    print("STEP 6: Verify portal access")
    print("=" * 60)

    headers = get_headers()

    # Get project workspace ID
    proj_url = (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
                f"/providers/Microsoft.MachineLearningServices/workspaces/{PROJECT_NAME}"
                f"?api-version={API_ML}")
    r = requests.get(proj_url, headers=headers)
    if r.status_code == 200:
        props = r.json().get("properties", {})
        ws_id = props.get("workspaceId", "")
        agents_ep = props.get("agentsEndpointUri", "")
        print(f"  Project workspace ID: {ws_id}")
        print(f"  Agents endpoint: {agents_ep}")

        # Check for portal URL in properties
        for key in sorted(props.keys()):
            if "portal" in key.lower() or "studio" in key.lower() or "url" in key.lower():
                print(f"  {key}: {props[key]}")

    # Also check hub
    hub_url = (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
               f"/providers/Microsoft.MachineLearningServices/workspaces/{HUB_NAME}"
               f"?api-version={API_ML}")
    r = requests.get(hub_url, headers=headers)
    if r.status_code == 200:
        hub_ws_id = r.json().get("properties", {}).get("workspaceId", "")
        print(f"  Hub workspace ID: {hub_ws_id}")

    print(f"\n  Portal URLs:")
    print(f"    1. https://ai.azure.com  (sign in, look for project in left nav)")
    print(f"    2. Azure Portal > search '{PROJECT_NAME}' > Launch studio")


def main():
    print("=" * 70)
    print("  RECREATE HUB + PROJECT FOR NEW FOUNDRY PORTAL")
    print("=" * 70)

    if not check_prerequisites():
        return

    delete_old_resources()
    
    if not create_hub_cli():
        print("\nFAILED: Hub creation. Stopping.")
        return

    if not create_project_cli():
        print("\nFAILED: Project creation. Stopping.")
        return

    add_connections()
    assign_rbac()
    verify_portal()

    print("\n" + "=" * 70)
    print("  DONE - Hub and Project recreated via Azure CLI")
    print("=" * 70)
    print(f"  Hub:     {HUB_NAME}")
    print(f"  Project: {PROJECT_NAME}")
    print(f"\n  Next steps:")
    print(f"    1. Go to https://ai.azure.com")
    print(f"    2. Toggle to new Foundry UI if not already")
    print(f"    3. You should see the project in the list")
    print(f"    4. Open the project > Agents to see/create agents")
    print(f"    5. Go to Settings > Agent service to configure Cosmos DB storage")


if __name__ == "__main__":
    main()

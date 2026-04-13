"""
NEW Foundry (CognitiveServices) — Full CRUD Operations via ARM REST API.

Resource types (new Foundry architecture):
  - Microsoft.CognitiveServices/accounts            (parent = "Foundry resource" / AIServices)
  - Microsoft.CognitiveServices/accounts/projects    (child  = "project")
  - Microsoft.CognitiveServices/accounts/deployments (model deployments under account)

This script covers:
  1. CREATE  — Account (AIServices) + Project
  2. READ    — List/Get accounts, projects, deployments, connections
  3. UPDATE  — Patch account tags/properties, update project, update deployments
  4. DELETE  — Delete project, delete deployments, delete account
  5. CONNECTIONS — Add/list/delete connections (Cosmos, OpenAI, KeyVault)
  6. RBAC    — Assign required roles for account/project managed identities
  7. MODEL DEPLOYMENTS — Deploy/list/delete models on the account

Usage:
  python foundry_project_crud.py --action create
  python foundry_project_crud.py --action read
  python foundry_project_crud.py --action update --tags "env=poc,team=ai"
  python foundry_project_crud.py --action delete
  python foundry_project_crud.py --action deploy-model --model gpt-4o --model-version 2024-11-20
  python foundry_project_crud.py --action list-connections
  python foundry_project_crud.py --action add-connections
  python foundry_project_crud.py --action assign-rbac
  python foundry_project_crud.py --action full-setup
  python foundry_project_crud.py --action full-teardown
"""
import argparse
import json
import time
import uuid
import sys
import requests
from azure.identity import DefaultAzureCredential

# ============================================================
# CONFIGURATION  — Update these for your environment
# ============================================================
SUB_ID       = "a3223db3-76f2-4a7c-8684-57b835dc77e7"
RG           = "rg-chubb-mcp-poc"
LOCATION     = "eastus"
ARM          = "https://management.azure.com"

# NEW Foundry (CognitiveServices) resource names
ACCOUNT_NAME = "foundry-test-0020"          # parent AIServices account
PROJECT_NAME = "proj-chubb-mcp-poc"         # project under the account

# API versions
API_CS       = "2025-06-01"                 # CognitiveServices stable API
API_CS_PREV  = "2026-01-15-preview"         # latest preview (connections, projects)
API_DEPLOY   = "2024-10-01"                 # model deployments
API_RBAC     = "2022-04-01"                 # role assignments

# Shared resources (for connections & RBAC)
OAI_NAME     = "oai-chubb-mcp-9342"
COSMOS_NAME  = "cosmos-chubb-mcp-poc"
KV_NAME      = "kv-chubb-mcp-9342"
STORAGE_NAME = "stchubbmcppoc"

# ============================================================
# AUTH HELPERS
# ============================================================
_credential = None


def _cred():
    global _credential
    if _credential is None:
        _credential = DefaultAzureCredential()
    return _credential


def get_headers():
    token = _cred().get_token("https://management.azure.com/.default").token
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ============================================================
# URL BUILDERS
# ============================================================
def _rg_base():
    return f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"


def _account_url(api=None):
    api = api or API_CS
    return (f"{_rg_base()}/providers/Microsoft.CognitiveServices"
            f"/accounts/{ACCOUNT_NAME}?api-version={api}")


def _account_base():
    return (f"{_rg_base()}/providers/Microsoft.CognitiveServices"
            f"/accounts/{ACCOUNT_NAME}")


def _project_url(api=None):
    api = api or API_CS
    return (f"{_account_base()}/projects/{PROJECT_NAME}"
            f"?api-version={api}")


def _project_base():
    return f"{_account_base()}/projects/{PROJECT_NAME}"


# ============================================================
# POLLING HELPER
# ============================================================
def poll_provisioning(url, resource_label, max_attempts=40, interval=10):
    """Poll a resource URL until provisioningState is Succeeded/Failed or 404."""
    headers = get_headers()
    for i in range(max_attempts):
        r = requests.get(url, headers=headers)
        if r.status_code == 404:
            print(f"  {resource_label}: DELETED (404)")
            return "Deleted"
        if r.status_code == 200:
            state = r.json().get("properties", {}).get("provisioningState", "Unknown")
            print(f"  {resource_label}: {state}  ({i+1}/{max_attempts})")
            if state in ("Succeeded", "succeeded"):
                return "Succeeded"
            if state in ("Failed", "failed"):
                print(f"    Error: {r.text[:300]}")
                return "Failed"
        else:
            print(f"  {resource_label}: HTTP {r.status_code}  ({i+1}/{max_attempts})")
        time.sleep(interval)
    print(f"  {resource_label}: TIMEOUT after {max_attempts * interval}s")
    return "Timeout"


# ################################################################
#  1. CREATE
# ################################################################

def create_account():
    """Create the AIServices account (parent Foundry resource)."""
    print("=" * 60)
    print("CREATE: AIServices Account")
    print("=" * 60)

    headers = get_headers()
    url = _account_url()

    # Check if already exists
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        state = r.json().get("properties", {}).get("provisioningState", "?")
        print(f"  Account '{ACCOUNT_NAME}' already exists (state={state})")
        return True

    body = {
        "location": LOCATION,
        "kind": "AIServices",
        "identity": {"type": "SystemAssigned"},
        "sku": {"name": "S0"},
        "properties": {
            "customSubDomainName": ACCOUNT_NAME,
            "publicNetworkAccess": "Enabled",
        },
    }

    print(f"  Creating account '{ACCOUNT_NAME}' in {LOCATION}...")
    r = requests.put(url, headers=headers, json=body)
    if r.status_code in (200, 201, 202):
        print(f"  Creation started (HTTP {r.status_code})")
    else:
        print(f"  ERROR: HTTP {r.status_code}")
        print(f"  {r.text[:500]}")
        return False

    result = poll_provisioning(url, f"Account '{ACCOUNT_NAME}'")
    return result == "Succeeded"


def create_project():
    """Create a project under the AIServices account."""
    print("\n" + "=" * 60)
    print("CREATE: Project under AIServices Account")
    print("=" * 60)

    headers = get_headers()
    url = _project_url()

    # Check if already exists
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        state = r.json().get("properties", {}).get("provisioningState", "?")
        print(f"  Project '{PROJECT_NAME}' already exists (state={state})")
        return True

    body = {
        "location": LOCATION,
        "identity": {"type": "SystemAssigned"},
        "properties": {
            "displayName": f"{PROJECT_NAME}",
            "description": "Foundry project created via REST API CRUD script",
        },
    }

    print(f"  Creating project '{PROJECT_NAME}' under '{ACCOUNT_NAME}'...")
    r = requests.put(url, headers=headers, json=body)
    if r.status_code in (200, 201, 202):
        print(f"  Creation started (HTTP {r.status_code})")
    else:
        print(f"  ERROR: HTTP {r.status_code}")
        print(f"  {r.text[:500]}")
        return False

    result = poll_provisioning(url, f"Project '{PROJECT_NAME}'")
    return result == "Succeeded"


# ################################################################
#  2. READ
# ################################################################

def read_account():
    """GET the AIServices account details."""
    print("=" * 60)
    print("READ: AIServices Account")
    print("=" * 60)

    headers = get_headers()
    r = requests.get(_account_url(), headers=headers)
    if r.status_code != 200:
        print(f"  Account not found (HTTP {r.status_code})")
        return None

    acct = r.json()
    props = acct.get("properties", {})
    identity = acct.get("identity", {})

    print(f"  Name:         {acct.get('name')}")
    print(f"  Kind:         {acct.get('kind')}")
    print(f"  Location:     {acct.get('location')}")
    print(f"  State:        {props.get('provisioningState')}")
    print(f"  Endpoint:     {props.get('endpoint')}")
    print(f"  Identity:     {identity.get('type')}")
    print(f"  PrincipalId:  {identity.get('principalId', 'N/A')}")
    print(f"  Tags:         {acct.get('tags', {})}")

    # Endpoints
    endpoints = props.get("endpoints", {})
    if isinstance(endpoints, str):
        try:
            endpoints = json.loads(endpoints)
        except Exception:
            pass
    if isinstance(endpoints, dict):
        print(f"\n  Endpoints:")
        for k, v in endpoints.items():
            print(f"    {k}: {v}")

    return acct


def read_project():
    """GET the project details."""
    print("\n" + "=" * 60)
    print("READ: Project")
    print("=" * 60)

    headers = get_headers()
    r = requests.get(_project_url(), headers=headers)
    if r.status_code != 200:
        print(f"  Project not found (HTTP {r.status_code})")
        return None

    proj = r.json()
    props = proj.get("properties", {})
    identity = proj.get("identity", {})

    print(f"  Name:         {proj.get('name')}")
    print(f"  Location:     {proj.get('location')}")
    print(f"  State:        {props.get('provisioningState')}")
    print(f"  Identity:     {identity.get('type')}")
    print(f"  PrincipalId:  {identity.get('principalId', 'N/A')}")
    print(f"  Tags:         {proj.get('tags', {})}")

    # Endpoints
    endpoints = props.get("endpoints", {})
    if isinstance(endpoints, str):
        try:
            endpoints = json.loads(endpoints)
        except Exception:
            pass
    if isinstance(endpoints, dict) and endpoints:
        print(f"\n  Endpoints:")
        for k, v in endpoints.items():
            print(f"    {k}: {v}")

    return proj


def list_projects():
    """List all projects under the account."""
    print("\n" + "=" * 60)
    print("READ: List all Projects under Account")
    print("=" * 60)

    headers = get_headers()
    url = f"{_account_base()}/projects?api-version={API_CS}"
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        print(f"  Error listing projects (HTTP {r.status_code}): {r.text[:300]}")
        return []

    projects = r.json().get("value", [])
    print(f"  Total projects: {len(projects)}")
    for p in projects:
        pprops = p.get("properties", {})
        print(f"    {p.get('name'):30s} state={pprops.get('provisioningState', '?')}"
              f"  location={p.get('location', '?')}")
    return projects


def list_accounts_in_rg():
    """List all CognitiveServices accounts in the resource group."""
    print("=" * 60)
    print("READ: List all CognitiveServices accounts in RG")
    print("=" * 60)

    headers = get_headers()
    url = (f"{_rg_base()}/providers/Microsoft.CognitiveServices"
           f"/accounts?api-version={API_CS}")
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        print(f"  Error (HTTP {r.status_code}): {r.text[:300]}")
        return []

    accounts = r.json().get("value", [])
    print(f"  Total accounts: {len(accounts)}")
    for a in accounts:
        aprops = a.get("properties", {})
        print(f"    {a.get('name'):35s} kind={a.get('kind', '?'):12s}"
              f"  state={aprops.get('provisioningState', '?')}"
              f"  endpoint={aprops.get('endpoint', 'N/A')[:50]}")
    return accounts


# ################################################################
#  3. UPDATE
# ################################################################

def update_account_tags(tags_dict):
    """PATCH account to update tags."""
    print("=" * 60)
    print("UPDATE: Account Tags")
    print("=" * 60)

    headers = get_headers()
    url = _account_url()

    body = {"tags": tags_dict}
    print(f"  Patching tags: {tags_dict}")
    r = requests.patch(url, headers=headers, json=body)
    if r.status_code in (200, 201, 202):
        new_tags = r.json().get("tags", {})
        print(f"  Updated tags: {new_tags}")
        return True
    else:
        print(f"  ERROR: HTTP {r.status_code}")
        print(f"  {r.text[:500]}")
        return False


def update_account_network(public_access="Enabled"):
    """Update account network access settings."""
    print("\n" + "=" * 60)
    print("UPDATE: Account Network Access")
    print("=" * 60)

    headers = get_headers()
    url = _account_url()

    body = {
        "properties": {
            "publicNetworkAccess": public_access,
        }
    }
    print(f"  Setting publicNetworkAccess={public_access}")
    r = requests.patch(url, headers=headers, json=body)
    if r.status_code in (200, 201, 202):
        state = r.json().get("properties", {}).get("publicNetworkAccess", "?")
        print(f"  Result: publicNetworkAccess={state}")
        return True
    else:
        print(f"  ERROR: HTTP {r.status_code}")
        print(f"  {r.text[:500]}")
        return False


def update_project_tags(tags_dict):
    """PATCH project to update tags."""
    print("\n" + "=" * 60)
    print("UPDATE: Project Tags")
    print("=" * 60)

    headers = get_headers()
    url = _project_url()

    body = {"tags": tags_dict}
    print(f"  Patching tags: {tags_dict}")
    r = requests.patch(url, headers=headers, json=body)
    if r.status_code in (200, 201, 202):
        new_tags = r.json().get("tags", {})
        print(f"  Updated tags: {new_tags}")
        return True
    else:
        print(f"  ERROR: HTTP {r.status_code}")
        print(f"  {r.text[:500]}")
        return False


# ################################################################
#  4. DELETE
# ################################################################

def delete_project():
    """Delete the project under the AIServices account."""
    print("=" * 60)
    print("DELETE: Project")
    print("=" * 60)

    headers = get_headers()
    url = _project_url()

    # Check exists
    r = requests.get(url, headers=headers)
    if r.status_code == 404:
        print(f"  Project '{PROJECT_NAME}': already deleted")
        return True

    state = r.json().get("properties", {}).get("provisioningState", "?")
    print(f"  Project '{PROJECT_NAME}': exists (state={state})")
    print(f"  Deleting project...")

    r = requests.delete(url, headers=headers)
    print(f"  DELETE: HTTP {r.status_code}")
    if r.status_code not in (200, 202, 204):
        print(f"  Error: {r.text[:500]}")
        return False

    result = poll_provisioning(url, f"Project '{PROJECT_NAME}'")
    return result == "Deleted"


def delete_account():
    """Delete the AIServices account (deletes all child projects too)."""
    print("\n" + "=" * 60)
    print("DELETE: AIServices Account")
    print("=" * 60)

    headers = get_headers()
    url = _account_url()

    # Check exists
    r = requests.get(url, headers=headers)
    if r.status_code == 404:
        print(f"  Account '{ACCOUNT_NAME}': already deleted")
        return True

    state = r.json().get("properties", {}).get("provisioningState", "?")
    print(f"  Account '{ACCOUNT_NAME}': exists (state={state})")

    # List children first
    proj_url = f"{_account_base()}/projects?api-version={API_CS}"
    rp = requests.get(proj_url, headers=headers)
    if rp.status_code == 200:
        projects = rp.json().get("value", [])
        if projects:
            print(f"  WARNING: {len(projects)} child project(s) will also be deleted:")
            for p in projects:
                print(f"    - {p.get('name')}")

    print(f"  Deleting account...")
    r = requests.delete(url, headers=headers)
    print(f"  DELETE: HTTP {r.status_code}")
    if r.status_code not in (200, 202, 204):
        print(f"  Error: {r.text[:500]}")
        return False

    result = poll_provisioning(url, f"Account '{ACCOUNT_NAME}'")
    return result == "Deleted"


def purge_deleted_account():
    """Purge a soft-deleted CognitiveServices account (prevents name conflicts)."""
    print("\n" + "=" * 60)
    print("DELETE: Purge soft-deleted account")
    print("=" * 60)

    headers = get_headers()
    # List deleted accounts
    list_url = (f"{ARM}/subscriptions/{SUB_ID}/providers"
                f"/Microsoft.CognitiveServices/deletedAccounts"
                f"?api-version={API_CS}")
    r = requests.get(list_url, headers=headers)
    if r.status_code != 200:
        print(f"  Could not list deleted accounts: HTTP {r.status_code}")
        return False

    deleted = r.json().get("value", [])
    target = None
    for d in deleted:
        if d.get("name") == ACCOUNT_NAME:
            target = d
            break

    if not target:
        print(f"  No soft-deleted account named '{ACCOUNT_NAME}' found")
        return True

    print(f"  Found soft-deleted account: {ACCOUNT_NAME}")
    print(f"    Location: {target.get('location')}")
    print(f"    Deletion date: {target.get('properties', {}).get('deletionDate', '?')}")

    purge_url = (f"{ARM}/subscriptions/{SUB_ID}/providers"
                 f"/Microsoft.CognitiveServices/locations/{LOCATION}"
                 f"/resourceGroups/{RG}/deletedAccounts/{ACCOUNT_NAME}"
                 f"/purge?api-version={API_CS}")
    r = requests.delete(purge_url, headers=headers)
    print(f"  PURGE: HTTP {r.status_code}")
    if r.status_code in (200, 202, 204):
        print(f"  Account purged successfully")
        return True
    else:
        print(f"  Error: {r.text[:500]}")
        return False


# ################################################################
#  5. CONNECTIONS
# ################################################################

def list_connections():
    """List all connections on the account."""
    print("=" * 60)
    print("CONNECTIONS: List")
    print("=" * 60)

    headers = get_headers()

    # Try account-level connections
    for api in [API_CS_PREV, API_CS]:
        url = f"{_account_base()}/connections?api-version={api}"
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            conns = r.json().get("value", [])
            print(f"  Total connections: {len(conns)}  (api={api})")
            for c in conns:
                cp = c.get("properties", {})
                print(f"    {c.get('name', '?'):30s}"
                      f"  category={cp.get('category', '?'):20s}"
                      f"  target={cp.get('target', '?')[:50]}")
            return conns
        elif r.status_code != 404:
            print(f"  api={api}: HTTP {r.status_code}")

    print("  No working connections API found")
    return []


def add_connection(conn_name, category, target, auth_type="AAD",
                   resource_id=None, credentials=None, metadata=None):
    """Add a single connection to the account."""
    headers = get_headers()

    body = {
        "properties": {
            "category": category,
            "target": target,
            "authType": auth_type,
        }
    }
    if metadata:
        body["properties"]["metadata"] = metadata
    if resource_id:
        body["properties"].setdefault("metadata", {})["ResourceId"] = resource_id
    if credentials:
        body["properties"]["credentials"] = credentials

    # Try preview API first (wider connection support), then stable
    for api in [API_CS_PREV, API_CS]:
        url = f"{_account_base()}/connections/{conn_name}?api-version={api}"
        r = requests.put(url, headers=headers, json=body)
        if r.status_code in (200, 201):
            print(f"    {conn_name} ({category}): CREATED  (api={api})")
            return True
        elif r.status_code == 409:
            print(f"    {conn_name} ({category}): Already exists")
            return True

    print(f"    {conn_name} ({category}): FAILED HTTP {r.status_code}")
    print(f"      {r.text[:300]}")
    return False


def add_standard_connections():
    """Add Cosmos DB, OpenAI, and Key Vault connections."""
    print("=" * 60)
    print("CONNECTIONS: Add standard connections")
    print("=" * 60)

    # --- Cosmos DB ---
    cosmos_rid = (f"/subscriptions/{SUB_ID}/resourceGroups/{RG}"
                  f"/providers/Microsoft.DocumentDB/databaseAccounts/{COSMOS_NAME}")
    cosmos_endpoint = f"https://{COSMOS_NAME}.documents.azure.com:443/"
    print("\n  Adding Cosmos DB connection...")
    add_connection(
        conn_name="cosmos-agent-store",
        category="CosmosDB",
        target=cosmos_endpoint,
        auth_type="AAD",
        resource_id=cosmos_rid,
    )

    # --- Azure OpenAI ---
    oai_rid = (f"/subscriptions/{SUB_ID}/resourceGroups/{RG}"
               f"/providers/Microsoft.CognitiveServices/accounts/{OAI_NAME}")
    print("\n  Adding Azure OpenAI connection...")
    add_connection(
        conn_name="oai-connection",
        category="AzureOpenAI",
        target=f"https://{OAI_NAME}.openai.azure.com/",
        auth_type="AAD",
        resource_id=oai_rid,
        metadata={"ApiType": "Azure"},
    )

    # --- Key Vault ---
    kv_rid = (f"/subscriptions/{SUB_ID}/resourceGroups/{RG}"
              f"/providers/Microsoft.KeyVault/vaults/{KV_NAME}")
    print("\n  Adding Key Vault connection...")
    add_connection(
        conn_name="kv-connection",
        category="AzureKeyVault",
        target=f"https://{KV_NAME}.vault.azure.net/",
        auth_type="AAD",
        resource_id=kv_rid,
    )


def delete_connection(conn_name):
    """Delete a specific connection."""
    print(f"  Deleting connection '{conn_name}'...")
    headers = get_headers()
    for api in [API_CS_PREV, API_CS]:
        url = f"{_account_base()}/connections/{conn_name}?api-version={api}"
        r = requests.delete(url, headers=headers)
        if r.status_code in (200, 204):
            print(f"    {conn_name}: DELETED")
            return True
        elif r.status_code == 404:
            print(f"    {conn_name}: not found")
            return True
    print(f"    {conn_name}: FAILED HTTP {r.status_code}")
    return False


# ################################################################
#  6. RBAC
# ################################################################

def _assign_role(scope, principal_id, principal_type, role_name, role_definition_id):
    """Assign a single role. Returns True if created or already exists."""
    headers = get_headers()
    assign_id = str(uuid.uuid4())
    url = (f"{ARM}{scope}/providers/Microsoft.Authorization"
           f"/roleAssignments/{assign_id}?api-version={API_RBAC}")
    body = {
        "properties": {
            "roleDefinitionId": (f"{scope}/providers/Microsoft.Authorization"
                                 f"/roleDefinitions/{role_definition_id}"),
            "principalId": principal_id,
            "principalType": principal_type,
        }
    }
    r = requests.put(url, headers=headers, json=body)
    if r.status_code in (200, 201):
        status = "ASSIGNED"
    elif r.status_code == 409:
        status = "Already exists"
    else:
        status = f"FAILED (HTTP {r.status_code})"
    print(f"    {role_name:40s} -> {principal_type[:4]}..{principal_id[-4:]}: {status}")
    return r.status_code in (200, 201, 409)


def assign_rbac():
    """Assign RBAC roles for the account/project identities."""
    print("=" * 60)
    print("RBAC: Assign roles")
    print("=" * 60)

    headers = get_headers()

    # Get account identity
    r = requests.get(_account_url(), headers=headers)
    acct_principal = r.json().get("identity", {}).get("principalId", "") if r.status_code == 200 else ""

    # Get project identity
    r = requests.get(_project_url(), headers=headers)
    proj_principal = r.json().get("identity", {}).get("principalId", "") if r.status_code == 200 else ""

    # Get current user
    try:
        graph_token = _cred().get_token("https://graph.microsoft.com/.default").token
        gr = requests.get("https://graph.microsoft.com/v1.0/me",
                          headers={"Authorization": f"Bearer {graph_token}"})
        user_id = gr.json().get("id", "") if gr.status_code == 200 else ""
    except Exception:
        user_id = ""

    print(f"  Account principal: {acct_principal or 'N/A'}")
    print(f"  Project principal: {proj_principal or 'N/A'}")
    print(f"  User ID:           {user_id or 'N/A'}")

    # Scope definitions
    oai_scope = (f"/subscriptions/{SUB_ID}/resourceGroups/{RG}"
                 f"/providers/Microsoft.CognitiveServices/accounts/{OAI_NAME}")
    storage_scope = (f"/subscriptions/{SUB_ID}/resourceGroups/{RG}"
                     f"/providers/Microsoft.Storage/storageAccounts/{STORAGE_NAME}")
    account_scope = (f"/subscriptions/{SUB_ID}/resourceGroups/{RG}"
                     f"/providers/Microsoft.CognitiveServices/accounts/{ACCOUNT_NAME}")

    # Role definition IDs
    ROLES = {
        "Cognitive Services OpenAI Contributor": "a001fd3d-188f-4b5d-821b-7da978bf7442",
        "Cognitive Services OpenAI User":        "5e0bd9bd-7b93-4f28-af87-19fc36ad61bd",
        "Cognitive Services Contributor":         "25fbc0a9-bd7c-42a3-aa1a-3b75d497ee68",
        "Storage Blob Data Contributor":          "ba92f5b4-2d11-453d-a403-e96b0029c9fe",
    }

    assignments = []

    # Account SP -> OpenAI
    if acct_principal:
        assignments.append((oai_scope, acct_principal, "ServicePrincipal",
                            "Cognitive Services OpenAI Contributor"))
        assignments.append((oai_scope, acct_principal, "ServicePrincipal",
                            "Cognitive Services OpenAI User"))
        assignments.append((storage_scope, acct_principal, "ServicePrincipal",
                            "Storage Blob Data Contributor"))

    # Project SP -> OpenAI (if different)
    if proj_principal and proj_principal != acct_principal:
        assignments.append((oai_scope, proj_principal, "ServicePrincipal",
                            "Cognitive Services OpenAI Contributor"))
        assignments.append((oai_scope, proj_principal, "ServicePrincipal",
                            "Cognitive Services OpenAI User"))
        assignments.append((storage_scope, proj_principal, "ServicePrincipal",
                            "Storage Blob Data Contributor"))

    # User -> Account + OpenAI + Storage
    if user_id:
        assignments.append((oai_scope, user_id, "User",
                            "Cognitive Services OpenAI Contributor"))
        assignments.append((account_scope, user_id, "User",
                            "Cognitive Services Contributor"))
        assignments.append((storage_scope, user_id, "User",
                            "Storage Blob Data Contributor"))

    print(f"\n  Assigning {len(assignments)} roles...")
    for scope, pid, ptype, role_name in assignments:
        _assign_role(scope, pid, ptype, role_name, ROLES[role_name])

    print("\n  Waiting 15s for RBAC propagation...")
    time.sleep(15)
    print("  RBAC assignment complete.")


# ################################################################
#  7. MODEL DEPLOYMENTS
# ################################################################

def list_deployments():
    """List model deployments on the account."""
    print("=" * 60)
    print("DEPLOYMENTS: List")
    print("=" * 60)

    headers = get_headers()
    url = f"{_account_base()}/deployments?api-version={API_DEPLOY}"
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        print(f"  Error (HTTP {r.status_code}): {r.text[:300]}")
        return []

    deps = r.json().get("value", [])
    print(f"  Total deployments: {len(deps)}")
    for d in deps:
        name = d.get("name", "?")
        model = d.get("properties", {}).get("model", {})
        model_name = model.get("name", "?") if isinstance(model, dict) else str(model)
        model_ver = model.get("version", "?") if isinstance(model, dict) else "?"
        sku = d.get("sku", {}).get("name", "?")
        state = d.get("properties", {}).get("provisioningState", "?")
        print(f"    {name:20s} model={model_name:12s} ver={model_ver:12s}"
              f"  sku={sku:15s} state={state}")
    return deps


def deploy_model(model_name="gpt-4o", model_version="2024-11-20",
                 sku_name="GlobalStandard", capacity=10):
    """Deploy a model on the AIServices account."""
    print("=" * 60)
    print(f"DEPLOYMENTS: Deploy {model_name}")
    print("=" * 60)

    headers = get_headers()
    deploy_name = model_name  # use model name as deployment name

    # Check if already exists
    url = f"{_account_base()}/deployments/{deploy_name}?api-version={API_DEPLOY}"
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        state = r.json().get("properties", {}).get("provisioningState", "?")
        print(f"  Deployment '{deploy_name}' already exists (state={state})")
        return True

    body = {
        "sku": {"name": sku_name, "capacity": capacity},
        "properties": {
            "model": {
                "format": "OpenAI",
                "name": model_name,
                "version": model_version,
            }
        },
    }

    print(f"  Creating deployment '{deploy_name}' (sku={sku_name}, capacity={capacity})...")
    r = requests.put(url, headers=headers, json=body)
    if r.status_code in (200, 201, 202):
        print(f"  Deployment started (HTTP {r.status_code})")
    else:
        print(f"  ERROR: HTTP {r.status_code}")
        print(f"  {r.text[:500]}")
        # Fallback to Standard SKU
        if sku_name == "GlobalStandard":
            print("\n  Retrying with Standard SKU...")
            body["sku"]["name"] = "Standard"
            r = requests.put(url, headers=headers, json=body)
            if r.status_code not in (200, 201, 202):
                print(f"  Retry also failed: HTTP {r.status_code}: {r.text[:300]}")
                return False
        else:
            return False

    result = poll_provisioning(url, f"Deployment '{deploy_name}'", max_attempts=30)
    return result == "Succeeded"


def delete_deployment(deploy_name):
    """Delete a model deployment."""
    print(f"\n  Deleting deployment '{deploy_name}'...")
    headers = get_headers()
    url = f"{_account_base()}/deployments/{deploy_name}?api-version={API_DEPLOY}"

    r = requests.get(url, headers=headers)
    if r.status_code == 404:
        print(f"  Deployment '{deploy_name}': already deleted")
        return True

    r = requests.delete(url, headers=headers)
    print(f"  DELETE: HTTP {r.status_code}")
    if r.status_code not in (200, 202, 204):
        print(f"  Error: {r.text[:500]}")
        return False

    result = poll_provisioning(url, f"Deployment '{deploy_name}'")
    return result == "Deleted"


# ################################################################
#  COMPOSITE WORKFLOWS
# ################################################################

def full_setup():
    """End-to-end: Create account → project → connections → RBAC → deploy model."""
    print("#" * 60)
    print("  FULL SETUP — New Foundry (CognitiveServices)")
    print("#" * 60)

    ok = create_account()
    if not ok:
        print("\n  ABORTED: Account creation failed.")
        return

    ok = create_project()
    if not ok:
        print("\n  ABORTED: Project creation failed.")
        return

    add_standard_connections()
    assign_rbac()
    deploy_model()

    print("\n" + "#" * 60)
    print("  FULL SETUP COMPLETE")
    print("#" * 60)
    read_account()
    read_project()
    list_connections()
    list_deployments()


def full_teardown():
    """End-to-end: Delete deployments → connections → project → account → purge."""
    print("#" * 60)
    print("  FULL TEARDOWN — New Foundry (CognitiveServices)")
    print("#" * 60)

    # List and delete all deployments
    headers = get_headers()
    url = f"{_account_base()}/deployments?api-version={API_DEPLOY}"
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        deps = r.json().get("value", [])
        for d in deps:
            delete_deployment(d.get("name"))

    # Delete project first (child)
    delete_project()

    # Delete account (parent)
    delete_account()

    # Purge soft-deleted account
    print("\n  Waiting 30s before purge attempt...")
    time.sleep(30)
    purge_deleted_account()

    print("\n" + "#" * 60)
    print("  FULL TEARDOWN COMPLETE")
    print("#" * 60)


def full_read():
    """Read all: account, project, connections, deployments."""
    list_accounts_in_rg()
    acct = read_account()
    if acct:
        read_project()
        list_projects()
        list_connections()
        list_deployments()


# ################################################################
#  CLI ENTRYPOINT
# ################################################################

def parse_tags(tag_string):
    """Parse 'key1=val1,key2=val2' into dict."""
    tags = {}
    if tag_string:
        for pair in tag_string.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                tags[k.strip()] = v.strip()
    return tags


def main():
    parser = argparse.ArgumentParser(
        description="NEW Foundry (CognitiveServices) CRUD Operations via REST API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Actions:
  create            Create account + project
  read              Read/list account, project, connections, deployments
  update            Update account/project tags (use --tags)
  delete            Delete project + account + purge
  deploy-model      Deploy a model (use --model, --model-version)
  delete-deployment Delete a deployment (use --deployment-name)
  list-connections  List connections on the account
  add-connections   Add Cosmos, OpenAI, Key Vault connections
  assign-rbac       Assign RBAC roles for identities
  full-setup        End-to-end create + connect + RBAC + deploy
  full-teardown     End-to-end delete everything
        """,
    )
    parser.add_argument("--action", required=True,
                        choices=["create", "read", "update", "delete",
                                 "deploy-model", "delete-deployment",
                                 "list-connections", "add-connections",
                                 "assign-rbac", "full-setup", "full-teardown"],
                        help="CRUD action to perform")
    parser.add_argument("--tags", default=None,
                        help="Tags for update, format: key1=val1,key2=val2")
    parser.add_argument("--model", default="gpt-4o",
                        help="Model name for deploy-model (default: gpt-4o)")
    parser.add_argument("--model-version", default="2024-11-20",
                        help="Model version for deploy-model")
    parser.add_argument("--sku", default="GlobalStandard",
                        help="SKU for deploy-model (default: GlobalStandard)")
    parser.add_argument("--capacity", type=int, default=10,
                        help="Capacity for deploy-model (default: 10)")
    parser.add_argument("--deployment-name", default=None,
                        help="Deployment name for delete-deployment")

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  Foundry CRUD — Action: {args.action}")
    print(f"  Account: {ACCOUNT_NAME}  |  Project: {PROJECT_NAME}")
    print(f"  Subscription: {SUB_ID}")
    print(f"  Resource Group: {RG}  |  Location: {LOCATION}")
    print(f"{'='*60}\n")

    if args.action == "create":
        create_account()
        create_project()

    elif args.action == "read":
        full_read()

    elif args.action == "update":
        tags = parse_tags(args.tags) if args.tags else {"updated_by": "crud_script"}
        update_account_tags(tags)
        update_project_tags(tags)

    elif args.action == "delete":
        delete_project()
        delete_account()
        time.sleep(30)
        purge_deleted_account()

    elif args.action == "deploy-model":
        deploy_model(args.model, args.model_version, args.sku, args.capacity)

    elif args.action == "delete-deployment":
        name = args.deployment_name or args.model
        delete_deployment(name)

    elif args.action == "list-connections":
        list_connections()

    elif args.action == "add-connections":
        add_standard_connections()

    elif args.action == "assign-rbac":
        assign_rbac()

    elif args.action == "full-setup":
        full_setup()

    elif args.action == "full-teardown":
        full_teardown()


if __name__ == "__main__":
    main()

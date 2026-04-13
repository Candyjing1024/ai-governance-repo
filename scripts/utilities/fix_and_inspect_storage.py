"""
Fix: Assign Storage Blob Data Reader to current user on stchubbmcppoc,
then re-run Phase 5b (Storage) and 5c (Key Vault) inspection.
"""
import json
import uuid
import requests
from azure.identity import DefaultAzureCredential

SUB_ID = "a3223db3-76f2-4a7c-8684-57b835dc77e7"
RG = "rg-chubb-mcp-poc"
STORAGE_NAME = "stchubbmcppoc"
ARM = "https://management.azure.com"

def get_headers():
    cred = DefaultAzureCredential()
    token = cred.get_token("https://management.azure.com/.default").token
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def assign_storage_rbac():
    print("=" * 60)
    print("ASSIGNING STORAGE BLOB DATA ROLES")
    print("=" * 60)

    headers = get_headers()

    # Get current user ID
    cred = DefaultAzureCredential()
    graph_token = cred.get_token("https://graph.microsoft.com/.default").token
    gr = requests.get("https://graph.microsoft.com/v1.0/me",
                       headers={"Authorization": f"Bearer {graph_token}"})
    user_id = gr.json().get("id", "")
    print(f"  User ID: {user_id}")

    storage_rid = f"/subscriptions/{SUB_ID}/resourceGroups/{RG}/providers/Microsoft.Storage/storageAccounts/{STORAGE_NAME}"

    # Storage Blob Data Contributor: ba92f5b4-2d11-453d-a403-e96b0029c9fe
    # Storage Blob Data Reader: 2a2b9908-6ea1-4ae2-8e65-a410df84e7d1
    roles = [
        ("Storage Blob Data Contributor", "ba92f5b4-2d11-453d-a403-e96b0029c9fe"),
        ("Storage Blob Data Reader", "2a2b9908-6ea1-4ae2-8e65-a410df84e7d1"),
    ]

    for role_name, role_id in roles:
        assign_id = str(uuid.uuid4())
        url = f"{ARM}{storage_rid}/providers/Microsoft.Authorization/roleAssignments/{assign_id}?api-version=2022-04-01"
        body = {
            "properties": {
                "roleDefinitionId": f"{storage_rid}/providers/Microsoft.Authorization/roleDefinitions/{role_id}",
                "principalId": user_id,
                "principalType": "User",
            }
        }
        r = requests.put(url, headers=headers, json=body)
        if r.status_code in (200, 201):
            print(f"  Assigned: {role_name}")
        elif r.status_code == 409:
            print(f"  Already assigned: {role_name}")
        else:
            print(f"  {role_name}: HTTP {r.status_code}: {r.text[:200]}")

    # Also assign to the Hub and Project managed identities
    for ws_name in ["hub-chubb-storage-val", "proj-chubb-storage-val"]:
        ws_url = f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}/providers/Microsoft.MachineLearningServices/workspaces/{ws_name}?api-version=2024-10-01"
        wr = requests.get(ws_url, headers=headers)
        if wr.status_code == 200:
            pid = wr.json().get("identity", {}).get("principalId", "")
            if pid:
                for role_name, role_id in roles:
                    assign_id = str(uuid.uuid4())
                    url = f"{ARM}{storage_rid}/providers/Microsoft.Authorization/roleAssignments/{assign_id}?api-version=2022-04-01"
                    body = {
                        "properties": {
                            "roleDefinitionId": f"{storage_rid}/providers/Microsoft.Authorization/roleDefinitions/{role_id}",
                            "principalId": pid,
                            "principalType": "ServicePrincipal",
                        }
                    }
                    r = requests.put(url, headers=headers, json=body)
                    status = "Assigned" if r.status_code in (200, 201) else ("Already" if r.status_code == 409 else f"HTTP {r.status_code}")
                    print(f"  {ws_name} -> {role_name}: {status}")

    print("\n  Waiting 15s for RBAC propagation...")
    import time
    time.sleep(15)


def inspect_storage_account():
    print("\n" + "=" * 60)
    print("PHASE 5b: INSPECT STORAGE ACCOUNT")
    print("=" * 60)

    from azure.storage.blob import BlobServiceClient

    cred = DefaultAzureCredential()
    blob_url = "https://stchubbmcppoc.blob.core.windows.net"
    client = BlobServiceClient(blob_url, credential=cred)

    print("\n  Listing blob containers:")
    try:
        containers = list(client.list_containers())
    except Exception as e:
        print(f"  ERROR listing containers: {e}")
        # Fallback: use storage key
        print("  Trying with storage key...")
        headers = get_headers()
        keys_url = f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}/providers/Microsoft.Storage/storageAccounts/{STORAGE_NAME}/listKeys?api-version=2023-05-01"
        kr = requests.post(keys_url, headers=headers)
        if kr.status_code == 200:
            key = kr.json()["keys"][0]["value"]
            client = BlobServiceClient(blob_url, credential=key)
            containers = list(client.list_containers())
        else:
            print(f"  Cannot get keys: HTTP {kr.status_code}")
            return

    if not containers:
        print("    (no containers found)")
    else:
        print(f"  Found {len(containers)} containers:")

    for cont in containers:
        cont_name = cont["name"]
        cont_client = client.get_container_client(cont_name)
        try:
            blobs = list(cont_client.list_blobs())
            print(f"\n    Container: {cont_name} ({len(blobs)} blobs)")
            for blob in blobs[:10]:
                size = blob.size or 0
                ct = blob.content_settings.content_type if blob.content_settings else "?"
                print(f"      {blob.name} ({size} bytes, {ct})")
            if len(blobs) > 10:
                print(f"      ... and {len(blobs) - 10} more")
        except Exception as e:
            print(f"\n    Container: {cont_name} (error: {str(e)[:100]})")


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


if __name__ == "__main__":
    assign_storage_rbac()
    inspect_storage_account()
    inspect_key_vault()

    print("\n" + "=" * 60)
    print("PHASE 5 COMPLETE")
    print("=" * 60)

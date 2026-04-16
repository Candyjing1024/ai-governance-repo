"""
00 - Create Service Principal + Resource Group.

Creates an SP via Microsoft Graph, assigns Contributor + Cognitive Services
Contributor on the new resource group, and saves credentials back to config.json.

Prerequisites:
  - az login with a user that has Global Admin or App Admin + RG Owner
  - pip install requests
"""
import json, sys, os, uuid, requests
sys.path.insert(0, os.path.dirname(__file__))
from _auth import load_config, ARM, CONFIG_PATH


def run():
    cfg = load_config()
    tenant = cfg["tenant_id"]
    sub = cfg["subscription_id"]
    sp_name = cfg["service_principal"]["name"]
    rg = cfg["resource_group"]
    location = cfg["location"]

    # Use az CLI token for bootstrapping (SP doesn't exist yet)
    from azure.identity import AzureCliCredential
    cred = AzureCliCredential()

    # ---- 1. Create Resource Group ----
    print("=" * 60)
    print("STEP 1: Create Resource Group")
    print("=" * 60)
    arm_token = cred.get_token("https://management.azure.com/.default").token
    h = {"Authorization": f"Bearer {arm_token}", "Content-Type": "application/json"}

    rg_url = f"{ARM}/subscriptions/{sub}/resourceGroups/{rg}?api-version=2024-03-01"
    r = requests.put(rg_url, headers=h, json={"location": location})
    if r.status_code in (200, 201):
        print(f"  RG '{rg}' ready in {location}")
    else:
        print(f"  ERROR: {r.status_code} {r.text[:300]}")
        return

    # ---- 2. Create App Registration + SP via Graph ----
    print(f"\n{'='*60}")
    print("STEP 2: Create Service Principal")
    print("=" * 60)
    graph_token = cred.get_token("https://graph.microsoft.com/.default").token
    gh = {"Authorization": f"Bearer {graph_token}", "Content-Type": "application/json"}

    # Create app registration
    app_body = {"displayName": sp_name, "signInAudience": "AzureADMyOrg"}
    r = requests.post("https://graph.microsoft.com/v1.0/applications", headers=gh, json=app_body)
    if r.status_code == 201:
        app = r.json()
        print(f"  App registered: {app['appId']}")
    elif r.status_code == 400 and "already exists" in r.text.lower():
        # Find existing
        r2 = requests.get(f"https://graph.microsoft.com/v1.0/applications?$filter=displayName eq '{sp_name}'", headers=gh)
        apps = r2.json().get("value", [])
        if not apps:
            print(f"  ERROR: App conflict but not found. {r.text[:300]}")
            return
        app = apps[0]
        print(f"  App exists: {app['appId']}")
    else:
        print(f"  ERROR creating app: {r.status_code} {r.text[:300]}")
        return

    app_id = app["appId"]
    app_object_id = app["id"]

    # Create SP for the app
    sp_body = {"appId": app_id}
    r = requests.post("https://graph.microsoft.com/v1.0/servicePrincipals", headers=gh, json=sp_body)
    if r.status_code == 201:
        sp = r.json()
        print(f"  SP created: {sp['id']}")
    elif r.status_code == 409:
        r2 = requests.get(f"https://graph.microsoft.com/v1.0/servicePrincipals?$filter=appId eq '{app_id}'", headers=gh)
        sp = r2.json()["value"][0]
        print(f"  SP exists: {sp['id']}")
    else:
        print(f"  ERROR creating SP: {r.status_code} {r.text[:300]}")
        return

    sp_object_id = sp["id"]

    # Create client secret
    secret_body = {"passwordCredential": {"displayName": "e2e-poc-key", "endDateTime": "2027-01-01T00:00:00Z"}}
    r = requests.post(f"https://graph.microsoft.com/v1.0/applications/{app_object_id}/addPassword",
                       headers=gh, json=secret_body)
    if r.status_code == 200:
        secret = r.json()["secretText"]
        print(f"  Secret generated (save it now!)")
    else:
        print(f"  ERROR creating secret: {r.status_code} {r.text[:300]}")
        return

    # ---- 3. Assign roles on RG ----
    print(f"\n{'='*60}")
    print("STEP 3: Assign RBAC roles on Resource Group")
    print("=" * 60)

    rg_scope = f"/subscriptions/{sub}/resourceGroups/{rg}"
    roles = {
        "Contributor": "b24988ac-6180-42a0-ab88-20f7382dd24c",
        "Cognitive Services Contributor": "25fbc0a9-bd7c-42a3-aa1a-3b75d497ee68",
        "Cognitive Services OpenAI User": "5e0bd9bd-7b93-4f28-af87-19fc36ad61bd",
        "Azure AI Developer": "64702f94-c441-49e6-a78b-ef80e0188fee",
        "API Management Service Contributor": "312a565d-c81f-4fd8-895a-4e21e48d571c",
    }

    for role_name, role_def_id in roles.items():
        ra_id = str(uuid.uuid4())
        ra_url = f"{ARM}{rg_scope}/providers/Microsoft.Authorization/roleAssignments/{ra_id}?api-version=2022-04-01"
        ra_body = {
            "properties": {
                "roleDefinitionId": f"{rg_scope}/providers/Microsoft.Authorization/roleDefinitions/{role_def_id}",
                "principalId": sp_object_id,
                "principalType": "ServicePrincipal",
            }
        }
        r = requests.put(ra_url, headers=h, json=ra_body)
        if r.status_code in (200, 201):
            print(f"  {role_name}: assigned")
        elif r.status_code == 409:
            print(f"  {role_name}: already assigned")
        else:
            print(f"  {role_name}: {r.status_code} {r.text[:200]}")

    # ---- 4. Save credentials to config ----
    print(f"\n{'='*60}")
    print("STEP 4: Save SP credentials to config.json")
    print("=" * 60)

    cfg["service_principal"]["client_id"] = app_id
    cfg["service_principal"]["client_secret"] = secret
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"  config.json updated with client_id and client_secret")
    print(f"\n  Client ID:     {app_id}")
    print(f"  SP Object ID:  {sp_object_id}")
    print(f"  Secret:        {secret[:8]}...")
    print(f"\n  IMPORTANT: Rotate this secret before production use.")


if __name__ == "__main__":
    run()

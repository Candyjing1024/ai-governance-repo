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
        "User Access Administrator": "18d7d88d-d35e-4fb5-a5c3-7773c20a72d9",
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

    # ---- 5. Create Entra Security Group ----
    print(f"\n{'='*60}")
    print("STEP 5: Create Entra Security Group")
    print("=" * 60)

    group_name = cfg.get("security_group", {}).get("name", "sg-foundry-e2e-users")
    group_body = {
        "displayName": group_name,
        "mailEnabled": False,
        "mailNickname": group_name.replace(" ", "-"),
        "securityEnabled": True,
        "description": "Foundry E2E POC — authorized users for APIM JWT group validation",
    }
    r = requests.post("https://graph.microsoft.com/v1.0/groups", headers=gh, json=group_body)
    if r.status_code == 201:
        grp = r.json()
        print(f"  Group created: {grp['displayName']} ({grp['id']})")
    elif r.status_code == 400 and "already exist" in r.text.lower():
        r2 = requests.get(f"https://graph.microsoft.com/v1.0/groups?$filter=displayName eq '{group_name}'", headers=gh)
        grps = r2.json().get("value", [])
        if grps:
            grp = grps[0]
            print(f"  Group exists: {grp['displayName']} ({grp['id']})")
        else:
            print(f"  ERROR: group conflict but not found")
            grp = None
    else:
        print(f"  Warning: {r.status_code} {r.text[:200]}")
        grp = None

    if grp:
        group_id = grp["id"]

        # Add current user to the group
        me = requests.get("https://graph.microsoft.com/v1.0/me", headers=gh).json()
        my_id = me.get("id", "")
        if my_id:
            add_body = {"@odata.id": f"https://graph.microsoft.com/v1.0/directoryObjects/{my_id}"}
            r = requests.post(f"https://graph.microsoft.com/v1.0/groups/{group_id}/members/$ref",
                              headers=gh, json=add_body)
            if r.status_code == 204:
                print(f"  Added {me.get('displayName', my_id)} to group")
            elif r.status_code == 400 and "already exist" in r.text.lower():
                print(f"  {me.get('displayName', my_id)} already in group")
            else:
                print(f"  Warning adding member: {r.status_code} {r.text[:150]}")

        # Save group ID to config
        if "security_group" not in cfg:
            cfg["security_group"] = {"name": group_name}
        cfg["security_group"]["object_id"] = group_id
        cfg["jwt_policy"]["allowed_groups"] = [group_id]
        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=2)
        print(f"  config.json updated with group ID + jwt_policy.allowed_groups")

    # ---- 6. Create App Registration for JWT validation ----
    print(f"\n{'='*60}")
    print("STEP 6: Create App Registration for JWT audience")
    print("=" * 60)

    jwt_app_name = cfg.get("jwt_policy", {}).get("app_name", "app-foundry-e2e-jwt")
    jwt_app_body = {"displayName": jwt_app_name, "signInAudience": "AzureADMyOrg"}
    r = requests.post("https://graph.microsoft.com/v1.0/applications", headers=gh, json=jwt_app_body)
    if r.status_code == 201:
        jwt_app = r.json()
        print(f"  App registered: {jwt_app['appId']}")
    else:
        r2 = requests.get(
            f"https://graph.microsoft.com/v1.0/applications?$filter=displayName eq '{jwt_app_name}'",
            headers=gh)
        apps = r2.json().get("value", [])
        if apps:
            jwt_app = apps[0]
            print(f"  App exists: {jwt_app['appId']}")
        else:
            print(f"  ERROR: {r.status_code} {r.text[:200]}")
            jwt_app = None

    if jwt_app:
        jwt_app_id = jwt_app["appId"]
        jwt_app_obj_id = jwt_app["id"]

        # Set identifier URI
        id_uri_body = {"identifierUris": [f"api://{jwt_app_id}"]}
        r = requests.patch(f"https://graph.microsoft.com/v1.0/applications/{jwt_app_obj_id}",
                           headers=gh, json=id_uri_body)
        if r.status_code == 204:
            print(f"  Identifier URI set: api://{jwt_app_id}")
        else:
            print(f"  Identifier URI: {r.status_code} (may already be set)")

        # Add user_impersonation scope
        scope_id = str(uuid.uuid4())
        scope_body = {
            "api": {
                "oauth2PermissionScopes": [{
                    "adminConsentDescription": "Allow user impersonation",
                    "adminConsentDisplayName": "user_impersonation",
                    "id": scope_id,
                    "isEnabled": True,
                    "type": "User",
                    "userConsentDescription": "Allow user impersonation",
                    "userConsentDisplayName": "user_impersonation",
                    "value": "user_impersonation",
                }]
            }
        }
        r = requests.patch(f"https://graph.microsoft.com/v1.0/applications/{jwt_app_obj_id}",
                           headers=gh, json=scope_body)
        if r.status_code == 204:
            print(f"  Scope user_impersonation added")
        else:
            print(f"  Scope: {r.status_code} (may already exist)")

        # Enable groups claim — two separate PATCHes (Graph API can
        # silently ignore groupMembershipClaims when sent with optionalClaims)
        r = requests.patch(
            f"https://graph.microsoft.com/v1.0/applications/{jwt_app_obj_id}",
            headers=gh,
            json={"groupMembershipClaims": "SecurityGroup"})
        if r.status_code == 204:
            print(f"  groupMembershipClaims set to SecurityGroup")
        else:
            print(f"  groupMembershipClaims: {r.status_code} {r.text[:150]}")

        optional_claims_body = {
            "optionalClaims": {
                "accessToken": [
                    {"name": "groups", "essential": False, "additionalProperties": []},
                ],
                "idToken": [
                    {"name": "groups", "essential": False, "additionalProperties": []},
                ],
            }
        }
        r = requests.patch(
            f"https://graph.microsoft.com/v1.0/applications/{jwt_app_obj_id}",
            headers=gh, json=optional_claims_body)
        if r.status_code == 204:
            print(f"  optionalClaims set for groups in access/ID tokens")
        else:
            print(f"  optionalClaims: {r.status_code} {r.text[:150]}")

        # Pre-authorize Azure CLI as known client
        az_cli_app_id = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"
        # Read current scopes to get scope ID
        r = requests.get(f"https://graph.microsoft.com/v1.0/applications/{jwt_app_obj_id}", headers=gh)
        current_scopes = r.json().get("api", {}).get("oauth2PermissionScopes", [])
        scope_ids = [s["id"] for s in current_scopes if s.get("value") == "user_impersonation"]
        if scope_ids:
            preauth_body = {
                "api": {
                    "oauth2PermissionScopes": current_scopes,
                    "preAuthorizedApplications": [{
                        "appId": az_cli_app_id,
                        "delegatedPermissionIds": scope_ids,
                    }]
                }
            }
            r = requests.patch(f"https://graph.microsoft.com/v1.0/applications/{jwt_app_obj_id}",
                               headers=gh, json=preauth_body)
            if r.status_code == 204:
                print(f"  Azure CLI pre-authorized as known client")
            else:
                print(f"  Pre-auth: {r.status_code} {r.text[:150]}")

        # Ensure SP exists for the JWT app (needed for token issuance)
        jwt_sp_body = {"appId": jwt_app_id}
        r = requests.post("https://graph.microsoft.com/v1.0/servicePrincipals", headers=gh, json=jwt_sp_body)
        if r.status_code == 201:
            print(f"  SP created for JWT app")
        elif r.status_code == 409:
            print(f"  SP already exists for JWT app")

        # Save JWT app ID to config
        cfg["jwt_policy"]["audience"] = jwt_app_id
        cfg["jwt_policy"]["app_object_id"] = jwt_app_obj_id
        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=2)
        print(f"  config.json updated with jwt_policy.audience = {jwt_app_id}")

    print(f"\n  IMPORTANT: Rotate SP secret before production use.")


if __name__ == "__main__":
    run()

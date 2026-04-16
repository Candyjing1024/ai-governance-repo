"""
04 - Create APIM, connect to Foundry via "Microsoft Foundry" API type,
     and apply JWT + group claims + MI auth policy.

Uses:
  - ARM REST API for APIM (2024-06-01-preview — supports Microsoft Foundry API type)
  - Managed Identity for backend auth to Foundry
  - validate-jwt policy for Entra ID token + group claims
"""
import json, sys, os, uuid, time, requests
sys.path.insert(0, os.path.dirname(__file__))
from _auth import load_config, arm_headers, ARM, account_id, rg_id, poll, get_sp_token


def run():
    cfg = load_config()
    h = arm_headers(cfg)
    apim_cfg = cfg["apim"]
    foundry_cfg = cfg["foundry"]
    jwt_cfg = cfg["jwt_policy"]
    sub = cfg["subscription_id"]
    rg = cfg["resource_group"]
    location = cfg["location"]
    tenant = cfg["tenant_id"]

    apim_name = apim_cfg["name"]
    apim_api = apim_cfg["api_version"]
    acct_name = foundry_cfg["account_name"]

    apim_id = f"{rg_id(cfg)}/providers/Microsoft.ApiManagement/service/{apim_name}"

    # ================================================================
    # STEP 1: Create APIM instance (Developer SKU)
    # ================================================================
    print("=" * 60)
    print(f"STEP 1: Create APIM '{apim_name}'")
    print("=" * 60)

    apim_url = f"{ARM}{apim_id}?api-version={apim_api}"

    r = requests.get(apim_url, headers=h)
    if r.status_code == 200:
        state = r.json().get("properties", {}).get("provisioningState", "?")
        print(f"  Already exists (state={state})")
    else:
        body = {
            "location": location,
            "sku": {"name": apim_cfg["sku"], "capacity": 1},
            "identity": {"type": "SystemAssigned"},
            "properties": {
                "publisherEmail": apim_cfg["publisher_email"],
                "publisherName": apim_cfg["publisher_name"],
            },
        }
        r = requests.put(apim_url, headers=h, json=body)
        if r.status_code in (200, 201, 202):
            print(f"  Creating... (HTTP {r.status_code})")
            print(f"  Developer SKU takes ~30-45 minutes to provision.")
        else:
            print(f"  ERROR: {r.status_code} {r.text[:400]}")
            return
        poll(apim_url, h, f"APIM '{apim_name}'", max_wait=3600, interval=30)

    # Get APIM MI principal ID
    r = requests.get(apim_url, headers=h)
    apim_data = r.json()
    apim_mi = apim_data.get("identity", {}).get("principalId", "")
    apim_gateway = apim_data.get("properties", {}).get("gatewayUrl", "")
    print(f"  Gateway: {apim_gateway}")
    print(f"  MI Principal: {apim_mi}")

    # ================================================================
    # STEP 2: Assign "Cognitive Services OpenAI User" to APIM MI
    # ================================================================
    print(f"\n{'='*60}")
    print("STEP 2: Assign RBAC for APIM MI on Foundry account")
    print("=" * 60)

    acct_scope = account_id(cfg)
    role_def_id = "5e0bd9bd-7b93-4f28-af87-19fc36ad61bd"  # Cognitive Services OpenAI User
    ra_id = str(uuid.uuid4())
    ra_url = f"{ARM}{acct_scope}/providers/Microsoft.Authorization/roleAssignments/{ra_id}?api-version=2022-04-01"
    ra_body = {
        "properties": {
            "roleDefinitionId": f"{acct_scope}/providers/Microsoft.Authorization/roleDefinitions/{role_def_id}",
            "principalId": apim_mi,
            "principalType": "ServicePrincipal",
        }
    }

    r = requests.put(ra_url, headers=h, json=ra_body)
    if r.status_code in (200, 201):
        print(f"  Cognitive Services OpenAI User: assigned")
    elif r.status_code == 409:
        print(f"  Role already assigned")
    else:
        print(f"  Warning: {r.status_code} {r.text[:200]}")

    # Also assign Cognitive Services User for agent calls
    role_cs_user = "a97b65f3-24c7-4388-baec-2e87135dc908"  # Cognitive Services User
    ra2_id = str(uuid.uuid4())
    ra2_url = f"{ARM}{acct_scope}/providers/Microsoft.Authorization/roleAssignments/{ra2_id}?api-version=2022-04-01"
    ra2_body = {
        "properties": {
            "roleDefinitionId": f"{acct_scope}/providers/Microsoft.Authorization/roleDefinitions/{role_cs_user}",
            "principalId": apim_mi,
            "principalType": "ServicePrincipal",
        }
    }
    r = requests.put(ra2_url, headers=h, json=ra2_body)
    if r.status_code in (200, 201):
        print(f"  Cognitive Services User: assigned")
    elif r.status_code == 409:
        print(f"  Role already assigned")
    else:
        print(f"  Warning: {r.status_code} {r.text[:200]}")

    # ================================================================
    # STEP 3: Create "Microsoft Foundry" API in APIM
    # ================================================================
    print(f"\n{'='*60}")
    print("STEP 3: Create Microsoft Foundry API in APIM")
    print("=" * 60)

    # Get the Foundry account endpoint
    acct_url = f"{ARM}{acct_scope}?api-version={foundry_cfg['api_version']}"
    r = requests.get(acct_url, headers=h)
    foundry_endpoint = r.json().get("properties", {}).get("endpoint", "")
    print(f"  Foundry endpoint: {foundry_endpoint}")

    # Create the API using the "Microsoft Foundry" type
    api_url = f"{ARM}{apim_id}/apis/foundry-api?api-version={apim_api}"
    api_body = {
        "properties": {
            "displayName": f"Foundry - {acct_name}",
            "description": "Microsoft Foundry V2 API — models, agents, chat",
            "path": "foundry",
            "protocols": ["https"],
            "type": "azure-ai-foundry",
            "serviceUrl": foundry_endpoint,
            "subscriptionRequired": False,
            "azureAIFoundryProperties": {
                "resourceId": f"/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.CognitiveServices/accounts/{acct_name}",
            },
        }
    }

    r = requests.put(api_url, headers=h, json=api_body)
    if r.status_code in (200, 201):
        print(f"  Foundry API created (type=azure-ai-foundry)")
    elif r.status_code == 409:
        print(f"  API already exists")
    else:
        # Fallback: create as standard HTTP API with Foundry operations
        print(f"  azure-ai-foundry type returned {r.status_code}, falling back to HTTP API")
        api_body_fallback = {
            "properties": {
                "displayName": f"Foundry - {acct_name}",
                "description": "Microsoft Foundry V2 API — models, agents, chat",
                "path": "foundry",
                "protocols": ["https"],
                "serviceUrl": foundry_endpoint,
                "subscriptionRequired": False,
            }
        }
        r = requests.put(api_url, headers=h, json=api_body_fallback)
        if r.status_code in (200, 201):
            print(f"  API created (fallback HTTP type)")
        else:
            print(f"  ERROR: {r.status_code} {r.text[:400]}")
            return

        # Add operations manually for fallback
        print(f"\n  Adding operations...")
        operations = [
            {"id": "chat-completions", "name": "Chat Completions", "method": "POST",
             "template": "/openai/deployments/{deployment-id}/chat/completions"},
            {"id": "completions", "name": "Completions", "method": "POST",
             "template": "/openai/deployments/{deployment-id}/completions"},
            {"id": "embeddings", "name": "Embeddings", "method": "POST",
             "template": "/openai/deployments/{deployment-id}/embeddings"},
            {"id": "list-models", "name": "List Models", "method": "GET",
             "template": "/openai/models"},
            {"id": "list-deployments", "name": "List Deployments", "method": "GET",
             "template": "/openai/deployments"},
            {"id": "agents-create", "name": "Create Agent", "method": "POST",
             "template": "/agents"},
            {"id": "agents-list", "name": "List Agents", "method": "GET",
             "template": "/agents"},
        ]
        for op in operations:
            op_url = f"{ARM}{apim_id}/apis/foundry-api/operations/{op['id']}?api-version={apim_api}"
            op_body = {"properties": {"displayName": op["name"], "method": op["method"],
                                       "urlTemplate": op["template"]}}
            r = requests.put(op_url, headers=h, json=op_body)
            status = "OK" if r.status_code in (200, 201) else f"ERR {r.status_code}"
            print(f"    {op['name']}: {status}")

    # ================================================================
    # STEP 4: Fix operations — add template parameters
    # ================================================================
    print(f"\n{'='*60}")
    print("STEP 4: Fix operations (template parameters)")
    print("=" * 60)

    ops_with_deploy_param = [
        {"id": "chat-completions", "name": "Chat Completions", "method": "POST",
         "template": "/openai/deployments/{deployment-id}/chat/completions"},
        {"id": "completions", "name": "Completions", "method": "POST",
         "template": "/openai/deployments/{deployment-id}/completions"},
        {"id": "embeddings", "name": "Embeddings", "method": "POST",
         "template": "/openai/deployments/{deployment-id}/embeddings"},
    ]

    # Responses API uses model-scoped path (no deployment in URL)
    responses_op = {"id": "responses", "name": "Responses", "method": "POST",
                    "template": "/openai/responses"}
    op_url = f"{ARM}{apim_id}/apis/foundry-api/operations/{responses_op['id']}?api-version={apim_api}"
    op_body = {
        "properties": {
            "displayName": responses_op["name"],
            "method": responses_op["method"],
            "urlTemplate": responses_op["template"],
            "request": {
                "queryParameters": [
                    {"name": "api-version", "description": "API version",
                     "type": "string", "required": True}
                ]
            }
        }
    }
    r = requests.put(op_url, headers=h, json=op_body)
    status = "✓" if r.status_code in (200, 201) else f"✗ {r.status_code}"
    print(f"  Responses (model-scoped): {status}")

    for op in ops_with_deploy_param:
        op_url = f"{ARM}{apim_id}/apis/foundry-api/operations/{op['id']}?api-version={apim_api}"
        op_body = {
            "properties": {
                "displayName": op["name"],
                "method": op["method"],
                "urlTemplate": op["template"],
                "templateParameters": [
                    {"name": "deployment-id", "description": "Deployment name",
                     "type": "string", "required": True}
                ],
                "request": {
                    "queryParameters": [
                        {"name": "api-version", "description": "API version",
                         "type": "string", "required": True}
                    ]
                }
            }
        }
        r = requests.put(op_url, headers=h, json=op_body)
        status = "✓" if r.status_code in (200, 201) else f"✗ {r.status_code}"
        print(f"  {op['name']}: {status}")

    # ================================================================
    # STEP 5: Apply JWT validation + MI Auth Policy
    # ================================================================
    print(f"\n{'='*60}")
    print("STEP 5: Apply inbound policy (JWT + MI)")
    print("=" * 60)

    audience = jwt_cfg["audience"]
    groups = jwt_cfg.get("allowed_groups", [])
    openid_url = f"https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration"

    # Build optional group validation section
    group_section = ""
    if groups:
        groups_xml = "\n".join(f'                    <value>{g}</value>' for g in groups)
        group_section = f"""
        <!-- 2. Check group membership -->
        <validate-jwt header-name="Authorization" failed-validation-httpcode="403"
                      failed-validation-error-message="Forbidden. User is not in an authorized group.">
            <openid-config url="{openid_url}" />
            <audiences>
                <audience>{audience}</audience>
                <audience>api://{audience}</audience>
            </audiences>
            <issuers>
                <issuer>https://sts.windows.net/{tenant}/</issuer>
                <issuer>https://login.microsoftonline.com/{tenant}/v2.0</issuer>
            </issuers>
            <required-claims>
                <claim name="groups" match="any">
{groups_xml}
                </claim>
            </required-claims>
        </validate-jwt>"""
        print(f"  Group validation: {len(groups)} group(s)")
    else:
        print(f"  Group validation: skipped (none configured)")

    policy_xml = f"""<policies>
    <inbound>
        <base />
        <!-- 1. Validate user JWT (Entra ID) — accepts both v1 and v2 tokens -->
        <validate-jwt header-name="Authorization" failed-validation-httpcode="401"
                      failed-validation-error-message="Unauthorized"
                      require-expiration-time="true" require-scheme="Bearer"
                      require-signed-tokens="true">
            <openid-config url="{openid_url}" />
            <audiences>
                <audience>{audience}</audience>
                <audience>api://{audience}</audience>
            </audiences>
            <issuers>
                <issuer>https://sts.windows.net/{tenant}/</issuer>
                <issuer>https://login.microsoftonline.com/{tenant}/v2.0</issuer>
            </issuers>
        </validate-jwt>{group_section}
        <!-- 3. Replace user token with Managed Identity token -->
        <authentication-managed-identity resource="https://cognitiveservices.azure.com" output-token-variable-name="managed-id-token" />
        <set-header name="Authorization" exists-action="override">
            <value>@("Bearer " + (string)context.Variables["managed-id-token"])</value>
        </set-header>
        <set-header name="Ocp-Apim-Subscription-Key" exists-action="delete" />
        <!-- 4. Route to Foundry endpoint -->
        <set-backend-service base-url="{foundry_endpoint}" />
    </inbound>
    <backend>
        <base />
    </backend>
    <outbound>
        <base />
    </outbound>
    <on-error>
        <base />
    </on-error>
</policies>"""

    policy_url = f"{ARM}{apim_id}/apis/foundry-api/policies/policy?api-version={apim_api}"
    policy_body = {"properties": {"format": "xml", "value": policy_xml}}

    r = requests.put(policy_url, headers=h, json=policy_body)
    if r.status_code in (200, 201):
        print(f"  Policy applied:")
        print(f"    - JWT validation (Entra ID)")
        print(f"    - Group claims check ({len(jwt_cfg['allowed_groups'])} groups)")
        print(f"    - MI token swap (cognitiveservices.azure.com)")
        print(f"    - Backend: {foundry_endpoint}")
    else:
        print(f"  ERROR: {r.status_code} {r.text[:400]}")

    # ================================================================
    # Summary
    # ================================================================
    print(f"\n{'='*60}")
    print("APIM Setup Complete")
    print("=" * 60)
    print(f"  APIM Gateway:   {apim_gateway}")
    print(f"  API Path:       /foundry")
    print(f"  Backend:        {foundry_endpoint}")
    print(f"  Auth:           JWT (Entra ID) → group check → MI swap")
    print(f"\n  Test URL: {apim_gateway}/foundry/openai/deployments/{cfg['model']['deployment_name']}/chat/completions?api-version=2024-12-01-preview")
    print(f"\nDone. Run 05-test-endpoints.py next.")


if __name__ == "__main__":
    run()

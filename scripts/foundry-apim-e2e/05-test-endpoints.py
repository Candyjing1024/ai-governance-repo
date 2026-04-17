"""
05 - Test APIM endpoints with JWT authentication.

Gets a user JWT via az CLI, then tests:
  1. List Models          (GET  /openai/models)
  2. Chat Completions V1  (POST /openai/deployments/{id}/chat/completions)
  3. Responses API        (POST /openai/responses  — model-scoped, not deployment-scoped)
All requests go through APIM → JWT validated → MI swap → Foundry.
"""
import json, sys, os, subprocess, base64, requests
sys.path.insert(0, os.path.dirname(__file__))
from _auth import load_config, arm_headers, ARM, account_id, get_sp_token


def get_user_jwt(app_id):
    """Get a user JWT for the app registration audience via az CLI."""
    r = subprocess.run(
        ["az.cmd", "account", "get-access-token",
         "--resource", f"api://{app_id}",
         "--query", "accessToken", "-o", "tsv"],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print(f"  ERROR getting JWT: {r.stderr.strip()[:200]}")
        return None
    return r.stdout.strip()


def decode_jwt_claims(token):
    """Decode JWT payload (no verification) to inspect claims."""
    parts = token.split(".")
    if len(parts) < 2:
        return {}
    payload = parts[1]
    payload += "=" * (-len(payload) % 4)  # pad base64url to multiple of 4
    return json.loads(base64.urlsafe_b64decode(payload))


def test_endpoint(label, method, url, headers, body=None):
    """Call an endpoint and print result summary."""
    print(f"\n  --- {label} ---")
    print(f"  {method} {url}")
    r = requests.request(method, url, headers=headers, json=body)
    print(f"  Status: {r.status_code}")

    if r.status_code in (200, 201):
        data = r.json()
        text = json.dumps(data, indent=2)
        print(f"  {text[:500]}{'...' if len(text) > 500 else ''}")
        return data
    else:
        print(f"  {r.text[:300]}")
        return None


def run():
    cfg = load_config()
    h_arm = arm_headers(cfg)
    deploy_name = cfg["model"]["deployment_name"]
    app_id = cfg["jwt_policy"]["audience"]
    oai_api = "2024-12-01-preview"  # latest stable for chat/completions
    responses_api = "2025-03-01-preview"  # Responses API version

    # Get APIM gateway URL
    apim_name = cfg["apim"]["name"]
    apim_url = f"{ARM}/subscriptions/{cfg['subscription_id']}/resourceGroups/{cfg['resource_group']}" \
               f"/providers/Microsoft.ApiManagement/service/{apim_name}?api-version={cfg['apim']['api_version']}"
    r = requests.get(apim_url, headers=h_arm)
    gateway = r.json().get("properties", {}).get("gatewayUrl", "").rstrip("/")

    print("=" * 70)
    print("E2E Test: User JWT → APIM → Foundry")
    print("=" * 70)
    print(f"  APIM Gateway: {gateway}")
    print(f"  Deployment:   {deploy_name}")
    print(f"  JWT Audience: {app_id}")

    # ================================================================
    # STEP 1: Get user JWT
    # ================================================================
    print(f"\n{'='*70}")
    print("STEP 1: Acquire user JWT from Entra ID")
    print("=" * 70)

    jwt_token = get_user_jwt(app_id)
    if not jwt_token:
        print("\n  Cannot proceed without JWT. Ensure:")
        print(f"    1. App registration {app_id} has identifier URI api://{app_id}")
        print(f"    2. Azure CLI is pre-authorized on the app")
        print(f"    3. Run: az account get-access-token --resource api://{app_id}")
        return

    claims = decode_jwt_claims(jwt_token)
    print(f"  ✅ JWT acquired")
    print(f"  Audience: {claims.get('aud', '?')}")
    print(f"  Issuer:   {claims.get('iss', '?')}")
    print(f"  Name:     {claims.get('name', '?')}")
    print(f"  Scope:    {claims.get('scp', '?')}")
    groups = claims.get("groups", [])
    print(f"  Groups:   {groups if groups else '(none)'}")

    h_jwt = {"Authorization": f"Bearer {jwt_token}", "Content-Type": "application/json"}

    # ================================================================
    # STEP 2: Test List Models via APIM
    # ================================================================
    print(f"\n{'='*70}")
    print("STEP 2: List Models via APIM (GET)")
    print("=" * 70)
    print(f"  API version: {oai_api}")

    result = test_endpoint(
        "List Models",
        "GET",
        f"{gateway}/foundry/openai/models?api-version={oai_api}",
        h_jwt
    )
    if result:
        models = result.get("data", [])
        print(f"\n  ✅ {len(models)} models returned")

    # ================================================================
    # STEP 3: Chat Completions via APIM (V1 path)
    # ================================================================
    print(f"\n{'='*70}")
    print("STEP 3: Chat Completions via APIM (POST)")
    print("=" * 70)
    print(f"  Path: /openai/deployments/{deploy_name}/chat/completions")
    print(f"  API version: {oai_api}")

    chat_body = {
        "messages": [{"role": "user", "content": "Say 'APIM JWT test successful!' and nothing else."}],
        "max_tokens": 50,
    }

    result = test_endpoint(
        "Chat Completions",
        "POST",
        f"{gateway}/foundry/openai/deployments/{deploy_name}/chat/completions?api-version={oai_api}",
        h_jwt,
        chat_body
    )
    if result:
        reply = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        print(f"\n  ✅ Response: {reply}")

    # ================================================================
    # STEP 4: Responses API via APIM (latest path)
    # ================================================================
    print(f"\n{'='*70}")
    print("STEP 4: Responses API via APIM (POST) — latest")
    print("=" * 70)
    print(f"  Path: /openai/responses (model-scoped, model in body)")
    print(f"  API version: {responses_api}")
    print(f"  (This is the newer replacement for chat/completions)")

    responses_body = {
        "model": deploy_name,
        "input": "Say 'Responses API test successful!' and nothing else.",
        "max_output_tokens": 50,
    }

    result = test_endpoint(
        "Responses API",
        "POST",
        f"{gateway}/foundry/openai/responses?api-version={responses_api}",
        h_jwt,
        responses_body
    )
    if result:
        # Responses API returns output in a different structure
        output_text = ""
        for item in result.get("output", []):
            if item.get("type") == "message":
                for c in item.get("content", []):
                    output_text += c.get("text", "")
        if output_text:
            print(f"\n  ✅ Response: {output_text}")
        else:
            print(f"\n  ✅ Response received (check JSON above)")

    # ================================================================
    # Summary
    # ================================================================
    print(f"\n{'='*70}")
    print("E2E Test Summary")
    print("=" * 70)
    print(f"  Flow: User JWT → APIM validates → MI swap → Foundry → Response")
    print(f"")
    print(f"  Tested endpoints via APIM ({gateway}):")
    print(f"    1. GET  /foundry/openai/models                                    (api-version={oai_api})")
    print(f"    2. POST /foundry/openai/deployments/{deploy_name}/chat/completions (api-version={oai_api})")
    print(f"    3. POST /foundry/openai/responses                                 (api-version={responses_api})")
    print(f"")
    print(f"  Auth chain:")
    print(f"    User → Entra ID JWT (aud={app_id})")
    print(f"    APIM → validates JWT signature, audience, issuer")
    print(f"    APIM → swaps to Managed Identity token")
    print(f"    Foundry → processes request with MI auth")


if __name__ == "__main__":
    run()

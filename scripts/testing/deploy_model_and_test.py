"""Deploy gpt-4o model on the new AIServices account and re-test the agent."""
import json
import time
import requests
from azure.identity import DefaultAzureCredential

SUB_ID = "a3223db3-76f2-4a7c-8684-57b835dc77e7"
RG = "rg-chubb-mcp-poc"
ARM = "https://management.azure.com"
ACCOUNT_NAME = "proj-chubb-storage-val-resource"
PROJECT_NAME = "proj-chubb-storage-val"
AGENT_ID = "asst_jRfE1bi4RV39diHnbL5k0FdI"

cred = DefaultAzureCredential()


def get_headers():
    token = cred.get_token("https://management.azure.com/.default").token
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ============================================================
# STEP 1: Deploy gpt-4o on the AIServices account
# ============================================================
def deploy_model():
    print("=" * 60)
    print("STEP 1: Deploy gpt-4o on AIServices account")
    print("=" * 60)

    headers = get_headers()
    base = (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
            f"/providers/Microsoft.CognitiveServices/accounts/{ACCOUNT_NAME}")

    # Check existing deployments
    r = requests.get(f"{base}/deployments?api-version=2024-10-01", headers=headers)
    existing = [d.get("name") for d in r.json().get("value", [])] if r.status_code == 200 else []
    print(f"  Existing deployments: {existing}")

    if "gpt-4o" in existing:
        print("  gpt-4o already deployed!")
        return True

    # Deploy gpt-4o
    deploy_body = {
        "sku": {
            "name": "GlobalStandard",
            "capacity": 10
        },
        "properties": {
            "model": {
                "format": "OpenAI",
                "name": "gpt-4o",
                "version": "2024-11-20"
            }
        }
    }

    url = f"{base}/deployments/gpt-4o?api-version=2024-10-01"
    print(f"  Creating gpt-4o deployment...")
    r = requests.put(url, headers=headers, json=deploy_body)
    print(f"  HTTP {r.status_code}")

    if r.status_code not in (200, 201, 202):
        print(f"  Error: {r.text[:500]}")
        # Try Standard SKU instead
        print("\n  Retrying with Standard SKU...")
        deploy_body["sku"]["name"] = "Standard"
        r = requests.put(url, headers=headers, json=deploy_body)
        print(f"  HTTP {r.status_code}")
        if r.status_code not in (200, 201, 202):
            print(f"  Error: {r.text[:500]}")
            return False

    state = r.json().get("properties", {}).get("provisioningState", "?")
    print(f"  Provisioning state: {state}")

    # Wait for deployment to complete
    if state not in ("Succeeded", "Running"):
        print("  Waiting for deployment...")
        for i in range(30):
            time.sleep(10)
            r2 = requests.get(url, headers=headers)
            if r2.status_code == 200:
                state = r2.json().get("properties", {}).get("provisioningState", "?")
                print(f"    {i*10}s: {state}")
                if state == "Succeeded":
                    break
                if state == "Failed":
                    print(f"    FAILED: {r2.text[:300]}")
                    return False

    # Verify
    r = requests.get(f"{base}/deployments?api-version=2024-10-01", headers=headers)
    if r.status_code == 200:
        deps = r.json().get("value", [])
        print(f"\n  All deployments ({len(deps)}):")
        for d in deps:
            name = d.get("name", "?")
            model = d.get("properties", {}).get("model", {})
            model_name = model.get("name", "?") if isinstance(model, dict) else str(model)
            state = d.get("properties", {}).get("provisioningState", "?")
            print(f"    {name}: model={model_name} state={state}")

    return True


# ============================================================
# STEP 2: Re-test the agent
# ============================================================
def test_agent():
    print("\n" + "=" * 60)
    print("STEP 2: Test agent with deployed model")
    print("=" * 60)

    from azure.ai.agents import AgentsClient
    from azure.ai.agents.models import MessageRole

    endpoint = (f"https://{ACCOUNT_NAME}.services.ai.azure.com"
                f"/api/projects/{PROJECT_NAME}")
    client = AgentsClient(endpoint=endpoint, credential=cred)

    # Create new thread and run
    thread = client.threads.create()
    print(f"  Thread: {thread.id}")

    client.messages.create(
        thread_id=thread.id,
        role=MessageRole.USER,
        content="What is Chubb's AI governance policy?",
    )

    start = time.time()
    run = client.runs.create_and_process(
        thread_id=thread.id,
        agent_id=AGENT_ID,
    )
    elapsed = time.time() - start
    print(f"  Run: {run.id}")
    print(f"  Status: {run.status}")
    print(f"  Time: {elapsed:.1f}s")

    if hasattr(run, "last_error") and run.last_error:
        print(f"  Error: {run.last_error.code} - {run.last_error.message}")

    if hasattr(run, "usage") and run.usage:
        print(f"  Tokens: {run.usage.prompt_tokens}+{run.usage.completion_tokens}={run.usage.total_tokens}")

    # Get assistant response
    response = client.messages.get_last_message_text_by_role(
        thread_id=thread.id,
        role=MessageRole.AGENT,
    )
    if response:
        text = response.text.value if hasattr(response, "text") else str(response)
        print(f"\n  Response ({len(text)} chars):")
        print(f"  {text[:500]}")
    else:
        print("  No response from agent")

    return thread.id, run.status


if __name__ == "__main__":
    ok = deploy_model()
    if ok:
        thread_id, status = test_agent()
        print(f"\n  Result: {'SUCCESS' if 'completed' in str(status).lower() else 'FAILED'}")
    else:
        print("\nModel deployment failed. Cannot test agent.")

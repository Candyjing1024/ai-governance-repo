"""Diagnose why the agent run failed: check model deployments and run error details."""
import json
import requests
from azure.identity import DefaultAzureCredential

SUB_ID = "a3223db3-76f2-4a7c-8684-57b835dc77e7"
RG = "rg-chubb-mcp-poc"
ARM = "https://management.azure.com"
ACCOUNT_NAME = "proj-chubb-storage-val-resource"
PROJECT_NAME = "proj-chubb-storage-val"
AGENT_ID = "asst_jRfE1bi4RV39diHnbL5k0FdI"
THREAD_ID = "thread_8UaMatlU75vsi5xZEGxmPNTD"
RUN_ID = "run_AnjLWqfQNin79IWUng6KlrA6"

cred = DefaultAzureCredential()


def get_arm_headers():
    token = cred.get_token("https://management.azure.com/.default").token
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def check_deployments():
    print("=" * 60)
    print("CHECK 1: Model deployments on AIServices account")
    print("=" * 60)
    headers = get_arm_headers()

    for api in ["2024-10-01", "2025-06-01", "2026-01-15-preview"]:
        url = (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
               f"/providers/Microsoft.CognitiveServices/accounts/{ACCOUNT_NAME}"
               f"/deployments?api-version={api}")
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            deps = r.json().get("value", [])
            print(f"\n  API {api}: {len(deps)} deployment(s)")
            for d in deps:
                name = d.get("name", "?")
                model = d.get("properties", {}).get("model", {})
                model_name = model.get("name", "?") if isinstance(model, dict) else str(model)
                model_ver = model.get("version", "?") if isinstance(model, dict) else "?"
                sku = d.get("sku", {})
                state = d.get("properties", {}).get("provisioningState", "?")
                print(f"    {name}: model={model_name} v{model_ver}  sku={sku}  state={state}")
            break
        else:
            print(f"  API {api}: HTTP {r.status_code}")

    # Also check the OAI account
    print(f"\n  --- Deployments on oai-chubb-mcp-9342 ---")
    for api in ["2024-10-01", "2025-06-01"]:
        url = (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
               f"/providers/Microsoft.CognitiveServices/accounts/oai-chubb-mcp-9342"
               f"/deployments?api-version={api}")
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            deps = r.json().get("value", [])
            print(f"  API {api}: {len(deps)} deployment(s)")
            for d in deps:
                name = d.get("name", "?")
                model = d.get("properties", {}).get("model", {})
                model_name = model.get("name", "?") if isinstance(model, dict) else str(model)
                print(f"    {name}: model={model_name}")
            break


def check_run_error():
    print("\n" + "=" * 60)
    print("CHECK 2: Run error details")
    print("=" * 60)

    from azure.ai.agents import AgentsClient

    # Use project-level endpoint
    endpoint = (f"https://{ACCOUNT_NAME}.services.ai.azure.com"
                f"/api/projects/{PROJECT_NAME}")
    client = AgentsClient(endpoint=endpoint, credential=cred)

    # Get run details
    run = client.runs.get(thread_id=THREAD_ID, run_id=RUN_ID)
    print(f"  Status: {run.status}")
    print(f"  Model: {run.model}")
    if hasattr(run, "last_error") and run.last_error:
        print(f"  Error code: {run.last_error.code}")
        print(f"  Error message: {run.last_error.message}")
    if hasattr(run, "incomplete_details") and run.incomplete_details:
        print(f"  Incomplete: {run.incomplete_details}")

    # List run steps
    print("\n  Run steps:")
    steps = client.run_steps.list(thread_id=THREAD_ID, run_id=RUN_ID)
    for step in steps:
        print(f"    Step {step.id}: type={step.type} status={step.status}")
        if hasattr(step, "last_error") and step.last_error:
            print(f"      Error: {step.last_error}")
        if hasattr(step, "step_details") and step.step_details:
            print(f"      Details: {str(step.step_details)[:300]}")

    # List agents on project
    print("\n  All agents on project:")
    agents = client.list_agents()
    for a in agents:
        print(f"    {a.id}: {a.name} model={a.model}")


def check_oai_connection_details():
    print("\n" + "=" * 60)
    print("CHECK 3: OpenAI connection details")
    print("=" * 60)
    headers = get_arm_headers()
    url = (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
           f"/providers/Microsoft.CognitiveServices/accounts/{ACCOUNT_NAME}"
           f"/connections/oai-chubb-connection?api-version=2026-01-15-preview")
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        conn = r.json()
        props = conn.get("properties", {})
        print(f"  Category: {props.get('category')}")
        print(f"  Target: {props.get('target')}")
        print(f"  AuthType: {props.get('authType')}")
        meta = props.get("metadata", {})
        if meta:
            print(f"  Metadata: {json.dumps(meta, indent=4)}")
    else:
        print(f"  HTTP {r.status_code}: {r.text[:300]}")


if __name__ == "__main__":
    check_deployments()
    check_run_error()
    check_oai_connection_details()

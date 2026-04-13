"""Delete old hub + project via ARM REST API."""
import time
import requests
from azure.identity import DefaultAzureCredential

SUB_ID = "a3223db3-76f2-4a7c-8684-57b835dc77e7"
RG = "rg-chubb-mcp-poc"
ARM = "https://management.azure.com"
API = "2025-01-01-preview"


def get_headers():
    cred = DefaultAzureCredential()
    token = cred.get_token("https://management.azure.com/.default").token
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def delete_resource(name):
    headers = get_headers()
    url = (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
           f"/providers/Microsoft.MachineLearningServices/workspaces/{name}"
           f"?api-version={API}")

    # Check exists
    r = requests.get(url, headers=headers)
    if r.status_code == 404:
        print(f"  {name}: already deleted")
        return True

    print(f"  {name}: exists (state={r.json().get('properties',{}).get('provisioningState','?')})")
    print(f"  Deleting {name}...")
    r = requests.delete(url, headers=headers)
    print(f"  DELETE: HTTP {r.status_code}")

    # Poll
    for i in range(40):
        time.sleep(10)
        r2 = requests.get(url, headers=headers)
        if r2.status_code == 404:
            print(f"  {name}: DELETED")
            return True
        state = r2.json().get("properties", {}).get("provisioningState", "?")
        print(f"  {name}: {state} ({i+1}/40)")
    print(f"  {name}: TIMEOUT")
    return False


def main():
    print("Deleting old hub + project...")

    # Delete project first (child of hub)
    delete_resource("proj-chubb-storage-val")

    # Delete hub
    delete_resource("hub-chubb-storage-val")

    # Verify
    print("\nVerifying - listing remaining workspaces in RG:")
    headers = get_headers()
    url = (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
           f"/providers/Microsoft.MachineLearningServices/workspaces"
           f"?api-version={API}")
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        for ws in r.json().get("value", []):
            print(f"  {ws['name']} (kind={ws.get('kind','?')}, state={ws.get('properties',{}).get('provisioningState','?')})")
        if not r.json().get("value"):
            print("  (none remaining)")
    print("\nDone. Now create the new project from the Foundry portal.")


if __name__ == "__main__":
    main()

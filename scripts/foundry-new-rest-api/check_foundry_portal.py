"""
Diagnose why project doesn't open in AI Foundry portal.
Check project/hub details and construct correct portal URLs.
"""
import json
import requests
from azure.identity import DefaultAzureCredential

SUB_ID = "a3223db3-76f2-4a7c-8684-57b835dc77e7"
RG = "rg-chubb-mcp-poc"
ARM = "https://management.azure.com"
HUB_NAME = "hub-chubb-storage-val"
PROJECT_NAME = "proj-chubb-storage-val"


def get_headers():
    cred = DefaultAzureCredential()
    token = cred.get_token("https://management.azure.com/.default").token
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def main():
    headers = get_headers()

    # 1. Get Hub details
    print("=" * 60)
    print("HUB DETAILS")
    print("=" * 60)
    hub_url = (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
               f"/providers/Microsoft.MachineLearningServices/workspaces/{HUB_NAME}"
               f"?api-version=2025-01-01-preview")
    r = requests.get(hub_url, headers=headers)
    if r.status_code == 200:
        hub = r.json()
        props = hub.get("properties", {})
        print(f"  Name: {hub.get('name')}")
        print(f"  Kind: {hub.get('kind')}")
        print(f"  Location: {hub.get('location')}")
        print(f"  State: {props.get('provisioningState')}")
        print(f"  WorkspaceId: {props.get('workspaceId', 'N/A')}")
        print(f"  DiscoveryUrl: {props.get('discoveryUrl', 'N/A')}")
        print(f"  MlFlowTrackingUri: {props.get('mlFlowTrackingUri', 'N/A')}")
        print(f"  Hub resource ID: {hub.get('id')}")
        hub_id = props.get('workspaceId', '')
        
        # Dump ALL properties for diagnosis
        print(f"\n  All property keys: {sorted(props.keys())}")
        for key in ['studioWebPortalUrl', 'portalUrl', 'notebookInfo', 'workspaceHubConfig']:
            if key in props:
                val = props[key]
                print(f"  {key}: {json.dumps(val) if isinstance(val, (dict, list)) else val}")
    else:
        print(f"  ERROR: HTTP {r.status_code}: {r.text[:300]}")
        hub_id = ""

    # 2. Get Project details
    print("\n" + "=" * 60)
    print("PROJECT DETAILS")
    print("=" * 60)
    proj_url = (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
                f"/providers/Microsoft.MachineLearningServices/workspaces/{PROJECT_NAME}"
                f"?api-version=2025-01-01-preview")
    r = requests.get(proj_url, headers=headers)
    if r.status_code == 200:
        proj = r.json()
        props = proj.get("properties", {})
        print(f"  Name: {proj.get('name')}")
        print(f"  Kind: {proj.get('kind')}")
        print(f"  Location: {proj.get('location')}")
        print(f"  State: {props.get('provisioningState')}")
        print(f"  WorkspaceId: {props.get('workspaceId', 'N/A')}")
        print(f"  HubResourceId: {props.get('hubResourceId', 'N/A')}")
        print(f"  DiscoveryUrl: {props.get('discoveryUrl', 'N/A')}")
        print(f"  AgentsEndpointUri: {props.get('agentsEndpointUri', 'N/A')}")
        print(f"  Project resource ID: {proj.get('id')}")
        proj_workspace_id = props.get('workspaceId', '')
        
        print(f"\n  All property keys: {sorted(props.keys())}")
        for key in ['studioWebPortalUrl', 'portalUrl', 'notebookInfo']:
            if key in props:
                val = props[key]
                print(f"  {key}: {json.dumps(val) if isinstance(val, (dict, list)) else val}")
    else:
        print(f"  ERROR: HTTP {r.status_code}: {r.text[:300]}")
        proj_workspace_id = ""

    # 3. List ALL workspaces in the RG to see what portal shows
    print("\n" + "=" * 60)
    print("ALL WORKSPACES IN RESOURCE GROUP")
    print("=" * 60)
    list_url = (f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}"
                f"/providers/Microsoft.MachineLearningServices/workspaces"
                f"?api-version=2025-01-01-preview")
    r = requests.get(list_url, headers=headers)
    if r.status_code == 200:
        workspaces = r.json().get("value", [])
        for ws in workspaces:
            name = ws.get("name", "?")
            kind = ws.get("kind", "?")
            state = ws.get("properties", {}).get("provisioningState", "?")
            ws_id = ws.get("properties", {}).get("workspaceId", "?")
            print(f"  {name} (kind={kind}, state={state}, wsId={ws_id})")

    # 4. Generate portal URLs
    print("\n" + "=" * 60)
    print("PORTAL URLs TO TRY")
    print("=" * 60)
    
    # Format 1: New AI Foundry format
    print(f"\n  Format 1 - AI Foundry (new):")
    print(f"    https://ai.azure.com/manage/project/overview"
          f"?wsid=/subscriptions/{SUB_ID}/resourceGroups/{RG}"
          f"/providers/Microsoft.MachineLearningServices/workspaces/{PROJECT_NAME}")
    
    # Format 2: AI Studio legacy
    print(f"\n  Format 2 - AI Studio (legacy):")
    print(f"    https://ai.azure.com/build/overview"
          f"?wsid=/subscriptions/{SUB_ID}/resourceGroups/{RG}"
          f"/providers/Microsoft.MachineLearningServices/workspaces/{PROJECT_NAME}")

    # Format 3: ML Studio 
    print(f"\n  Format 3 - ML Studio:")
    print(f"    https://ml.azure.com/home?wsid=/subscriptions/{SUB_ID}"
          f"/resourceGroups/{RG}/providers/Microsoft.MachineLearningServices"
          f"/workspaces/{PROJECT_NAME}")

    # Format 4: Portal direct
    print(f"\n  Format 4 - Azure Portal resource:")
    print(f"    https://portal.azure.com/#@/resource/subscriptions/{SUB_ID}"
          f"/resourceGroups/{RG}/providers/Microsoft.MachineLearningServices"
          f"/workspaces/{PROJECT_NAME}/overview")

    # Format 5: Foundry with workspace GUID
    if proj_workspace_id:
        print(f"\n  Format 5 - AI Foundry with workspace GUID:")
        print(f"    https://ai.azure.com/project/{proj_workspace_id}")

    # 5. Check if we can discover the portal URL from discovery endpoint
    print("\n" + "=" * 60)
    print("DISCOVERY ENDPOINT CHECK")
    print("=" * 60)
    r = requests.get(proj_url, headers=headers)
    if r.status_code == 200:
        discovery = r.json().get("properties", {}).get("discoveryUrl", "")
        if discovery:
            print(f"  Discovery URL: {discovery}")
            try:
                dr = requests.get(discovery, headers=headers, timeout=10)
                print(f"  Discovery response: HTTP {dr.status_code}")
                if dr.status_code == 200:
                    disc_data = dr.json()
                    print(f"  Discovery data: {json.dumps(disc_data, indent=2)[:500]}")
                    if "studio" in str(disc_data).lower() or "portal" in str(disc_data).lower():
                        print("  Found portal-related URL in discovery!")
            except Exception as e:
                print(f"  Discovery error: {str(e)[:100]}")

    # 6. Try the Management Center approach - check connected resources
    print("\n" + "=" * 60)
    print("MANAGEMENT CENTER - Connected Resources")
    print("=" * 60)
    print(f"\n  Azure Portal path to configure Agent Service:")
    print(f"    1. Go to: https://portal.azure.com")
    print(f"    2. Search for: {PROJECT_NAME}")
    print(f"    3. Or navigate: Resource Groups > {RG} > {PROJECT_NAME}")
    print(f"    4. This opens the Azure ML workspace resource page")
    print(f"    5. Click 'Launch studio' button to open in AI Foundry")


if __name__ == "__main__":
    main()

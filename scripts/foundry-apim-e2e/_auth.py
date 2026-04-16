"""Shared auth + config loader for all scripts in this folder."""
import json, os, sys, time, requests

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def get_sp_token(cfg, scope="https://management.azure.com/.default"):
    """Get an OAuth2 token using service principal client credentials."""
    sp = cfg["service_principal"]
    r = requests.post(
        f"https://login.microsoftonline.com/{cfg['tenant_id']}/oauth2/v2.0/token",
        data={
            "grant_type": "client_credentials",
            "client_id": sp["client_id"],
            "client_secret": sp["client_secret"],
            "scope": scope,
        },
    )
    r.raise_for_status()
    return r.json()["access_token"]


def arm_headers(cfg):
    token = get_sp_token(cfg)
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


ARM = "https://management.azure.com"


def rg_id(cfg):
    return f"/subscriptions/{cfg['subscription_id']}/resourceGroups/{cfg['resource_group']}"


def account_id(cfg):
    return f"{rg_id(cfg)}/providers/Microsoft.CognitiveServices/accounts/{cfg['foundry']['account_name']}"


def project_id(cfg):
    return f"{account_id(cfg)}/projects/{cfg['foundry']['project_name']}"


def poll(url, headers, label, max_wait=600, interval=15):
    """Poll until provisioningState is terminal."""
    for i in range(max_wait // interval):
        r = requests.get(url, headers=headers)
        if r.status_code == 404:
            print(f"  {label}: DELETED")
            return "Deleted"
        if r.status_code == 200:
            state = r.json().get("properties", {}).get("provisioningState", "Unknown")
            print(f"  {label}: {state}  ({(i+1)*interval}s)")
            if state in ("Succeeded", "succeeded"):
                return "Succeeded"
            if state in ("Failed", "failed"):
                print(f"    {r.text[:300]}")
                return "Failed"
        time.sleep(interval)
    return "Timeout"

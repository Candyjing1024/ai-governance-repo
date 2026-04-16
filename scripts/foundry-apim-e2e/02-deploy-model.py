"""
02 - Deploy a model on the Foundry V2 account.

Uses CognitiveServices deployments API (2025-12-01).
Deploys the model specified in config.json.
"""
import json, sys, os, time, requests
sys.path.insert(0, os.path.dirname(__file__))
from _auth import load_config, arm_headers, ARM, account_id, poll


def run():
    cfg = load_config()
    h = arm_headers(cfg)
    api = cfg["foundry"]["api_version"]
    m = cfg["model"]
    deploy_name = m["deployment_name"]
    acct = account_id(cfg)

    print("=" * 60)
    print(f"Deploy model: {m['name']}/{m['version']} as '{deploy_name}'")
    print("=" * 60)

    deploy_url = f"{ARM}{acct}/deployments/{deploy_name}?api-version={api}"

    # Check if exists
    r = requests.get(deploy_url, headers=h)
    if r.status_code == 200:
        state = r.json()["properties"].get("provisioningState", "?")
        print(f"  Deployment already exists (state={state})")
        return

    body = {
        "sku": {"name": m["sku"], "capacity": m["capacity"]},
        "properties": {
            "model": {
                "format": "OpenAI",
                "name": m["name"],
                "version": m["version"],
            }
        },
    }

    r = requests.put(deploy_url, headers=h, json=body)
    if r.status_code in (200, 201, 202):
        print(f"  Deploying... (HTTP {r.status_code})")
    else:
        print(f"  ERROR: {r.status_code} {r.text[:400]}")
        return

    poll(deploy_url, h, f"Deployment '{deploy_name}'")

    # List all deployments
    print(f"\n{'='*60}")
    print("All deployments on account:")
    print("=" * 60)
    r = requests.get(f"{ARM}{acct}/deployments?api-version={api}", headers=h)
    for d in r.json().get("value", []):
        dm = d["properties"]["model"]
        print(f"  {d['name']:20s} {dm['name']}/{dm['version']}  sku={d['sku']['name']}")

    print(f"\nDone. Run 03-create-agent.py next.")


if __name__ == "__main__":
    run()

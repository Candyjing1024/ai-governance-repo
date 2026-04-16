"""
03 - Create an Agent on the Foundry V2 project.

Uses the Foundry V2 Agent REST API (data plane):
  POST {project-endpoint}/agents?api-version=2025-05-01
"""
import json, sys, os, requests
sys.path.insert(0, os.path.dirname(__file__))
from _auth import load_config, arm_headers, ARM, account_id, project_id


def _get_project_endpoint(cfg):
    """Read the project's data-plane endpoint from ARM."""
    h = arm_headers(cfg)
    api = cfg["foundry"]["api_version"]
    url = f"{ARM}{project_id(cfg)}?api-version={api}"
    r = requests.get(url, headers=h)
    r.raise_for_status()
    proj = r.json()
    # V2 projects expose endpoints dict
    endpoints = proj.get("properties", {}).get("endpoints", {})
    # Prefer "AI Foundry API" (V2), then fallback keys
    for key in ["AI Foundry API", "AI Services", "Azure OpenAI", "OpenAI"]:
        if key in endpoints:
            return endpoints[key]
    # Fallback: use the account endpoint
    acct_url = f"{ARM}{account_id(cfg)}?api-version={api}"
    r2 = requests.get(acct_url, headers=h)
    return r2.json().get("properties", {}).get("endpoint", "")


def _get_agent_token(cfg):
    """Get a token for the Foundry V2 data-plane (ai.azure.com scope)."""
    from _auth import get_sp_token
    return get_sp_token(cfg, scope="https://ai.azure.com/.default")


def run():
    cfg = load_config()
    agent_cfg = cfg["agent"]
    model_cfg = cfg["model"]

    endpoint = _get_project_endpoint(cfg)
    if not endpoint:
        print("ERROR: Could not determine project endpoint")
        return

    # Strip trailing slash
    endpoint = endpoint.rstrip("/")
    print("=" * 60)
    print(f"Create Agent: {agent_cfg['name']}")
    print("=" * 60)
    print(f"  Project endpoint: {endpoint}")
    print(f"  Model: {model_cfg['deployment_name']}")

    token = _get_agent_token(cfg)
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # ---- List existing agents ----
    agent_api = "2025-05-15-preview"
    r = requests.get(f"{endpoint}/agents?api-version={agent_api}", headers=h)
    if r.status_code == 200:
        agents = r.json().get("data", r.json().get("value", []))
        existing = [a for a in agents if a.get("name") == agent_cfg["name"] or a.get("id") == agent_cfg["name"]]
        if existing:
            agent = existing[0]
            print(f"  Agent already exists: {agent.get('id')}  (keys: {list(agent.keys())})")
    elif r.status_code != 404:
        print(f"  List agents: HTTP {r.status_code} {r.text[:200]}")

    if "agent" not in dir():
        # ---- Create agent ----
        # 2025-05-15-preview requires top-level name + definition with kind
        body = {
            "name": agent_cfg["name"],
            "definition": {
                "kind": "prompt",
                "model": model_cfg["deployment_name"],
                "instructions": agent_cfg["instructions"],
            }
        }

        r = requests.post(f"{endpoint}/agents?api-version={agent_api}", headers=h, json=body)
        if r.status_code in (200, 201):
            agent = r.json()
            print(f"  Agent created!")
            print(f"  ID: {agent.get('id')}")
            print(f"  Model: {agent.get('model', agent.get('definition', {}).get('model'))}")
        else:
            print(f"  ERROR: {r.status_code} {r.text[:400]}")
            return

    # ---- Quick test: chat completion via project endpoint ----
    print(f"\n{'='*60}")
    print("Quick test: chat completion via project endpoint")
    print("=" * 60)

    # Use OpenAI-compatible chat endpoint on the project
    oai_api = "2024-12-01-preview"
    # Need cognitiveservices token for OpenAI-compatible endpoint
    from _auth import get_sp_token
    oai_token = get_sp_token(cfg, scope="https://cognitiveservices.azure.com/.default")
    oai_h = {"Authorization": f"Bearer {oai_token}", "Content-Type": "application/json"}

    # Get the account endpoint (OpenAI-compatible)
    from _auth import account_id
    acct_url = f"{ARM}{account_id(cfg)}?api-version={cfg['foundry']['api_version']}"
    r = requests.get(acct_url, headers=arm_headers(cfg))
    acct_endpoint = r.json().get("properties", {}).get("endpoint", "").rstrip("/")

    chat_body = {
        "messages": [
            {"role": "system", "content": agent_cfg["instructions"]},
            {"role": "user", "content": "Hello, what can you do?"},
        ],
        "model": model_cfg["deployment_name"],
    }
    r = requests.post(
        f"{acct_endpoint}/openai/deployments/{model_cfg['deployment_name']}/chat/completions?api-version={oai_api}",
        headers=oai_h,
        json=chat_body,
    )
    if r.status_code == 200:
        reply = r.json()["choices"][0]["message"]["content"]
        print(f"  [user] Hello, what can you do?")
        print(f"  [assistant] {reply[:200]}")
    else:
        print(f"  Chat failed: {r.status_code} {r.text[:300]}")

    agent_name = agent.get("id", agent.get("name", ""))
    print(f"\n  Note: V2 agent '{agent_name}' created with kind=prompt.")
    print(f"  Agent invocation via threads/runs requires asst_ IDs (classic API).")
    print(f"  For V2 prompt agents, use the Foundry SDK or portal for invocation.")

    print(f"\nDone. Run 04-connect-apim.py next.")


if __name__ == "__main__":
    run()

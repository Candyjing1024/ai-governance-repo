"""Retry agent test after waiting for gpt-4o deployment to propagate."""
import time
from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import MessageRole

ACCOUNT_NAME = "proj-chubb-storage-val-resource"
PROJECT_NAME = "proj-chubb-storage-val"
AGENT_ID = "asst_jRfE1bi4RV39diHnbL5k0FdI"

cred = DefaultAzureCredential()
endpoint = f"https://{ACCOUNT_NAME}.services.ai.azure.com/api/projects/{PROJECT_NAME}"
client = AgentsClient(endpoint=endpoint, credential=cred)

for attempt in range(1, 6):
    print(f"\n--- Attempt {attempt} ---")
    thread = client.threads.create()
    client.messages.create(thread_id=thread.id, role=MessageRole.USER,
                           content="What is Chubb's AI governance policy?")
    start = time.time()
    run = client.runs.create_and_process(thread_id=thread.id, agent_id=AGENT_ID)
    elapsed = time.time() - start
    print(f"  Status: {run.status}  Time: {elapsed:.1f}s")

    if hasattr(run, "last_error") and run.last_error:
        print(f"  Error: {run.last_error.code} - {run.last_error.message}")

    if "completed" in str(run.status).lower():
        if hasattr(run, "usage") and run.usage:
            print(f"  Tokens: {run.usage.prompt_tokens}+{run.usage.completion_tokens}={run.usage.total_tokens}")
        resp = client.messages.get_last_message_text_by_role(thread_id=thread.id, role=MessageRole.AGENT)
        if resp:
            text = resp.text.value if hasattr(resp, "text") else str(resp)
            print(f"\n  Response ({len(text)} chars):\n  {text[:500]}")
        print("\n  SUCCESS!")
        break
    else:
        if attempt < 5:
            print(f"  Waiting 60s before retry...")
            time.sleep(60)
else:
    print("\n  All attempts failed.")

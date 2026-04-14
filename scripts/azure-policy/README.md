# Azure Policy — Limit Foundry Model Deployments

POC for controlling which AI models can be deployed in Azure Foundry using Azure Policy.

**Tested and validated on April 14, 2026** against a live Foundry (CognitiveServices) account.

## User Story

> **As an Azure admin, I want to keep a curated list of models for users, so I can control which models users can request to deploy.**

## How It Works

Azure provides a **built-in policy**: `Cognitive Services Deployments should only use approved Registry Models`

When assigned with **Deny** effect:
- Deployments of unapproved models are **blocked** at the ARM/data plane layer
- Approved models deploy normally
- Works across Foundry portal, CLI, REST API, and SDK
- Enforced by the CognitiveServices resource provider (`Microsoft.CognitiveServices.Data`)

## Files

| File | Type | Purpose |
|------|------|---------|
| `policy-params.json` | JSON | Policy parameters — approved publishers and model asset IDs |
| `01-Deploy-Model-Policy-POC.ps1` | PowerShell | Full POC: find policy, assign to RG, test blocked/allowed deployments |
| `02-Validate-Model-Policy.py` | Python | Same POC via ARM REST API with automated validation |

---

## Step-by-Step Instructions

### Prerequisites

- Azure CLI installed **and** logged in (`az login`)
- **Owner** or **Resource Policy Contributor** role on target resource group
- A CognitiveServices/AIServices account (Foundry resource) in the resource group
- For Python: `pip install azure-identity requests`

### Step 1: Configure the Approved Model List

Edit `policy-params.json` with the models you want to allow:

```json
{
    "effect": { "value": "Deny" },
    "allowedPublishers": { "value": [] },
    "allowedAssetIds": {
        "value": [
            "azureml://registries/azure-openai/models/gpt-4o/versions/2024-11-20",
            "azureml://registries/azure-openai/models/gpt-4o-mini/versions/2024-07-18"
        ]
    }
}
```

> **CRITICAL — `allowedPublishers` must be `[]` (empty)**
>
> The policy uses **AND** logic: a model is denied only when **both** conditions are true:
> - Publisher NOT in `allowedPublishers`
> - Asset ID NOT in `allowedAssetIds`
>
> If you set `allowedPublishers: ["OpenAI"]`, **ALL OpenAI models pass** regardless of `allowedAssetIds`.
> Use **empty publishers** (`[]`) and rely only on `allowedAssetIds` for fine-grained model control.

**Model Asset ID Format:**
```
azureml://registries/<registry>/models/<model-name>/versions/<version>
```
Find model IDs in the [Azure AI Model Catalog](https://ai.azure.com/explore/models).

### Step 2: Update Script Configuration

**Option A — PowerShell** (`01-Deploy-Model-Policy-POC.ps1`):
```powershell
# Edit these variables at the top of the script:
$SubscriptionId   = "<your-subscription-id>"
$ResourceGroup    = "<your-resource-group>"
$AccountName      = "<your-foundry-account-name>"
```

**Option B — Python** (`02-Validate-Model-Policy.py`):
```python
# Edit these variables at the top of the script:
SUB_ID       = "<your-subscription-id>"
RG           = "<your-resource-group>"
ACCOUNT_NAME = "<your-foundry-account-name>"
```

### Step 3: Run the POC

**Option A — PowerShell:**
```powershell
cd scripts/azure-policy
.\01-Deploy-Model-Policy-POC.ps1
```

**Option B — Python:**
```bash
cd scripts/azure-policy
python 02-Validate-Model-Policy.py
```

Both scripts will:
1. **Find** the built-in policy definition in your tenant
2. **Assign** the policy to your resource group with Deny effect
3. **Pause** — you need to wait ~15 minutes for policy propagation
4. **Test blocked model** — attempt to deploy a model NOT in the approved list
5. **Test allowed model** — attempt to deploy a model that IS in the approved list
6. **Check compliance** — show policy compliance status

### Step 4: Wait for Policy Propagation

After policy assignment, Azure needs **up to 15 minutes** to enforce it. The scripts will pause and prompt you before testing.

### Step 5: Verify Results

Expected output:

| Test | Model | Expected HTTP | Expected Result |
|------|-------|---------------|-----------------|
| Blocked | gpt-4o (not in list) | 400 | `NonCompliant` — "This action is noncompliant with policy..." |
| Allowed | gpt-4.1 (in list) | 201 | Deployment succeeds |

**Actual test results (April 14, 2026):**
- **Blocked model (gpt-4o)**: HTTP 400 — `Policy evaluation returned compliance: NonCompliant for model gpt-4o/2024-11-20` ✅
- **Allowed model (gpt-4.1)**: HTTP 201 — Deployed successfully ✅

### Step 6: Cleanup

```bash
# Python — remove policy assignment
python 02-Validate-Model-Policy.py --cleanup

# Azure CLI — remove policy assignment
az policy assignment delete \
    --name "limit-foundry-model-deployments" \
    --scope "/subscriptions/<sub-id>/resourceGroups/<rg>"
```

---

## Key Findings from Testing

1. **Policy type is data plane** (`Microsoft.CognitiveServices.Data`) — enforced by the CognitiveServices resource provider, not standard ARM policy evaluation
2. **Propagation takes 10-15 minutes** — do not test immediately after assignment
3. **Blocked deployments return HTTP 400** (not 403) with `NonCompliant` in the error message, not `RequestDisallowedByPolicy`
4. **`allowedPublishers` short-circuits `allowedAssetIds`** — always use `[]` for publishers if you want per-model control
5. **Asset IDs are case-sensitive** — must match exactly including version
6. **Compliance dashboard** takes up to 24 hours for full evaluation

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Blocked model deploys successfully | Policy not propagated yet | Wait 15 minutes after assignment |
| Allowed model is blocked | Asset ID doesn't match exactly | Check model name + version in Model Catalog |
| All OpenAI models pass | `allowedPublishers` includes "OpenAI" | Set `allowedPublishers` to `[]` |
| `InvalidPolicyRule` on assignment | Parameter names don't match definition | Run `az policy definition show` to verify parameter names |
| No compliance data | Evaluation hasn't run | Wait 24 hours or trigger: `az policy state trigger-scan` |

## Reference

- [Built-in policy for model deployment in Foundry](https://learn.microsoft.com/en-us/azure/foundry/how-to/model-deployment-policy?tabs=cli)
- [Azure Policy overview](https://learn.microsoft.com/en-us/azure/governance/policy/overview)
- [Model catalog overview](https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/model-catalog-overview)

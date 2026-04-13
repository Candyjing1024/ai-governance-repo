"""
This module serves as the central configuration hub for the agentic framework,
managing all external service connections, credentials, and application settings.

TEMPLATE FILE: This is a generic template for business use case configuration.
Replace placeholder values with your specific domain requirements.

Key Features:
    1. Azure Key Vault Integration: Securely retrieves all sensitive credentials and configuration
    2. Azure OpenAI Configuration: Sets up chat completion models and embedding services
    3. Azure AI Search Setup: Configures search endpoints and credentials for RAG functionality
    4. Cosmos DB Configuration: Manages database connections for conversation persistence
    5. Environment-Based Settings: Uses environment variables with sensible defaults

Security:
All sensitive information (API keys, endpoints, connection strings) is stored in
Azure Key Vault and retrieved using DefaultAzureCredential for secure authentication.
No hardcoded secrets are present in the codebase.

Configuration Areas:
- Azure OpenAI: Chat completion models, embeddings, API versions
- Azure AI Search: Search endpoints, credentials, index configurations
- Cosmos DB: Database connections for checkpointing and conversation storage
- Application Insights: Telemetry and logging configuration
- Key Vault: Centralized secret management

Usage:
This module is imported by other components to access configured services and
credentials. It initializes all necessary Azure service clients and provides
them as module-level variables for easy consumption throughout the application.

CUSTOMIZATION:
1. Update KEY_VAULT_NAME to your Key Vault instance
2. Configure domain-specific index names and search fields
3. Adjust model parameters for your use case requirements
4. Set appropriate database container names
"""

from dotenv import load_dotenv
import os
import logging
from azure.keyvault.secrets import SecretClient # type: ignore
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential # type: ignore
from azure.identity import ClientSecretCredential

# Suppress Azure Identity warnings about CLI authentication failures
logging.getLogger('azure.identity').setLevel(logging.ERROR)
logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)

# Load environment variables
load_dotenv()

# Basic Configuration - UPDATE THESE FOR YOUR DEPLOYMENT
CONFIG = {
    "KEY_VAULT_NAME": os.getenv("KEY_VAULT_NAME", "<your-keyvault-name>"),
    "AZURE_OPENAI_API_VERSION": os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
    "EMBEDDING_VECTOR_DIMENSION": os.getenv("EMBEDDING_VECTOR_DIMENSION", "3072")
}

keyVaultName = CONFIG["KEY_VAULT_NAME"]
keyVaultURL = f"https://{keyVaultName}.vault.azure.net"
azureOpenAIVersion = CONFIG["AZURE_OPENAI_API_VERSION"]
embeddingVectorDimension = int(CONFIG["EMBEDDING_VECTOR_DIMENSION"])

# Azure Authentication
credential = DefaultAzureCredential()

# Secret retrieval: use env vars if set (container deployment), otherwise Key Vault
def _get_secret(env_var: str, kv_name: str) -> str:
    """Get secret from env var first, fall back to Key Vault."""
    val = os.getenv(env_var)
    if val:
        return val
    kv_client = SecretClient(vault_url=keyVaultURL, credential=credential)
    return kv_client.get_secret(name=kv_name).value

# Azure OpenAI Configuration
azure_openai_endpoint = _get_secret("AZURE_OPENAI_ENDPOINT", "aisvc-endpoint")
azure_openai_api_key = _get_secret("AZURE_OPENAI_API_KEY", "aisvc-key")
azure_openai_api_version = azureOpenAIVersion

# Embedding Configuration
azure_openai_embedding_deployment = "text-embedding-3-large"
azure_openai_embedding_model = "text-embedding-3-large"
embedding_vector_dimension = embeddingVectorDimension

# Azure AI Search Configuration
search_credential = AzureKeyCredential(_get_secret("AZURE_SEARCH_KEY", "aisearch-key"))
search_endpoint = _get_secret("AZURE_SEARCH_ENDPOINT", "aisearch-endpoint")

# Chat Completion Model Configuration - ADJUST FOR YOUR USE CASE
chat_completion_model_name = "gpt-4o"
chat_completion_model_temperature = 0.2
chat_completion_model_max_tokens = 1000

# DOMAIN-SPECIFIC CONFIGURATION - CUSTOMIZE FOR YOUR USE CASE
# Example: AI Governance use case

# Primary Domain Index Configuration
# AI Governance specific configuration
domain_index_name = "index-ai-governance"
domain_semantic_configuration_name = "domain-semantic-config"
domain_search_nearest_neighbour = 50  # Adjust based on your knowledge base size
domain_search_field_name = "contentVector"  # Vector field name (matches create_index.py schema)
domain_scoring_profile = "default-scoring-profile"

# Secondary Index Configuration (if needed)
# Example: For compliance documents, policies, etc.
secondary_index_name = "index-compliance"
secondary_semantic_configuration_name = "compliance-semantic-config"
secondary_search_nearest_neighbour = 25
secondary_search_field_name = "content_vector"

# TEMPLATE EXAMPLE CONFIGURATIONS - REMOVE OR REPLACE WITH YOUR DOMAIN
# These are examples that should be replaced with your specific use case configurations

# Example 1: Knowledge Base Index
knowledge_base_index_name = "index-knowledge-base"
knowledge_base_semantic_configuration_name = "knowledge-semantic-config"
knowledge_base_search_nearest_neighbour = 30
knowledge_base_search_field_name = "knowledge_vector"

# Example 2: Analytics Index
analytics_index_name = "index-analytics"
analytics_semantic_configuration_name = "analytics-semantic-config"
analytics_search_nearest_neighbour = 20
analytics_search_field_name = "analytics_vector"

import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential

load_dotenv()

# Basic Configuration - UPDATE THESE FOR YOUR DEPLOYMENT
CONFIG = {
    "AZURE_OPENAI_API_VERSION": os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
    "EMBEDDING_VECTOR_DIMENSION": os.getenv("EMBEDDING_VECTOR_DIMENSION", "1536")
}

azureOpenAIVersion = CONFIG["AZURE_OPENAI_API_VERSION"]
embeddingVectorDimension = int(CONFIG["EMBEDDING_VECTOR_DIMENSION"])

# Azure Authentication
credential = DefaultAzureCredential()

# Azure OpenAI Configuration
azure_openai_endpoint="https://apim-chubb.azure-api.net"
azure_openai_api_version = azureOpenAIVersion

# Embedding Configuration
azure_openai_embedding_deployment = "text-embedding-3-large"
azure_openai_embedding_model = "text-embedding-3-large"
embedding_vector_dimension = embeddingVectorDimension

from openai import AzureOpenAI

# APIM endpoint with your base path
client = AzureOpenAI(
    azure_endpoint=azure_openai_endpoint,
    api_version=azure_openai_api_version,
    api_key="none"   # required by SDK but NOT used (APIM ignores it)
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "user", "content": "Hello! Can you confirm you're reachable through APIM?"}
    ]
)

print(response.choices[0].message.content)

# Test embeddings
print("\n--- Testing Embeddings ---")
embedding_response = client.embeddings.create(
    model=azure_openai_embedding_deployment,
    input="This is a test sentence for embedding generation.",
    dimensions=embedding_vector_dimension
)

print(f"Embedding model: {azure_openai_embedding_deployment}")
print(f"Embedding dimensions: {len(embedding_response.data[0].embedding)}")
print(f"First 5 values: {embedding_response.data[0].embedding[:5]}")

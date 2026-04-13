"""Upload Chubb AI Governance document to Azure AI Search index"""
import re
import logging
from azure.search.documents import SearchClient
from openai import AzureOpenAI
from azure.identity import get_bearer_token_provider
from config import (
    search_endpoint,
    search_credential,
    domain_index_name,
    azure_openai_endpoint,
    azure_openai_api_version,
    azure_openai_embedding_deployment,
    embedding_vector_dimension,
    credential,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Embedding client
token_provider = get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")
embedding_client = AzureOpenAI(
    azure_ad_token_provider=token_provider,
    api_version=azure_openai_api_version,
    azure_endpoint=azure_openai_endpoint,
)

SEPARATOR = "-" * 50
SOURCE_FILE = r"C:\Users\atraksha\Downloads\Chubb_Agentic_AI_Transformation_Extract.txt"


def generate_embedding(text: str):
    resp = embedding_client.embeddings.create(
        input=text,
        model=azure_openai_embedding_deployment,
        dimensions=embedding_vector_dimension,
    )
    return resp.data[0].embedding


def chunk_document(filepath: str):
    """Split the document on separator lines into titled sections."""
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    # Split by the separator line
    sections = re.split(r"\n-{10,}\n", raw)
    documents = []

    for idx, section in enumerate(sections):
        text = section.strip()
        if not text:
            continue

        # Use the first non-empty line as a title
        lines = text.splitlines()
        title = next((l.strip() for l in lines if l.strip()), f"Section {idx}")
        content = text

        documents.append({
            "id": str(idx + 1),
            "title": title,
            "content": content,
        })

    return documents


def upload_documents():
    print(f"\n========== Uploading to '{domain_index_name}' ==========\n")

    # 1. Chunk the document
    docs = chunk_document(SOURCE_FILE)
    print(f"Found {len(docs)} sections to upload\n")

    # 2. Generate embeddings for each chunk
    for doc in docs:
        print(f"  Generating embedding for: {doc['title'][:60]}...")
        doc["contentVector"] = generate_embedding(doc["content"])

    # 3. Upload to Azure AI Search
    search_client = SearchClient(
        endpoint=search_endpoint,
        index_name=domain_index_name,
        credential=search_credential,
    )

    result = search_client.upload_documents(documents=docs)

    succeeded = sum(1 for r in result if r.succeeded)
    failed = sum(1 for r in result if not r.succeeded)
    print(f"\n✅ Uploaded: {succeeded}  ❌ Failed: {failed}\n")


if __name__ == "__main__":
    upload_documents()

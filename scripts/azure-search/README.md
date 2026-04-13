# Azure AI Search Scripts

Scripts for managing Azure AI Search indexes, indexers, and document upload for RAG (Retrieval-Augmented Generation).

## Overview

Azure AI Search provides vector and semantic search capabilities for AI applications. These scripts help:
- Create and manage search indexes
- Upload and index documents
- Configure indexers for automatic updates
- Integrate with RAG tools

## Scripts

### `create_index.py`
Creates Azure AI Search index with vector and semantic capabilities.

**Features:**
- **Vector fields**: For embedding-based search
- **Text fields**: For keyword search
- **Semantic configuration**: For semantic ranking
- **Suggester**: For autocomplete

**Index schema:**
```python
{
    "name": "ai-governance-docs",
    "fields": [
        {"name": "id", "type": "Edm.String", "key": True},
        {"name": "content", "type": "Edm.String", "searchable": True},
        {"name": "title", "type": "Edm.String", "searchable": True},
        {"name": "contentVector", "type": "Collection(Edm.Single)", 
         "dimensions": 1536, "vectorSearchProfile": "default"},
        {"name": "metadata", "type": "Edm.String"}
    ]
}
```

**Usage:**
```bash
python create_index.py
```

**Configuration:**
```python
SEARCH_ENDPOINT = "https://<search-service-name>.search.windows.net"
SEARCH_KEY = "..."
INDEX_NAME = "ai-governance-docs"
```

### `upload_documents.py`
Uploads documents to Azure AI Search index.

**Supported formats:**
- PDF
- Word (docx)
- Text (txt, md)
- JSON
- HTML

**Features:**
- **Chunking**: Splits large documents into chunks
- **Embedding generation**: Creates vectors using Azure OpenAI
- **Metadata extraction**: Extracts title, author, date
- **Batch upload**: Uploads in batches of 1000

**Usage:**
```bash
# Upload single file
python upload_documents.py --file "policy.pdf"

# Upload directory
python upload_documents.py --dir "documents/"

# Upload with custom chunk size
python upload_documents.py --dir "documents/" --chunk-size 1000
```

**Example:**
```python
from upload_documents import DocumentUploader

uploader = DocumentUploader()
uploader.upload_file("ai-governance-policy.pdf")
```

### `ai_search_indexer.py`
Creates and manages indexers for automatic document indexing.

**Indexer types:**
- **Blob Storage indexer**: Indexes files from Azure Blob Storage
- **Cosmos DB indexer**: Indexes documents from Cosmos DB
- **SQL indexer**: Indexes data from Azure SQL

**Example - Blob Storage indexer:**
```python
{
    "name": "blob-indexer",
    "dataSourceName": "blob-datasource",
    "targetIndexName": "ai-governance-docs",
    "schedule": {"interval": "PT2H"},  # Run every 2 hours
    "fieldMappings": [
        {"sourceFieldName": "metadata_storage_path", "targetFieldName": "id"},
        {"sourceFieldName": "content", "targetFieldName": "content"}
    ]
}
```

**Usage:**
```bash
# Create indexer
python ai_search_indexer.py create

# Run indexer
python ai_search_indexer.py run

# Check indexer status
python ai_search_indexer.py status

# Delete indexer
python ai_search_indexer.py delete
```

**Configuration:**
```python
STORAGE_CONNECTION_STRING = "DefaultEndpointsProtocol=https;..."
CONTAINER_NAME = "documents"
INDEXER_SCHEDULE = "PT2H"  # ISO 8601 duration
```

## Dependencies

```bash
pip install azure-search-documents azure-identity azure-storage-blob openai PyPDF2 python-docx
```

## Configuration

### Environment Variables
```bash
export AZURE_SEARCH_ENDPOINT="https://search-chubb-mcp-poc.search.windows.net"
export AZURE_SEARCH_KEY="..."
export AZURE_OPENAI_ENDPOINT="https://..."
export AZURE_OPENAI_KEY="..."
export AZURE_STORAGE_CONNECTION_STRING="..."
```

### Search Service Requirements
- **Tier**: Basic or higher (for vector search)
- **Region**: Same as OpenAI for best performance
- **Replicas**: 2+ for production

## Index Configuration

### Vector Search Profile
```json
{
  "name": "default",
  "algorithm": "hnsw",
  "vectorizer": "text-embedding-ada-002"
}
```

### Semantic Configuration
```json
{
  "name": "default",
  "prioritizedFields": {
    "titleField": {"fieldName": "title"},
    "contentFields": [{"fieldName": "content"}]
  }
}
```

## Document Chunking

### Strategy
```python
CHUNK_SIZE = 1000  # characters
CHUNK_OVERLAP = 200  # overlap between chunks
```

### Example
```python
document = "..." # 5000 characters
chunks = [
    document[0:1000],      # Chunk 1
    document[800:1800],    # Chunk 2 (200 char overlap)
    document[1600:2600],   # Chunk 3
    ...
]
```

## Embedding Generation

### Azure OpenAI
```python
from openai import AzureOpenAI

client = AzureOpenAI(
    api_key="...",
    api_version="2024-02-01",
    azure_endpoint="https://..."
)

embedding = client.embeddings.create(
    model="text-embedding-ada-002",
    input="Your text here"
)
```

### Dimensions
- **text-embedding-ada-002**: 1536 dimensions
- **text-embedding-3-small**: 1536 dimensions
- **text-embedding-3-large**: 3072 dimensions

## Search Queries

### Vector Search
```python
from azure.search.documents import SearchClient

search_client = SearchClient(endpoint, index_name, credential)

results = search_client.search(
    search_text=None,
    vector_queries=[{
        "vector": query_vector,
        "k_nearest_neighbors": 5,
        "fields": "contentVector"
    }]
)
```

### Hybrid Search (Vector + Keyword)
```python
results = search_client.search(
    search_text="AI governance",
    vector_queries=[{
        "vector": query_vector,
        "k_nearest_neighbors": 5,
        "fields": "contentVector"
    }]
)
```

### Semantic Search
```python
results = search_client.search(
    search_text="AI governance policies",
    query_type="semantic",
    semantic_configuration_name="default"
)
```

## Common Operations

### Setup from Scratch
```bash
# 1. Create index
python create_index.py

# 2. Upload documents
python upload_documents.py --dir "documents/"

# 3. Create indexer (optional)
python ai_search_indexer.py create

# 4. Test search
python test_search.py
```

### Update Documents
```bash
# Re-upload changed files
python upload_documents.py --file "updated-policy.pdf"

# Or trigger indexer
python ai_search_indexer.py run
```

### Monitor Indexer
```bash
# Check status
python ai_search_indexer.py status

# View indexer history
az search indexer show-status \
  --service-name search-chubb-mcp-poc \
  --name blob-indexer
```

## Performance Tuning

### Indexing
- Use batch upload (1000 docs per batch)
- Parallel uploads for large datasets
- Schedule indexers during off-peak hours

### Search
- Use filters to reduce result set
- Limit fields returned (`select` parameter)
- Use search mode "all" for precision, "any" for recall

### Vector Search
- Adjust `k_nearest_neighbors` (higher = slower but more results)
- Use HNSW algorithm for fast approximate search
- Consider pre-filtering before vector search

## Troubleshooting

### Index Creation Fails
Check:
1. Search service tier supports vector search
2. Index schema valid
3. Field names follow naming rules

### Upload Fails
Check:
1. Document size < 16 MB
2. Batch size < 1000 documents
3. API key valid and has permissions

### Indexer Not Running
Check:
1. Data source connection string valid
2. Container/database exists
3. Field mappings correct

### Search Returns No Results
Check:
1. Documents indexed (check doc count)
2. Query vector generated correctly
3. Field names match index schema

## Integration with RAG

```python
# In rag_tool.py
from azure.search.documents import SearchClient

def search(query: str, top_k: int = 5):
    # 1. Generate embedding for query
    query_vector = generate_embedding(query)
    
    # 2. Search index
    results = search_client.search(
        search_text=query,
        vector_queries=[{
            "vector": query_vector,
            "k_nearest_neighbors": top_k,
            "fields": "contentVector"
        }]
    )
    
    # 3. Return context
    context = "\n\n".join([doc["content"] for doc in results])
    return context
```

## References

- [Azure AI Search Documentation](https://docs.microsoft.com/azure/search/)
- [Vector Search](https://docs.microsoft.com/azure/search/vector-search-overview)
- [Semantic Search](https://docs.microsoft.com/azure/search/semantic-search-overview)
- [Azure Search Python SDK](https://pypi.org/project/azure-search-documents/)

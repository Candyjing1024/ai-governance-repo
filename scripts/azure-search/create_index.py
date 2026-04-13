"""Create Azure AI Search index for RAG functionality"""
import logging
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    VectorSearchProfile,
    VectorSearchAlgorithmKind,
    HnswAlgorithmConfiguration,
)
from config import search_endpoint, search_credential

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_search_index():
    """Create the AI governance search index"""
    index_name = "index-chubb-ai-governance"
    vector_dimension = 3072  # text-embedding-3-large dimension
    
    # Define index schema
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="title", type=SearchFieldDataType.String),
        SearchableField(name="content", type=SearchFieldDataType.String),
        
        # Vector field for semantic search
        SearchField(
            name="contentVector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=vector_dimension,
            vector_search_profile_name="vector-profile"
        ),
    ]

    # Configure vector search
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="hnsw-algorithm",
                kind=VectorSearchAlgorithmKind.HNSW,
                parameters={
                    "m": 4,
                    "efConstruction": 400,
                    "efSearch": 500,
                    "metric": "cosine"
                }
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="vector-profile",
                algorithm_configuration_name="hnsw-algorithm",
            )
        ]
    )

    # Create the index
    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search
    )

    # Create index client and create the index
    index_client = SearchIndexClient(
        endpoint=search_endpoint,
        credential=search_credential
    )
    
    try:
        # Check if index exists
        try:
            existing = index_client.get_index(index_name)
            logger.info(f"✓ Index '{index_name}' already exists")
            return True
        except:
            pass
        
        # Create the index
        logger.info(f"Creating index '{index_name}'...")
        result = index_client.create_index(index)
        logger.info(f"✓ Index '{index_name}' created successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating index: {e}")
        return False

if __name__ == "__main__":
    print("\n========== Creating Azure AI Search Index ==========\n")
    success = create_search_index()
    if success:
        print("\n✅ Index is ready for RAG operations!\n")
    else:
        print("\n❌ Failed to create index\n")

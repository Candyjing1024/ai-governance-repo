"""
Generic AI Search Indexer Template

TEMPLATE FILE: This is a generic template for creating Azure AI Search indices
for your domain-specific knowledge bases and data sources.

This module provides functionality to create, configure, and populate Azure AI Search
indices with your domain-specific content for RAG (Retrieval-Augmented Generation) capabilities.

Key Features:
    1. Index Creation: Automated creation of search indices with proper schema
    2. Vector Configuration: Setup of vector fields for semantic search
    3. Data Ingestion: Bulk upload of documents and content
    4. Schema Management: Flexible schema definition for different content types
    5. Indexing Pipeline: Automated processing and indexing workflows

CUSTOMIZATION:
1. Update the index schema for your domain-specific fields
2. Configure vector dimensions and embedding models
3. Implement your data source connectors
4. Customize the document processing pipeline
5. Add domain-specific search configurations

Usage:
    from backend.services.ai_search_indexer import DomainIndexer
    
    indexer = DomainIndexer()
    indexer.create_index()
    indexer.upload_documents(documents)
"""

import json
import os
from typing import List, Dict, Any, Optional
from azure.search.documents import SearchClient
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
    VectorSearchAlgorithmMetric,
    HnswAlgorithmConfiguration,
    SemanticConfiguration,
    SemanticSearch,
    SemanticPrioritizedFields,
    SemanticField
)
from backend.config import (
    search_endpoint,
    search_credential,
    # CUSTOMIZE: Import your domain-specific configurations
    domain_index_name,
    domain_semantic_configuration_name,
    domain_search_field_name,
    embedding_vector_dimension
)
from backend.utils import logger

class DomainIndexer:
    """
    Generic indexer class for creating and managing Azure AI Search indices.
    
    CUSTOMIZE: Adapt this class for your specific domain requirements.
    """
    
    def __init__(self, index_name: str = None):
        """
        Initialize the indexer with configuration.
        
        Args:
            index_name (str, optional): Override default index name
        """
        self.index_name = index_name or domain_index_name
        self.search_endpoint = search_endpoint
        self.credential = search_credential
        self.vector_dimension = embedding_vector_dimension
        
        # Initialize clients
        self.index_client = SearchIndexClient(
            endpoint=self.search_endpoint,
            credential=self.credential
        )
        self.search_client = SearchClient(
            endpoint=self.search_endpoint,
            index_name=self.index_name,
            credential=self.credential
        )
        
        logger.info(f"Initialized DomainIndexer for index: {self.index_name}")

    def create_index_schema(self) -> SearchIndex:
        """
        Create the search index schema for your domain.
        
        CUSTOMIZE: Update the fields and configuration for your domain data structure.
        
        Returns:
            SearchIndex: The configured search index schema
        """
        # CUSTOMIZE: Define your domain-specific fields
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="title", type=SearchFieldDataType.String),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SearchableField(name="summary", type=SearchFieldDataType.String),
            
            # Metadata fields - customize for your domain
            SimpleField(name="category", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="tags", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True),
            SimpleField(name="source", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="created_date", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
            SimpleField(name="last_updated", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
            
            # Vector field for semantic search
            SearchField(
                name=domain_search_field_name,
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=self.vector_dimension,
                vector_search_profile_name="default-vector-profile"
            ),
            
            # Add additional domain-specific fields here
            # Example fields (uncomment and customize as needed):
            # SimpleField(name="priority", type=SearchFieldDataType.String, filterable=True),
            # SimpleField(name="status", type=SearchFieldDataType.String, filterable=True),
            # SearchableField(name="keywords", type=SearchFieldDataType.String),
        ]

        # Configure vector search
        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="default-algorithm",
                    kind=VectorSearchAlgorithmKind.HNSW,
                    parameters={
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500,
                        "metric": VectorSearchAlgorithmMetric.COSINE
                    }
                )
            ],
            profiles=[
                VectorSearchProfile(
                    name="default-vector-profile",
                    algorithm_configuration_name="default-algorithm",
                )
            ]
        )

        # Configure semantic search
        semantic_search = SemanticSearch(
            configurations=[
                SemanticConfiguration(
                    name=domain_semantic_configuration_name,
                    prioritized_fields=SemanticPrioritizedFields(
                        title_field=SemanticField(field_name="title"),
                        content_fields=[
                            SemanticField(field_name="content"),
                            SemanticField(field_name="summary")
                        ],
                        keywords_fields=[
                            SemanticField(field_name="tags"),
                            SemanticField(field_name="category")
                        ]
                    )
                )
            ]
        )

        # Create the index
        index = SearchIndex(
            name=self.index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=semantic_search
        )

        return index

    def create_index(self) -> bool:
        """
        Create the search index if it doesn't exist.
        
        Returns:
            bool: True if index was created or already exists, False if error
        """
        try:
            # Check if index already exists
            try:
                existing_index = self.index_client.get_index(self.index_name)
                logger.info(f"Index {self.index_name} already exists")
                return True
            except Exception:
                # Index doesn't exist, create it
                pass

            # Create the index
            index_schema = self.create_index_schema()
            result = self.index_client.create_index(index_schema)
            
            logger.info(f"Successfully created index: {self.index_name}")
            return True

        except Exception as e:
            logger.error(f"Error creating index {self.index_name}: {str(e)}")
            return False

    def upload_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """
        Upload documents to the search index.
        
        CUSTOMIZE: Update document processing for your domain data format.
        
        Args:
            documents (List[Dict]): List of documents to upload
            
        Returns:
            bool: True if upload successful, False otherwise
        """
        try:
            if not documents:
                logger.warning("No documents provided for upload")
                return True

            # Process documents in batches
            batch_size = 100  # Adjust based on your needs
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                
                # Upload batch
                result = self.search_client.upload_documents(batch)
                
                # Check for failures
                failed_uploads = [r for r in result if not r.succeeded]
                if failed_uploads:
                    logger.warning(f"Failed to upload {len(failed_uploads)} documents in batch {i//batch_size + 1}")
                
                logger.info(f"Uploaded batch {i//batch_size + 1}: {len(batch) - len(failed_uploads)}/{len(batch)} successful")

            logger.info(f"Document upload completed for {len(documents)} documents")
            return True

        except Exception as e:
            logger.error(f"Error uploading documents: {str(e)}")
            return False

    def delete_index(self) -> bool:
        """
        Delete the search index.
        
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            self.index_client.delete_index(self.index_name)
            logger.info(f"Successfully deleted index: {self.index_name}")
            return True

        except Exception as e:
            logger.error(f"Error deleting index {self.index_name}: {str(e)}")
            return False


class DocumentProcessor:
    """
    Generic document processor for preparing content for indexing.
    
    CUSTOMIZE: Adapt this class for your specific document types and processing needs.
    """
    
    def __init__(self):
        self.logger = logger

    def process_document(self, raw_document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a raw document into the format expected by the search index.
        
        CUSTOMIZE: Update this method for your document structure and requirements.
        
        Args:
            raw_document (Dict): Raw document data
            
        Returns:
            Dict: Processed document ready for indexing
        """
        try:
            # CUSTOMIZE: Update field mapping for your domain
            processed_doc = {
                "id": raw_document.get("id") or raw_document.get("document_id", ""),
                "title": raw_document.get("title", ""),
                "content": raw_document.get("content", ""),
                "summary": raw_document.get("summary", ""),
                "category": raw_document.get("category", ""),
                "tags": raw_document.get("tags", []),
                "source": raw_document.get("source", ""),
                "created_date": raw_document.get("created_date"),
                "last_updated": raw_document.get("last_updated"),
                # Vector field will be populated during indexing if embeddings are provided
                domain_search_field_name: raw_document.get("embeddings", [])
            }

            # Add any additional processing logic here
            
            return processed_doc

        except Exception as e:
            self.logger.error(f"Error processing document: {str(e)}")
            return {}

    def process_batch(self, raw_documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a batch of raw documents.
        
        Args:
            raw_documents (List[Dict]): List of raw documents
            
        Returns:
            List[Dict]: List of processed documents
        """
        processed_docs = []
        for doc in raw_documents:
            processed_doc = self.process_document(doc)
            if processed_doc:
                processed_docs.append(processed_doc)
        
        return processed_docs


# EXAMPLE USAGE
def example_usage():
    """
    Example of how to use the generic indexer.
    
    CUSTOMIZE: Replace with your actual data source and processing logic.
    """
    # Initialize indexer
    indexer = DomainIndexer()
    
    # Create index
    if indexer.create_index():
        logger.info("Index created successfully")
    
    # Example documents (customize for your data)
    sample_documents = [
        {
            "id": "doc1",
            "title": "Sample Document 1",
            "content": "This is sample content for testing the indexer.",
            "summary": "Sample document for testing",
            "category": "test",
            "tags": ["sample", "test"],
            "source": "manual",
            "created_date": "2024-01-01T00:00:00Z",
            "last_updated": "2024-01-01T00:00:00Z"
        }
    ]
    
    # Process and upload documents
    processor = DocumentProcessor()
    processed_docs = processor.process_batch(sample_documents)
    
    if indexer.upload_documents(processed_docs):
        logger.info("Documents uploaded successfully")


if __name__ == "__main__":
    example_usage()
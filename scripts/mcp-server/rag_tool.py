"""
Generic RAG (Retrieval-Augmented Generation) Tool Template

This template provides generic search and retrieval functions for Azure AI Search.
Customize the functions below for your specific domain and knowledge base.

CUSTOMIZATION GUIDE:
1. Update index names in config.py for your domain
2. Modify search fields and metadata based on your document schema
3. Customize the search results formatting for your use case
4. Implement domain-specific search logic as needed

Authors: Microsoft ASTRA Team
License: MIT
"""

import logging
from typing import List, Dict, Any, Optional
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery, QueryType, QueryCaptionType, QueryAnswerType
from openai import AzureOpenAI
from azure.identity import get_bearer_token_provider

# Import configuration
from config import (
    search_endpoint,
    search_credential,
    domain_index_name,
    domain_semantic_configuration_name,
    domain_search_field_name,
    domain_search_nearest_neighbour,
    azure_openai_endpoint,
    azure_openai_api_key,
    azure_openai_api_version,
    azure_openai_embedding_deployment,
    embedding_vector_dimension,
    credential
)

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Azure OpenAI client for embeddings
# Use API key if available (container deployment), otherwise use Azure AD token auth
if azure_openai_api_key:
    embedding_client = AzureOpenAI(
        api_key=azure_openai_api_key,
        api_version=azure_openai_api_version,
        azure_endpoint=azure_openai_endpoint
    )
else:
    token_provider = get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")
    embedding_client = AzureOpenAI(
        azure_ad_token_provider=token_provider,
        api_version=azure_openai_api_version,
        azure_endpoint=azure_openai_endpoint
    )

def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding for the input text using Azure OpenAI.
    
    Args:
        text (str): The text to generate embedding for
        
    Returns:
        List[float]: The embedding vector
    """
    try:
        response = embedding_client.embeddings.create(
            input=text,
            model=azure_openai_embedding_deployment,
            dimensions=embedding_vector_dimension
        )
        embedding = response.data[0].embedding
        return embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        return []


def domain_search_retrieval(user_input: str, top_results: int = 3) -> List[Dict[str, Any]]:
    """
    Generic domain search and retrieval function.
    
    CUSTOMIZE THIS FUNCTION for your specific domain and knowledge base.
    This template shows the basic pattern for Azure AI Search integration.
    
    Args:
        user_input (str): The user's search query
        top_results (int): Number of results to return (default: 3)
        
    Returns:
        List[Dict[str, Any]]: List of search results with metadata
    """
    search_results = []
    logger.info(f"Starting domain search retrieval for query: {user_input}")
    
    try:
        # Initialize Azure AI Search client
        search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=domain_index_name,
            credential=search_credential
        )
        
        # Generate embedding for the user query
        query_embedding = generate_embedding(user_input)
        
        if not query_embedding:
            logger.error("Failed to generate embedding for query")
            return []
        
        # Create vector query with manually generated embedding
        vector_query = VectorizedQuery(
            vector=query_embedding,
            k_nearest_neighbors=domain_search_nearest_neighbour,
            fields=domain_search_field_name
        )
        
        logger.info(f"Executing search query with embedding of dimension: {len(query_embedding)}")
        
        # Select fields that exist in the simple index schema
        results = search_client.search(
            search_text=user_input,
            vector_queries=[vector_query],
            select=[
                "id",           # Document ID
                "title",        # Document title field
                "content"       # Main content field
            ],
            query_type=QueryType.SIMPLE,  # Use simple query type since we don't have semantic config
            top=top_results
        )
        
        logger.info(f"Processing search results...")
        
        for result in results:
            # Format result data based on simple index schema
            result_dict = {
                # Core fields from simple index
                "id": result.get('id', ''),
                "content": result.get('content', ''),
                "title": result.get('title', ''),
                
                # Search quality metrics
                "search_score": result.get('@search.score', 0),
                "reranker_score": result.get('@search.reranker_score', 0),
                "highlights": result.get('@search.highlights', None),
                "captions": result.get('@search.captions', None)
            }
            
            logger.info(f"Retrieved result: {result_dict['title']}")
            search_results.append(result_dict)
        
        logger.info(f"Domain search completed successfully. Retrieved {len(search_results)} results")
        return search_results
        
    except Exception as e:
        logger.error(f"Error in domain search retrieval: {str(e)}")
        return []


def secondary_search_retrieval(user_input: str, search_type: str = "general") -> List[Dict[str, Any]]:
    """
    Generic secondary search function for additional knowledge sources.
    
    CUSTOMIZE THIS FUNCTION if you have multiple knowledge bases or search indices.
    
    Args:
        user_input (str): The user's search query
        search_type (str): Type of search to perform ("general", "specific", etc.)
        
    Returns:
        List[Dict[str, Any]]: List of search results from secondary sources
    """
    search_results = []
    logger.info(f"Starting secondary search retrieval: {search_type}")
    
    try:
        # CUSTOMIZE: Implement secondary search logic here
        # Example: Different index, different search parameters, etc.
        
        search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=domain_index_name,  # CUSTOMIZE: Use different index if needed
            credential=search_credential
        )
        
        # Simple text search for secondary results
        results = search_client.search(
            search_text=user_input,
            select=["content", "title", "category", "source"],
            top=2  # Fewer results for secondary search
        )
        
        for result in results:
            result_dict = {
                "content": result.get('content', ''),
                "title": result.get('title', ''),
                "category": result.get('category', ''),
                "source": result.get('source', ''),
                "search_type": search_type,
                "search_score": result.get('@search.score', 0)
            }
            search_results.append(result_dict)
        
        logger.info(f"Secondary search completed. Retrieved {len(search_results)} results")
        return search_results
        
    except Exception as e:
        logger.error(f"Error in secondary search: {str(e)}")
        return []


def search_by_category(user_input: str, category: str, top_results: int = 2) -> List[Dict[str, Any]]:
    """
    Search within a specific category or domain.
    
    CUSTOMIZE THIS FUNCTION to implement category-specific search logic.
    
    Args:
        user_input (str): The user's search query
        category (str): Specific category to search within
        top_results (int): Number of results to return
        
    Returns:
        List[Dict[str, Any]]: Filtered search results for the category
    """
    search_results = []
    logger.info(f"Starting category search: {category}")
    
    try:
        search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=domain_index_name,
            credential=search_credential
        )
        
        # CUSTOMIZE: Add category filter to your search
        filter_expression = f"category eq '{category}'"  # CUSTOMIZE: Adjust filter field name
        
        results = search_client.search(
            search_text=user_input,
            filter=filter_expression,
            select=["content", "title", "category", "source"],
            top=top_results
        )
        
        for result in results:
            formatted_result = {
                "content": result.get('content', ''),
                "title": result.get('title', ''),
                "category": result.get('category', ''),
                "source": result.get('source', ''),
                "search_context": {
                    "category_filter": category,
                    "score": result["@search.score"],
                    "document_id": result.get("id", "")
                }
            }
            search_results.append(formatted_result)

        logger.info(f"Category search ({category}) retrieved {len(search_results)} results")
        return search_results

    except Exception as e:
        logger.error(f"Error in category search: {str(e)}")
        return []


# Export the main search function for agent use
# CUSTOMIZE: Update the function name to match your domain
__all__ = [
    "domain_search_retrieval",
    "secondary_search_retrieval", 
    "search_by_category",
]

# NOTE: Template file - all customer-specific functions have been removed
# To customize for your domain, implement specific search functions following
# the pattern of domain_search_retrieval() above

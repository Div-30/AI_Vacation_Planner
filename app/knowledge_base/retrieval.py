from sentence_transformers import SentenceTransformer
import chromadb

from app.knowledge_base. import (
    get_vector_store_client,
    get_or_create_collection,
)

def retrieve_relevant_context(
        
)
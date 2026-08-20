from sentence_transformers import SentenceTransformer
import chromadb

from app.knowledge_base.vector_store import (
    get_vector_store_client,
    get_or_create_collection,
)

def retrieve_relevant_context(
     query: str,
     destination: str | None = None,
     doc_type: str | None = None,
     limit: int = 3,
) -> list[dict]:
    model = SentenceTransformer("all-MiniLM-L6-v2")
    client = get_vector_store_client()
    collection = get_or_create_collection(client)

    query_vector = model.encode(query, normalize_embeddings=True).tolist()
    where_filter = {}
    if destination and doc_type:
        where_filter = {
            "$and": [
                {"destination": destination},
                {"doc_type": doc_type}
            ]
        }
    elif destination:
        where_filter = {"destination": destination}
    elif doc_type:
        where_filter = {"doc_type": doc_type}
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=limit,
        where=where_filter if where_filter else None
    )
    retrieved_chunks = []
    if results and results["documents"]:
        for doc_text, metadata, score in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):
            retrieved_chunks.append({
                "content": doc_text,
                "destination": metadata.get("destination"),
                "doc_type": metadata.get("doc_type"),
                "source": metadata.get("source"),
                "similarity_distance": score
            })
    return retrieved_chunks
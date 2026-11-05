from pathlib import Path
from app.knowledge_base.ingestion import load_documents_from_directory
from app.knowledge_base.chunking import chunk_documents
from app.knowledge_base.embedding import load_embedding_model, embed_chunks
from app.knowledge_base.vector_store import (
    get_vector_store_client,
    get_or_create_collection,
    index_embedded_chunks,
)

DOCUMENT_DIR = Path(__file__).parent / "documents"

def run_indexing_pipeline() -> None:
    documents = load_documents_from_directory(DOCUMENT_DIR)
    print(f"Loaded {len(documents)} documents.")
    chunks = chunk_documents(documents)
    print(f"Created {len(chunks)} chunks")
    model = load_embedding_model()
    embedded_chunks = embed_chunks(chunks, model)
    print(f"Embedded {len(embedded_chunks)} chunks.")
    client = get_vector_store_client()
    collection = get_or_create_collection(client)
    index_embedded_chunks(embedded_chunks, collection)
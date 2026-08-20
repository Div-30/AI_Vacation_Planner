import chromadb
from chromadb.config import Settings
from pathlib import Path 

from app.knowledge_base.embedding import EmbeddedChunk

CHROMA_PERSIST_DIR = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "travel_knowledge_base"

def get_vector_store_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(
        path=str(CHROMA_PERSIST_DIR),
        settings=Settings(anonymized_telemetry=False),
    )

def get_or_create_collection(client: chromadb.PersistentClient) -> chromadb.Collection:
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
def index_embedded_chunks(chunks: list[EmbeddedChunk], collection: chromadb.Collection) -> None:
    if not chunks:
        return
    ids: list[str] = []
    embeddings: list[list[float]] = []
    documents: list[dict] = []
    metadatas: list[dict] = []
    for chunk in chunks:
        unique_id = f"{chunk.source}::chunk_{chunk.chunk_index}"
        ids.append(unique_id)
        embeddings.append(chunk.embedding)
        documents.append(chunk.content)
        metadatas.append({
            "doc_type": chunk.doc_type,
            "destination": chunk.destination,
            "source": chunk.source,
            "chunk_index": chunk.chunk_index,
        })
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )
    print(f"Indexed {len(chunks)} chunks into '{COLLECTION_NAME}'.")

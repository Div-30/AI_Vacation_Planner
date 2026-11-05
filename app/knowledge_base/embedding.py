from dataclasses import dataclass, field
from app.knowledge_base.ingestion import BaseDocument
from sentence_transformers import SentenceTransformer
from app.knowledge_base.chunking import DocumentChunk

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

@dataclass
class EmbeddedChunk(BaseDocument):
    chunk_index: int = 0
    embedding: list[float] = field(default_factory=list)

def load_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL_NAME)

def embed_chunks(chunks: list[DocumentChunk],
                 model: SentenceTransformer,
                 batch_size: int = 32) -> list[EmbeddedChunk]: 
    if not chunks:
        return []
    texts: list[str] = [chunk.content for chunk in chunks]

    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True
    )
    embedded_chunks: list[EmbeddedChunk] = []
    for chunk, vector in zip(chunks, embeddings):
        embedded_chunk = EmbeddedChunk(
            content=chunk.content, 
            doc_type=chunk.doc_type,
            destination=chunk.destination,
            source=chunk.source,
            chunk_index=chunk.chunk_index,
            embedding=vector.tolist(),
            metadata=chunk.metadata,
        )
        embedded_chunks.append(embedded_chunk)
    return embedded_chunks

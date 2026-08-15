from dataclasses import dataclass, field
from langchain_text_splitters import RecursiveCharacterTextSplitter 
from app.knowledge_base.ingestion import TravelDocument

@dataclass
class DocumentChunk:
    content: str
    doc_type: str
    destination: str
    source: str
    chunk_index: int
    metadata: dict = field(default_factory=dict)

CHUNK_SIZE = 800
CHUNK_OVERLAY = 150

def chunk_documents(documents: list[TravelDocument]) -> list[DocumentChunk]:
    splitters = RecursiveCharacterTextSplitter(
        Chunk_size = CHUNK_SIZE,
        chunk_overlay = CHUNK_OVERLAY,
        separators=["n/n", "/n", ". ", " ", ""]
    )

    all_chunks: list[DocumentChunk] = []
    for doc in documents:
        text_chunks: list[str] = splitters.split_text(doc.content)
        for index, chunk_text in enumerate(text_chunks):
            chunk = DocumentChunk(
                content=chunk_text.strip(),
                doc_type=doc.doc_type,
                destination=doc.destination,
                source=doc.source,
                chunk_index=index,
                metadata={
                    **doc.metadata,
                    "chunk_index": index,
                    "total_chunks": len(text_chunks)
                }
            )
            all_chunks.append(chunk)
        return all_chunks
from dataclasses import dataclass, field
from langchain_text_splitters import RecursiveCharacterTextSplitter 
from app.knowledge_base.ingestion import BaseDocument, TravelDocument

@dataclass
class DocumentChunk(BaseDocument):
    chunk_index: int = 0

CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

def chunk_documents(documents: list[TravelDocument]) -> list[DocumentChunk]:
    splitters = RecursiveCharacterTextSplitter(
        chunk_size = CHUNK_SIZE,
        chunk_overlap = CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
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
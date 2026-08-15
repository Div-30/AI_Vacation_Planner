import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

@dataclass
class TravelDocument:
    content: str
    doc_type: str
    destination: str
    source: str
    metadata: dict = field(default_factory=dict)
DOCUMENT_TYPES = {
    "travel_guides": "travel_guide",
    "local_tips": "local_tips",
    "hidden_gems": "hidden_gems",
    "faqs": "faqs",
    "destination_notes": "destination_notes",
}

def load_documents_from_directory(base_dir: str | Path) -> list[TravelDocument]: 
    base_path = Path(base_dir)
    documents: list[TravelDocument] = []

    for folder_name, doc_type in DOCUMENT_TYPES.items():
        folder_path = base_path / folder_name
        if not folder_path.exists():
            continue
        for file_path in folder_path.glob("**/*"):
            if file_path.suffix not in {".txt", ".md"}:
                continue
            raw_text = file_path.read_text(encoding="utf-8").strip()
            if not raw_text:
                continue
            destination = file_path.stem.replace("_", " ").title()

            doc = TravelDocument(
                content=raw_text,
                doc_type=doc_type,
                destination=destination,
                source=str(file_path.relative_to(base_path)),
                metadata={
                    "ingested_at": datetime.now(timezone.utc).isoformat(),
                    "file_size_bytes": file_path.stat().st_size,
                }
            )
            documents.append(doc)

    return documents
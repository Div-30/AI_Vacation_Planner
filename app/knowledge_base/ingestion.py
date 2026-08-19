from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

@dataclass
class BaseDocument:
    content: str
    doc_type: str
    destination: str
    source: str
    metadata: dict = field(default_factory=dict)
@dataclass
class TravelDocument(BaseDocument):
    pass

def load_documents_from_directory(base_dir: str | Path) -> list[TravelDocument]: 
    base_path = Path(base_dir)
    documents: list[TravelDocument] = []

    for file_path in base_path.glob("**/*"):
        if file_path.suffix not in {".txt", ".md"}:
            continue
        raw_text = file_path.read_text(encoding="utf-8").strip()
        if not raw_text:
            continue
        destination = file_path.stem.replace("_", " ").title()

        doc = TravelDocument(
            content=raw_text,
            doc_type="general",
            destination=destination,
            source=str(file_path.relative_to(base_path)),
            metadata={
                "ingested_at": datetime.now(timezone.utc).isoformat(),
                "file_size_bytes": file_path.stat().st_size,
            }
        )
        documents.append(doc)

    return documents
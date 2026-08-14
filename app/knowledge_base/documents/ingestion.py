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
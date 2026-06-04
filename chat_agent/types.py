from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal

RetrievalPass = Literal["filtered", "unfiltered"]

CONTEXT_METADATA_KEYS = (
    "domain_primary",
    "domain_secondary",
    "subdomain",
    "lifecycle_stage",
    "durability_tier",
    "source_url",
    "title",
    "publication_date",
    "source_type",
    "regulatory_body",
    "validation_status",
    "sec_dataset",
    "type",
)


@dataclass
class RetrievedChunk:
    id: str
    text: str
    metadata: Dict[str, Any]
    pinecone_score: float
    retrieval_passes: List[RetrievalPass] = field(default_factory=list)

    def context_payload(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"id": self.id, "text": self.text}
        for key in CONTEXT_METADATA_KEYS:
            if key in self.metadata and self.metadata[key] not in (None, ""):
                payload[key] = self.metadata[key]
        return payload

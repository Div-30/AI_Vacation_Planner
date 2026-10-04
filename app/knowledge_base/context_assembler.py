from app.knowledge_base.retrieval import retrieve_relevant_context

def assemble_context_for_destination(destination: str) -> str:
    results = retrieve_relevant_context(
        query=f"travel tips, highlights, and recommendations for {destination}",
        destination=destination,
        limit=5,
    )
    if not results:
        return ""
    context_lines = [
        "=== TRAVEL KNOWLEDGE BASE ==="
        f"The following is curated travel knowledge about {destination}",
        "Use this information to enrich and ground the itinerary you generate.",
        "",
    ]
    for i, chunk in enumerate(results, start=1):
        doc_type_label = chunk.get("doc_type", "general").replace("_", " ").title()
        context_lines.append(f"[Source {i} - {doc_type_label}]")
        context_lines.append(chunk["content"])
        context_lines.append("")
    context_lines.append("=== END OF KNOWLEDGE BASE ===")

    return "\n".join(context_lines)
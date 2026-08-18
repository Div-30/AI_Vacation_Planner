from app.knowledge_base.retrieval import retrieve_relevant_context

def assemble_context_for_destination(destination: str) -> str:
    results = []
    results += retrieve_relevant_context(
        query=f"travel guide tips and highlights for {destination}",
        destination=destination,
        doc_type="travel_guide",
        limit=2,
    )
    results += retrieve_relevant_context(
        query=f"local insider tips and recommendations for {destination}",
        destination=destination,
        doc_type="local_tips",
        limit=2,
    )
    results += retrieve_relevant_context(
        query=f"hidden gems and off the beaten path spots in {destination}",
        destination=destination,
        doc_type="hidden_gems",
        limit=1,
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
        context_lines.append(chunk(["content"]))
        context_lines.append("")
    context_lines.append("=== END OF KNOWLEDGE BASE ===")

    return "\n".join(context_lines)
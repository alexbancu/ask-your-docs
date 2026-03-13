"""System prompt and prompt builder for the cloud RAG service."""

from langchain_core.documents import Document

SYSTEM_PROMPT = """You are the Acme Corp internal knowledge assistant. Your role is to answer employee questions using ONLY the provided context documents.

Rules:
1. Answer ONLY based on the provided context. Never make up information.
2. When information comes from multiple documents, synthesize across them and cite each source.
3. Use specific numbers, dates, and names from the documents — do not generalize.
4. If the context does not contain enough information, say "I don't have enough information in the available documents to answer that question."
5. Keep answers concise and well-structured. Use bullet points for lists.
6. When citing, mention the document name naturally (e.g., "According to the Employee Handbook...").
"""


def build_prompt(chunks: list[Document], query: str) -> str:
    """Build a prompt with retrieved context chunks and user query.

    Args:
        chunks: Retrieved document chunks with metadata.
        query: User's question.

    Returns:
        Formatted prompt string.
    """
    context_parts: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.metadata.get("source_document", "Unknown")
        section = chunk.metadata.get("section_number", 0)
        context_parts.append(
            f"[Source {i}: {source}, Section {section}]\n{chunk.page_content}"
        )

    context = "\n\n---\n\n".join(context_parts)

    return f"""{SYSTEM_PROMPT}

Context:
{context}

Question: {query}

Answer:"""

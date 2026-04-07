import chromadb
import os
import re
from django.conf import settings
from chromadb.utils import embedding_functions

db_path = os.path.join(settings.BASE_DIR, "chroma_db")
chroma_client = chromadb.PersistentClient(path=db_path)
model_cache_path = settings.BASE_DIR / "model_cache" / "chroma_onnx"
embedding_function_instance = None


def get_embedding_function():
    global embedding_function_instance

    if embedding_function_instance is not None:
        return embedding_function_instance

    embedding_functions.ONNXMiniLM_L6_V2.DOWNLOAD_PATH = model_cache_path
    embedding_function_instance = embedding_functions.ONNXMiniLM_L6_V2(
        preferred_providers=["CPUExecutionProvider"]
    )

    return embedding_function_instance


NORMALIZATION_REPLACEMENTS = {
    "behaviorial": "behavioral",
    "behavorial": "behavioral",
    "behavioural": "behavioral",
    "git hub": "github",
    "git-hub": "github",
    "c plus plus": "c++",
    "c sharp": "c#",
    "resume": "resume cv",
    "interview prep": "interview preparation",
}

def get_collection():
    return chroma_client.get_or_create_collection(
        name="resume_dataset",
        embedding_function=get_embedding_function(),
    )


def reset_collection():
    try:
        chroma_client.delete_collection(name="resume_dataset")
    except Exception:
        pass

    return get_collection()


def normalize_text(text):
    normalized = text.lower().strip()
    for source, replacement in NORMALIZATION_REPLACEMENTS.items():
        normalized = normalized.replace(source, replacement)
    return re.sub(r"\s+", " ", normalized)

def chunk_text(text, chunk_size=500, overlap=100):
    cleaned_text = re.sub(r"\s+", " ", text).strip()
    if not cleaned_text:
        return []

    if len(cleaned_text) <= chunk_size:
        return [cleaned_text]

    sentences = re.split(r"(?<=[.!?])\s+", cleaned_text)
    sentences = [sentence.strip() for sentence in sentences if sentence.strip()]

    if len(sentences) == 1:
        return [cleaned_text]

    chunks = []
    current_sentences = []
    current_length = 0

    for sentence in sentences:
        sentence_length = len(sentence)

        if current_sentences and current_length + 1 + sentence_length > chunk_size:
            chunks.append(" ".join(current_sentences).strip())

            overlap_sentences = []
            overlap_length = 0
            for existing_sentence in reversed(current_sentences):
                proposed_length = overlap_length + len(existing_sentence) + (1 if overlap_sentences else 0)
                if proposed_length > overlap:
                    break
                overlap_sentences.insert(0, existing_sentence)
                overlap_length = proposed_length

            current_sentences = overlap_sentences[:]
            current_length = len(" ".join(current_sentences))

        current_sentences.append(sentence)
        current_length = len(" ".join(current_sentences))

    if current_sentences:
        chunks.append(" ".join(current_sentences).strip())

    return chunks


def sync_knowledge_documents():
    from .models import KnowledgeDocument

    documents = KnowledgeDocument.objects.filter(is_active=True)
    active_collection = reset_collection()

    chunked_documents = []
    metadatas = []
    ids = []

    for document in documents:
        for index, chunk in enumerate(chunk_text(document.content)):
            chunked_documents.append(chunk)
            metadatas.append({
                "source": document.source_label,
                "title": document.title,
                "topic": document.topic or "General Job Prep",
                "document_id": document.id,
                "chunk_index": index,
            })
            ids.append(f"knowledge-{document.id}-chunk-{index}")

    if chunked_documents:
        active_collection.add(
            documents=chunked_documents,
            metadatas=metadatas,
            ids=ids,
        )

    return len(chunked_documents)


def collection_count(active_collection):
    try:
        return active_collection.count()
    except Exception:
        return 0


def get_rag_response(user_query):
    # SMALL TALK ROUTING (DELETE this once User story 8 integrates LLM API)
    message = user_query.lower().strip()
    words = re.findall(r"\b[\w']+\b", message)

    # Greetings
    if "hello" in words or "hi" in words or "hey" in words:
        return {"answer": "Hey! I can help with resumes, cover letters, interviews, internships, and general job prep.", "sources": []}
    if "how are you" in message:
        return {"answer": "I am doing well, thank you. I am ready to help with your job preparation questions.", "sources": []}
    if "bye" in words or "goodbye" in words:
        return {"answer": "Goodbye! Come back anytime if you want help with job prep.", "sources": []}
    if "thanks" in words or "thank" in words:
        return {"answer": "You're welcome! I'm happy to help.", "sources": []}
    
    # General Help
    if "what can you do" in message or "how can you help" in message or ("help" in words and len(words) <= 3):
        return {"answer": "I can answer questions about resumes, cover letters, interviews, internships, and general job preparation.", "sources": []}

    # RAG
    active_collection = get_collection()

    if collection_count(active_collection) == 0:
        sync_knowledge_documents()
        active_collection = get_collection()

    if collection_count(active_collection) == 0:
        return {
            "answer": "The knowledge base is empty right now. A developer needs to add job prep documents before I can answer dataset-grounded questions.",
            "sources": []
        }

    results = active_collection.query(
        query_texts=[normalize_text(user_query)],
        n_results=1
    )
    retrieved_docs = results["documents"][0]
    retrieved_metadata = results["metadatas"][0]

    if not retrieved_docs:
        return {
            "answer": "I could not find a relevant match in the current job prep dataset. Try rephrasing your question or ask a developer to expand the knowledge base.",
            "sources": []
        }

    sources = list(dict.fromkeys(meta["source"] for meta in retrieved_metadata))
    context_string = "\n- ".join(retrieved_docs)

    mock_llm_answer = (
        f"I found the following relevant information in our dataset:\n\n"
        f"- {context_string}\n\n"
        f"(Note: A real LLM will eventually turn this context into a natural, conversational answer!)"
    )
    
    return {
        "answer": mock_llm_answer,
        "sources": sources
    }

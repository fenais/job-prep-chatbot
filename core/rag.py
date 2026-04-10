import chromadb
import os
import re
import anthropic
from dotenv import load_dotenv
from pathlib import Path
from django.conf import settings
from chromadb.utils import embedding_functions
import html

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

db_path = os.path.join(settings.BASE_DIR, "chroma_db")
chroma_client = chromadb.PersistentClient(path=db_path)
model_cache_path = settings.BASE_DIR / "model_cache" / "chroma_onnx"
embedding_function_instance = None


class SimpleEmbeddingFunction:
    @staticmethod
    def name():
        return "simple_local_embedding"

    def _embed(self, input):
        embeddings = []

        for text in input:
            tokens = [token for token in re.split(r"\s+", text.lower().strip()) if token]
            vector = [0.0] * 64

            for token in tokens:
                vector[hash(token) % len(vector)] += 1.0

            norm = sum(value * value for value in vector) ** 0.5
            if norm:
                vector = [value / norm for value in vector]

            embeddings.append(vector)

        return embeddings

    def __call__(self, input):
        return self._embed(input)

    def embed_documents(self, input):
        return self._embed(input)

    def embed_query(self, input):
        return self._embed(input)


def get_embedding_function():
    global embedding_function_instance

    if embedding_function_instance is not None:
        return embedding_function_instance

    model_cache_path.mkdir(parents=True, exist_ok=True)

    try:
        embedding_functions.ONNXMiniLM_L6_V2.DOWNLOAD_PATH = model_cache_path
        embedding_function_instance = embedding_functions.ONNXMiniLM_L6_V2(
            preferred_providers=["CPUExecutionProvider"]
        )
    except Exception:
        embedding_function_instance = SimpleEmbeddingFunction()

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

_BOILERPLATE_PATTERNS = [
    r"cookie[s]? policy",
    r"privacy policy",
    r"terms of (service|use)",
    r"all rights reserved",
    r"subscribe to our newsletter",
    r"follow us on",
    r"share this (article|post|page)",
    r"advertisement",
    r"click here to",
    r"sign up (for|to)",
    r"log in to (continue|read|access)",
]
_BOILERPLATE_RE = re.compile("|".join(_BOILERPLATE_PATTERNS), flags=re.IGNORECASE)


def clean_html(text):
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", text)
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return text


def remove_boilerplate(text):
    lines = text.splitlines()
    return "\n".join(
        line for line in lines
        if not _BOILERPLATE_RE.search(line) or len(line) > 200
    )


def preprocess_content(text):
    text = clean_html(text)
    text = remove_boilerplate(text)
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def deduplicate_chunks(chunks):
    seen = []
    for chunk in chunks:
        chunk_lower = chunk.lower()
        is_duplicate = False
        for existing in seen:
            shorter = min(len(chunk_lower), len(existing))
            if shorter == 0:
                continue
            overlap = sum(c1 == c2 for c1, c2 in zip(chunk_lower[:shorter], existing[:shorter]))
            if (overlap / shorter) * 100 >= 80:
                is_duplicate = True
                break
        if not is_duplicate:
            seen.append(chunk)
    return seen


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
        preprocessed = preprocess_content(document.content)
        unique_chunks = deduplicate_chunks(chunk_text(preprocessed))

        for index, chunk in enumerate(unique_chunks):
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


_INTENT_FACTUAL = "factual_lookup"
_INTENT_EXPLANATION = "explanation"
_INTENT_HOW_TO = "how_to"
_INTENT_REVIEW = "review_and_feedback"
_INTENT_CREATIVE = "creative"
_INTENT_GENERAL = "general"

_FACTUAL_KEYWORDS = {"what is", "what are", "define", "definition", "who is", "when is", "which", "list", "name", "tell me about"}
_EXPLANATION_KEYWORDS = {"why", "explain", "how does", "what does it mean", "difference between", "compare", "vs", "versus", "understand"}
_HOW_TO_KEYWORDS = {"how do i", "how to", "steps to", "guide", "tips", "advice", "best way to", "help me", "improve", "should i"}
_REVIEW_KEYWORDS = {"review", "feedback", "critique", "evaluate", "check my", "look at my", "is this good", "rate my", "assess"}
_CREATIVE_KEYWORDS = {"write", "draft", "create", "generate", "make", "compose", "sample", "example", "template"}


def classify_intent(user_query):
    q = user_query.lower().strip()
    if any(kw in q for kw in _REVIEW_KEYWORDS):
        return _INTENT_REVIEW
    if any(kw in q for kw in _CREATIVE_KEYWORDS):
        return _INTENT_CREATIVE
    if any(kw in q for kw in _HOW_TO_KEYWORDS):
        return _INTENT_HOW_TO
    if any(kw in q for kw in _EXPLANATION_KEYWORDS):
        return _INTENT_EXPLANATION
    if any(kw in q for kw in _FACTUAL_KEYWORDS):
        return _INTENT_FACTUAL
    return _INTENT_GENERAL


def build_system_prompt(intent, topic):
    base = (
        "You are JobPrepChatbot, an expert career coach specialising in "
        f"job preparation{', specifically ' + topic if topic and topic.lower() != 'general job prep' else ''}. "
        "Answer only using the provided context. "
        "If the context does not contain enough information, say so clearly."
    )
    if intent == _INTENT_FACTUAL:
        return base + "\n\nThe user wants a direct factual answer. Be concise and precise. Lead with the key fact, then add brief supporting detail."
    if intent == _INTENT_EXPLANATION:
        return base + "\n\nThe user wants a conceptual explanation. Break down the concept clearly. Structure your answer: (1) core idea, (2) why it matters, (3) brief example."
    if intent == _INTENT_HOW_TO:
        return base + "\n\nThe user wants actionable, step-by-step guidance. Format your answer as numbered steps or a short bulleted list. Be practical and specific."
    if intent == _INTENT_REVIEW:
        return base + "\n\nThe user is asking for feedback or a critique. Be constructive and specific. Identify strengths first, then areas to improve with concrete suggestions."
    if intent == _INTENT_CREATIVE:
        return base + "\n\nThe user wants you to draft or generate content. Produce polished, professional output grounded in the provided context. Label any generated example as a sample."
    return base + "\n\nProvide a helpful, well-organised answer. Use the context to ground your response and keep it relevant to job preparation."


def build_user_prompt(user_query, context_chunks, intent):
    context_block = "\n\n".join(f"- {chunk}" for chunk in context_chunks)
    if intent == _INTENT_REVIEW:
        return f"Context from the knowledge base:\n{context_block}\n\nPlease review and give feedback on the following:\n{user_query}"
    if intent == _INTENT_CREATIVE:
        return f"Context from the knowledge base:\n{context_block}\n\nUsing the context above, please fulfil this request:\n{user_query}"
    return f"Context from the knowledge base:\n{context_block}\n\nQuestion: {user_query}"


def get_rag_response(user_query):
    message = user_query.lower().strip()
    words = re.findall(r"\b[\w']+\b", message)

    if "hello" in words or "hi" in words or "hey" in words:
        return {"answer": "Hey! I can help with resumes, cover letters, interviews, internships, and general job prep.", "sources": []}
    if "how are you" in message:
        return {"answer": "I am doing well, thank you. I am ready to help with your job preparation questions.", "sources": []}
    if "bye" in words or "goodbye" in words:
        return {"answer": "Goodbye! Come back anytime if you want help with job prep.", "sources": []}
    if "thanks" in words or "thank" in words:
        return {"answer": "You're welcome! I'm happy to help.", "sources": []}
    if "what can you do" in message or "how can you help" in message or ("help" in words and len(words) <= 3):
        return {"answer": "I can answer questions about resumes, cover letters, interviews, internships, and general job preparation.", "sources": []}

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
        n_results=min(3, collection_count(active_collection))
    )
    retrieved_docs = results["documents"][0]
    retrieved_metadata = results["metadatas"][0]

    if not retrieved_docs:
        return {
            "answer": "I could not find a relevant match in the current job prep dataset. Try rephrasing your question or ask a developer to expand the knowledge base.",
            "sources": []
        }

    sources = list(dict.fromkeys(meta["source"] for meta in retrieved_metadata))
    topic = retrieved_metadata[0].get("topic", "General Job Prep") if retrieved_metadata else "General Job Prep"

    intent = classify_intent(user_query)
    system_prompt = build_system_prompt(intent, topic)
    user_prompt = build_user_prompt(user_query, retrieved_docs, intent)

    try:
        anthropic_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        response = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        answer = response.content[0].text
    except Exception as exc:
        answer = f"I retrieved relevant context from the knowledge base but could not generate a response due to an API error: {exc}"

    return {
        "answer": answer,
        "sources": sources
    }

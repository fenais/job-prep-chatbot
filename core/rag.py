import chromadb
import os
import re 
from django.conf import settings

db_path = os.path.join(settings.BASE_DIR, "chroma_db")
chroma_client = chromadb.PersistentClient(path=db_path)
collection = chroma_client.get_or_create_collection(name="resume_dataset")

def ingest_mock_kaggle_data():
    """Temporary function to simulate US 6 & 7.
    REPLACE (this is just mock data)
    """
    if collection.count() == 0:
        collection.add(
            documents=[
                "Software Engineering resumes should list technical skills like Python, Java, and Django at the top.",
                "When writing experience bullets, use the STAR method (Situation, Task, Action, Result).",
                "Keep resumes to a single page if you are a recent graduate or have less than 5 years of experience."
            ],
            metadatas=[
                {"source": "kaggle_swe_resume_12.txt", "category": "Tech Skills"},
                {"source": "kaggle_hr_guide_4.txt", "category": "Formatting"},
                {"source": "kaggle_entry_level_resume_1.txt", "category": "Length"}
            ],
            ids=["doc_1", "doc_2", "doc_3"]
        )

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
    ingest_mock_kaggle_data()

    results = collection.query(
        query_texts=[user_query],
        n_results=2 
    )
    
    retrieved_docs = results['documents'][0]
    retrieved_metadata = results['metadatas'][0]
    
    sources = [meta['source'] for meta in retrieved_metadata]
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
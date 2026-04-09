# JobPrepChatbot

A RAG-based (Retrieval-Augmented Generation) job preparation chatbot built for CS 2340 at Georgia Tech.
Users can ask natural language questions about resumes, cover letters, interviews, and internships,
and receive answers grounded in a curated knowledge base powered by the Anthropic Claude API.

---

## Tech Stack

- **Backend:** Django 5.2
- **Vector Database:** ChromaDB (with ONNXMiniLM embeddings)
- **LLM:** Anthropic Claude (via `anthropic` Python SDK)
- **Frontend:** Django templates + custom CSS
- **Deployment:** Docker / Gunicorn

---

## Project Structure

```
jobprepchatbot/       # Django project settings and URL config
core/
  models.py           # KnowledgeDocument model
  views.py            # Page views and document ingestion logic
  rag.py              # RAG pipeline: preprocessing, retrieval, prompt construction, LLM call
  urls.py             # App URL routes
templates/            # HTML templates (base, chat, developer, admin)
static/               # CSS styles
```

---

## Local Setup

### 1. Clone the repo

```bash
git clone <your-repo-url>
cd jobprepchatbot
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# Mac/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up your environment variables

Create a file called `.env` in the project root (next to `manage.py`):

```
ANTHROPIC_API_KEY=(team key)
```

> **Never commit this file.** It is already listed in `.gitignore`.

### 5. Run database migrations

```bash
python manage.py migrate
```

### 6. Start the development server

```bash
python manage.py runserver
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

---

## Pages

| URL | Description |
|---|---|
| `/` | Home page |
| `/chat/` | End-user chatbot interface |
| `/developer/` | Developer view — manage and ingest knowledge documents |
| `/admin-dashboard/` | Administrator dashboard |

---

## Adding Knowledge Documents

Go to `/developer/` and use one of three methods:

- **Upload a file** — supports `.txt`, `.md`, `.docx`, and simple `.pdf` files
- **Scrape a URL** — paste any public webpage URL
- **Manual entry** — type or paste content directly into the form

After adding documents, click **Re-sync Knowledge Base** to rebuild the search index.
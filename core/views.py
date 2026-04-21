from pathlib import Path
import json
import logging
import re
import ssl
from urllib.parse import urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import zipfile
from xml.etree import ElementTree

import certifi
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models.functions import Substr
from django.utils.text import slugify
from pypdf import PdfReader

from .models import KnowledgeDocument
from .rag import get_rag_response, sync_knowledge_documents

import time
from django.db.models import Avg, Max, Count, Q
from django.shortcuts import render
from .models import PerformanceLog
from django.contrib.admin.views.decorators import staff_member_required

logger = logging.getLogger(__name__)


def extract_uploaded_text(uploaded_file):
    extension = Path(uploaded_file.name).suffix.lower()

    if extension in {".txt", ".md"}:
        return uploaded_file.read().decode("utf-8")

    if extension == ".docx":
        with zipfile.ZipFile(uploaded_file) as archive:
            document_xml = archive.read("word/document.xml")

        root = ElementTree.fromstring(document_xml)
        paragraphs = []

        for paragraph in root.iter():
            if paragraph.tag.endswith("}p"):
                text_runs = [
                    node.text
                    for node in paragraph.iter()
                    if node.tag.endswith("}t") and node.text
                ]
                paragraph_text = "".join(text_runs).strip()
                if paragraph_text:
                    paragraphs.append(paragraph_text)

        return "\n".join(paragraphs)

    if extension == ".pdf":
        reader = PdfReader(uploaded_file)
        pages = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append(page_text.strip())
        return "\n".join(pages)

    raise ValueError("Supported file types are .txt, .md, .docx, and basic text-based .pdf files.")


def create_document_from_upload(uploaded_file, topic, is_active):
    extracted_text = extract_uploaded_text(uploaded_file).strip()

    if not extracted_text:
        raise ValueError("I could not extract readable text from that file.")

    filename_stem = Path(uploaded_file.name).stem
    words = re.split(r"[_\-\s]+", filename_stem)
    acronym_words = {"ai", "api", "aws", "css", "cs", "gpa", "hr", "html", "js", "ml", "pdf", "ui", "ux"}
    formatted_words = [
        word.upper() if word.lower() in acronym_words else word.capitalize()
        for word in words
        if word
    ]
    title = " ".join(formatted_words)
    source_label = slugify(filename_stem).replace("-", "_") or "uploaded_document"

    document = KnowledgeDocument.objects.create(
        title=title,
        source_label=source_label,
        topic=topic,
        content=extracted_text,
        is_active=is_active,
    )

    return document


def extract_url_text(url):
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )

    try:
        with urlopen(request, timeout=12, context=ssl_context) as response:
            raw_bytes = response.read()
            content_type = response.headers.get("Content-Type", "")
    except HTTPError as exc:
        raise ValueError(f"The website blocked the request with HTTP {exc.code}.")
    except URLError as exc:
        raise ValueError(f"Could not reach that URL: {exc.reason}")

    text = raw_bytes.decode("utf-8", errors="ignore")

    if "application/json" in content_type or text.strip().startswith(("{", "[")):
        parsed_json = json.loads(text)
        return json.dumps(parsed_json, indent=2)

    main_match = re.search(r"(?is)<main[^>]*>(.*?)</main>", text)
    article_match = re.search(r"(?is)<article[^>]*>(.*?)</article>", text)
    body_match = re.search(r"(?is)<body[^>]*>(.*?)</body>", text)
    preferred_content = article_match or main_match or body_match
    if preferred_content:
        text = preferred_content.group(1)

    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", text)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?is)<nav.*?>.*?</nav>", " ", text)
    text = re.sub(r"(?is)<footer.*?>.*?</footer>", " ", text)
    text = re.sub(r"(?is)<header.*?>.*?</header>", " ", text)
    text = re.sub(r"(?is)<aside.*?>.*?</aside>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"\s+", " ", text)
    cleaned_text = text.strip()

    if len(cleaned_text) < 120:
        raise ValueError("The page did not return enough readable text to ingest.")

    return cleaned_text


def create_document_from_url(url, topic, is_active):
    extracted_text = extract_url_text(url)

    if not extracted_text:
        raise ValueError("I could not extract readable text from that URL.")

    parsed_url = urlparse(url)
    path_tail = Path(parsed_url.path).stem or parsed_url.netloc
    source_label = slugify(path_tail).replace("-", "_") or "imported_url"
    title = " ".join(word.capitalize() for word in re.split(r"[_\-\s]+", path_tail) if word) or parsed_url.netloc

    document = KnowledgeDocument.objects.create(
        title=title,
        source_label=source_label,
        topic=topic,
        content=extracted_text,
        is_active=is_active,
    )

    return document


def extract_api_text(api_url, field_names):
    request = Request(
        api_url,
        headers={
            "User-Agent": "JobPrepChatbot/1.0",
            "Accept": "application/json,text/plain;q=0.9,*/*;q=0.8",
        },
    )

    with urlopen(request, timeout=10) as response:
        raw_bytes = response.read()

    text = raw_bytes.decode("utf-8", errors="ignore")
    parsed_json = json.loads(text)

    if isinstance(parsed_json, list):
        records = parsed_json[:5]
    else:
        records = [parsed_json]

    normalized_fields = [field.strip() for field in field_names if field.strip()]
    extracted_sections = []

    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            extracted_sections.append(str(record))
            continue

        lines = []
        for field in normalized_fields:
            value = record.get(field)
            if value not in (None, "", [], {}):
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=True)
                lines.append(f"{field}: {value}")

        if not lines:
            for key, value in list(record.items())[:6]:
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=True)
                lines.append(f"{key}: {value}")

        if lines:
            extracted_sections.append(f"Record {index}\n" + "\n".join(lines))

    return "\n\n".join(extracted_sections).strip()


def create_document_from_api(api_url, topic, is_active, field_names):
    extracted_text = extract_api_text(api_url, field_names)

    if not extracted_text:
        raise ValueError("I could not extract readable text from that API response.")

    parsed_url = urlparse(api_url)
    path_tail = Path(parsed_url.path).stem or parsed_url.netloc
    source_label = (slugify(path_tail).replace("-", "_") or "api_import") + "_api"
    title = " ".join(word.capitalize() for word in re.split(r"[_\-\s]+", path_tail) if word) or parsed_url.netloc
    if not title.lower().endswith("api"):
        title = f"{title} API Import"

    document = KnowledgeDocument.objects.create(
        title=title,
        source_label=source_label,
        topic=topic,
        content=extracted_text,
        is_active=is_active,
    )

    return document


def home(request):
    return render(request, "home.html")


def chat(request):
    chat_history = request.session.get("chat_history", [])

    if request.method == "POST":
        if "clear_chat" in request.POST:
            request.session["chat_history"] = []
            return render(request, "chat.html", {"chat_history": []})

        user_message = request.POST.get("message", "").strip()

        if user_message:
            start = time.perf_counter()
            try:
                rag_data = get_rag_response(user_message)
                latency_ms = (time.perf_counter() - start) * 1000

                PerformanceLog.objects.create(
                    question=user_message,
                    latency_ms=latency_ms,
                    success=True,
                    source_count=len(rag_data.get("sources", [])),
                )

                chat_history.append({
                    "user": user_message,
                    "bot": rag_data["answer"],
                    "sources": rag_data["sources"],
                })

            except Exception as e:
                latency_ms = (time.perf_counter() - start) * 1000

                PerformanceLog.objects.create(
                    question=user_message,
                    latency_ms=latency_ms,
                    success=False,
                    error_message=str(e),
                )

                chat_history.append({
                    "user": user_message,
                    "bot": "Sorry, something went wrong. Please try again.",
                    "sources": [],
                })

            request.session["chat_history"] = chat_history

    return render(request, "chat.html", {
        "chat_history": chat_history
    })


def developer(request):
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "upload_document":
            uploaded_file = request.FILES.get("knowledge_file")
            topic = request.POST.get("upload_topic", "").strip()
            is_active = request.POST.get("upload_is_active") == "on"

            if not uploaded_file:
                messages.error(request, "Choose a file before uploading.")
                return redirect("developer")

            try:
                document = create_document_from_upload(uploaded_file, topic, is_active)
                messages.success(
                    request,
                    f'Uploaded "{document.title}" into the knowledge base. Click Re-sync Knowledge Base to update search.',
                )
            except (ValueError, KeyError, UnicodeDecodeError, zipfile.BadZipFile):
                messages.error(
                    request,
                    "Upload failed. Use a readable .txt, .md, .docx, or simple text-based .pdf file.",
                )

            return redirect("developer")

        if action == "scrape_document":
            source_url = request.POST.get("source_url", "").strip()
            topic = request.POST.get("scrape_topic", "").strip()
            is_active = request.POST.get("scrape_is_active") == "on"

            if not source_url:
                messages.error(request, "Enter a URL before scraping.")
                return redirect("developer")

            try:
                document = create_document_from_url(source_url, topic, is_active)
                messages.success(
                    request,
                    f'Scraped "{document.title}" from URL. Click Re-sync Knowledge Base to update search.',
                )
            except Exception as exc:
                logger.exception("Scraping failed for URL: %s", source_url)
                messages.error(request, "Scraping failed. Try a public article or guide page.")

            return redirect("developer")

        if action == "save_document":
            document_id = request.POST.get("document_id")
            title = request.POST.get("title", "").strip()
            source_label = request.POST.get("source_label", "").strip()
            topic = request.POST.get("topic", "").strip()
            content = request.POST.get("content", "").strip()
            is_active = request.POST.get("is_active") == "on"

            if not title or not source_label or not content:
                messages.error(request, "Title, source label, and content are required.")
            else:
                if document_id:
                    document = get_object_or_404(KnowledgeDocument, pk=document_id)
                    success_message = "Knowledge document updated."
                else:
                    document = KnowledgeDocument()
                    success_message = "Knowledge document created."

                document.title = title
                document.source_label = source_label
                document.topic = topic
                document.content = content
                document.is_active = is_active
                document.save()
                messages.success(
                    request,
                    f"{success_message} Click Re-sync Knowledge Base to update search.",
                )

            return redirect("developer")

        if action == "delete_document":
            document_id = request.POST.get("document_id")
            document = KnowledgeDocument.objects.filter(pk=document_id).first()
            if not document:
                messages.error(request, "That knowledge document could not be found.")
                return redirect("developer")

            document.delete()
            messages.success(request, "Knowledge document deleted. Click Re-sync Knowledge Base to update search.")
            return redirect("developer")

        if action == "toggle_document_status":
            document_id = request.POST.get("document_id")
            document = KnowledgeDocument.objects.filter(pk=document_id).first()
            if not document:
                messages.error(request, "That knowledge document could not be found.")
                return redirect("developer")

            document.is_active = not document.is_active
            document.save()
            status_label = "active" if document.is_active else "inactive"
            messages.success(
                request,
                f'"{document.title}" is now {status_label}. Click Re-sync Knowledge Base to update search.',
            )
            return redirect("developer")

        if action == "sync_documents":
            chunk_count = sync_knowledge_documents()
            messages.success(request, f"Search index rebuilt from saved documents with {chunk_count} chunk(s).")
            return redirect("developer")

    edit_id = request.GET.get("edit")
    editing_document = None

    if edit_id:
        editing_document = get_object_or_404(KnowledgeDocument, pk=edit_id)

    documents = (
        KnowledgeDocument.objects
        .annotate(content_preview=Substr("content", 1, 180))
        .only("id", "title", "source_label", "topic", "is_active", "updated_at")
        .order_by("-updated_at", "title")
    )

    paginator = Paginator(documents, 10)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    return render(request, "developer.html", {
        "documents": page_obj,
        "editing_document": editing_document,
    })


@staff_member_required
def admin_dashboard(request):
    logs = PerformanceLog.objects.order_by("-timestamp")
    recent_logs = logs[:20]

    stats = logs.aggregate(
        total_requests=Count("id"),
        avg_latency=Avg("latency_ms"),
        max_latency=Max("latency_ms"),
        failures=Count("id", filter=Q(success=False)),
        successes=Count("id", filter=Q(success=True)),
    )

    return render(request, "admin_dashboard.html", {
        "stats": stats,
        "recent_logs": recent_logs,
    })
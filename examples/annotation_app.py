#!/usr/bin/env python3
"""
Single Page Document Annotation App with PDF Integration

A modern single-page application for document extraction annotation featuring:
- Real PDF viewing via iframe integration
- Dynamic form updates without page reloads
- Progress tracking and status management
- Auto-save functionality
- Mobile-responsive design

Run with: python document_annotation_spa.py
"""

import datetime
import json
import sqlite3
from pathlib import Path
from typing import List, Literal, Optional, Union

import fasthtml.common as fh
import monsterui.all as mui
from pydantic import BaseModel, Field

from fh_pydantic_form import PydanticForm, list_manipulation_js

# FastHTML app setup with MonsterUI
app, rt = fh.fast_app(
    hdrs=[
        mui.Theme.blue.headers(),
        list_manipulation_js(),
    ],
    pico=False,
    live=True,
)

# Database setup
DB_PATH = Path.cwd() / "document_annotations_spa.db"


def init_db():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS annotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id TEXT NOT NULL,
            annotation_data TEXT NOT NULL,
            status TEXT DEFAULT 'in_progress',
            confidence_score REAL DEFAULT 0.5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


# Initialize database on startup
init_db()


# Pydantic Models for Document Extraction
class KeyFigure(BaseModel):
    """Represents a key figure or metric extracted from a document"""

    name: str = Field(description="Name or description of the figure")
    value: Union[str, float] = Field(description="The actual value")
    unit: Optional[str] = Field(None, description="Unit of measurement if applicable")
    confidence: Literal["HIGH", "MEDIUM", "LOW"] = Field(
        "MEDIUM", description="Extraction confidence"
    )


class DocumentExtraction(BaseModel):
    """Complete schema for document extraction annotation"""

    # Document Metadata
    title: str = Field(description="Document title")
    authors: List[str] = Field(default_factory=list, description="Document authors")
    publication_date: Optional[datetime.date] = Field(
        None, description="Publication or creation date"
    )
    document_type: Literal["academic_paper"] = Field(
        default="academic_paper", description="Type of document being annotated"
    )

    # Key Entities and Information
    organizations: List[str] = Field(
        default_factory=list,
        description="Organizations, companies, or institutions mentioned",
    )
    key_figures: List[KeyFigure] = Field(
        default_factory=list, description="Important numbers, metrics, or measurements"
    )
    important_dates: List[datetime.date] = Field(
        default_factory=list, description="Significant dates mentioned in the document"
    )

    # Content Analysis
    abstract_summary: Optional[str] = Field(
        None, description="Brief summary or abstract of the document"
    )
    key_findings: List[str] = Field(
        default_factory=list, description="Main findings, conclusions, or takeaways"
    )
    confidence_score: float = Field(
        0.5, ge=0.0, le=1.0, description="Overall confidence in the extraction quality"
    )

    # Processing flags (excluded from form)
    annotator_id: str = Field(
        default="demo_user", description="ID of the person performing the annotation"
    )
    annotation_timestamp: datetime.datetime = Field(
        default_factory=datetime.datetime.now,
        description="When the annotation was created/updated",
    )
    processing_status: Literal[
        "pending", "in_progress", "completed", "needs_review"
    ] = Field(default="in_progress", description="Current status of the annotation")


# Sample Documents with PDF URLs
SAMPLE_DOCUMENTS = {
    "attention_paper": {
        "title": "Attention Is All You Need",
        "pdf_url": "https://arxiv.org/pdf/1706.03762.pdf",
        "fallback_pdf_url": "https://papers.neurips.cc/paper/7181-attention-is-all-you-need.pdf",
        "authors": [
            "Ashish Vaswani",
            "Noam Shazeer",
            "Niki Parmar",
            "Jakob Uszkoreit",
            "Llion Jones",
            "Aidan N. Gomez",
            "Lukasz Kaiser",
            "Illia Polosukhin",
        ],
        "year": 2017,
        "content": """The dominant sequence transduction models are based on complex recurrent or 
        convolutional neural networks that include an encoder and a decoder. The best 
        performing models also connect the encoder and decoder through an attention 
        mechanism. We propose a new simple network architecture, the Transformer...""",
        "initial_extraction": DocumentExtraction(
            title="Attention Is All You Need",
            authors=[
                "Ashish Vaswani",
                "Noam Shazeer",
                "Niki Parmar",
            ],  # Intentionally incomplete
            publication_date=datetime.date(2017, 6, 12),
            document_type="academic_paper",
            organizations=["Google Brain", "University of Toronto"],  # Missing some
            key_figures=[
                KeyFigure(
                    name="BLEU Score English-German",
                    value=28.4,
                    unit="BLEU",
                    confidence="HIGH",
                ),
                KeyFigure(
                    name="BLEU Score English-French",
                    value=41.8,
                    unit="BLEU",
                    confidence="HIGH",
                ),
            ],
            abstract_summary="Introduces the Transformer architecture based solely on attention mechanisms",
            key_findings=[
                "Transformer outperforms recurrent and convolutional models",
                "More parallelizable architecture",
            ],
            confidence_score=0.75,
        ),
    },
    "bert_paper": {
        "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        "pdf_url": "https://aclanthology.org/N19-1423.pdf",
        "fallback_pdf_url": "https://arxiv.org/pdf/1810.04805.pdf",
        "authors": [
            "Jacob Devlin",
            "Ming-Wei Chang",
            "Kenton Lee",
            "Kristina Toutanova",
        ],
        "year": 2019,
        "content": """We introduce a new language representation model called BERT, which stands for 
        Bidirectional Encoder Representations from Transformers. Unlike recent language representation 
        models, BERT is designed to pre-train deep bidirectional representations from unlabeled text...""",
        "initial_extraction": DocumentExtraction(
            title="BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
            authors=["Jacob Devlin", "Ming-Wei Chang"],  # Incomplete
            publication_date=datetime.date(2019, 6, 1),
            document_type="academic_paper",
            organizations=["Google AI Language"],
            key_figures=[
                KeyFigure(
                    name="GLUE Score", value=80.5, unit="percent", confidence="HIGH"
                ),
                KeyFigure(
                    name="SQuAD v1.1 F1", value=93.2, unit="F1", confidence="HIGH"
                ),
            ],
            abstract_summary="BERT uses bidirectional training for language understanding",
            key_findings=[
                "Bidirectional pre-training improves performance",
                "Fine-tuning works well for downstream tasks",
            ],
            confidence_score=0.65,
        ),
    },
    "gpt_paper": {
        "title": "Improving Language Understanding by Generative Pre-Training",
        "pdf_url": "https://cdn.openai.com/research-covers/language-unsupervised/language_understanding_paper.pdf",
        "fallback_pdf_url": "https://www.semanticscholar.org/paper/Improving-Language-Understanding-by-Generative-Radford-Narasimhan/cd18800a0fe0b668a1cc19f2ec95b5003d0a5035",
        "authors": [
            "Alec Radford",
            "Karthik Narasimhan",
            "Tim Salimans",
            "Ilya Sutskever",
        ],
        "year": 2018,
        "content": """Natural language understanding comprises a wide range of diverse tasks such as 
        textual entailment, question answering, semantic similarity assessment, and document classification...""",
        "initial_extraction": DocumentExtraction(
            title="Improving Language Understanding by Generative Pre-Training",
            authors=["Alec Radford"],  # Incomplete
            publication_date=None,  # Missing
            document_type="academic_paper",
            organizations=["OpenAI"],
            key_figures=[],  # Empty - needs filling
            abstract_summary="Demonstrates generative pre-training for language understanding tasks",
            key_findings=["Two-stage training procedure is effective"],
            confidence_score=0.45,
        ),
    },
}


def get_document_ids():
    """Get list of available document IDs"""
    return list(SAMPLE_DOCUMENTS.keys())


def get_document(doc_id: str) -> Optional[dict]:
    """Get document by ID"""
    return SAMPLE_DOCUMENTS.get(doc_id)


def get_annotation(doc_id: str) -> Optional[DocumentExtraction]:
    """Get existing annotation for a document"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "SELECT annotation_data FROM annotations WHERE document_id = ? ORDER BY updated_at DESC LIMIT 1",
        (doc_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        data = json.loads(row[0])
        return DocumentExtraction(**data)
    return None


def save_annotation(doc_id: str, annotation: DocumentExtraction):
    """Save or update annotation for a document"""
    conn = sqlite3.connect(DB_PATH)

    # Check if annotation exists
    cursor = conn.execute("SELECT id FROM annotations WHERE document_id = ?", (doc_id,))
    existing = cursor.fetchone()

    annotation_json = annotation.model_dump_json()

    if existing:
        conn.execute(
            "UPDATE annotations SET annotation_data = ?, confidence_score = ?, updated_at = CURRENT_TIMESTAMP WHERE document_id = ?",
            (annotation_json, annotation.confidence_score, doc_id),
        )
    else:
        conn.execute(
            "INSERT INTO annotations (document_id, annotation_data, confidence_score) VALUES (?, ?, ?)",
            (doc_id, annotation_json, annotation.confidence_score),
        )

    conn.commit()
    conn.close()


def get_document_status(doc_id: str) -> str:
    """Get annotation status: not_started, completed"""
    annotation = get_annotation(doc_id)
    if not annotation:
        return "not_started"

    # If annotation exists and was saved, consider it completed
    return "completed"


# Pre-create form renderers for all documents
form_renderers = {}


def init_form_renderers():
    """Initialize form renderers for all documents"""
    for doc_id, doc_data in SAMPLE_DOCUMENTS.items():
        initial_data = doc_data["initial_extraction"]
        form_renderer = PydanticForm(
            form_name=f"annotation_form_{doc_id}",
            model_class=DocumentExtraction,
            initial_values=initial_data,
            exclude_fields=[
                "annotator_id",
                "annotation_timestamp",
                "processing_status",
            ],
            label_colors={
                "title": "blue",
                "authors": "green",
                "publication_date": "purple",
                "document_type": "orange",
                "organizations": "teal",
                "key_figures": "red",
                "important_dates": "pink",
                "abstract_summary": "indigo",
                "key_findings": "amber",
                "confidence_score": "violet",
            },
            spacing="compact",
        )
        form_renderer.register_routes(app)
        form_renderers[doc_id] = form_renderer


# Initialize form renderers
init_form_renderers()


def create_pdf_viewer(doc_id: str):
    """Create PDF viewer component"""
    document = get_document(doc_id)
    if not document:
        return mui.Alert("Document not found", type="error")

    pdf_url = document.get("pdf_url")

    if pdf_url:
        return mui.Card(
            mui.CardBody(
                fh.Iframe(
                    src=pdf_url,
                    style="width: 100%; height: 600px; border: none;",
                    title=f"PDF Viewer for {document['title']}",
                ),
                fh.P(
                    fh.A("📖 Open PDF in new tab", href=pdf_url, target="_blank"),
                    cls="mt-2 text-center",
                ),
            )
        )
    else:
        # Fallback to text content
        return mui.Card(
            mui.CardHeader(mui.H4("📄 Document Content")),
            mui.CardBody(
                fh.Pre(
                    document.get("content", "No content available"),
                    style="height: 600px; overflow-y: auto; background: #f8f9fa; padding: 1rem;",
                )
            ),
        )


def create_navigation_header(doc_id: str):
    """Create navigation header with prev/next buttons and document index"""
    docs = get_document_ids()
    current_idx = docs.index(doc_id) if doc_id in docs else 0
    prev_doc = docs[current_idx - 1] if current_idx > 0 else None
    next_doc = docs[current_idx + 1] if current_idx < len(docs) - 1 else None

    document = get_document(doc_id)
    document_title = document["title"] if document else "Unknown Document"

    return fh.Div(
        # Previous button
        mui.Button(
            "◀ Previous",
            hx_post="/api/switch_document",
            hx_target="body",
            hx_vals=f'{{"doc_id": "{prev_doc}"}}' if prev_doc else "{}",
            disabled=not prev_doc,
            cls="mr-4",
        ),
        # Current document title with index
        mui.H3(f"{document_title} ({current_idx + 1})", cls="flex-1 text-center"),
        # Next button
        mui.Button(
            "Next ▶",
            hx_post="/api/switch_document",
            hx_target="body",
            hx_vals=f'{{"doc_id": "{next_doc}"}}' if next_doc else "{}",
            disabled=not next_doc,
            cls="ml-4",
        ),
        cls="flex items-center justify-between mt-4",
    )


# Routes
@rt("/")
def get(doc_id: str = "attention_paper"):
    """Main single page application"""
    if doc_id not in SAMPLE_DOCUMENTS:
        doc_id = "attention_paper"

    return mui.Container(
        # Header with navigation
        mui.Card(
            mui.CardBody(
                mui.H1("📄 Document Annotation Workflow"),
                create_navigation_header(doc_id),
            )
        ),
        # Main content area
        fh.Div(id="main-content"),
        # Initialize with first document
        fh.Script(
            f"htmx.ajax('GET', '/api/load_document?doc_id={doc_id}', '#main-content');"
        ),
        cls="p-4",
    )


@rt("/api/load_document")
def get_load_document(doc_id: str = "attention_paper"):
    """HTMX endpoint to load document content"""
    if doc_id not in SAMPLE_DOCUMENTS:
        return mui.Alert("Document not found", type="error")

    # Update the form with current data (either saved annotation or initial extraction)
    form_renderer = form_renderers[doc_id]
    current_annotation = get_annotation(doc_id)
    if current_annotation:
        form_renderer.initial_values_dict = current_annotation.model_dump()
    else:
        initial_extraction = SAMPLE_DOCUMENTS[doc_id]["initial_extraction"]
        form_renderer.initial_values_dict = initial_extraction.model_dump()  # type: ignore

    status = get_document_status(doc_id)
    status_label = (
        mui.Label("✓ Completed", style="primary")
        if status == "completed"
        else mui.Label("○ Not Started", style="secondary")
    )

    return fh.Div(
        # Two-column layout
        mui.Grid(
            # PDF viewer (left column)
            create_pdf_viewer(doc_id),
            # Annotation form (right column)
            mui.Card(
                mui.CardHeader(
                    fh.Div(
                        mui.H3("✏️ Annotation Form"),
                        status_label,
                        cls="flex items-center justify-between",
                        id="form-status-header",
                    )
                ),
                mui.CardBody(
                    fh.Div(id="save-status"),
                    mui.Form(
                        form_renderer.render_inputs(),
                        hx_post=f"/api/save_annotation/{doc_id}",
                        hx_target="#annotation-container",
                        hx_swap="outerHTML",
                        hx_trigger="submit",
                        id=f"annotation-form-{doc_id}",
                    ),
                    fh.Div(
                        mui.Button(
                            "💾 Save",
                            form=f"annotation-form-{doc_id}",
                            type="submit",
                            cls=mui.ButtonT.primary,
                        ),
                        mui.Button(
                            "🗑️ Clear",
                            hx_post=f"/api/clear_annotation/{doc_id}",
                            hx_target="#annotation-container",
                            hx_swap="outerHTML",
                            hx_confirm="Clear annotation?",
                            cls=mui.ButtonT.destructive,
                        ),
                        form_renderer.refresh_button("🔄 Refresh"),
                        cls="flex gap-2 mt-4",
                    ),
                    id="annotation-container",
                ),
            ),
            cols=2,
        ),
        cls="space-y-4",
    )


@rt("/api/save_annotation/{doc_id}")
async def post_save_annotation(doc_id: str, req):
    """Save annotation and return updated form"""
    if doc_id not in SAMPLE_DOCUMENTS:
        return mui.Alert("Document not found", type="error")

    try:
        form_renderer = form_renderers[doc_id]
        validated = await form_renderer.model_validate_request(req)
        save_annotation(doc_id, validated)

        # Update form with saved data
        form_renderer.initial_values_dict = validated.model_dump()

        # Create updated status label for OOB swap
        updated_status_label = mui.Label("✓ Completed", style="primary")

        return fh.Div(
            mui.Alert("✅ Annotation saved!", type="success", id="save-status"),
            mui.Form(
                form_renderer.render_inputs(),
                hx_post=f"/api/save_annotation/{doc_id}",
                hx_target="#annotation-container",
                hx_swap="outerHTML",
                hx_trigger="submit",
                id=f"annotation-form-{doc_id}",
            ),
            fh.Div(
                mui.Button(
                    "💾 Save",
                    form=f"annotation-form-{doc_id}",
                    type="submit",
                    cls=mui.ButtonT.primary,
                ),
                mui.Button(
                    "🗑️ Clear",
                    hx_post=f"/api/clear_annotation/{doc_id}",
                    hx_target="#annotation-container",
                    hx_swap="outerHTML",
                    hx_confirm="Clear?",
                    cls=mui.ButtonT.destructive,
                ),
                form_renderer.refresh_button("🔄 Refresh"),
                cls="flex gap-2 mt-4",
            ),
            # OOB swap to update the status header
            fh.Div(
                mui.H3("✏️ Annotation Form"),
                updated_status_label,
                cls="flex items-center justify-between",
                id="form-status-header",
                hx_swap_oob="true",
            ),
            id="annotation-container",
        )

    except Exception as e:
        return fh.Div(
            mui.Alert(f"Error: {str(e)[:100]}...", type="error", id="save-status"),
            id="annotation-container",
        )


@rt("/api/switch_document")
async def post_switch_document(req):
    """Switch to a different document"""
    form_data = await req.form()
    doc_id = form_data.get("doc_id", "attention_paper")

    if doc_id not in SAMPLE_DOCUMENTS:
        doc_id = "attention_paper"

    # Update form renderer with current annotation data
    form_renderer = form_renderers[doc_id]
    current_annotation = get_annotation(doc_id)
    if current_annotation:
        form_renderer.initial_values_dict = current_annotation.model_dump()
    else:
        initial_extraction = SAMPLE_DOCUMENTS[doc_id]["initial_extraction"]
        form_renderer.initial_values_dict = initial_extraction.model_dump()  # type: ignore

    return mui.Container(
        # Header with navigation
        mui.Card(
            mui.CardBody(
                mui.H1("📄 Document Annotation Workflow"),
                create_navigation_header(doc_id),
            )
        ),
        # Main content
        get_load_document(doc_id),
        cls="p-4",
    )


@rt("/api/clear_annotation/{doc_id}")
def post_clear_annotation(doc_id: str):
    """Clear annotation and reset form"""
    if doc_id not in SAMPLE_DOCUMENTS:
        return mui.Alert("Document not found", type="error")

    try:
        # Delete from database
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM annotations WHERE document_id = ?", (doc_id,))
        conn.commit()
        conn.close()

        # Reset form to initial data
        form_renderer = form_renderers[doc_id]
        initial_extraction = SAMPLE_DOCUMENTS[doc_id]["initial_extraction"]
        form_renderer.initial_values_dict = initial_extraction.model_dump()  # type: ignore

        # Create updated status label for OOB swap (cleared = not started)
        updated_status_label = mui.Label("○ Not Started", style="secondary")

        return fh.Div(
            mui.Alert("🗑️ Annotation cleared!", type="info", id="save-status"),
            mui.Form(
                form_renderer.render_inputs(),
                hx_post=f"/api/save_annotation/{doc_id}",
                hx_target="#annotation-container",
                hx_swap="outerHTML",
                hx_trigger="submit",
                id=f"annotation-form-{doc_id}",
            ),
            fh.Div(
                mui.Button(
                    "💾 Save",
                    form=f"annotation-form-{doc_id}",
                    type="submit",
                    cls=mui.ButtonT.primary,
                ),
                mui.Button(
                    "🗑️ Clear",
                    hx_post=f"/api/clear_annotation/{doc_id}",
                    hx_target="#annotation-container",
                    hx_swap="outerHTML",
                    hx_confirm="Clear?",
                    cls=mui.ButtonT.destructive,
                ),
                form_renderer.refresh_button("🔄 Refresh"),
                cls="flex gap-2 mt-4",
            ),
            # OOB swap to update the status header
            fh.Div(
                mui.H3("✏️ Annotation Form"),
                updated_status_label,
                cls="flex items-center justify-between",
                id="form-status-header",
                hx_swap_oob="true",
            ),
            id="annotation-container",
        )

    except Exception as e:
        return mui.Alert(f"Error: {str(e)[:100]}...", type="error")


if __name__ == "__main__":
    print("🚀 Starting Single Page Document Annotation App")
    print("📊 Database initialized at:", DB_PATH)
    print("🌐 Open your browser to: http://localhost:5001")
    print("\n📚 Available documents:")
    for doc_id, doc in SAMPLE_DOCUMENTS.items():
        print(f"  - {doc['title']} ({doc['initial_extraction'].document_type})")  # type: ignore

    fh.serve()

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

from typing import List, Literal, Optional

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

# Database setup using FastHTML's fastlite - enhanced schema
db = fh.database("annotation_app.db")
annotations = db.t.annotations

# Create table with enhanced schema
if annotations not in db.t:
    annotations.create(
        document_id=str,
        title=str,
        pdf_url=str,
        annotation_status=str,  # "new", "annotated"
        data=str,  # JSON of entire annotation
        pk="document_id",
    )


# Pydantic Models for Document Extraction
class Author(BaseModel):
    """Represents an author of the document"""

    name: str = Field(description="Author's full name")
    affiliation: Optional[str] = Field(
        None, description="Author's institution or organization"
    )

    def __str__(self):
        return f"{self.name} @ {self.affiliation}"


class DocumentExtraction(BaseModel):
    """Simplified schema for document extraction annotation showcasing fh-pydantic-form capabilities"""

    # Simple fields - Basic document info
    title: str = Field(description="Document title")
    document_type: Literal["academic_paper", "report", "article"] = Field(
        default="academic_paper", description="Type of document"
    )
    abstract_summary: Optional[str] = Field(
        None, description="Brief summary of the document"
    )

    # List[BaseModel] - Multiple authors
    authors: List[Author] = Field(
        default_factory=list, description="Authors of the document"
    )


# Sample Documents - Simplified Structure
SAMPLE_DOCUMENTS = {
    "attention_paper": {
        "title": "Attention Is All You Need",
        "pdf_url": "https://arxiv.org/pdf/1706.03762.pdf",
        "initial_extraction": DocumentExtraction(
            title="Attention Is All You Need",
            document_type="academic_paper",
            abstract_summary="Introduces the Transformer architecture based solely on attention mechanisms",
            authors=[
                Author(name="Ashish Vaswani", affiliation="Google Brain"),
                Author(name="Noam Shazeer", affiliation="Google Brain"),
                Author(name="Niki Parmar", affiliation="Google Brain"),
            ],
        ),
    },
    "bert_paper": {
        "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        "pdf_url": "https://aclanthology.org/N19-1423.pdf",
        "initial_extraction": DocumentExtraction(
            title="BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
            document_type="academic_paper",
            abstract_summary="BERT uses bidirectional training for language understanding",
            authors=[
                Author(name="Jacob Devlin", affiliation="Google AI Language"),
                Author(name="Ming-Wei Chang", affiliation="Google AI Language"),
                Author(name="Kenton Lee", affiliation="Google AI Language"),
            ],
        ),
    },
    "word2vec_paper": {
        "title": "Efficient Estimation of Word Representations in Vector Space",
        "pdf_url": "https://arxiv.org/pdf/1301.3781.pdf",
        "initial_extraction": DocumentExtraction(
            title="Efficient Estimation of Word Representations in Vector Space",
            document_type="academic_paper",
            abstract_summary="Proposes two novel model architectures for computing continuous vector representations of words from very large data sets. The quality of these representations is measured in a word similarity task, and the results are compared to the previously best performing techniques based on different types of neural networks.",
            authors=[
                Author(name="Tomas Mikolov", affiliation="Google Inc."),
                Author(name="Kai Chen", affiliation="Google Inc."),
                Author(name="Greg Corrado", affiliation="Google Inc."),
                Author(name="Jeffrey Dean", affiliation="Google Inc."),
            ],
        ),
    },
}


def insert_sample_documents():
    """Insert sample documents into database (replacing any existing ones)"""
    for doc_id, doc_data in SAMPLE_DOCUMENTS.items():
        initial_annotation: DocumentExtraction = doc_data["initial_extraction"]  # type: ignore
        annotations.upsert(
            {
                "document_id": doc_id,
                "title": doc_data["title"],
                "pdf_url": doc_data["pdf_url"],
                "annotation_status": "new",
                "data": initial_annotation.model_dump_json(),
            }
        )
        print(f"  ✓ {doc_data['title']}")


def get_document_ids() -> list[str]:
    """Get list of available document IDs from database"""
    rows = annotations()  # Get all rows
    return [row["document_id"] for row in rows]


def get_annotation(doc_id: str) -> DocumentExtraction:
    """Load annotation from database"""
    row = annotations[doc_id]  # Direct lookup by primary key!
    return DocumentExtraction.model_validate_json(row["data"])


def save_annotation(doc_id: str, annotation: DocumentExtraction):
    """Save or update annotation - preserve metadata fields"""
    existing = annotations[doc_id]
    annotations.upsert(
        {
            "document_id": doc_id,
            "title": existing["title"],
            "pdf_url": existing["pdf_url"],
            "annotation_status": "annotated",  # Mark as annotated when updated
            "data": annotation.model_dump_json(),
        }
    )


def get_document_status(doc_id: str) -> str:
    """Get document annotation status from database"""
    row = annotations[doc_id]
    return row["annotation_status"]


# Initialize a single base form that registers routes
base_form = PydanticForm("annotation_form", DocumentExtraction)
base_form.register_routes(app)


# Helper function for status labels
def create_status_label(status: str):
    """Create a status label based on annotation status"""
    status_labels = {
        "new": mui.Alert("📝 New", cls=mui.AlertT.info),
        "annotated": mui.Alert("✅ Annotated", cls=mui.AlertT.success),
    }
    return status_labels.get(status, mui.Alert("❓ Unknown", cls=mui.AlertT.error))


def create_form_for_document(doc_id: str) -> PydanticForm:
    """Create a PydanticForm instance for a specific document with current data"""
    current_annotation = get_annotation(doc_id)

    # Create form reusing the same "annotation_form" name
    form_renderer = PydanticForm(
        form_name="annotation_form",
        model_class=DocumentExtraction,
        initial_values=current_annotation,
        label_colors={
            "title": "blue",
            "document_type": "orange",
            "abstract_summary": "indigo",
            "authors": "green",
        },
        spacing="compact",
    )
    return form_renderer


def create_pdf_viewer(doc_id: str):
    """Create PDF viewer component"""
    row = annotations[doc_id]
    pdf_url = row["pdf_url"]
    title = row["title"]

    return mui.Card(
        mui.CardBody(
            fh.Iframe(
                src=pdf_url,
                style="width: 100%; height: 600px; border: none;",
                title=f"PDF Viewer for {title}",
            ),
            fh.P(
                fh.A("📖 Open PDF in new tab", href=pdf_url, target="_blank"),
                cls="mt-2 text-center",
            ),
        )
    )


def create_navigation_header(doc_id: str):
    """Create navigation header with prev/next buttons pointing to direct routes"""
    docs = get_document_ids()
    current_idx = docs.index(doc_id)

    # Simple previous/next logic - no circular navigation
    prev_doc = docs[current_idx - 1] if current_idx > 0 else None
    next_doc = docs[current_idx + 1] if current_idx < len(docs) - 1 else None

    # Get title from database
    row = annotations[doc_id]
    document_title = row["title"]

    return fh.Div(
        # Current document info
        fh.Div(
            mui.H3(document_title, cls="mb-0"),
            fh.P(
                f"Document {current_idx + 1} of {len(docs)}",
                cls="text-sm text-gray-600 mb-0",
            ),
            cls="flex-1 text-center",
        ),
        # Simple prev/next navigation
        fh.Div(
            mui.Button(
                "◀ Previous",
                hx_get=f"/{prev_doc}",
                hx_target="body",
                hx_swap="outerHTML",
                hx_push_url="true",
                variant="outline",
                disabled=prev_doc is None,
            ),
            mui.Button(
                "Next ▶",
                hx_get=f"/{next_doc}",
                hx_target="body",
                hx_swap="outerHTML",
                hx_push_url="true",
                variant="outline",
                disabled=next_doc is None,
                cls="ml-2",
            ),
            cls="flex",
        ),
        cls="flex items-center justify-center gap-8 mt-4",
    )


# Routes
@rt("/")
def get():
    """Root route redirects to first document"""
    available_docs = get_document_ids()
    first_doc = available_docs[0] if available_docs else "attention_paper"
    return fh.RedirectResponse(url=f"/{first_doc}", status_code=303)


@rt("/{doc_id}")
def get_document_route(doc_id: str):
    """Individual route for each document"""
    # Create form renderer for this document with current data
    form_renderer = create_form_for_document(doc_id)
    status = get_document_status(doc_id)

    return mui.Container(
        # Header with navigation
        mui.Card(
            mui.CardBody(
                mui.H1("📄 Document Annotation Workflow"),
                create_navigation_header(doc_id),
            )
        ),
        # Two-column layout
        mui.Grid(
            # PDF viewer (left column)
            create_pdf_viewer(doc_id),
            # Annotation form (right column)
            mui.Card(
                mui.CardHeader(
                    fh.Div(
                        mui.H3("✏️ Annotation Form"),
                        fh.Div(
                            create_status_label(status),
                            cls="text-xs text-gray-600 text-right",
                        ),
                        cls="flex items-center justify-between",
                    )
                ),
                mui.CardBody(
                    # Success/feedback messages
                    fh.Form(
                        form_renderer.render_inputs(),
                        fh.Div(
                            fh.Button(
                                "💾 Save",
                                type="submit",
                                cls="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded",
                            ),
                            cls="mt-4",
                        ),
                        action=f"/save/{doc_id}",
                        method="post",
                    ),
                ),
            ),
            cols=2,
        ),
        cls="p-4",
    )


@rt("/save/{doc_id}")
async def post_save_annotation(doc_id: str, req):
    """Save annotation and redirect back to document"""
    # Get the form renderer to parse the form data properly
    form_renderer = create_form_for_document(doc_id)

    # Parse the form data using fh-pydantic-form's validation
    annotation = await form_renderer.model_validate_request(req)
    save_annotation(doc_id, annotation)

    # Redirect back to the document page with success parameter
    return fh.RedirectResponse(url=f"/{doc_id}?saved=true", status_code=303)


if __name__ == "__main__":
    print("🚀 Starting Document Annotation App")
    print("📊 Database initialized: annotation_app.db")

    print("\n📚 Loading sample documents into database:")
    insert_sample_documents()

    available_docs = get_document_ids()
    first_doc = available_docs[0] if available_docs else "attention_paper"

    print("\n🌐 Open your browser to: http://localhost:5001")
    print(f"📄 Starting with: {annotations[first_doc]['title']}")
    print(
        f"📚 Navigate between {len(available_docs)} documents using prev/next buttons"
    )

    fh.serve()

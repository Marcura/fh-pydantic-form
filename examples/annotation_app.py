from typing import List, Literal, Optional

import fasthtml.common as fh
import monsterui.all as mui
from pydantic import BaseModel, Field

from fh_pydantic_form import PydanticForm, list_manipulation_js

app, rt = fh.fast_app(
    hdrs=[
        mui.Theme.blue.headers(),
        list_manipulation_js(),
    ],
    pico=False,
    live=True,
)

db = fh.database("annotation_app.db")
annotations = db.t.annotations

if annotations not in db.t:
    annotations.create(
        document_id=str,
        title=str,
        pdf_url=str,
        annotation_status=str,  # "new", "annotated"
        data=str,  # JSON of entire annotation
        pk="document_id",
    )


class Author(BaseModel):
    name: str = Field(description="Author's full name")
    affiliation: Optional[str] = Field(
        None, description="Author's institution or organization"
    )

    def __str__(self):
        return f"{self.name} @ {self.affiliation}"


class DocumentExtraction(BaseModel):
    title: str = Field(description="Document title")
    document_type: Literal["academic_paper", "report", "article"] = Field(
        default="academic_paper", description="Type of document"
    )
    abstract_summary: Optional[str] = Field(
        None, description="Brief summary of the document"
    )
    authors: List[Author] = Field(
        default_factory=list, description="Authors of the document"
    )


SAMPLE_DOCUMENTS = {
    "attention_paper": {
        "title": "Attention Is All You Need",
        "pdf_url": "https://arxiv.org/pdf/1706.03762.pdf",
        "initial_extraction": DocumentExtraction(
            title="Attention Is All You Need",
            document_type="academic_paper",
            abstract_summary="The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train. Our model achieves 28.4 BLEU on the WMT 2014 English-to-German translation task, improving over the existing best results, including ensembles, by over 2 BLEU. On the WMT 2014 English-to-French translation task, our model establishes a new single-model state-of-the-art BLEU score of 41.8 after training for 3.5 days on eight GPUs.",
            authors=[
                Author(name="Ashish Vaswani", affiliation="Google Brain"),
                Author(name="Noam Shazeer", affiliation="Google Brain"),
                Author(name="Niki Parmar", affiliation="Google Brain"),
                Author(name="Jakob Uszkoreit", affiliation="Google Brain"),
                Author(name="Llion Jones", affiliation="Google Brain"),
                Author(name="Aidan N. Gomez", affiliation="University of Toronto"),
                Author(name="Łukasz Kaiser", affiliation="Google Brain"),
                Author(
                    name="Illia Polosukhin", affiliation=None
                ),  # Missing affiliation - to be annotated
            ],
        ),
    },
    "bert_paper": {
        "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        "pdf_url": "https://aclanthology.org/N19-1423.pdf",
        "initial_extraction": DocumentExtraction(
            title="BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
            document_type="report",
            abstract_summary="We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers. Unlike recent language representation models, BERT is designed to pre-train deep bidirectional representations from unlabeled text by jointly conditioning on both left and right context in all layers. As a result, the pre-trained BERT model can be fine-tuned with just one additional output layer to create state-of-the-art models for a wide range of tasks, such as question answering and language inference, without substantial task-specific architecture modifications. BERT is conceptually simple and empirically powerful. It obtains new state-of-the-art results on eleven natural language processing tasks, including pushing the GLUE score to 80.5% (7.7% point absolute improvement), MultiNLI accuracy to 86.7% (4.6% absolute improvement), SQuAD v1.1 question answering Test F1 to 93.2 (1.5 point absolute improvement) and SQuAD v2.0 Test F1 to 83.1 (5.1 point absolute improvement).",
            authors=[
                Author(name="Jacob Devlin", affiliation="Google AI Language"),
                Author(name="Ming-Wei Chang", affiliation="Google AI Language"),
                Author(name="Kenton Lee", affiliation="Google AI Language"),
                Author(name="Kristina Toutanova", affiliation="Google AI Language"),
                # Missing one author - to be annotated
            ],
        ),
    },
    "word2vec_paper": {
        "title": "Efficient Estimation of Word Representations in Vector Space",
        "pdf_url": "https://arxiv.org/pdf/1301.3781.pdf",
        "initial_extraction": DocumentExtraction(
            title="Efficient Estimation of Word Representations in Vector Space",
            document_type="academic_paper",
            abstract_summary="We propose two novel model architectures for computing continuous vector representations of words from very large data sets. The quality of these representations is measured in a word similarity task, and the results are compared to the previously best performing techniques based on different types of neural networks. We observe large improvements in accuracy at much lower computational cost, i.e. it takes less than a day to learn high quality word vectors from a 1.6 billion words data set. Furthermore, we show that these vectors provide state-of-the-art performance on our test set for measuring syntactic and semantic word similarities. The main goal of this paper is to introduce these techniques to the NLP community. We also provide a comprehensive evaluation of the word representations on various tasks including word similarity, word analogy, and part-of-speech tagging. The Skip-gram model with negative sampling achieves the best performance on semantic tasks, while the CBOW model is faster and achieves better performance on syntactic tasks.",
            authors=[
                Author(name="Tomas Mikolov", affiliation="Google Inc."),
                Author(name="Kai Chen", affiliation="Google Inc."),
                Author(name="Greg Corrado", affiliation="Google Inc."),
                Author(name="Jeffrey Dean", affiliation="Google Inc."),
                # Note: Abstract summary is complete but could be more detailed about specific techniques
            ],
        ),
    },
}


def insert_sample_documents():
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


def get_document_ids() -> list[str]:
    return [row["document_id"] for row in annotations()]


def get_annotation(doc_id: str) -> DocumentExtraction:
    return DocumentExtraction.model_validate_json(annotations[doc_id]["data"])


def get_document_status(doc_id: str) -> str:
    return annotations[doc_id]["annotation_status"]


def save_annotation(doc_id: str, annotation: DocumentExtraction):
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


# Initialize a single base form that registers routes
base_form = PydanticForm(
    "annotation_form",
    DocumentExtraction,
    spacing="compact",
    label_colors={
        "title": "blue",
        "document_type": "orange",
        "abstract_summary": "indigo",
        "authors": "green",
    },
)
base_form.register_routes(app)


# Helper function for status labels
def create_status_label(status: str):
    """Create a status label based on annotation status"""
    status_labels = {
        "new": mui.Alert("📝 New", cls=mui.AlertT.info),
        "annotated": mui.Alert("✅ Annotated", cls=mui.AlertT.success),
    }
    return status_labels.get(status, mui.Alert("❓ Unknown", cls=mui.AlertT.error))


def create_pdf_viewer(doc_id: str):
    pdf_url = annotations[doc_id]["pdf_url"]
    title = annotations[doc_id]["title"]

    return mui.Card(
        mui.CardBody(
            fh.Iframe(
                src=pdf_url,
                style="width: 100%; height: 600px; border: none;",
                title=f"PDF Viewer for {title}",
            ),
        )
    )


def create_navigation_header(doc_id: str):
    docs = get_document_ids()
    current_idx = docs.index(doc_id)

    prev_doc = docs[current_idx - 1] if current_idx > 0 else docs[-1]
    next_doc = docs[current_idx + 1] if current_idx < len(docs) - 1 else docs[0]

    document_title = annotations[doc_id]["title"]

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
            ),
            mui.Button(
                "Next ▶",
                hx_get=f"/{next_doc}",
                hx_target="body",
                hx_swap="outerHTML",
                hx_push_url="true",
                variant="outline",
                cls="ml-2",
            ),
            cls="flex",
        ),
        cls="flex items-center justify-center gap-8 mt-4",
    )


# Routes
@rt("/")
def get():
    return fh.RedirectResponse(url=f"/{get_document_ids()[0]}", status_code=303)


@rt("/{doc_id}")
def get_document_route(doc_id: str):
    current_annotation = get_annotation(doc_id)
    form_renderer = base_form.with_initial_values(current_annotation)
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
                        ),
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
                            ),
                        ),
                        action=f"/save/{doc_id}",
                        method="post",
                    ),
                ),
            ),
            cols=2,
        ),
    )


@rt("/save/{doc_id}")
async def post_save_annotation(doc_id: str, req):
    current_annotation = get_annotation(doc_id)
    form_renderer = base_form.with_initial_values(current_annotation)

    annotation = await form_renderer.model_validate_request(req)
    save_annotation(doc_id, annotation)

    # Automatically go to next paper after saving
    docs = get_document_ids()
    current_idx = docs.index(doc_id)
    next_doc = docs[current_idx + 1] if current_idx < len(docs) - 1 else docs[0]
    return fh.RedirectResponse(url=f"/{next_doc}", status_code=303)


if __name__ == "__main__":
    insert_sample_documents()

    available_docs = get_document_ids()
    first_doc = available_docs[0] if available_docs else "attention_paper"

    fh.serve()

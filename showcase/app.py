from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markdown_it import MarkdownIt
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request

from cocoindex.ops.text import RecursiveSplitter
from examples_registry import load_examples
from patient_schema import Patient

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="CocoIndex Showcase")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

_splitter = RecursiveSplitter()
_markdown = MarkdownIt("gfm-like")
_examples = load_examples()

MAX_TEXT_LENGTH = 50_000
MAX_FILE_SIZE = 15 * 1024 * 1024  # 15 MB

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CODE_SUMMARY_LLM_MODEL = os.environ.get("LLM_MODEL", "gemini/gemini-2.5-flash")
PATIENT_INTAKE_LLM_MODEL = os.environ.get(
    "PATIENT_INTAKE_LLM_MODEL", "gemini/gemini-2.5-flash"
)

# litellm-style "<provider>/<model>" prefix -> the API key env var that provider expects.
_PROVIDER_KEY_ENV = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}

SPLITTER_LANGUAGES = [
    ("", "Plain text"),
    ("markdown", "Markdown"),
    ("python", "Python"),
    ("rust", "Rust"),
    ("javascript", "JavaScript"),
    ("typescript", "TypeScript"),
    ("go", "Go"),
    ("java", "Java"),
]

SPLITTER_SAMPLE_TEXT = """# CocoIndex

CocoIndex is a declarative data pipeline library. You declare what your
output should look like, and the engine keeps it in sync as inputs change.

## Why chunking matters

Before embedding or indexing a document, you usually need to split it into
smaller pieces. CocoIndex's RecursiveSplitter does this with syntax
awareness — it respects paragraph breaks, code blocks, and other structural
boundaries instead of cutting text at arbitrary character counts.

## Try it yourself

Paste your own text or code on the left, pick a language, and press Chunk
it to see exactly how CocoIndex's splitter breaks it apart.
"""

MARKDOWN_SAMPLE_TEXT = """# Hello, CocoIndex

This is the exact rendering approach used by the **files_transform** example:
`MarkdownIt("gfm-like")` turns Markdown source into HTML.

- Bullet one
- Bullet two

> CocoIndex just declares the target file; the engine keeps it in sync.
"""

EMBED_SEARCH_SAMPLE_TEXT = """CocoIndex chunks documents with syntax-aware
splitting, then embeds each chunk with a local sentence-transformer model.

The engine keeps a Postgres or LanceDB table in sync as source files change,
so a semantic search index updates incrementally instead of a full rebuild.

Search works by embedding the query with the same model, then ranking
chunks by vector similarity — this is the foundation under every RAG system.
"""
EMBED_SEARCH_SAMPLE_QUERY = "how does incremental indexing work?"

SUMMARIZE_SAMPLE_CODE = '''import cocoindex as coco
from cocoindex.connectors import localfs
from cocoindex.resources.file import FileLike, PatternFilePathMatcher


@coco.fn(memo=True)
async def process_file(file: FileLike, outdir) -> None:
    """Convert one markdown file into HTML."""
    html = render(await file.read_text())
    localfs.declare_file(outdir / (file.file_path.path.stem + ".html"), html)


@coco.fn
async def app_main(sourcedir, outdir) -> None:
    """Walk a directory of markdown files and transform each one."""
    files = localfs.walk_dir(
        sourcedir, path_matcher=PatternFilePathMatcher(included_patterns=["**/*.md"])
    )
    await coco.mount_each(process_file, files.items(), outdir)
'''


class ChunkRequest(BaseModel):
    text: str
    language: str | None = None
    chunk_size: int = Field(default=300, ge=20, le=4000)
    chunk_overlap: int = Field(default=50, ge=0, le=2000)


class ChunkOut(BaseModel):
    index: int
    text: str
    char_start: int
    char_end: int
    line_start: int
    line_end: int


class ChunkResponse(BaseModel):
    chunks: list[ChunkOut]
    count: int


class MarkdownRequest(BaseModel):
    text: str


class MarkdownResponse(BaseModel):
    html: str


class MarkdownTextResponse(BaseModel):
    markdown: str


class EmbedSearchRequest(BaseModel):
    text: str
    query: str
    language: str | None = None
    chunk_size: int = Field(default=500, ge=50, le=4000)
    chunk_overlap: int = Field(default=100, ge=0, le=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class EmbedSearchHit(BaseModel):
    text: str
    score: float
    char_start: int
    char_end: int
    line_start: int
    line_end: int


class EmbedSearchResponse(BaseModel):
    hits: list[EmbedSearchHit]


class SummarizeRequest(BaseModel):
    text: str


class ClassInfo(BaseModel):
    name: str
    summary: str


class FunctionInfo(BaseModel):
    name: str
    summary: str


class CodeSummary(BaseModel):
    summary: str
    public_classes: list[ClassInfo] = Field(default_factory=list)
    public_functions: list[FunctionInfo] = Field(default_factory=list)


class PatientIntakeResponse(BaseModel):
    patient: dict[str, Any]


def _check_text(text: str, *, max_length: int = MAX_TEXT_LENGTH) -> None:
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text must not be empty.")
    if len(text) > max_length:
        raise HTTPException(
            status_code=400,
            detail=f"Text is too long (max {max_length} characters).",
        )


def _check_upload(content: bytes, filename: str | None, suffix: str) -> None:
    if not (filename or "").lower().endswith(suffix):
        raise HTTPException(
            status_code=400, detail=f"Please upload a {suffix} file."
        )
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File is too large (max {MAX_FILE_SIZE // (1024 * 1024)} MB).",
        )


def _missing_llm_key_error(model: str) -> HTTPException | None:
    provider = model.split("/", 1)[0]
    env_name = _PROVIDER_KEY_ENV.get(provider)
    if env_name and not os.environ.get(env_name):
        return HTTPException(
            status_code=503,
            detail=(
                f"This demo needs an LLM API key on the server. "
                f"Set {env_name} as an environment variable (model: {model})."
            ),
        )
    return None


# ============================================================================
# Lazy singletons for heavy, not-always-used dependencies.
# ============================================================================

_embedder: Any | None = None
_embedder_lock = asyncio.Lock()


async def _get_embedder() -> Any:
    global _embedder
    if _embedder is None:
        async with _embedder_lock:
            if _embedder is None:
                from cocoindex.ops.sentence_transformers import (
                    SentenceTransformerEmbedder,
                )

                _embedder = SentenceTransformerEmbedder(EMBED_MODEL)
    return _embedder


_docling_converter: Any | None = None


def _get_docling_converter() -> Any:
    global _docling_converter
    if _docling_converter is None:
        from docling.datamodel.accelerator_options import (
            AcceleratorDevice,
            AcceleratorOptions,
        )
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        pipeline_options = PdfPipelineOptions(
            accelerator_options=AcceleratorOptions(device=AcceleratorDevice.CPU)
        )
        _docling_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
    return _docling_converter


_instructor_client: Any | None = None


def _get_instructor_client() -> Any:
    global _instructor_client
    if _instructor_client is None:
        import instructor
        from litellm import acompletion

        _instructor_client = instructor.from_litellm(
            acompletion, mode=instructor.Mode.JSON
        )
    return _instructor_client


_dspy_configured = False
_patient_extractor: Any | None = None


def _get_patient_extractor() -> Any:
    global _dspy_configured, _patient_extractor
    import dspy

    if not _dspy_configured:
        dspy.configure(lm=dspy.LM(PATIENT_INTAKE_LLM_MODEL))
        _dspy_configured = True

    if _patient_extractor is None:

        class PatientExtractionSignature(dspy.Signature):
            """Extract structured patient information from a medical intake form image."""

            form_images: list[dspy.Image] = dspy.InputField(
                desc="Images of the patient intake form pages"
            )
            patient: Patient = dspy.OutputField(
                desc="Extracted patient information with all available fields filled"
            )

        _patient_extractor = dspy.ChainOfThought(PatientExtractionSignature)

    return _patient_extractor


# ============================================================================
# Routes
# ============================================================================


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "splitter_languages": SPLITTER_LANGUAGES,
            "splitter_sample_text": SPLITTER_SAMPLE_TEXT,
            "markdown_sample_text": MARKDOWN_SAMPLE_TEXT,
            "embed_search_sample_text": EMBED_SEARCH_SAMPLE_TEXT,
            "embed_search_sample_query": EMBED_SEARCH_SAMPLE_QUERY,
            "summarize_sample_code": SUMMARIZE_SAMPLE_CODE,
            "examples": _examples,
        },
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chunk", response_model=ChunkResponse)
def chunk(req: ChunkRequest) -> ChunkResponse:
    _check_text(req.text)

    chunks = _splitter.split(
        req.text,
        req.chunk_size,
        chunk_overlap=req.chunk_overlap,
        language=req.language or None,
    )

    out = [
        ChunkOut(
            index=i,
            text=c.text,
            char_start=c.start.char_offset,
            char_end=c.end.char_offset,
            line_start=c.start.line,
            line_end=c.end.line,
        )
        for i, c in enumerate(chunks)
    ]
    return ChunkResponse(chunks=out, count=len(out))


@app.post("/api/markdown", response_model=MarkdownResponse)
def render_markdown(req: MarkdownRequest) -> MarkdownResponse:
    _check_text(req.text)
    return MarkdownResponse(html=_markdown.render(req.text))


@app.post("/api/pdf-to-markdown", response_model=MarkdownTextResponse)
async def pdf_to_markdown(file: UploadFile = File(...)) -> MarkdownTextResponse:
    content = await file.read()
    _check_upload(content, file.filename, ".pdf")

    converter = _get_docling_converter()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        markdown = await run_in_threadpool(
            lambda: converter.convert(tmp_path).document.export_to_markdown()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"Could not convert this PDF: {exc}"
        ) from exc
    finally:
        os.unlink(tmp_path)

    return MarkdownTextResponse(markdown=markdown)


@app.post("/api/embed-search", response_model=EmbedSearchResponse)
async def embed_search(req: EmbedSearchRequest) -> EmbedSearchResponse:
    _check_text(req.text)
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty.")

    chunks = _splitter.split(
        req.text,
        req.chunk_size,
        chunk_overlap=req.chunk_overlap,
        language=req.language or None,
    )
    if not chunks:
        return EmbedSearchResponse(hits=[])

    embedder = await _get_embedder()
    from cocoindex.connectors import lancedb

    rows = []
    for i, c in enumerate(chunks):
        vec = await embedder.embed(c.text)
        rows.append(
            {
                "id": i,
                "text": c.text,
                "char_start": c.start.char_offset,
                "char_end": c.end.char_offset,
                "line_start": c.start.line,
                "line_end": c.end.line,
                "embedding": vec.tolist(),
            }
        )
    query_vec = (await embedder.embed(req.query)).tolist()

    tmp_dir = tempfile.mkdtemp(prefix="coco-showcase-")
    try:
        conn = await lancedb.connect_async(tmp_dir)
        table = await conn.create_table("chunks", data=rows)
        search = await table.search(query_vec, vector_column_name="embedding")
        hits = await search.limit(req.top_k).to_list()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return EmbedSearchResponse(
        hits=[
            EmbedSearchHit(
                text=h["text"],
                score=1.0 - float(h["_distance"]),
                char_start=h["char_start"],
                char_end=h["char_end"],
                line_start=h["line_start"],
                line_end=h["line_end"],
            )
            for h in hits
        ]
    )


@app.post("/api/summarize-code", response_model=CodeSummary)
async def summarize_code(req: SummarizeRequest) -> CodeSummary:
    _check_text(req.text, max_length=20_000)

    error = _missing_llm_key_error(CODE_SUMMARY_LLM_MODEL)
    if error:
        raise error

    client = _get_instructor_client()
    prompt = f"""Analyze the following code and extract structured information.

```
{req.text}
```

Instructions:
1. Identify all public classes (not starting with _) and briefly summarize their purpose.
2. Identify all public functions (not starting with _) and briefly summarize their purpose.
3. Provide a brief overall summary of what this code does.
"""
    try:
        result = await client.chat.completions.create(
            model=CODE_SUMMARY_LLM_MODEL,
            response_model=CodeSummary,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"LLM extraction failed: {exc}"
        ) from exc
    return result


@app.post("/api/patient-intake", response_model=PatientIntakeResponse)
async def patient_intake(file: UploadFile = File(...)) -> PatientIntakeResponse:
    content = await file.read()
    _check_upload(content, file.filename, ".pdf")

    error = _missing_llm_key_error(PATIENT_INTAKE_LLM_MODEL)
    if error:
        raise error

    import dspy
    import pymupdf

    extractor = _get_patient_extractor()

    def _extract() -> dict[str, Any]:
        pdf_doc = pymupdf.open(stream=content, filetype="pdf")
        try:
            form_images = [
                dspy.Image(page.get_pixmap(matrix=pymupdf.Matrix(2, 2)).tobytes("png"))
                for page in pdf_doc
            ]
        finally:
            pdf_doc.close()
        result = extractor(form_images=form_images)
        return result.patient.model_dump(mode="json")

    try:
        patient = await run_in_threadpool(_extract)
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"Could not extract patient info: {exc}"
        ) from exc

    return PatientIntakeResponse(patient=patient)

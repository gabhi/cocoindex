from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markdown_it import MarkdownIt
from pydantic import BaseModel, Field
from starlette.requests import Request

from cocoindex.ops.text import RecursiveSplitter
from examples_registry import load_examples

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="CocoIndex Showcase")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

_splitter = RecursiveSplitter()
_markdown = MarkdownIt("gfm-like")
_examples = load_examples()

MAX_TEXT_LENGTH = 50_000

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


def _check_text(text: str) -> None:
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text must not be empty.")
    if len(text) > MAX_TEXT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Text is too long (max {MAX_TEXT_LENGTH} characters).",
        )


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "splitter_languages": SPLITTER_LANGUAGES,
            "splitter_sample_text": SPLITTER_SAMPLE_TEXT,
            "markdown_sample_text": MARKDOWN_SAMPLE_TEXT,
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

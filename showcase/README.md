# CocoIndex Showcase

A small FastAPI app showcasing CocoIndex: six live, in-process demos backed
by real `cocoindex` library calls (and a couple of adjacent libraries used by
the corresponding examples), plus a gallery of all 38 example pipelines in
`examples/` (pulled live from their README + source, so it can't drift out
of sync with the repo).

## Live demos

No external database/queue/cloud storage required for any of these — that's
what makes them viable as a public demo. Two need an LLM API key.

- **Text Splitter** — `cocoindex.ops.text.RecursiveSplitter`, syntax-aware
  chunking.
- **Markdown → HTML** — the exact approach used by the `files_transform`
  example (`MarkdownIt("gfm-like").render(...)`). Rendered inside a
  sandboxed iframe since the `gfm-like` preset allows raw HTML passthrough.
- **Embed & Search** — `RecursiveSplitter` + `SentenceTransformerEmbedder`
  (`all-MiniLM-L6-v2`) + an embedded, per-request LanceDB table, matching
  `text_embedding_lancedb` / `code_embedding_lancedb`. LanceDB is
  file-based (no server), so this needs no external service — but it does
  pull in `torch`, which is heavy; see resource notes below. First request
  downloads the model.
- **Code Summarizer** — LLM structured extraction via `instructor` +
  `litellm`, the technique from `multi_codebase_summarization`. **Needs an
  LLM API key** (see below).
- **PDF → Markdown** — `docling`'s `DocumentConverter`, the exact approach
  from `pdf_to_markdown`. No LLM or database. First request downloads
  layout models, so it can be slow initially.
- **Patient Intake Extraction** — DSPy structured extraction from an
  uploaded PDF, matching `patient_intake_extraction_dspy`. **Needs an LLM
  API key** (see below). The BAML variant of this example isn't live here —
  BAML requires a `baml-cli generate` codegen step before its client exists,
  which adds real build-pipeline risk for one demo; it's in the gallery
  instead.

### LLM API keys

Two demos call an LLM through `litellm`, which resolves the key from an
environment variable based on the model's provider prefix:

| Demo | Env var (model) | Default model |
|---|---|---|
| Code Summarizer | `LLM_MODEL` | `gemini/gemini-2.5-flash` (needs `GEMINI_API_KEY`) |
| Patient Intake Extraction | `PATIENT_INTAKE_LLM_MODEL` | `gemini/gemini-2.5-flash` (needs `GEMINI_API_KEY`) |

Point either at `openai/gpt-4o-mini` (`OPENAI_API_KEY`) or
`anthropic/claude-...` (`ANTHROPIC_API_KEY`) instead if you'd rather not use
Gemini. Without the corresponding key set, both demos return a clear 503
instead of crashing.

### Resource notes

`sentence-transformers` (→ `torch`) and `docling` are both substantial
dependencies — expect a slow first build and a slow first request to each
(model/weights download) on a fresh deploy. Render's free tier (512 MB RAM)
may not be enough once all of these are loaded in the same process; if the
Embed & Search or PDF → Markdown demos crash or hang, try a paid instance
tier with more memory.

## All Examples gallery

Every directory under `../examples` gets a card: title + description
parsed from its `README.md`, and an excerpt of its main source file, with
a link to the full example on GitHub. Most examples need external
infrastructure (Postgres, Qdrant, Kafka, Neo4j, cloud storage, ...) so they
aren't runnable from this page — the gallery is a browse/read experience
for anything beyond the six demos above.

## Run locally

```bash
pip install -r requirements.txt
uvicorn app:app --reload
```

## Deploy on Render

When creating the Web Service on Render:

- **Language**: Python 3
- **Root Directory**: `showcase`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- **Environment variables** (optional, enable the two LLM demos):
  `GEMINI_API_KEY` (or `LLM_MODEL`/`PATIENT_INTAKE_LLM_MODEL` +
  `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` for a different provider)

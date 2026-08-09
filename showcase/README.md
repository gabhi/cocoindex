# CocoIndex Showcase

A small FastAPI app showcasing CocoIndex: two live, in-process demos backed
by real `cocoindex` library calls, plus a gallery of all example pipelines
in `examples/` (pulled live from their README + source, so it can't drift
out of sync with the repo).

## Live demos

- **Text Splitter** — `cocoindex.ops.text.RecursiveSplitter`, syntax-aware
  chunking. No external services required.
- **Markdown → HTML** — the exact approach used by the `files_transform`
  example (`MarkdownIt("gfm-like").render(...)`). Rendered inside a
  sandboxed iframe since the `gfm-like` preset allows raw HTML passthrough.

## All Examples gallery

Every directory under `../examples` gets a card: title + description
parsed from its `README.md`, and an excerpt of its main source file, with
a link to the full example on GitHub. Most examples need external
infrastructure (Postgres, Qdrant, Kafka, Neo4j, cloud storage, ...) so they
aren't runnable from this page — the gallery is a browse/read experience,
not a live demo, for anything beyond the two demos above.

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

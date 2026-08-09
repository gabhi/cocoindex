# CocoIndex Showcase

Minimal deployment smoke test for Render.com. Currently just a hello-world
page to validate the deploy pipeline before building out the real showcase
(interactive demos of CocoIndex examples).

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

# Healthcare AI Assistant

A concise, demo-ready healthcare assistant that demonstrates an upload-first ingestion pipeline, OCR extraction, retrieval-augmented generation (RAG), and optional hosted or local LLM integration.

**Primary features**
- Upload documents (PDFs/images/text) and extract text via OCR
- Build a persistent knowledge base and vector index
- Retrieve relevant context for user questions (RAG)
- Generate answers using Ollama (local) or OpenAI (hosted), with a safe, context-only prompt
- Simple mock tool for appointment routing to demonstrate an agentic workflow

## Architecture & Pipeline

The application follows a linear pipeline that is easy to inspect and extend:

1. Upload: users POST files to the ingestion endpoint (`/ingest/upload`). Files are saved to `data/ocr_sources/`.
2. OCR Extraction: `app/ocr.py` extracts text from images and PDFs (PyMuPDF text extraction + `pytesseract` fallback for scanned pages).
3. Embeddings: `app/embeddings.py` converts texts into deterministic embeddings used for similarity search.
4. Vector Store: embeddings and document metadata are persisted in `vector_store/index.json` and `data/knowledge_base.json`.
5. Retrieval: `app/rag.py` performs similarity search to collect top-k context passages for a query.
6. Prompt Construction: `ResponseGenerator` builds a prompt that instructs the model to answer only from provided context and to refuse to guess.
7. Generation: `app/llm.py` attempts Ollama (if `USE_OLLAMA=1`), falls back to OpenAI (if `USE_OPENAI=1`), then to a safe local generator.
8. Tool Routing: `app/agent.py` inspects questions and routes appointment-like queries to the mock `check_available_slots()` tool when appropriate.

## Project Structure

- `app/` — core application code
	- `config.py` — paths and environment flags
	- `ocr.py` — extraction helpers for images/PDFs/text
	- `embeddings.py` — deterministic hashing embedding + similarity
	- `rag.py` — knowledge document model, ingestion, retrieval
	- `llm.py` — model connectors (Ollama/OpenAI) and local fallback
	- `agent.py` — orchestrator and tool router
	- `tools.py` — mock external tools (appointment slots)
	- `main.py` — FastAPI app and static file serving
- `data/` — persisted documents and uploads (ignored by `.gitignore`)
- `vector_store/` — saved index and vectors (ignored)
- `public/` — SPA demo UI (`index.html`, `app.js`, `styles.css`)
- `tests/` — pytest tests for ingestion, OCR, and endpoints
- `.env.example` — template for runtime environment variables (do NOT commit secrets)
- `data/sample_docs/` — synthetic healthcare documents included for demo/RAG ingestion

## Dataset

The repository includes small synthetic healthcare documents in `data/sample_docs/`:

- `discharge_instructions.txt`
- `appointment_policy.txt`
- `telehealth_guidelines.txt`

These documents are intentionally non-PHI and are suitable for demo ingestion, retrieval, and source citation testing.

## Quick start

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create a local virtual environment and add configuration in `.env` (copy from `.env.example`).

3. Start the server:

```bash
python -m app.main --serve
```

4. Open the demo UI at `http://127.0.0.1:8000`.

Docker run

```bash
docker compose up --build
```

API examples

Ask:

```bash
curl -X POST http://127.0.0.1:8000/ask -H "Content-Type: application/json" -d '{"question":"What should I do for a fever?"}'
```

Upload:

```bash
curl -F "files=@/path/to/report.pdf" http://127.0.0.1:8000/ingest/upload
```

## Environment & Secrets

- Use `.env` for runtime secrets (OpenAI key, model flags). **Never commit `.env`**.
- An example `.env.example` is included; copy it to `.env` and populate real keys locally.
- If any secrets were accidentally committed, rotate them immediately. The repository maintainer has removed `.env` from the index; confirm that no secrets remain in history.

## Testing

Run tests with:

```bash
pytest -q
```

## API endpoints

- `GET /health` — health check
- `POST /ingest` — folder-based document ingestion
- `POST /ingest/upload` — upload documents through the API
- `POST /ask` — ask a question and receive grounded answers with sources

## Safety & Limitations

- The assistant is for informational/demo use only. It does not provide medical diagnoses.
- The prompt enforces context-only answers and escalation for emergencies.

## Contact / Submission

If you want this prepared for an interview submission, I can create a GitHub release, add a repository description, and include a short demo script. See `.env.example` and `README.md` for run instructions.



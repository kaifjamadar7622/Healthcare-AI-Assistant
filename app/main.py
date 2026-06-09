"""Command-line entry point."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from textwrap import indent

import uvicorn
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .agent import HealthcareAssistant
from .config import AssistantConfig, load_config


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1)


class DocumentSummary(BaseModel):
    id: str
    title: str
    source_path: str | None = None
    source_type: str


class QueryResponse(BaseModel):
    question: str
    answer: str
    provider: str
    model: str
    sources: list[dict]


class IngestResponse(BaseModel):
    ingested: list[DocumentSummary]
    total_documents: int


class HealthResponse(BaseModel):
    status: str
    total_documents: int


def create_app(config: AssistantConfig | None = None) -> FastAPI:
    config = config or load_config()
    assistant = HealthcareAssistant(config=config)

    api = FastAPI(title=config.app_name, version="1.0.0")
    # Serve the single-page UI from the public directory
    api.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parent.parent / "public")), name="static")
    api.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    api.state.config = config
    api.state.assistant = assistant

    @api.get("/health", response_model=HealthResponse)
    def health(request: Request) -> HealthResponse:
        service = request.app.state.assistant
        return HealthResponse(status="ok", total_documents=len(service.knowledge_base.documents))

    @api.post("/ask", response_model=QueryResponse)
    def ask(payload: QuestionRequest, request: Request) -> QueryResponse:
        service = request.app.state.assistant
        reply = service.answer(payload.question)
        return QueryResponse(
            question=reply.question,
            answer=reply.answer,
            provider=reply.provider,
            model=reply.model,
            sources=[
                {
                    "id": source.document.id,
                    "title": source.document.title,
                    "score": round(source.score, 4),
                    "source_path": source.document.source_path,
                    "source_type": source.document.source_type,
                }
                for source in reply.sources
            ],
        )

    @api.post("/ingest/upload", response_model=IngestResponse)
    async def ingest_upload(request: Request, files: list[UploadFile] = File(...)) -> IngestResponse:
        service = request.app.state.assistant
        config = request.app.state.config
        saved_paths: list[Path] = []

        config.ocr_source_dir.mkdir(parents=True, exist_ok=True)
        for upload in files:
            if not upload.filename:
                raise HTTPException(status_code=400, detail="Each uploaded file must have a filename.")

            destination = config.ocr_source_dir / Path(upload.filename).name
            destination.write_bytes(await upload.read())
            saved_paths.append(destination)

        ingested = service.knowledge_base.ingest_paths(saved_paths)
        return IngestResponse(
            ingested=[
                DocumentSummary(
                    id=document.id,
                    title=document.title,
                    source_path=document.source_path,
                    source_type=document.source_type,
                )
                for document in ingested
            ],
            total_documents=len(service.knowledge_base.documents),
        )


    @api.get("/", include_in_schema=False)
    def root() -> FileResponse:
        index_path = Path(__file__).resolve().parent.parent / "public" / "index.html"
        return FileResponse(index_path)

    return api


app = create_app()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Healthcare AI Assistant")
    parser.add_argument("-q", "--question", help="Ask a healthcare question directly.")
    parser.add_argument("--json", action="store_true", help="Emit the reply as JSON.")
    return parser


def format_reply(reply) -> str:
    source_lines = []
    for index, source in enumerate(reply.sources, start=1):
        source_lines.append(f"{index}. {source.document.title} (score={source.score:.2f})")

    parts = [
        f"Question: {reply.question}",
        f"Provider: {reply.provider}",
        f"Model: {reply.model}",
        "Answer:",
        indent(reply.answer, "  "),
    ]

    if source_lines:
        parts.extend(["Sources:", indent("\n".join(source_lines), "  ")])

    return "\n".join(parts)


def main() -> None:
    parser = build_parser()
    parser.add_argument("--serve", action="store_true", help="Run the FastAPI app with Uvicorn.")
    parser.add_argument("--host", default="127.0.0.1", help="Host for the API server.")
    parser.add_argument("--port", type=int, default=8000, help="Port for the API server.")
    args = parser.parse_args()

    if args.serve:
        uvicorn.run("app.main:app", host=args.host, port=args.port, reload=False)
        return

    config = load_config()
    assistant = HealthcareAssistant(config=config)

    if args.question:
        reply = assistant.answer(args.question)
        if args.json:
            print(
                json.dumps(
                    {
                        "question": reply.question,
                        "answer": reply.answer,
                        "provider": reply.provider,
                        "model": reply.model,
                        "sources": [
                            {
                                "id": source.document.id,
                                "title": source.document.title,
                                "score": round(source.score, 4),
                            }
                            for source in reply.sources
                        ],
                    },
                    indent=2,
                )
            )
        else:
            print(format_reply(reply))
        return

    print(f"{config.app_name} ({config.environment})")
    print("Type a question and press Enter. Press Enter on a blank line to exit.\n")

    while True:
        question = input("You: ").strip()
        if not question:
            break
        reply = assistant.answer(question)
        print(f"\n{format_reply(reply)}\n")


if __name__ == "__main__":
    main()

from pathlib import Path

from app.config import AssistantConfig
from app.main import create_app
from app.ocr import extract_documents
from app.rag import KnowledgeBase, KnowledgeDocument


def test_extract_documents_from_text_file(tmp_path: Path):
    source = tmp_path / "scan.txt"
    source.write_text("Patient reports headache and nausea.", encoding="utf-8")

    docs = extract_documents([source])

    assert len(docs) == 1
    assert docs[0].text.startswith("Patient reports")


def test_ingest_paths_persists_documents(tmp_path: Path):
    source = tmp_path / "doctor_note.txt"
    source.write_text("Patient should rest and hydrate after fever.", encoding="utf-8")

    config = AssistantConfig(
        knowledge_base_path=tmp_path / "knowledge_base.json",
        vector_store_path=tmp_path / "vector_store.json",
        ocr_source_dir=tmp_path,
    )
    kb = KnowledgeBase(config=config)
    ingested = kb.ingest_paths([source])

    assert ingested
    assert config.knowledge_base_path.exists()
    assert kb.search("fever", top_k=3)


def test_upload_endpoint_ingests_file(tmp_path: Path, monkeypatch):
    config = AssistantConfig(
        knowledge_base_path=tmp_path / "knowledge_base.json",
        vector_store_path=tmp_path / "vector_store.json",
        ocr_source_dir=tmp_path / "uploads",
    )
    app = create_app(config)

    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.post(
        "/ingest/upload",
        files={"files": ("report.txt", b"Patient needs hydration after fever.", "text/plain")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ingested"]

    ask = client.post("/ask", json={"question": "What should I do for a fever?"})
    assert ask.status_code == 200
    assert "hydration" in ask.json()["answer"].lower()


def test_empty_store_has_no_fallback_docs(tmp_path: Path):
    config = AssistantConfig(
        knowledge_base_path=tmp_path / "knowledge_base.json",
        vector_store_path=tmp_path / "index.json",
    )
    kb = KnowledgeBase(config=config)

    assert kb.documents == []
    context, _ = kb.build_context("headache")
    assert "upload" in context.lower()
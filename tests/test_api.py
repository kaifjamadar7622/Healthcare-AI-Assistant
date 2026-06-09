from pathlib import Path

from fastapi.testclient import TestClient

from app.api import app as default_app
from app.config import AssistantConfig
from app.main import create_app
from app.llm import ResponseGenerator


def test_health_route_reports_zero_documents_when_empty(tmp_path: Path):
    config = AssistantConfig(
        knowledge_base_path=tmp_path / "knowledge_base.json",
        vector_store_path=tmp_path / "index.json",
        ocr_source_dir=tmp_path / "uploads",
    )
    client = TestClient(create_app(config))

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["total_documents"] == 0


def test_upload_endpoint_ingests_file(tmp_path: Path):
    config = AssistantConfig(
        knowledge_base_path=tmp_path / "knowledge_base.json",
        vector_store_path=tmp_path / "index.json",
        ocr_source_dir=tmp_path / "uploads",
    )
    client = TestClient(create_app(config))

    response = client.post(
        "/ingest/upload",
        files={"files": ("report.txt", b"Patient should rest and hydrate after fever.", "text/plain")},
    )
    assert response.status_code == 200
    assert response.json()["ingested"] == [{"id": response.json()["ingested"][0]["id"], "title": response.json()["ingested"][0]["title"], "source_path": response.json()["ingested"][0]["source_path"], "source_type": response.json()["ingested"][0]["source_type"]}]

    answer = client.post("/ask", json={"question": "What should I do for a fever?"})
    assert answer.status_code == 200
    assert "hydrate" in answer.json()["answer"].lower()


def test_appointment_question_routes_to_mock_tool(tmp_path: Path):
    config = AssistantConfig(
        knowledge_base_path=tmp_path / "knowledge_base.json",
        vector_store_path=tmp_path / "index.json",
        ocr_source_dir=tmp_path / "uploads",
    )
    client = TestClient(create_app(config))

    response = client.post("/ask", json={"question": "Can I book a cardiology appointment for Monday?"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "tool-router"
    assert payload["model"] == "check_available_slots"
    assert "available slots" in payload["answer"].lower()
    assert payload["sources"] == []


def test_default_app_is_importable():
    assert default_app is not None


def test_ollama_response_generator_falls_back_without_server(tmp_path: Path):
    config = AssistantConfig(
        knowledge_base_path=tmp_path / "knowledge_base.json",
        vector_store_path=tmp_path / "index.json",
        ocr_source_dir=tmp_path / "uploads",
        use_ollama=True,
        ollama_url="http://127.0.0.1:9",
    )
    generator = ResponseGenerator(config=config)
    assert generator._ollama_ready is False

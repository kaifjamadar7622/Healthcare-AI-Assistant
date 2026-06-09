from app.agent import HealthcareAssistant
from app.config import AssistantConfig
from app.main import format_reply


def _build_assistant(tmp_path, filename: str, text: str) -> HealthcareAssistant:
    config = AssistantConfig(
        knowledge_base_path=tmp_path / "knowledge_base.json",
        vector_store_path=tmp_path / "index.json",
        ocr_source_dir=tmp_path / "uploads",
    )
    assistant = HealthcareAssistant(config=config)
    source = config.ocr_source_dir / filename
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(text, encoding="utf-8")
    assistant.knowledge_base.ingest_paths([source])
    assistant.reload()
    return assistant


def test_retrieval_returns_relevant_fever_document(tmp_path):
    assistant = _build_assistant(
        tmp_path,
        "fever_note.txt",
        "Patient has fever. Rest, hydrate, and monitor symptoms.",
    )
    reply = assistant.answer("What should I do for a fever?")

    assert reply.sources
    assert any("fever" in source.document.text.lower() for source in reply.sources)
    assert "fever" in reply.answer.lower()


def test_emergency_questions_trigger_disclaimer(tmp_path):
    assistant = _build_assistant(
        tmp_path,
        "triage_note.txt",
        "Emergency warning signs include chest pain and trouble breathing.",
    )
    reply = assistant.answer("I have chest pain and trouble breathing.")

    assert "emergency" in reply.answer.lower()
    assert reply.sources


def test_format_reply_includes_sources(tmp_path):
    assistant = _build_assistant(
        tmp_path,
        "visit_note.txt",
        "Bring your symptom timeline, medication list, and questions to the clinic visit.",
    )
    reply = assistant.answer("How do I prepare for a clinic visit?")

    formatted = format_reply(reply)

    assert "Question:" in formatted
    assert "Sources:" in formatted

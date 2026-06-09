"""Assistant orchestration layer."""

from __future__ import annotations

from dataclasses import dataclass
import re

from .config import AssistantConfig
from .llm import GeneratedResponse, ResponseGenerator
from .rag import KnowledgeBase, RetrievedDocument
from .tools import check_available_slots


EMERGENCY_KEYWORDS = (
    "chest pain",
    "trouble breathing",
    "shortness of breath",
    "stroke",
    "unconscious",
    "severe bleeding",
    "suicidal",
    "overdose",
)


@dataclass(frozen=True, slots=True)
class AssistantReply:
    question: str
    answer: str
    provider: str
    model: str
    sources: list[RetrievedDocument]


class HealthcareAssistant:
    """High-level assistant that ties retrieval and generation together."""

    def __init__(self, config: AssistantConfig | None = None) -> None:
        self.config = config or AssistantConfig()
        self.knowledge_base = KnowledgeBase(config=self.config)
        self.generator = ResponseGenerator(config=self.config)

    def reload(self) -> None:
        """Refresh the knowledge base after new documents are ingested."""

        self.knowledge_base = KnowledgeBase(config=self.config)

    def answer(self, question: str) -> AssistantReply:
        tool_reply = self._route_to_tool(question)
        if tool_reply is not None:
            return tool_reply

        context, sources = self.knowledge_base.build_context(question)
        emergency_flag = self._looks_like_emergency(question)
        generated = self.generator.generate(
            question=question,
            context=context,
            retrieved_documents=sources,
            has_documents=bool(self.knowledge_base.documents),
            emergency_flag=emergency_flag,
        )

        answer = generated.answer
        if emergency_flag and self.config.emergency_disclaimer not in answer:
            answer = f"{self.config.emergency_disclaimer}\n\n{answer}"

        return AssistantReply(
            question=question,
            answer=answer,
            provider=generated.provider,
            model=generated.model,
            sources=sources,
        )

    def _route_to_tool(self, question: str) -> AssistantReply | None:
        lowered = question.lower()
        if "appointment" not in lowered and "book" not in lowered and "slot" not in lowered:
            return None

        match = re.search(r"\b(cardiology|dermatology|orthopedics?|orthopaedics?|neurology|pediatrics?|general medicine)\b", lowered)
        department = match.group(1) if match else "general medicine"

        date_match = re.search(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|today|tomorrow)\b", lowered)
        date = date_match.group(1) if date_match else "next available date"

        slot_result = check_available_slots(department=department, date=date)
        answer = (
            f"I checked the mock appointment tool for {slot_result.department} on {slot_result.date}. "
            f"Available slots: {', '.join(slot_result.available_slots)}."
        )
        return AssistantReply(
            question=question,
            answer=answer,
            provider="tool-router",
            model="check_available_slots",
            sources=[],
        )

    def _looks_like_emergency(self, question: str) -> bool:
        lowered = question.lower()
        return any(keyword in lowered for keyword in EMERGENCY_KEYWORDS)


def run_agent(task: str) -> str:
    """Backward-compatible helper for simple callers."""

    return HealthcareAssistant().answer(task).answer

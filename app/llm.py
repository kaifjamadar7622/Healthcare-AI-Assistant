"""Response generation utilities for the assistant."""

from __future__ import annotations

from dataclasses import dataclass
import json
from urllib.request import Request, urlopen

from .config import AssistantConfig
from .rag import RetrievedDocument


@dataclass(frozen=True, slots=True)
class GeneratedResponse:
    answer: str
    provider: str
    model: str


class ResponseGenerator:
    """Generate a final answer from retrieved context.

    The default implementation is deterministic and offline. If `USE_OPENAI=1` is
    set and the OpenAI package/API key are available, it can upgrade to a hosted
    model without changing the application flow.
    """

    def __init__(self, config: AssistantConfig | None = None) -> None:
        self.config = config or AssistantConfig()
        self._client = None
        self._ollama_ready = False

        if self.config.use_ollama:
            self._ollama_ready = self._probe_ollama()

        if self._client is None and self.config.use_openai:
            try:
                from openai import OpenAI  # type: ignore

                self._client = OpenAI()
            except Exception:
                self._client = None

    def _probe_ollama(self) -> bool:
        try:
            request = Request(f"{self.config.ollama_url.rstrip('/')}/api/tags", method="GET")
            with urlopen(request, timeout=1.5) as response:
                return response.status == 200
        except Exception:
            return False

    def generate(
        self,
        question: str,
        context: str,
        retrieved_documents: list[RetrievedDocument],
        has_documents: bool,
        emergency_flag: bool = False,
    ) -> GeneratedResponse:
        if self._ollama_ready:
            try:
                return self._generate_with_ollama(question, context)
            except Exception:
                self._ollama_ready = False

        if self._client is not None:
            try:
                return self._generate_with_openai(question, context)
            except Exception:
                self._client = None

        return GeneratedResponse(
            answer=self._generate_local_answer(
                question,
                context,
                retrieved_documents,
                has_documents,
                emergency_flag,
            ),
            provider="local",
            model="rule-based",
        )

    def _generate_with_openai(self, question: str, context: str) -> GeneratedResponse:
        prompt = (
            "You are a concise healthcare information assistant. Answer only from the provided context. "
            "If the context does not contain the answer, say you do not know. Do not guess or invent facts. "
            "Keep the response clear, professional, and brief. Do not give a diagnosis or unsafe medical advice. "
            "Always include a brief safety note.\n\n"
            f"Question: {question}\n\nContext:\n{context}"
        )
        completion = self._client.chat.completions.create(  # type: ignore[union-attr]
            model=self.config.openai_model,
            messages=[
                {"role": "system", "content": "You give safe, practical healthcare information."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        answer = completion.choices[0].message.content or ""
        return GeneratedResponse(answer=answer.strip(), provider="openai", model=self.config.openai_model)

    def _generate_with_ollama(self, question: str, context: str) -> GeneratedResponse:
        prompt = (
            "You are a concise healthcare information assistant. Answer only from the provided context. "
            "If the context does not contain the answer, say you do not know. Do not guess or invent facts. "
            "Keep the response clear, professional, and brief. Do not give a diagnosis or unsafe medical advice. "
            "Always include a brief safety note.\n\n"
            f"Question: {question}\n\nContext:\n{context}"
        )
        payload = json.dumps(
            {
                "model": self.config.ollama_model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": "You give safe, practical healthcare information."},
                    {"role": "user", "content": prompt},
                ],
                "options": {"temperature": 0.2},
            }
        ).encode("utf-8")
        request = Request(
            f"{self.config.ollama_url.rstrip('/')}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
        answer = data.get("message", {}).get("content", "")
        return GeneratedResponse(answer=answer.strip(), provider="ollama", model=self.config.ollama_model)

    def _generate_local_answer(
        self,
        question: str,
        context: str,
        retrieved_documents: list[RetrievedDocument],
        has_documents: bool,
        emergency_flag: bool,
    ) -> str:
        lines = [
            "Here is a concise, safety-focused response:",
        ]

        if emergency_flag:
            lines.append(self.config.emergency_disclaimer)

        if retrieved_documents:
            lines.append("Based on the retrieved guidance, the most relevant points are:")
            for match in retrieved_documents:
                # include a short excerpt instead of the whole document for readability
                excerpt = match.document.text.replace('\n', ' ').strip()
                if len(excerpt) > 400:
                    excerpt = excerpt[:400].rsplit(' ', 1)[0] + '...'
                lines.append(f"- {match.document.title}: {excerpt}")
        elif not has_documents:
            lines.append(
                "No documents are indexed yet. Upload PDFs, images, or text files through the API to start retrieval."
            )
        else:
            lines.append(
                "I could not find a strong match in the local knowledge base, so I recommend confirming details with a clinician."
            )

        lines.append(f"Question understood: {question.strip()}")
        lines.append(self.config.medical_safety_note)
        return "\n".join(lines)

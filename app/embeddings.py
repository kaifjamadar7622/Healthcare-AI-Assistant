"""Deterministic local embeddings used for retrieval."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import sqrt
import re
from typing import Protocol


TOKEN_PATTERN = re.compile(r"[a-z0-9']+")


class EmbeddingModel(Protocol):
    """Protocol for embedding backends."""

    dimension: int

    def encode(self, texts: list[str]) -> list[list[float]]:
        ...


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def normalize_vector(vector: list[float]) -> list[float]:
    magnitude = sqrt(sum(value * value for value in vector))
    if magnitude == 0:
        return vector
    return [value / magnitude for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


@dataclass(slots=True)
class HashingEmbeddingModel:
    """Fast, dependency-free bag-of-words embeddings.

    The model is deterministic and works offline, which keeps the project
    runnable in constrained environments while still enabling meaningful search.
    """

    dimension: int = 256

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [self._encode_single(text) for text in texts]

    def _encode_single(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = tokenize(text)
        if not tokens:
            return vector

        counts = Counter(tokens)
        for token, count in counts.items():
            index = self._stable_hash(token)
            vector[index] += float(count)

        for first, second in zip(tokens, tokens[1:]):
            index = self._stable_hash(f"{first}_{second}")
            vector[index] += 0.5

        return normalize_vector(vector)

    def _stable_hash(self, token: str) -> int:
        value = 0
        for character in token:
            value = (value * 33 + ord(character)) % self.dimension
        return value

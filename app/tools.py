"""Simple tool layer for the assistant."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AppointmentSlotResult:
    department: str
    date: str
    available_slots: list[str]


def check_available_slots(department: str, date: str) -> AppointmentSlotResult:
    """Return deterministic mock slots for the demo workflow."""

    normalized_department = department.strip().lower() or "general medicine"
    normalized_date = date.strip() or "next available date"
    return AppointmentSlotResult(
        department=normalized_department,
        date=normalized_date,
        available_slots=["10:00 AM", "12:30 PM", "04:00 PM"],
    )

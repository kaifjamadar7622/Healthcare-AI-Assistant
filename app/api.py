"""Compatibility wrapper for the FastAPI application."""

from __future__ import annotations

from .main import app, create_app

__all__ = ["app", "create_app"]
"""Validate Markdown handoff notes for agent shared-memory systems."""

from .validator import Issue, ValidationResult, validate_markdown

__all__ = ["Issue", "ValidationResult", "validate_markdown"]

__version__ = "0.1.0"

from __future__ import annotations

"""
Feature-View Package.

Öffentliche API:
- render(): baut die komplette Feature-View in Streamlit auf.
"""

from .view import render  # noqa: F401

__all__ = ["render"]
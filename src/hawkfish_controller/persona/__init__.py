"""
Persona system for vendor compatibility layers.

This module provides a plugin architecture for implementing vendor-specific
compatibility modes while maintaining clear disclaimers about not being
the actual vendor.
"""

from .base import PersonaPlugin, PersonaManager
from .registry import persona_registry

__all__ = ["PersonaPlugin", "PersonaManager", "persona_registry"]

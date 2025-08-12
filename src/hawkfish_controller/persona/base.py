"""
Base persona plugin interface and management.
"""

from __future__ import annotations

from typing import Any, Protocol

from fastapi import FastAPI


class PersonaPlugin(Protocol):
    """Protocol for persona plugins."""
    
    name: str
    
    def mount(self, app: FastAPI) -> None:
        """Mount plugin routes to the FastAPI app."""
        ...
    
    def adapt_event(self, core_event: dict[str, Any]) -> list[dict[str, Any]]:
        """Adapt a core event to persona-specific format(s)."""
        ...
    
    def adapt_error(self, core_error: dict[str, Any]) -> dict[str, Any]:
        """Adapt a core error to persona-specific format."""
        ...


class PersonaManager:
    """Manages persona plugins and routing."""
    
    def __init__(self):
        self._plugins: dict[str, PersonaPlugin] = {}
        self._default_persona = "generic"
    
    def register_plugin(self, plugin: PersonaPlugin) -> None:
        """Register a persona plugin."""
        self._plugins[plugin.name] = plugin
    
    def get_plugin(self, persona_name: str) -> PersonaPlugin | None:
        """Get a persona plugin by name."""
        return self._plugins.get(persona_name)
    
    def list_personas(self) -> list[str]:
        """List all available persona names."""
        return list(self._plugins.keys())
    
    def mount_all(self, app: FastAPI) -> None:
        """Mount all registered persona plugins."""
        for plugin in self._plugins.values():
            plugin.mount(app)
    
    def adapt_event(self, persona_name: str, core_event: dict[str, Any]) -> list[dict[str, Any]]:
        """Adapt an event using the specified persona."""
        plugin = self.get_plugin(persona_name)
        if plugin:
            return plugin.adapt_event(core_event)
        return [core_event]  # Return original if no persona
    
    def adapt_error(self, persona_name: str, core_error: dict[str, Any]) -> dict[str, Any]:
        """Adapt an error using the specified persona."""
        plugin = self.get_plugin(persona_name)
        if plugin:
            return plugin.adapt_error(core_error)
        return core_error  # Return original if no persona
    
    @property
    def default_persona(self) -> str:
        """Get the default persona name."""
        return self._default_persona
    
    @default_persona.setter
    def default_persona(self, persona_name: str) -> None:
        """Set the default persona name."""
        if persona_name in self._plugins or persona_name == "generic":
            self._default_persona = persona_name

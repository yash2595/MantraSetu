"""Memory abstractions for conversation state and persistence."""

from abc import ABC


class BaseMemoryStore(ABC):
    """Marker base class for memory stores."""

"""Providers package initialization.

This module exposes the concrete provider implementations used by the
orchestrator.  Importing here allows a single import point for the
application code and enables easy dependency injection.
"""

from .catalog_retriever import CatalogRetriever

# Create a module‑level singleton that can be imported wherever the
# retriever is required.  The instance is initialized on import, which is
# sufficient because the catalogs are cached for the lifetime of the
# process (they are refreshed only on explicit restart as per user
# specification).
catalog_retriever = CatalogRetriever()

__all__ = ["CatalogRetriever", "catalog_retriever"]

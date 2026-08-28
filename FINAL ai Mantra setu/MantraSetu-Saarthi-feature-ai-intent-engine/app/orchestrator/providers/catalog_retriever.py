import httpx
import logging
from typing import List, Dict

try:
    from rapidfuzz import fuzz, process
except ImportError:
    fuzz = None
    process = None

from app.core.config import settings

logger = logging.getLogger(__name__)

_API_BASE = settings.api_base_url.rstrip("/")


class CatalogRetriever:
    """Retrieve and cache puja and pandit catalogs from live backend endpoints.

    The catalogs are fetched synchronously at initialization and stored in memory.
    ``search_puja`` and ``search_pandit`` provide fuzzy matching against the cached
    records using ``rapidfuzz``.
    """

    PUJA_ENDPOINT = f"{_API_BASE}/puja/list"
    PANDIT_ENDPOINT = f"{_API_BASE}/pandit/list"

    def __init__(self) -> None:
        self.puja_catalog: List[Dict] = []
        self.pandit_catalog: List[Dict] = []
        try:
            self._load_catalogs()
        except Exception as exc:
            logger.warning("CatalogRetriever: initial load failed (backend may not be ready yet): %s", exc)

    def _load_catalogs(self) -> None:
        """Synchronously fetch catalogs from the backend.

        If an endpoint is unavailable we log the error and keep the existing cache.
        """
        try:
            puja_resp = httpx.get(self.PUJA_ENDPOINT, timeout=5.0)
            puja_resp.raise_for_status()
            self.puja_catalog = puja_resp.json()
            logger.info("Fetched %d puja records from backend", len(self.puja_catalog))
        except Exception as exc:
            logger.error("Failed to fetch puja catalog: %s", exc)
            self.puja_catalog = []

        try:
            pandit_resp = httpx.get(self.PANDIT_ENDPOINT, timeout=5.0)
            pandit_resp.raise_for_status()
            self.pandit_catalog = pandit_resp.json()
            logger.info("Fetched %d pandit records from backend", len(self.pandit_catalog))
        except Exception as exc:
            logger.warning("Pandit endpoint not available, falling back to empty list: %s", exc)
            self.pandit_catalog = []

    def refresh(self) -> None:
        """Public method to re-fetch both catalogs (can be called on restart)."""
        self._load_catalogs()

    def _fuzzy_match(self, query: str, records: List[Dict], key: str, top_k: int = 3) -> List[Dict]:
        """Return the top_k records whose ``key`` best matches ``query``."""
        if not query or not records:
            return []
        if process is None:
            # rapidfuzz not installed – return first top_k records as fallback
            logger.warning("rapidfuzz not installed, returning unfiltered results")
            return records[:top_k]
        choices = [(rec.get(key, ""), rec) for rec in records]
        matches = process.extract(query, [c[0] for c in choices], scorer=fuzz.ratio, limit=top_k)
        result = []
        for match, score, idx in matches:
            result.append(choices[idx][1])
        return result

    def search_puja(self, query: str, top_k: int = 3) -> List[Dict]:
        """Fuzzy-search puja catalog by ``title`` field."""
        return self._fuzzy_match(query, self.puja_catalog, key="title", top_k=top_k)

    def search_pandit(self, query: str, top_k: int = 3) -> List[Dict]:
        """Fuzzy-search pandit catalog by ``name`` field."""
        return self._fuzzy_match(query, self.pandit_catalog, key="name", top_k=top_k)

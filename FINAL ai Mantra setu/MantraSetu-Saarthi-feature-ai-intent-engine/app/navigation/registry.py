"""Centralized Frontend Route Registry for MantraSetu AgentOS.

Architecture Layer: Static Metadata
Ownership: Route metadata ONLY. No runtime session state, no conversation memory.
Thread Safety: RLock-protected with duplicate-safe registration and stale-index cleanup.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.navigation.discovery import RouteDiscoveryEngine
from app.navigation.models import NavigationNodeType, WebsiteNode
from app.navigation.validation import MetadataValidator, RouteRegistrationError

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "RouteRegistry"
_COMPONENT_VERSION = "4.1"


class RouteRegistry:
    """Thread-safe, dynamically extensible registry storing all frontend routes and metadata.

    All O(1) indexes are kept strictly synchronized during registration and overwrite.
    Duplicate registrations remove stale index entries before rebuilding fresh ones.

    Public API (backward-compatible):
        get_route(), match_path(), register_route(), get_routes_by_workflow(),
        get_routes_by_capability(), get_routes_by_page_type(), get_child_routes(),
        search_routes(), search_by_semantic_label(), search_by_keywords(),
        get_all_routes(), get_all_raw_routes(), statistics(), health()
    """

    def __init__(
        self,
        discovery_engine: RouteDiscoveryEngine | None = None,
        validator: MetadataValidator | None = None,
    ) -> None:
        self._engine = discovery_engine or RouteDiscoveryEngine()
        self._validator = validator or MetadataValidator(default_strict=True)

        # Primary store: path -> WebsiteNode (O(1))
        self._routes: dict[str, WebsiteNode] = {}
        self._raw_routes: dict[str, dict[str, Any]] = {}

        # O(1) secondary indexes
        self._workflow_index: dict[str, list[WebsiteNode]] = {}
        self._capability_index: dict[str, list[WebsiteNode]] = {}
        self._page_type_index: dict[str, list[WebsiteNode]] = {}
        self._parent_index: dict[str, list[WebsiteNode]] = {}
        self._semantic_index: dict[str, list[WebsiteNode]] = {}

        # Diagnostics counters
        self._registration_count = 0
        self._lookup_count = 0
        self._search_count = 0
        self._started_at: str = datetime.now(timezone.utc).isoformat()

        # RLock prevents deadlocks from recursive public method invocations
        self._lock = RLock()
        self._auto_discover()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _auto_discover(self) -> None:
        """Discover and register all routes from RouteDiscoveryEngine on startup."""
        raw_list = self._engine.discover_routes()
        nodes = self._engine.to_website_nodes()
        existing_paths = {item["path"] for item in raw_list}
        for item, node in zip(raw_list, nodes):
            self._validator.validate_route(item, existing_paths=existing_paths, strict=True)
            self._index_node(item, node)
        logger.info(
            "RouteRegistry initialized [operation=auto_discover, route_count=%d, metadata_version=%s]",
            len(self._routes),
            _COMPONENT_VERSION,
        )

    def _remove_from_indexes(self, node: WebsiteNode) -> None:
        """Remove a WebsiteNode from all secondary indexes. Prevents stale entries on overwrite."""
        wf = node.metadata.get("workflow")
        if wf and wf in self._workflow_index:
            self._workflow_index[wf] = [n for n in self._workflow_index[wf] if n.url != node.url]

        pt = str(node.metadata.get("page_type", "PAGE"))
        if pt in self._page_type_index:
            self._page_type_index[pt] = [n for n in self._page_type_index[pt] if n.url != node.url]

        for cap in node.metadata.get("page_capabilities", []):
            if cap in self._capability_index:
                self._capability_index[cap] = [n for n in self._capability_index[cap] if n.url != node.url]

        parent = node.metadata.get("parent")
        if parent and parent in self._parent_index:
            self._parent_index[parent] = [n for n in self._parent_index[parent] if n.url != node.url]

        label = str(node.metadata.get("semantic_label", node.name)).lower()
        if label in self._semantic_index:
            self._semantic_index[label] = [n for n in self._semantic_index[label] if n.url != node.url]

    def _index_node(self, route_spec: dict[str, Any], node: WebsiteNode) -> None:
        """Add a WebsiteNode to primary store and all secondary indexes."""
        path = node.url

        # Evict stale indexes if overwriting an existing route
        if path in self._routes:
            self._remove_from_indexes(self._routes[path])

        self._routes[path] = node
        self._raw_routes[path] = route_spec
        self._registration_count += 1

        wf = node.metadata.get("workflow")
        if wf:
            self._workflow_index.setdefault(wf, []).append(node)

        pt = str(node.metadata.get("page_type", "PAGE"))
        self._page_type_index.setdefault(pt, []).append(node)

        for cap in node.metadata.get("page_capabilities", []):
            self._capability_index.setdefault(cap, []).append(node)

        parent = node.metadata.get("parent")
        if parent:
            self._parent_index.setdefault(parent, []).append(node)

        label = str(node.metadata.get("semantic_label", node.name)).lower()
        self._semantic_index.setdefault(label, []).append(node)

    @staticmethod
    def _build_node(route_spec: dict[str, Any]) -> WebsiteNode:
        """Construct a WebsiteNode from a raw route specification dict."""
        path = route_spec["path"]
        name = route_spec.get("name", path.strip("/").capitalize() or "Home")
        return WebsiteNode(
            url=path,
            name=name,
            node_type=NavigationNodeType.PAGE,
            metadata={
                "page_type": route_spec.get("page_type", "PAGE"),
                "semantic_label": route_spec.get("semantic_label", name),
                "description": route_spec.get("description", ""),
                "parent": route_spec.get("parent"),
                "children": route_spec.get("children", []),
                "breadcrumbs": route_spec.get("breadcrumbs", [name]),
                "workflow": route_spec.get("workflow"),
                "workflow_step": route_spec.get("workflow_step"),
                "parameters": route_spec.get("parameters", []),
                "validation_rules": route_spec.get("validation_rules", {}),
                "requires_auth": route_spec.get("requires_auth", False),
                "permissions": route_spec.get("permissions", []),
                "feature_flags": route_spec.get("feature_flags", []),
                "allowed_transitions": route_spec.get("allowed_transitions", []),
                "previous_routes": route_spec.get("previous_routes", []),
                "next_routes": route_spec.get("next_routes", []),
                "shortcut_routes": route_spec.get("shortcut_routes", []),
                "recovery_routes": route_spec.get("recovery_routes", []),
                "page_capabilities": route_spec.get("page_capabilities", []),
                "supported_ai_actions": route_spec.get("supported_ai_actions", []),
                "visible_regions": route_spec.get("visible_regions", []),
                "primary_actions": route_spec.get("primary_actions", []),
                "secondary_actions": route_spec.get("secondary_actions", []),
                "forms": route_spec.get("forms", []),
                "buttons": route_spec.get("buttons", []),
                "dropdowns": route_spec.get("dropdowns", []),
                "filters": route_spec.get("filters", []),
                "cards": route_spec.get("cards", []),
                "tables": route_spec.get("tables", []),
                "dialogs": route_spec.get("dialogs", []),
                "tabs": route_spec.get("tabs", []),
                "accordions": route_spec.get("accordions", []),
                "search_boxes": route_spec.get("search_boxes", []),
                "uploads": route_spec.get("uploads", []),
                "downloads": route_spec.get("downloads", []),
                "metadata_version": route_spec.get("metadata_version", _COMPONENT_VERSION),
                "updated_at": route_spec.get("updated_at", datetime.now(timezone.utc).isoformat()),
            },
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register_route(self, route_spec: dict[str, Any], strict: bool = False) -> WebsiteNode:
        """Register or overwrite a frontend route with duplicate-safe index rebuilding.

        Existing route at the same path is cleanly evicted from all indexes before
        the new node is indexed. Complexity: O(k) where k = number of capabilities.

        Args:
            route_spec: Route specification dictionary.
            strict: If True, validation raises on failure; if False, logs warning.

        Returns:
            The registered or overwritten WebsiteNode.

        Raises:
            RouteRegistrationError: If the route specification is fundamentally invalid.
        """
        with self._lock:
            existing_paths = set(self._routes.keys())
            valid = self._validator.validate_route(route_spec, existing_paths=existing_paths, strict=strict)
            if not valid:
                raise RouteRegistrationError(f"Route specification failed validation: {route_spec.get('path')}")

            node = self._build_node(route_spec)
            path = node.url
            is_overwrite = path in self._routes

            self._index_node(route_spec, node)
            logger.info(
                "Route %s [operation=register_route, route=%s, workflow=%s, metadata_version=%s]",
                "overwritten" if is_overwrite else "registered",
                path,
                route_spec.get("workflow"),
                route_spec.get("metadata_version", _COMPONENT_VERSION),
            )
            return node

    def get_route(self, path: str) -> WebsiteNode | None:
        """Retrieve WebsiteNode for an exact path string. Complexity: O(1)."""
        with self._lock:
            self._lookup_count += 1
            return self._routes.get(path)

    def get_all_routes(self) -> tuple[WebsiteNode, ...]:
        """Return immutable tuple of all registered WebsiteNode entities."""
        with self._lock:
            return tuple(self._routes.values())

    def get_all_raw_routes(self) -> tuple[dict[str, Any], ...]:
        """Return immutable tuple of raw route specification dicts."""
        with self._lock:
            return tuple(self._raw_routes.values())

    def match_path(self, path: str) -> WebsiteNode | None:
        """Match a path against registered routes, including dynamic patterns like /puja/[id].

        Exact match is O(1). Dynamic pattern fallback is O(n) and documented as such.
        """
        with self._lock:
            self._lookup_count += 1
            if path in self._routes:
                return self._routes[path]
            # O(n) dynamic pattern fallback — intentional and documented
            for registered_path, node in self._routes.items():
                if "[" in registered_path and "]" in registered_path:
                    pattern_parts = registered_path.strip("/").split("/")
                    actual_parts = path.strip("/").split("/")
                    if len(pattern_parts) == len(actual_parts):
                        matched = all(
                            (p.startswith("[") and p.endswith("]")) or p == a
                            for p, a in zip(pattern_parts, actual_parts)
                        )
                        if matched:
                            return node
            return None

    def get_routes_by_workflow(self, workflow_name: str) -> tuple[WebsiteNode, ...]:
        """Return all routes for a workflow. Complexity: O(1) index lookup."""
        with self._lock:
            self._lookup_count += 1
            return tuple(self._workflow_index.get(workflow_name, []))

    def get_routes_by_capability(self, capability_name: str) -> tuple[WebsiteNode, ...]:
        """Return all routes exhibiting a capability. Complexity: O(1) index lookup."""
        with self._lock:
            self._lookup_count += 1
            return tuple(self._capability_index.get(capability_name, []))

    def get_routes_by_page_type(self, page_type: str) -> tuple[WebsiteNode, ...]:
        """Return all routes of a given page type. Complexity: O(1) index lookup."""
        with self._lock:
            self._lookup_count += 1
            return tuple(self._page_type_index.get(page_type, []))

    def get_child_routes(self, parent_path: str) -> tuple[WebsiteNode, ...]:
        """Return all direct child routes of a parent path. Complexity: O(1) index lookup."""
        with self._lock:
            self._lookup_count += 1
            return tuple(self._parent_index.get(parent_path, []))

    def search_routes(self, query: str) -> tuple[WebsiteNode, ...]:
        """Search routes by path, name, or semantic label substring. Complexity: O(n)."""
        query_lower = query.lower()
        with self._lock:
            self._search_count += 1
            return tuple(
                node for node in self._routes.values()
                if query_lower in node.url.lower()
                or query_lower in node.name.lower()
                or query_lower in str(node.metadata.get("semantic_label", "")).lower()
            )

    def search_by_semantic_label(self, label_query: str) -> tuple[WebsiteNode, ...]:
        """Search routes by semantic label substring. Complexity: O(n)."""
        query_lower = label_query.lower()
        with self._lock:
            self._search_count += 1
            return tuple(
                node for node in self._routes.values()
                if query_lower in str(node.metadata.get("semantic_label", "")).lower()
            )

    def search_by_keywords(self, keywords: list[str]) -> tuple[WebsiteNode, ...]:
        """Search routes matching any keyword in name, description, or capabilities. Complexity: O(n)."""
        kw_set = {k.lower() for k in keywords}
        with self._lock:
            self._search_count += 1
            matched = []
            for node in self._routes.values():
                meta = node.metadata
                text = " ".join([
                    node.name,
                    str(meta.get("semantic_label", "")),
                    str(meta.get("description", "")),
                    " ".join(str(c) for c in meta.get("page_capabilities", [])),
                ]).lower()
                if any(kw in text for kw in kw_set):
                    matched.append(node)
            return tuple(matched)

    def statistics(self) -> dict[str, Any]:
        """Return read-only enterprise diagnostics for RouteRegistry."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_routes": len(self._routes),
                "registration_count": self._registration_count,
                "lookup_count": self._lookup_count,
                "search_count": self._search_count,
                "indexed_workflows": len(self._workflow_index),
                "indexed_capabilities": len(self._capability_index),
                "indexed_page_types": len(self._page_type_index),
                "indexed_parents": len(self._parent_index),
                "validation_failures": self._validator.validation_failures_count,
            }

    def health(self) -> dict[str, Any]:
        """Return read-only health status for RouteRegistry."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "status": "HEALTHY" if len(self._routes) > 0 else "UNHEALTHY",
                "route_count": len(self._routes),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

"""Connection Pool Manager for Enterprise Infrastructure Sprint 6A v1.1."""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import RLock
from typing import Any, Dict


@dataclass
class PoolStats:
    """Pool statistics for a database target."""

    name: str
    max_size: int = 50
    min_size: int = 5
    active_connections: int = 2
    idle_connections: int = 8
    exhausted_count: int = 0
    recovery_count: int = 0


class ConnectionPoolManager:
    """Manager monitoring and maintaining database connection pools (Postgres, Redis, Mongo)."""

    def __init__(self):
        self._lock = RLock()
        self._pools: Dict[str, PoolStats] = {
            "postgresql": PoolStats("postgresql", max_size=50, min_size=5, active_connections=3, idle_connections=10),
            "redis": PoolStats("redis", max_size=100, min_size=10, active_connections=5, idle_connections=20),
            "mongodb": PoolStats("mongodb", max_size=50, min_size=5, active_connections=2, idle_connections=8),
        }

    def acquire_connection(self, pool_name: str) -> bool:
        """Acquire connection from named pool."""
        with self._lock:
            pool = self._pools.get(pool_name)
            if not pool:
                return False
            if pool.idle_connections > 0:
                pool.idle_connections -= 1
                pool.active_connections += 1
                return True
            elif pool.active_connections < pool.max_size:
                pool.active_connections += 1
                return True
            else:
                pool.exhausted_count += 1
                return False

    def release_connection(self, pool_name: str) -> bool:
        """Release connection back to named pool."""
        with self._lock:
            pool = self._pools.get(pool_name)
            if not pool or pool.active_connections <= 0:
                return False
            pool.active_connections -= 1
            pool.idle_connections += 1
            if pool.exhausted_count > 0:
                pool.recovery_count += 1
            return True

    def get_pool_stats(self, pool_name: str) -> Dict[str, Any]:
        with self._lock:
            pool = self._pools.get(pool_name)
            if not pool:
                return {}
            return {
                "name": pool.name,
                "max_size": pool.max_size,
                "min_size": pool.min_size,
                "active_connections": pool.active_connections,
                "idle_connections": pool.idle_connections,
                "exhausted_count": pool.exhausted_count,
                "recovery_count": pool.recovery_count,
            }

    def statistics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "pools_monitored_count": len(self._pools),
                "total_active_connections": sum(p.active_connections for p in self._pools.values()),
                "total_idle_connections": sum(p.idle_connections for p in self._pools.values()),
            }

    def health(self) -> Dict[str, Any]:
        with self._lock:
            exhausted = sum(p.exhausted_count for p in self._pools.values())
            status = "HEALTHY" if exhausted == 0 else "DEGRADED"
            return {"status": status, "ready": True}

    def metrics(self) -> Dict[str, Any]:
        with self._lock:
            total_cap = sum(p.max_size for p in self._pools.values())
            total_active = sum(p.active_connections for p in self._pools.values())
            utilization = (total_active / total_cap * 100.0) if total_cap > 0 else 0.0
            return {
                "total_pool_capacity": total_cap,
                "pool_utilization_percentage": round(utilization, 2),
            }

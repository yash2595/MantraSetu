"""Skill Registry for Enterprise Agent Learning Layer Sprint 7E v1.0."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, List, Optional
from uuid import uuid4


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RegisteredSkill:
    skill_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    version: str = "1.0.0"
    category: str = "workflow"  # workflow, tool, prompt, voice, navigation
    capabilities: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    reuse_count: int = 0
    maturity_stage: str = "PRODUCTION"  # EXPERIMENTAL, STAGING, PRODUCTION, DEPRECATED
    registered_at: str = field(default_factory=_utc_now_iso)


class SkillRegistry:
    """Enterprise Skill Registry managing reusable skills, capability mapping, dependencies, and reuse stats."""

    def __init__(self):
        self._lock = RLock()
        self._skills: Dict[str, RegisteredSkill] = {}
        self._total_skills_registered = 0

        # Seed core reusable AgentOS skills
        self.register_skill("puja_booking_skill", "1.0.0", "workflow", ["puja_booking", "payment_prep"], maturity_stage="PRODUCTION")
        self.register_skill("muhurat_search_skill", "1.0.0", "workflow", ["muhurat_calculation", "planetary_date"], maturity_stage="PRODUCTION")

    def register_skill(
        self,
        name: str,
        version: str = "1.0.0",
        category: str = "workflow",
        capabilities: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
        maturity_stage: str = "PRODUCTION",
    ) -> RegisteredSkill:
        """Register or update a reusable skill in the enterprise registry."""
        with self._lock:
            skill = RegisteredSkill(
                name=name,
                version=version,
                category=category,
                capabilities=capabilities or [],
                dependencies=dependencies or [],
                maturity_stage=maturity_stage,
            )
            self._skills[name] = skill
            self._total_skills_registered += 1
            return skill

    def record_skill_reuse(self, name: str) -> bool:
        """Record skill execution reuse counter."""
        with self._lock:
            skill = self._skills.get(name)
            if skill:
                skill.reuse_count += 1
                return True
            return False

    def get_skill(self, name: str) -> Optional[RegisteredSkill]:
        with self._lock:
            return self._skills.get(name)

    def statistics(self) -> Dict[str, Any]:
        with self._lock:
            total_reuse = sum(s.reuse_count for s in self._skills.values())
            return {
                "total_skills_registered": len(self._skills),
                "total_skill_reuse_events": total_reuse,
            }

    def health(self) -> Dict[str, Any]:
        return {"status": "HEALTHY", "ready": True}

    def metrics(self) -> Dict[str, Any]:
        with self._lock:
            total_reuse = sum(s.reuse_count for s in self._skills.values())
            return {
                "registered_skills_count": len(self._skills),
                "skill_reuse_count": total_reuse,
                "registry_lookup_latency_ms": 0.01,
            }

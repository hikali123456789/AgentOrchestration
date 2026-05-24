"""Agent Registry — Manages agent lifecycle and metadata."""

import json
import logging
import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    FAILED = "failed"
    TERMINATED = "terminated"


class AgentRegistry:
    # Cache for capability discovery API
    _capability_cache: Dict[str, List[str]] = {}
    
    def __init__(self, storage_backend: str = "memory"):
        self.storage_backend = storage_backend
        self._agents: Dict[str, Dict[str, Any]] = {}
        self._index: Dict[str, List[str]] = {}

    def register(self, name: str, agent_type: str, config: Optional[Dict] = None) -> str:
        agent_id = str(uuid.uuid4())
        timestamp = time.time()
        self._agents[agent_id] = {
            "id": agent_id,
            "name": name,
            "type": agent_type,
            "status": AgentStatus.PENDING.value,
            "config": config or {},
            "created_at": timestamp,
            "updated_at": timestamp,
            "version": "1.0.0",
            "enabled": True,  # New field for enable/disable control
            "metrics": {"tasks_completed": 0, "errors": 0, "uptime": 0},
        }
        group = agent_type.split(".")[0]
        if group not in self._index:
            self._index[group] = []
        self._index[group].append(agent_id)
        # Invalidate cache when agent is registered
        self._invalidate_cache(group)
        return agent_id

    def get(self, agent_id: str) -> Optional[Dict[str, Any]]:
        return self._agents.get(agent_id)

    def list(self, status: Optional[AgentStatus] = None, group: Optional[str] = None, 
             include_disabled: bool = False) -> List[Dict[str, Any]]:
        """List agents with optional filtering.
        
        Args:
            status: Filter by agent status
            group: Filter by agent type group
            include_disabled: If False (default), exclude disabled agents from results.
                            This enforces the capability discovery API invariant.
        
        Returns:
            List of agent dictionaries matching the filters.
        
        Note:
            By default, disabled agents are excluded from listings to prevent
            tasks from resolving to unavailable, unauthorized, or incompatible handlers.
        """
        agents = self._agents.values()
        
        # Enforce capability discovery API invariant: exclude disabled entries
        if not include_disabled:
            agents = [a for a in agents if a.get("enabled", True)]
            logger.debug(f"Filtered out disabled agents, {len(list(agents))} enabled agents remain")
        
        if status:
            agents = [a for a in agents if a["status"] == status.value]
        if group:
            agent_ids = self._index.get(group, [])
            agents = [a for a in agents if a["id"] in agent_ids]
        return list(agents)

    def update_status(self, agent_id: str, status: AgentStatus) -> bool:
        if agent_id not in self._agents:
            return False
        self._agents[agent_id]["status"] = status.value
        self._agents[agent_id]["updated_at"] = time.time()
        return True

    def set_enabled(self, agent_id: str, enabled: bool) -> bool:
        """Enable or disable an agent.
        
        When an agent is disabled, it will be excluded from capability discovery
        API listings by default, preventing tasks from resolving to unavailable handlers.
        
        Args:
            agent_id: The agent ID to enable/disable
            enabled: True to enable, False to disable
            
        Returns:
            True if successful, False if agent not found
        """
        if agent_id not in self._agents:
            return False
        
        old_enabled = self._agents[agent_id].get("enabled", True)
        self._agents[agent_id]["enabled"] = enabled
        self._agents[agent_id]["updated_at"] = time.time()
        
        # Invalidate cache when agent enabled state changes
        group = self._agents[agent_id]["type"].split(".")[0]
        self._invalidate_cache(group)
        
        logger.info(f"Agent {agent_id} {'enabled' if enabled else 'disabled'} (was {old_enabled})")
        return True

    def is_enabled(self, agent_id: str) -> bool:
        """Check if an agent is enabled."""
        agent = self._agents.get(agent_id)
        return agent.get("enabled", True) if agent else False

    def _invalidate_cache(self, group: str) -> None:
        """Invalidate cached registry lookups for a group.
        
        This ensures that capability discovery API returns fresh data
        after agent enable/disable state changes.
        """
        if group in self._capability_cache:
            del self._capability_cache[group]
            logger.debug(f"Invalidated cache for group: {group}")

    def delete(self, agent_id: str) -> bool:
        if agent_id not in self._agents:
            return False
        agent = self._agents.pop(agent_id)
        group = agent["type"].split(".")[0]
        if group in self._index and agent_id in self._index[group]:
            self._index[group].remove(agent_id)
        # Invalidate cache when agent is deleted
        self._invalidate_cache(group)
        return True

    def count(self) -> int:
        return len(self._agents)
    
    def count_enabled(self) -> int:
        """Count only enabled agents."""
        return sum(1 for a in self._agents.values() if a.get("enabled", True))

# 2019-01-29T11:24:49 update

# 2019-04-09T13:38:38 update

# 2019-04-11T11:24:12 update

# 2019-06-26T17:03:48 update

# 2019-07-03T14:55:48 update

# 2019-07-18T18:18:47 update

# 2019-11-05T11:27:19 update

# 2019-11-20T11:35:05 update

# 2019-11-23T15:28:54 update

# 2020-03-13T09:23:07 update

# 2020-03-30T19:31:18 update

# 2020-04-22T15:03:30 update

# 2020-07-21T10:00:48 update

# 2020-09-10T09:02:08 update

# 2020-09-10T13:39:12 update

# 2020-09-22T16:27:52 update

# 2020-10-15T10:33:14 update

# 2021-05-13T11:15:56 update

# 2021-07-07T14:57:13 update

# 2021-07-13T15:15:19 update

# 2021-07-27T10:18:16 update

# 2022-03-11T15:24:11 update

# 2022-09-22T13:24:20 update

# 2022-11-01T12:20:40 update

# 2023-01-30T12:32:27 update

# 2023-03-10T09:43:50 update

# 2023-05-10T14:28:01 update

# 2023-05-11T20:04:46 update

# 2023-05-30T17:00:59 update

# 2023-07-13T17:54:32 update

# 2023-07-20T19:04:20 update

# 2023-07-31T17:00:02 update

# 2023-09-05T19:42:07 update

# 2024-01-02T10:29:47 update

# 2024-09-17T12:45:29 update

# 2024-09-17T11:51:01 update

# 2024-11-06T18:20:15 update

# 2025-01-12T15:13:14 update

# 2025-01-14T20:24:39 update

# 2025-03-26T20:21:27 update

# 2025-04-10T18:27:06 update

# 2025-06-19T20:34:58 update

# 2025-06-21T20:23:53 update

# 2025-06-24T20:30:30 update

# 2025-07-03T13:28:03 update

# 2025-07-24T17:42:21 update

# 2025-08-19T17:42:23 update

# 2025-08-21T11:06:52 update

# 2025-10-24T09:10:08 update

# 2025-12-18T19:34:38 update

# 2026-02-06T11:22:22 update

# 2026-02-13T15:42:04 update

# 2026-04-10T08:16:30 update

# 2026-04-29T18:16:11 update

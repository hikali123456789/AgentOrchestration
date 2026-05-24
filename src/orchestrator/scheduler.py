"""Task Scheduler — Priority-based task queuing with safe payload handling."""

import heapq
import time
import logging
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

logger = logging.getLogger(__name__)


class MalformedPayloadError(Exception):
    """Raised when a payload fails validation."""
    pass


def validate_task_payload(task: Dict) -> List[str]:
    """Validate a task payload. Returns list of errors (empty if valid)."""
    errors = []
    if not isinstance(task, dict):
        return ["Payload must be a dictionary"]
    if "type" not in task:
        errors.append("Missing required field: 'type'")
    if "type" in task and not isinstance(task["type"], str):
        errors.append("Field 'type' must be a string")
    if "priority" in task and not isinstance(task["priority"], (int, float)):
        errors.append("Field 'priority' must be a number")
    return errors


class PriorityQueue:
    def __init__(self):
        self._queue = []
        self._counter = 0

    def push(self, item: Any, priority: int = 0) -> None:
        heapq.heappush(self._queue, (-priority, self._counter, item))
        self._counter += 1

    def pop(self) -> Optional[Any]:
        if self._queue:
            return heapq.heappop(self._queue)[2]
        return None

    def __len__(self) -> int:
        return len(self._queue)


class TaskScheduler:
    def __init__(self, strict_validation: bool = True):
        self._queues: Dict[str, PriorityQueue] = {}
        self._scheduled: Dict[str, float] = {}
        self._in_flight: Dict[str, Dict] = {}
        self._max_retries = 3
        self._strict_validation = strict_validation
        self._rejected: Set[str] = set()

    def _validate(self, task: Dict) -> Dict:
        errors = validate_task_payload(task)
        if errors:
            logger.warning(f"Payload validation failed: {errors}")
            if self._strict_validation:
                raise MalformedPayloadError("; ".join(errors))
            task["_validation_errors"] = errors
        task.setdefault("type", "unknown")
        task.setdefault("payload", {})
        return task

    def enqueue(self, task: Dict, queue: str = "default", priority: int = 0) -> str:
        task = self._validate(task)
        task_id = str(uuid4())
        task["id"] = task_id
        task["enqueued_at"] = time.time()
        task["retries"] = 0
        if queue not in self._queues:
            self._queues[queue] = PriorityQueue()
        self._queues[queue].push(task, priority)
        logger.debug(f"Enqueued task {task_id}")
        return task_id

    def schedule(self, task: Dict, delay: float, queue: str = "default", priority: int = 0) -> str:
        task = self._validate(task)
        task_id = str(uuid4())
        task["id"] = task_id
        self._scheduled[task_id] = time.time() + delay
        return task_id

    async def dequeue(self, queue: str = "default", timeout: float = 1.0) -> Optional[Dict]:
        now = time.time()
        expired = [tid for tid, t in self._scheduled.items() if t <= now]
        for tid in expired:
            task = self._scheduled.pop(tid)
            if task:
                self.enqueue(task, queue)
        if queue in self._queues and len(self._queues[queue]) > 0:
            task = self._queues[queue].pop()
            if task:
                self._in_flight[task["id"]] = task
                return task
        return None

    def complete(self, task_id: str) -> bool:
        return self._in_flight.pop(task_id, None) is not None

    def fail(self, task_id: str, queue: str = "default") -> bool:
        task = self._in_flight.pop(task_id, None)
        if task:
            task["retries"] += 1
            if task["retries"] < self._max_retries:
                self.enqueue(task, queue, priority=task.get("priority", 0))
                return True
        return False

    def reject(self, task_id: str, reason: str) -> bool:
        task = self._in_flight.pop(task_id, None)
        if task:
            self._rejected.add(task_id)
            logger.warning(f"Rejected task {task_id}: {reason}")
            return True
        return False
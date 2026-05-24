"""Trace explorer API with nested filter depth guard."""

import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)
router = APIRouter()

# Maximum allowed nesting depth for trace filters
MAX_FILTER_DEPTH = 5


class TraceFilter(BaseModel):
    """Trace query filter with depth validation."""
    field: str
    op: str
    value: Any
    nested: Optional[List["TraceFilter"]] = None
    
    @validator("nested")
    def check_nested_depth(cls, v):
        """Validate nested filter depth doesn't exceed maximum."""
        if v is None:
            return v
        
        def get_depth(filters: List["TraceFilter"], current_depth: int = 1) -> int:
            if not filters:
                return current_depth
            max_depth = current_depth
            for f in filters:
                if f.nested:
                    depth = get_depth(f.nested, current_depth + 1)
                    max_depth = max(max_depth, depth)
            return max_depth
        
        depth = get_depth(v)
        if depth > MAX_FILTER_DEPTH:
            raise ValueError(
                f"Filter nesting depth ({depth}) exceeds maximum allowed ({MAX_FILTER_DEPTH})"
            )
        return v


class TraceQueryRequest(BaseModel):
    """Trace query request with guard."""
    agent_id: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    filters: Optional[List[TraceFilter]] = None
    limit: int = Field(default=100, ge=1, le=1000)


class TraceQueryService:
    """Shared service for trace queries with validation."""
    
    @staticmethod
    def validate_query(request: TraceQueryRequest) -> None:
        """
        Validate trace query before execution.
        
        Raises:
            HTTPException: If validation fails
        """
        # Validate filter depth
        if request.filters:
            def check_depth(filters: List[TraceFilter], depth: int = 1) -> int:
                if not filters:
                    return depth
                max_d = depth
                for f in filters:
                    if f.nested:
                        d = check_depth(f.nested, depth + 1)
                        max_d = max(max_d, d)
                return max_d
            
            actual_depth = check_depth(request.filters)
            if actual_depth > MAX_FILTER_DEPTH:
                logger.warning(
                    f"Trace query rejected: filter depth {actual_depth} exceeds {MAX_FILTER_DEPTH}"
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"Filter nesting depth ({actual_depth}) exceeds maximum ({MAX_FILTER_DEPTH})"
                )
        
        logger.info(f"Trace query validated for agent: {request.agent_id}")
    
    @staticmethod
    def execute_query(request: TraceQueryRequest) -> Dict[str, Any]:
        """
        Execute validated trace query.
        
        Args:
            request: Validated trace query request
            
        Returns:
            Query results
        """
        # Simulate trace lookup
        return {
            "traces": [],
            "total": 0,
            "query": {
                "agent_id": request.agent_id,
                "filters_count": len(request.filters) if request.filters else 0
            }
        }


@router.post("/traces/query")
async def query_traces(request: TraceQueryRequest):
    """
    Query traces with nested filter depth guard.
    
    Validates filter nesting depth before executing query.
    Returns 400 if depth exceeds maximum.
    """
    # Service-level validation (guard)
    TraceQueryService.validate_query(request)
    
    # Execute query only if validation passed
    result = TraceQueryService.execute_query(request)
    return result


@router.get("/traces/{trace_id}")
async def get_trace(trace_id: str):
    """Get a specific trace by ID."""
    # Simulate trace lookup
    return {"trace_id": trace_id, "status": "found", "events": []}


def count_filter_depth(filters: Optional[List[TraceFilter]]) -> int:
    """Helper to count filter nesting depth."""
    if not filters:
        return 0
    
    def get_depth(f: TraceFilter, current: int = 1) -> int:
        if not f.nested:
            return current
        return max(get_depth(nested, current + 1) for nested in f.nested)
    
    return max(get_depth(f) for f in filters)
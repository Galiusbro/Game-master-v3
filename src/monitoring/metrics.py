"""
Prometheus metrics for Game Master V3
"""
from prometheus_client import Counter, Histogram, Gauge
import time
from functools import wraps
from typing import Callable, Any

# AI Operations Metrics
ai_requests_total = Counter(
    'gamemaster_ai_requests_total',
    'Total number of AI requests',
    ['operation_type', 'model', 'status']
)

ai_request_duration = Histogram(
    'gamemaster_ai_request_duration_seconds',
    'Time spent on AI requests',
    ['operation_type', 'model'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0)
)

ai_tokens_used = Counter(
    'gamemaster_ai_tokens_total',
    'Total tokens used in AI requests',
    ['operation_type', 'model', 'token_type']
)

ai_confidence_score = Histogram(
    'gamemaster_ai_confidence_score',
    'AI response confidence scores',
    ['operation_type'],
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
)

ai_hallucinations_total = Counter(
    'gamemaster_ai_hallucinations_total',
    'Total number of detected hallucinations',
    ['operation_type']
)

# Context Building Metrics
context_entities_total = Histogram(
    'gamemaster_context_entities_total',
    'Number of entities in context',
    ['operation_type'],
    buckets=(1, 5, 10, 20, 50, 100, 200)
)

context_build_duration = Histogram(
    'gamemaster_context_build_duration_seconds',
    'Time spent building context',
    ['operation_type'],
    buckets=(0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0)
)

# Database Operations
db_operations_total = Counter(
    'gamemaster_db_operations_total',
    'Total database operations',
    ['db_type', 'operation', 'status']
)

db_operation_duration = Histogram(
    'gamemaster_db_operation_duration_seconds',
    'Database operation duration',
    ['db_type', 'operation'],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0)
)

# World State Metrics
active_players = Gauge(
    'gamemaster_active_players',
    'Number of active players'
)

world_entities_total = Gauge(
    'gamemaster_world_entities_total',
    'Total entities in world',
    ['entity_type']
)

# Event Sourcing Metrics
events_logged_total = Counter(
    'gamemaster_events_logged_total',
    'Total events logged',
    ['event_type', 'actor_type']
)

world_snapshots_total = Counter(
    'gamemaster_world_snapshots_total',
    'Total world snapshots created',
    ['trigger_type']
)


def track_ai_operation(operation_type: str, model: str = "unknown"):
    """Decorator to track AI operations"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            status = "success"
            
            try:
                result = await func(*args, **kwargs)
                
                # Track metrics from AI response if available
                if hasattr(result, 'tokens_used') and result.tokens_used:
                    ai_tokens_used.labels(
                        operation_type=operation_type,
                        model=model,
                        token_type="total"
                    ).inc(result.tokens_used)
                
                if hasattr(result, 'confidence') and result.confidence is not None:
                    ai_confidence_score.labels(
                        operation_type=operation_type
                    ).observe(result.confidence)
                
                if hasattr(result, 'hallucination_detected') and result.hallucination_detected:
                    ai_hallucinations_total.labels(
                        operation_type=operation_type
                    ).inc()
                
                return result
                
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time
                ai_request_duration.labels(
                    operation_type=operation_type,
                    model=model
                ).observe(duration)
                
                ai_requests_total.labels(
                    operation_type=operation_type,
                    model=model,
                    status=status
                ).inc()
        
        return wrapper
    return decorator


def track_context_building(operation_type: str):
    """Decorator to track context building operations"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                if hasattr(result, '__await__'):
                    result = await result
                
                # Track context metrics if available
                if isinstance(result, tuple) and len(result) == 2:
                    entities, metrics = result
                    
                    if hasattr(metrics, 'entities_included'):
                        context_entities_total.labels(
                            operation_type=operation_type
                        ).observe(metrics.entities_included)
                    
                    if hasattr(metrics, 'assembly_time'):
                        context_build_duration.labels(
                            operation_type=operation_type
                        ).observe(metrics.assembly_time)
                
                return result
                
            finally:
                duration = time.time() - start_time
                context_build_duration.labels(
                    operation_type=operation_type
                ).observe(duration)
        
        return wrapper
    return decorator


def track_db_operation(db_type: str, operation: str):
    """Decorator to track database operations"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            status = "success"
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time
                db_operation_duration.labels(
                    db_type=db_type,
                    operation=operation
                ).observe(duration)
                
                db_operations_total.labels(
                    db_type=db_type,
                    operation=operation,
                    status=status
                ).inc()
        
        return wrapper
    return decorator


def update_world_metrics(players_count: int, entities_by_type: dict):
    """Update world state metrics"""
    active_players.set(players_count)
    
    for entity_type, count in entities_by_type.items():
        world_entities_total.labels(entity_type=entity_type).set(count)


def log_event_metric(event_type: str, actor_type: str):
    """Log event creation metric"""
    events_logged_total.labels(
        event_type=event_type,
        actor_type=actor_type
    ).inc()


def log_snapshot_metric(trigger_type: str):
    """Log world snapshot creation metric"""
    world_snapshots_total.labels(trigger_type=trigger_type).inc()
"""
Event Sourcing system for Game Master V3
Tracks all changes to the world state for consistency and rollback capability
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, cast
from uuid import UUID, uuid4

class UUIDEncoder(json.JSONEncoder):
    """JSON encoder that handles UUID and datetime objects"""
    def default(self, obj: Any) -> Any:
        if isinstance(obj, UUID):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

from sqlalchemy import DateTime, Float, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import Mapped, mapped_column

from config.settings import settings
from core.db import Base
from domain.entities import (
    ActionType, ActorType, BaseEntity, ChangeLogEntry, EntityType,
    WorldSnapshot
)

logger = logging.getLogger(__name__)

class EventLogModel(Base):
    """SQLAlchemy model for event log table"""
    __tablename__ = "event_log"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )
    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, index=True
    )
    action_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    actor_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, index=True
    )
    before_state: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    after_state: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    session_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    rollback_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )


class WorldSnapshotModel(Base):
    """SQLAlchemy model for world snapshots"""
    __tablename__ = "world_snapshots"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )
    snapshot_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    snapshot_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    # 'system', 'manual', 'scheduled'
    created_by: Mapped[str] = mapped_column(String(50), nullable=False)


class EventStore:
    """Event store for tracking all world changes"""
    
    def __init__(self) -> None:
        # Both are populated in connect(); calling other methods before
        # connect() has always failed at runtime, so the annotations reflect
        # the connected state.
        self.engine: AsyncEngine = None  # type: ignore[assignment]
        self.async_session: async_sessionmaker[AsyncSession] = None  # type: ignore[assignment]
    
    def _serialize_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize state for JSONB storage, handling UUIDs and other complex types, including UUID dict keys"""
        from enum import Enum
        from uuid import UUID
        from datetime import datetime

        def stringify(obj: Any) -> Any:
            # Ensure dict keys are strings and values are serializable
            if isinstance(obj, dict):
                new_dict: Dict[str, Any] = {}
                for k, v in obj.items():
                    if isinstance(k, Enum):
                        key = str(k.value)
                    else:
                        key = str(k)
                    new_dict[key] = stringify(v)
                return new_dict
            if isinstance(obj, list):
                return [stringify(v) for v in obj]
            if isinstance(obj, tuple):
                return [stringify(v) for v in obj]
            if isinstance(obj, UUID):
                return str(obj)
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj

        safe_state = stringify(state)
        return cast(Dict[str, Any], json.loads(json.dumps(safe_state, cls=UUIDEncoder)))
        
    async def connect(self) -> None:
        """Initialize connection to PostgreSQL"""
        try:
            # Create async engine
            self.engine = create_async_engine(
                settings.postgres_url.replace("postgresql://", "postgresql+asyncpg://"),
                echo=settings.app_debug,
                pool_size=20,
                max_overflow=30,
                pool_timeout=30,
                pool_recycle=1800,
            )
            
            # Create session factory
            self.async_session = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            
            # Importing the account models registers them on the shared
            # metadata, so create_all below builds those tables too. Done
            # here rather than at module level to keep the import acyclic.
            from core import accounts  # noqa: F401

            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("Connected to Event Store (PostgreSQL)")
            
        except Exception as e:
            logger.error(f"Failed to connect to Event Store: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close Event Store connection"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Disconnected from Event Store")
    
    async def log_change(
        self,
        event_id: UUID,
        entity_type: EntityType,
        entity_id: UUID,
        action_type: ActionType,
        actor_type: ActorType,
        actor_id: UUID,
        before_state: Dict[str, Any],
        after_state: Dict[str, Any],
        session_id: Optional[UUID] = None,
        confidence_score: float = 1.0,
        rollback_data: Optional[Dict[str, Any]] = None,
    ) -> ChangeLogEntry:
        """Log a change to the event store"""
        
        entry = ChangeLogEntry(
            event_id=event_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action_type=action_type,
            actor_type=actor_type,
            actor_id=actor_id,
            before_state=before_state,
            after_state=after_state,
            session_id=session_id,
            confidence_score=confidence_score,
            rollback_data=rollback_data,
        )
        
        # Store in database
        event_log = EventLogModel(
            id=entry.id,
            timestamp=entry.timestamp,
            event_id=entry.event_id,
            entity_type=entry.entity_type.value,
            entity_id=entry.entity_id,
            action_type=entry.action_type.value,
            actor_type=entry.actor_type.value,
            actor_id=entry.actor_id,
            before_state=self._serialize_state(entry.before_state),
            after_state=self._serialize_state(entry.after_state),
            session_id=entry.session_id,
            confidence_score=entry.confidence_score,
            rollback_data=self._serialize_state(entry.rollback_data) if entry.rollback_data else None,
        )
        
        async with self.async_session() as session:
            session.add(event_log)
            await session.commit()
        
        logger.debug(f"Logged change: {action_type.value} on {entity_type.value} {entity_id}")
        return entry
    
    async def get_entity_history(
        self,
        entity_id: UUID,
        limit: int = 100,
        since: Optional[datetime] = None,
    ) -> List[ChangeLogEntry]:
        """Get change history for specific entity"""
        
        async with self.async_session() as session:
            query = select(EventLogModel).where(EventLogModel.entity_id == entity_id)
            
            if since:
                query = query.where(EventLogModel.timestamp >= since)
            
            query = query.order_by(EventLogModel.timestamp.desc()).limit(limit)
            
            result = await session.execute(query)
            event_logs = result.scalars().all()
        
        # Convert to domain objects
        changes = []
        for log in event_logs:
            change = ChangeLogEntry(
                id=log.id,
                timestamp=log.timestamp,
                event_id=log.event_id,
                entity_type=EntityType(log.entity_type),
                entity_id=log.entity_id,
                action_type=ActionType(log.action_type),
                actor_type=ActorType(log.actor_type),
                actor_id=log.actor_id,
                before_state=log.before_state,
                after_state=log.after_state,
                session_id=log.session_id,
                confidence_score=log.confidence_score,
                rollback_data=log.rollback_data,
            )
            changes.append(change)
        
        return changes
    
    async def get_session_changes(
        self,
        session_id: UUID,
        limit: int = 1000,
    ) -> List[ChangeLogEntry]:
        """Get all changes for a specific session"""
        
        async with self.async_session() as session:
            query = select(EventLogModel).where(
                EventLogModel.session_id == session_id
            ).order_by(EventLogModel.timestamp.asc()).limit(limit)
            
            result = await session.execute(query)
            event_logs = result.scalars().all()
        
        changes = []
        for log in event_logs:
            change = ChangeLogEntry(
                id=log.id,
                timestamp=log.timestamp,
                event_id=log.event_id,
                entity_type=EntityType(log.entity_type),
                entity_id=log.entity_id,
                action_type=ActionType(log.action_type),
                actor_type=ActorType(log.actor_type),
                actor_id=log.actor_id,
                before_state=log.before_state,
                after_state=log.after_state,
                session_id=log.session_id,
                confidence_score=log.confidence_score,
                rollback_data=log.rollback_data,
            )
            changes.append(change)
        
        return changes
    
    async def get_recent_changes(
        self,
        limit: int = 100,
        entity_types: Optional[List[EntityType]] = None,
        actor_types: Optional[List[ActorType]] = None,
        since: Optional[datetime] = None,
    ) -> List[ChangeLogEntry]:
        """Get recent changes with optional filters"""
        
        async with self.async_session() as session:
            query = select(EventLogModel)
            
            if entity_types:
                entity_type_values = [t.value for t in entity_types]
                query = query.where(EventLogModel.entity_type.in_(entity_type_values))
            
            if actor_types:
                actor_type_values = [t.value for t in actor_types]
                query = query.where(EventLogModel.actor_type.in_(actor_type_values))
            
            if since:
                query = query.where(EventLogModel.timestamp >= since)
            
            query = query.order_by(EventLogModel.timestamp.desc()).limit(limit)
            
            result = await session.execute(query)
            event_logs = result.scalars().all()
        
        changes = []
        for log in event_logs:
            change = ChangeLogEntry(
                id=log.id,
                timestamp=log.timestamp,
                event_id=log.event_id,
                entity_type=EntityType(log.entity_type),
                entity_id=log.entity_id,
                action_type=ActionType(log.action_type),
                actor_type=ActorType(log.actor_type),
                actor_id=log.actor_id,
                before_state=log.before_state,
                after_state=log.after_state,
                session_id=log.session_id,
                confidence_score=log.confidence_score,
                rollback_data=log.rollback_data,
            )
            changes.append(change)
        
        return changes
    
    async def create_world_snapshot(
        self,
        snapshot_data: Dict[str, Any],
        created_by: str = "system",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UUID:
        """Create a snapshot of the world state"""
        
        snapshot = WorldSnapshotModel(
            snapshot_data=snapshot_data,
            snapshot_metadata=metadata or {},
            created_by=created_by,
        )
        
        async with self.async_session() as session:
            session.add(snapshot)
            await session.commit()
            snapshot_id = snapshot.id

        logger.info(f"Created world snapshot: {snapshot_id}")
        return snapshot_id
    
    async def get_world_snapshot(self, snapshot_id: UUID) -> Optional[Dict[str, Any]]:
        """Get world snapshot by ID"""
        
        async with self.async_session() as session:
            query = select(WorldSnapshotModel).where(WorldSnapshotModel.id == snapshot_id)
            result = await session.execute(query)
            snapshot = result.scalar_one_or_none()
        
        if snapshot:
            return {
                "id": snapshot.id,
                "timestamp": snapshot.timestamp,
                "data": snapshot.snapshot_data,
                "metadata": snapshot.snapshot_metadata,
                "created_by": snapshot.created_by,
            }
        return None
    
    async def get_latest_snapshot(self) -> Optional[Dict[str, Any]]:
        """Get the most recent world snapshot"""
        
        async with self.async_session() as session:
            query = select(WorldSnapshotModel).order_by(
                WorldSnapshotModel.timestamp.desc()
            ).limit(1)
            result = await session.execute(query)
            snapshot = result.scalar_one_or_none()
        
        if snapshot:
            return {
                "id": snapshot.id,
                "timestamp": snapshot.timestamp,
                "data": snapshot.snapshot_data,
                "metadata": snapshot.snapshot_metadata,
                "created_by": snapshot.created_by,
            }
        return None
    
    async def rollback_to_snapshot(self, snapshot_id: UUID) -> bool:
        """Mark rollback point (actual rollback handled by world service)"""
        # This method logs the rollback intention
        # Actual rollback logic is handled by WorldService
        
        rollback_event_id = uuid4()
        
        await self.log_change(
            event_id=rollback_event_id,
            entity_type=EntityType.EVENT,  # Special system event
            entity_id=snapshot_id,  # Using snapshot ID as entity ID
            action_type=ActionType.WORLD_CHANGE,
            actor_type=ActorType.SYSTEM,
            actor_id=snapshot_id,  # System actor
            before_state={"action": "rollback_initiated"},
            after_state={"rollback_to_snapshot": str(snapshot_id)},
            confidence_score=1.0,
        )
        
        logger.info(f"Rollback initiated to snapshot: {snapshot_id}")
        return True
    
    async def get_changes_since_snapshot(
        self,
        snapshot_timestamp: datetime,
        entity_types: Optional[List[EntityType]] = None,
    ) -> List[ChangeLogEntry]:
        """Get all changes since a specific snapshot timestamp"""
        
        async with self.async_session() as session:
            query = select(EventLogModel).where(
                EventLogModel.timestamp > snapshot_timestamp
            )
            
            if entity_types:
                entity_type_values = [t.value for t in entity_types]
                query = query.where(EventLogModel.entity_type.in_(entity_type_values))
            
            query = query.order_by(EventLogModel.timestamp.asc())
            
            result = await session.execute(query)
            event_logs = result.scalars().all()
        
        changes = []
        for log in event_logs:
            change = ChangeLogEntry(
                id=log.id,
                timestamp=log.timestamp,
                event_id=log.event_id,
                entity_type=EntityType(log.entity_type),
                entity_id=log.entity_id,
                action_type=ActionType(log.action_type),
                actor_type=ActorType(log.actor_type),
                actor_id=log.actor_id,
                before_state=log.before_state,
                after_state=log.after_state,
                session_id=log.session_id,
                confidence_score=log.confidence_score,
                rollback_data=log.rollback_data,
            )
            changes.append(change)
        
        return changes


# Global event store instance
event_store = EventStore()
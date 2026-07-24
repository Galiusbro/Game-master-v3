"""Unit tests for snapshot rollback via reverse event replay.

The world service mutates module-level singletons (graph_db, vector_db,
cache_service, event_store), so tests patch those module globals directly.
No live services required.
"""
from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

import core.world_service as ws_module
from core.world_service import WorldService
from domain.entities import ActionType, ActorType, ChangeLogEntry, EntityType


def make_change(
    entity_type=EntityType.LOCATION,
    before=None,
    after=None,
    rollback_data=None,
    confidence=1.0,
    entity_id=None,
):
    return ChangeLogEntry(
        event_id=uuid4(),
        entity_type=entity_type,
        entity_id=entity_id or uuid4(),
        action_type=ActionType.WORLD_CHANGE,
        actor_type=ActorType.SYSTEM,
        actor_id=uuid4(),
        before_state=before or {},
        after_state=after or {},
        confidence_score=confidence,
        rollback_data=rollback_data,
    )


def location_state(entity_id, name="Old Tavern"):
    return {
        "id": str(entity_id),
        "type": "location",
        "name": name,
        "description": "A cozy tavern",
    }


@pytest.fixture
def service(monkeypatch):
    svc = WorldService()

    stores = {
        "event_store": AsyncMock(),
        "graph_db": AsyncMock(),
        "vector_db": AsyncMock(),
        "cache_service": AsyncMock(),
    }
    for name, mock in stores.items():
        monkeypatch.setattr(ws_module, name, mock)

    stores["event_store"].get_world_snapshot.return_value = {
        "id": uuid4(),
        "timestamp": datetime(2026, 1, 1),
        "data": {"entities": {}},
        "metadata": {},
        "created_by": "test",
    }
    stores["event_store"].get_changes_since_snapshot.return_value = []
    return svc, stores


@pytest.mark.asyncio
async def test_missing_snapshot_raises(service):
    svc, stores = service
    stores["event_store"].get_world_snapshot.return_value = None
    with pytest.raises(ValueError, match="not found"):
        await svc.rollback_to_snapshot(uuid4())


@pytest.mark.asyncio
async def test_create_is_reverted_by_delete(service):
    svc, stores = service
    entity_id = uuid4()
    stores["event_store"].get_changes_since_snapshot.return_value = [
        make_change(after=location_state(entity_id), entity_id=entity_id),
    ]

    report = await svc.rollback_to_snapshot(uuid4())

    stores["graph_db"].delete_entity.assert_awaited_once_with(entity_id)
    stores["vector_db"].delete_entity.assert_awaited_once_with(entity_id)
    stores["cache_service"].invalidate_entity.assert_awaited_once()
    assert report["reverted_creates"] == 1
    assert report["errors"] == []


@pytest.mark.asyncio
async def test_update_restores_before_state(service):
    svc, stores = service
    entity_id = uuid4()
    before = location_state(entity_id, name="Old Tavern")
    after = location_state(entity_id, name="Renamed Tavern")
    stores["event_store"].get_changes_since_snapshot.return_value = [
        make_change(before=before, after=after, rollback_data=before, entity_id=entity_id),
    ]

    report = await svc.rollback_to_snapshot(uuid4())

    restored = stores["graph_db"].update_entity.await_args.args[0]
    assert restored.name == "Old Tavern"
    assert str(restored.id) == str(entity_id)
    stores["vector_db"].update_entity.assert_awaited_once()
    assert report["reverted_updates"] == 1


@pytest.mark.asyncio
async def test_delete_is_restored_by_recreate(service):
    svc, stores = service
    entity_id = uuid4()
    before = location_state(entity_id)
    stores["event_store"].get_changes_since_snapshot.return_value = [
        make_change(before=before, after={"deleted": True}, rollback_data=before, entity_id=entity_id),
    ]

    report = await svc.rollback_to_snapshot(uuid4())

    recreated = stores["graph_db"].create_entity.await_args.args[0]
    assert recreated.name == "Old Tavern"
    stores["vector_db"].store_entity.assert_awaited_once()
    assert report["restored_deletes"] == 1


@pytest.mark.asyncio
async def test_events_replayed_in_reverse_order(service):
    svc, stores = service
    entity_id = uuid4()
    v1 = location_state(entity_id, "V1")
    v2 = location_state(entity_id, "V2")
    # Chronological: create(v1), update(v1->v2)
    stores["event_store"].get_changes_since_snapshot.return_value = [
        make_change(after=v1, entity_id=entity_id),
        make_change(before=v1, after=v2, rollback_data=v1, entity_id=entity_id),
    ]

    call_order = []
    stores["graph_db"].update_entity.side_effect = lambda e: call_order.append("update") or e
    stores["graph_db"].delete_entity.side_effect = lambda eid: call_order.append("delete") or True

    report = await svc.rollback_to_snapshot(uuid4())

    # Reverse replay: undo the update first, then undo the create.
    assert call_order == ["update", "delete"]
    assert report["reverted_updates"] == 1
    assert report["reverted_creates"] == 1


@pytest.mark.asyncio
async def test_failed_and_system_events_are_skipped(service):
    svc, stores = service
    stores["event_store"].get_changes_since_snapshot.return_value = [
        make_change(after={"error": "boom"}),                     # failed attempt
        make_change(confidence=0.0, after=location_state(uuid4())),  # zero confidence
        make_change(entity_type=EntityType.EVENT, after={"x": 1}),   # system event
    ]

    report = await svc.rollback_to_snapshot(uuid4())

    assert report["skipped"] == 3
    stores["graph_db"].delete_entity.assert_not_awaited()
    stores["graph_db"].update_entity.assert_not_awaited()


@pytest.mark.asyncio
async def test_replay_continues_past_a_failing_event(service):
    svc, stores = service
    id_bad, id_good = uuid4(), uuid4()
    stores["event_store"].get_changes_since_snapshot.return_value = [
        make_change(after=location_state(id_good), entity_id=id_good),
        make_change(after=location_state(id_bad), entity_id=id_bad),
    ]
    # Reverse order: id_bad first (fails), id_good second (succeeds).
    stores["graph_db"].delete_entity.side_effect = [RuntimeError("neo4j down"), True]

    report = await svc.rollback_to_snapshot(uuid4())

    assert len(report["errors"]) == 1
    assert report["reverted_creates"] == 1
    assert stores["graph_db"].delete_entity.await_count == 2


@pytest.mark.asyncio
async def test_rollback_is_logged(service):
    svc, stores = service
    await svc.rollback_to_snapshot(uuid4())
    # Intent marker + completion record.
    stores["event_store"].rollback_to_snapshot.assert_awaited_once()
    stores["event_store"].log_change.assert_awaited_once()
    logged = stores["event_store"].log_change.await_args.kwargs
    assert logged["before_state"] == {"action": "rollback_completed"}

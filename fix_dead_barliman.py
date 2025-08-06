#!/usr/bin/env python3
"""
Принудительное создание мертвого Барлимана в векторной базе
для тестирования системы описания мертвых NPC
"""
import asyncio
from uuid import UUID
from datetime import datetime

# Установка пути для импортов
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from domain.entities import NPC, NPCPersonality, NPCState, EntityType
from infrastructure.vector_db import vector_db

async def create_dead_barliman():
    """Создать мертвого Барлимана в векторной базе"""
    
    print("🔧 Подключаемся к Vector DB...")
    await vector_db.connect()
    
    # Создаем мертвого Барлимана
    dead_barliman = NPC(
        id=UUID("76afb2a3-894b-4d64-b430-2eb3c2aff980"),
        name="Barliman Butterbur",
        description="The lifeless body of the former innkeeper lies motionless on the tavern floor. His cheerful smile is gone forever, replaced by the cold stillness of death.",
        is_alive=False,
        importance_level=3,
        personality=NPCPersonality(
            core_traits=["formerly friendly", "once observant", "now silent forever"],
            speech_patterns=[],
            likes=[],
            dislikes=[],
            fears=[],
            goals=[],
            backstory="Former adventurer who settled down to run this tavern after an injury ended his traveling days. Met a tragic and violent end at the hands of a stranger.",
            example_phrases=[]
        ),
        current_state=NPCState(
            current_mood="dead",
            current_activity="deceased",
            relationship_to_player={},
            recent_events=[],
            current_location_id=UUID("07b9cc05-b319-45d6-995e-8ed2d154996a")
        ),
        created_at=datetime.fromisoformat("2025-08-05T13:49:12.219675"),
        updated_at=datetime.utcnow()  # Новое время обновления
    )
    
    print(f"💀 Создаем мертвого {dead_barliman.name}...")
    print(f"   - Жив: {dead_barliman.is_alive}")
    print(f"   - Настроение: {dead_barliman.current_state.current_mood}")
    print(f"   - Активность: {dead_barliman.current_state.current_activity}")
    
    # Сохраняем в векторную базу (с перезаписью)
    await vector_db.store_entity(dead_barliman)
    
    print("✅ Мертвый Барлиман сохранен в Vector DB!")
    
    # Проверяем поиск
    print("\n🔍 Проверяем поиск...")
    results = await vector_db.search_entities(
        query="Barliman",
        entity_types=[EntityType.NPC],
        limit=1
    )
    
    if results:
        entity, score = results[0]
        print(f"   - Найден: {entity.name}")
        print(f"   - Жив: {getattr(entity, 'is_alive', 'unknown')}")
        print(f"   - Score: {score}")
        print(f"   - Описание: {entity.description[:100]}...")
    else:
        print("   - ❌ Не найден!")
    
    await vector_db.disconnect()
    print("\n🎉 ГОТОВО! Барлиман теперь официально мертв в Vector DB!")

if __name__ == "__main__":
    asyncio.run(create_dead_barliman())
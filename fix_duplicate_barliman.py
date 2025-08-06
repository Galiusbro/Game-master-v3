#!/usr/bin/env python3
"""
Исправляем дублирующихся Барлиманов в Vector DB
"""
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from infrastructure.vector_db import vector_db
from domain.entities import EntityType
from uuid import UUID

async def fix_duplicate_barliman():
    """Удалить старого живого Барлимана, оставить мертвого"""
    
    print("🔍 Подключаемся к Vector DB...")
    await vector_db.connect()
    
    # Ищем всех Барлиманов
    results = await vector_db.search_entities(
        query="Barliman",
        entity_types=[EntityType.NPC],
        limit=10
    )
    
    print(f"\n📊 Найдено {len(results)} Барлиманов:")
    
    dead_barliman_id = "76afb2a3-894b-4d64-b430-2eb3c2aff980"
    alive_barliman_id = "23682530-fe94-4251-ae2e-70f41edffd4d"
    
    for entity, score in results:
        print(f"   - ID: {entity.id}")
        print(f"     Имя: {entity.name}")
        print(f"     Score: {score}")
        print(f"     Описание: {entity.description[:60]}...")
        
        if str(entity.id) == alive_barliman_id:
            print(f"   ❌ УДАЛЯЕМ старого живого Барлимана!")
            await vector_db.delete_entity(UUID(alive_barliman_id))
            print(f"   ✅ Удален!")
        elif str(entity.id) == dead_barliman_id:
            print(f"   💀 Оставляем мертвого Барлимана")
        print()
    
    # Проверяем что осталось
    print("🔍 Проверяем результат...")
    final_results = await vector_db.search_entities(
        query="Barliman",
        entity_types=[EntityType.NPC],
        limit=10
    )
    
    print(f"📊 Теперь найдено {len(final_results)} Барлиманов:")
    for entity, score in final_results:
        print(f"   - ID: {entity.id}")
        print(f"     Имя: {entity.name}")
        print(f"     Score: {score}")
    
    await vector_db.disconnect()
    print("\n🎉 ГОТОВО! Теперь должен остаться только мертвый Барлиман!")

if __name__ == "__main__":
    asyncio.run(fix_duplicate_barliman())
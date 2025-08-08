#!/usr/bin/env python3
"""
ПОЛНАЯ ОЧИСТКА всех Барлиманов из Vector DB, кроме одного мертвого
"""
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from infrastructure.vector_db import vector_db
from domain.entities import EntityType
from uuid import UUID

async def clean_all_barliman():
    """Удалить ВСЕХ Барлиманов кроме мертвого"""
    
    print("🔍 Подключаемся к Vector DB...")
    await vector_db.connect()
    
    dead_barliman_id = "76afb2a3-894b-4d64-b430-2eb3c2aff980"
    
    # Ищем всех Барлиманов
    results = await vector_db.search_entities(
        query="Barliman",
        entity_types=[EntityType.NPC],
        limit=20  # Больше лимит
    )
    
    print(f"\n🧹 ЧИСТИМ {len(results)} Барлиманов:")
    
    deleted_count = 0
    
    for entity, score in results:
        if str(entity.id) != dead_barliman_id:
            print(f"   ❌ УДАЛЯЕМ: {entity.id} - {entity.description[:40]}...")
            try:
                await vector_db.delete_entity(entity.id)
                deleted_count += 1
                print(f"   ✅ Удален!")
            except Exception as e:
                print(f"   ❌ Ошибка удаления: {e}")
        else:
            print(f"   💀 ОСТАВЛЯЕМ мертвого: {entity.id}")
    
    print(f"\n📊 Удалено {deleted_count} дубликатов")
    
    # Финальная проверка
    print("\n🔍 ФИНАЛЬНАЯ ПРОВЕРКА:")
    final_results = await vector_db.search_entities(
        query="Barliman",
        entity_types=[EntityType.NPC],
        limit=20
    )
    
    print(f"📊 Осталось {len(final_results)} Барлиманов:")
    for entity, score in final_results:
        print(f"   - ID: {entity.id}")
        print(f"     Описание: {entity.description[:60]}...")
        print(f"     Score: {score}")
        # Use semantic entity state detection
        try:
            sys.path.append('src')
            from infrastructure.command_classification_service import command_classifier
            entity_state, state_conf = command_classifier.detect_entity_state(entity.description)
            if entity_state == "dead" and state_conf > 0.5:
                print(f"     💀 МЕРТВЫЙ! (семантика: {entity_state}, уверенность: {state_conf:.2f})")
            else:
                print(f"     😊 Живой (семантика: {entity_state}, уверенность: {state_conf:.2f})")
        except Exception as e:
            # Fallback to old method if semantic classification fails
            if "lifeless" in entity.description.lower() or "motionless" in entity.description.lower():
                print(f"     💀 МЕРТВЫЙ! (fallback)")
            else:
                print(f"     😊 Живой (fallback)")
        print()
    
    await vector_db.disconnect()
    
    if len(final_results) == 1:
        print("🎉 УСПЕХ! Остался только один Барлиман!")
    else:
        print(f"⚠️ Все еще {len(final_results)} Барлиманов...")

if __name__ == "__main__":
    asyncio.run(clean_all_barliman())
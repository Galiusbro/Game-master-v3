#!/usr/bin/env python3
"""
Прямая проверка Neo4j - что там с Барлиманом
"""
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from infrastructure.graph_db import graph_db
from uuid import UUID

async def debug_neo4j():
    """Прямая проверка Neo4j"""
    print("🔍 Подключаемся к Neo4j...")
    await graph_db.connect()
    
    barliman_id = UUID("76afb2a3-894b-4d64-b430-2eb3c2aff980")
    
    print(f"\n🎯 ПРЯМОЙ ЗАПРОС К NEO4J для {barliman_id}:")
    
    # Сырой Neo4j запрос
    query = """
    MATCH (e:Entity {id: $entity_id})
    RETURN e, labels(e) as labels
    """
    
    async with graph_db.session() as session:
        try:
            result = await session.run(query, entity_id=str(barliman_id))
            record = await result.single()
            
            if record:
                node = record["e"]
                labels = record["labels"] 
                print(f"✅ НАЙДЕН!")
                print(f"   Labels: {labels}")
                print(f"   Properties: {dict(node)}")
                
                # Тестируем _record_to_entity
                print(f"\n🔧 Тестируем _record_to_entity:")
                try:
                    entity = graph_db._record_to_entity(record)
                    if entity:
                        print(f"✅ УСПЕХ! Конвертирован в: {entity.__class__.__name__}")
                        print(f"   Имя: {entity.name}")
                        print(f"   Жив: {getattr(entity, 'is_alive', 'MISSING')}")
                        print(f"   Type: {entity.type}")
                    else:
                        print("❌ _record_to_entity вернул None!")
                except Exception as e:
                    print(f"❌ _record_to_entity упал: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("❌ НЕ НАЙДЕН в Neo4j!")
                
        except Exception as e:
            print(f"❌ Ошибка запроса: {e}")
    
    await graph_db.disconnect()

if __name__ == "__main__":
    asyncio.run(debug_neo4j())
#!/usr/bin/env python3
"""
Финальная версия тестового скрипта для демонстрации работы с relationship_to_player
"""

import asyncio
import json
import uuid
from uuid import UUID
import requests

BASE_URL = "http://localhost:8000/api/v1"

def make_request(endpoint, method="GET", data=None):
    """Выполнить HTTP запрос"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        elif method == "PUT":
            response = requests.put(url, json=data)
        elif method == "DELETE":
            response = requests.delete(url)
        else:
            raise ValueError(f"Неизвестный метод: {method}")
        
        if response.status_code == 200:
            return response.json(), response.status_code
        else:
            print(f"Ошибка {response.status_code}: {response.text}")
            return None, response.status_code
            
    except Exception as e:
        print(f"Ошибка запроса: {e}")
        return None, 500

async def test_relationship_system():
    """Тестируем систему отношений"""
    print("🔗 ТЕСТ СИСТЕМЫ ОТНОШЕНИЙ (ФИНАЛЬНАЯ ВЕРСИЯ)")
    print("=" * 60)
    
    # 1. Создаем тестового игрока
    print("\n👤 Создаем тестового игрока...")
    player_data = {
        "entity_data": {
            "name": "TestPlayer3",
            "description": "Тестовый игрок для проверки отношений",
            "stats": {
                "ability_scores": {"strength": 14, "dexterity": 12, "constitution": 13, "intelligence": 10, "wisdom": 11, "charisma": 15},
                "character_class": "fighter",
                "level": 1
            }
        },
        "entity_type": "player",
        "actor_id": str(uuid.uuid4()),
        "session_id": str(uuid.uuid4())
    }
    
    response, status = make_request("/entities", method="POST", data=player_data)
    if response:
        player_id = response['entity']['id']
        print(f"✅ Игрок создан: {response['entity']['name']} (ID: {player_id})")
    else:
        print(f"❌ Ошибка создания игрока: {status}")
        return
    
    # 2. Создаем тестового NPC
    print("\n🤖 Создаем тестового NPC...")
    npc_data = {
        "entity_data": {
            "name": "TestNPC3",
            "description": "Тестовый NPC для проверки отношений",
            "personality": {
                "core_traits": ["friendly", "helpful"],
                "speech_patterns": ["speaks warmly"],
                "likes": ["helping others"],
                "dislikes": ["rudeness"],
                "fears": ["conflict"],
                "goals": ["make friends"],
                "backstory": "A helpful NPC who wants to make friends",
                "example_phrases": ["Hello there!"]
            },
            "current_state": {
                "current_mood": "happy",
                "current_activity": "greeting visitors",
                "relationship_to_player": {},  # Пока пустой
                "recent_events": [],
                "current_location_id": None
            }
        },
        "entity_type": "npc",
        "actor_id": str(uuid.uuid4()),
        "session_id": str(uuid.uuid4())
    }
    
    response, status = make_request("/entities", method="POST", data=npc_data)
    if response:
        npc_id = response['entity']['id']
        print(f"✅ NPC создан: {response['entity']['name']} (ID: {npc_id})")
    else:
        print(f"❌ Ошибка создания NPC: {status}")
        return
    
    # 3. Создаем отношение между NPC и игроком
    print("\n🤝 Создаем отношение между NPC и игроком...")
    relationship_data = {
        "from_entity_id": npc_id,
        "to_entity_id": player_id,
        "relationship_type": "KNOWS",
        "properties": {
            "relationship": "friendly",
            "first_met": "today",
            "trust_level": 5,
            "last_interaction": "just now"
        },
        "actor_id": str(uuid.uuid4()),
        "session_id": str(uuid.uuid4())
    }
    
    response, status = make_request("/relationships", method="POST", data=relationship_data)
    if response:
        print(f"✅ Отношение создано: {response['message']}")
    else:
        print(f"❌ Ошибка создания отношения: {status}")
    
    # 4. Обновляем relationship_to_player в NPC (исправленная версия)
    print("\n📝 Обновляем relationship_to_player в NPC...")
    
    # Сначала получаем текущего NPC
    response, status = make_request(f"/entities/{npc_id}")
    if response:
        npc = response['entity']
        
        # Обновляем relationship_to_player (используем строковый ключ)
        npc['current_state']['relationship_to_player'][str(player_id)] = "friendly"
        
        # Отправляем обновление
        update_data = {
            "entity_data": npc,
            "actor_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4())
        }
        
        response, status = make_request(f"/entities/{npc_id}", method="PUT", data=update_data)
        if response:
            print(f"✅ NPC обновлен: relationship_to_player установлен")
            
            # Проверяем обновление
            updated_npc = response['entity']
            relationship = updated_npc['current_state']['relationship_to_player'].get(str(player_id))
            print(f"📊 Отношение к игроку: {relationship}")
            
            # Показываем полную структуру relationship_to_player
            print(f"📋 Все отношения NPC:")
            for player_uuid, rel_type in updated_npc['current_state']['relationship_to_player'].items():
                print(f"   - {player_uuid}: {rel_type}")
        else:
            print(f"❌ Ошибка обновления NPC: {status}")
    else:
        print(f"❌ Ошибка получения NPC: {status}")
    
    # 5. Создаем еще одно отношение - игрок знает NPC
    print("\n🔄 Создаем обратное отношение...")
    reverse_relationship_data = {
        "from_entity_id": player_id,
        "to_entity_id": npc_id,
        "relationship_type": "KNOWS",
        "properties": {
            "relationship": "friendly",
            "first_met": "today",
            "impression": "helpful and kind"
        },
        "actor_id": str(uuid.uuid4()),
        "session_id": str(uuid.uuid4())
    }
    
    response, status = make_request("/relationships", method="POST", data=reverse_relationship_data)
    if response:
        print(f"✅ Обратное отношение создано: {response['message']}")
    else:
        print(f"❌ Ошибка создания обратного отношения: {status}")
    
    # 6. Демонстрируем различные типы отношений
    print("\n🎭 Демонстрируем различные типы отношений...")
    
    relationship_types = [
        ("LOCATED_IN", "находится в"),
        ("OWNS", "владеет"),
        ("WORKS_FOR", "работает на"),
        ("FRIEND_OF", "друг"),
        ("ENEMY_OF", "враг"),
        ("TEACHES", "учит"),
        ("LEARNS_FROM", "учится у"),
        ("KNOWS", "знает"),
        ("TRUSTS", "доверяет"),
        ("FEARS", "боится"),
        ("RESPECTS", "уважает"),
        ("DESPISES", "презирает")
    ]
    
    for rel_type, description in relationship_types:
        print(f"   📋 {rel_type}: {description}")
    
    # 7. Показываем структуру relationship_to_player
    print("\n📊 СТРУКТУРА relationship_to_player:")
    print("=" * 40)
    print("relationship_to_player - это словарь в NPCState:")
    print("   Ключ: UUID игрока (строка)")
    print("   Значение: строка с типом отношения")
    print()
    print("Примеры значений:")
    print("   - 'friendly' - дружелюбное отношение")
    print("   - 'hostile' - враждебное отношение")
    print("   - 'neutral' - нейтральное отношение")
    print("   - 'trusted' - доверяет")
    print("   - 'feared' - боится")
    print("   - 'respected' - уважает")
    print()
    print("Использование в коде:")
    print("   npc.current_state.relationship_to_player[str(player_id)] = 'friendly'")
    print("   relationship = npc.current_state.relationship_to_player.get(str(player_id), 'neutral')")
    
    # 8. Показываем как это работает в системе
    print("\n🔧 КАК ЭТО РАБОТАЕТ В СИСТЕМЕ:")
    print("=" * 40)
    print("1. В коде NPCState.relationship_to_player: Dict[UUID, str]")
    print("2. При сериализации в JSON UUID автоматически конвертируется в строку")
    print("3. При десериализации из JSON строка остается строкой")
    print("4. В коде можно использовать как UUID, так и строку")
    print()
    print("Примеры использования:")
    print("   # В коде Python:")
    print("   npc.current_state.relationship_to_player[player_id] = 'friendly'")
    print("   # В JSON API:")
    print("   'relationship_to_player': {'player_uuid_string': 'friendly'}")
    
    print("\n✅ Тест системы отношений завершен!")

if __name__ == "__main__":
    asyncio.run(test_relationship_system()) 
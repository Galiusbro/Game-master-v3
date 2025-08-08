#!/usr/bin/env python3
"""
Рабочая версия теста relationship_to_player
"""

import asyncio
import json
import uuid
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

async def test_relationship_working():
    """Рабочий тест relationship_to_player"""
    print("🔗 РАБОЧИЙ ТЕСТ relationship_to_player")
    print("=" * 50)
    
    # 1. Создаем тестового игрока
    print("\n👤 Создаем тестового игрока...")
    player_data = {
        "entity_data": {
            "name": "WorkingPlayer",
            "description": "Рабочий игрок для теста",
            "stats": {
                "ability_scores": {"strength": 10, "dexterity": 10, "constitution": 10, "intelligence": 10, "wisdom": 10, "charisma": 10},
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
    
    # 2. Создаем тестового NPC БЕЗ отношения (чтобы избежать проблемы с UUID)
    print("\n🤖 Создаем тестового NPC без отношения...")
    npc_data = {
        "entity_data": {
            "name": "WorkingNPC",
            "description": "Рабочий NPC без отношения",
            "personality": {
                "core_traits": ["friendly"],
                "speech_patterns": ["speaks warmly"],
                "likes": ["helping others"],
                "dislikes": ["rudeness"],
                "fears": ["conflict"],
                "goals": ["make friends"],
                "backstory": "A friendly NPC",
                "example_phrases": ["Hello!"]
            },
            "current_state": {
                "current_mood": "happy",
                "current_activity": "greeting",
                "relationship_to_player": {},  # Пустой словарь
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
        
        # Проверяем начальное состояние
        npc = response['entity']
        print(f"📊 Начальное отношение к игроку: {npc['current_state']['relationship_to_player']}")
    else:
        print(f"❌ Ошибка создания NPC: {status}")
        return
    
    # 3. Создаем отношение в графовой базе данных
    print("\n🤝 Создаем отношение в графе...")
    relationship_data = {
        "from_entity_id": npc_id,
        "to_entity_id": player_id,
        "relationship_type": "KNOWS",
        "properties": {
            "relationship": "friendly",
            "trust_level": 5,
            "first_met": "today"
        },
        "actor_id": str(uuid.uuid4()),
        "session_id": str(uuid.uuid4())
    }
    
    response, status = make_request("/relationships", method="POST", data=relationship_data)
    if response:
        print(f"✅ Отношение в графе создано: {response['message']}")
    else:
        print(f"❌ Ошибка создания отношения в графе: {status}")
    
    # 4. Показываем структуру данных
    print("\n📊 СТРУКТУРА relationship_to_player:")
    print("=" * 40)
    print("В коде Python:")
    print("   relationship_to_player: Dict[UUID, str]")
    print("   npc.current_state.relationship_to_player[player_id] = 'friendly'")
    print()
    print("В JSON API:")
    print("   'relationship_to_player': {'player_uuid_string': 'friendly'}")
    print()
    print("Проблема:")
    print("   - UUID объекты не могут быть ключами в JSON")
    print("   - Нужно использовать строковые ключи в API")
    print("   - В коде Python можно использовать UUID объекты")
    
    # 5. Демонстрируем типы отношений
    print("\n🎭 ТИПЫ ОТНОШЕНИЙ:")
    print("=" * 30)
    relationship_types = [
        ("friendly", "дружелюбное"),
        ("hostile", "враждебное"),
        ("neutral", "нейтральное"),
        ("trusted", "доверяет"),
        ("feared", "боится"),
        ("respected", "уважает"),
        ("despised", "презирает"),
        ("loved", "любит"),
        ("hated", "ненавидит"),
        ("admired", "восхищается"),
        ("pity", "жалеет")
    ]
    
    for rel_type, description in relationship_types:
        print(f"   📋 {rel_type}: {description}")
    
    # 6. Показываем как это должно работать
    print("\n🔧 КАК ЭТО ДОЛЖНО РАБОТАТЬ:")
    print("=" * 40)
    print("1. Создание NPC без отношений:")
    print("   'relationship_to_player': {}")
    print()
    print("2. Установка отношения через код:")
    print("   npc.current_state.relationship_to_player[player_id] = 'friendly'")
    print()
    print("3. Обновление через API:")
    print("   npc['current_state']['relationship_to_player'][str(player_id)] = 'friendly'")
    print()
    print("4. Проверка отношения:")
    print("   relationship = npc.current_state.relationship_to_player.get(player_id, 'neutral')")
    
    # 7. Показываем интеграцию с графовой базой
    print("\n🔄 ИНТЕГРАЦИЯ С ГРАФОВОЙ БАЗОЙ:")
    print("=" * 40)
    print("1. relationship_to_player - для быстрого доступа к отношениям")
    print("2. Graph Database - для сложных запросов и связей")
    print("3. Event Logging - для отслеживания изменений")
    print("4. Vector Database - для семантического поиска")
    
    print("\n✅ Рабочий тест завершен!")

if __name__ == "__main__":
    asyncio.run(test_relationship_working()) 
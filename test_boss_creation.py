#!/usr/bin/env python3
"""
Тест создания NPC босса
"""

import json
import subprocess
import uuid

def make_request(endpoint, method="GET", data=None):
    """Делаем HTTP запрос"""
    base_url = "http://localhost:8000"
    
    if method == "GET":
        cmd = ["curl", "-s", f"{base_url}{endpoint}"]
    else:
        cmd = ["curl", "-s", "-X", method, "-H", "Content-Type: application/json", 
               "-d", json.dumps(data), f"{base_url}{endpoint}"]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"❌ Ошибка curl: {result.stderr}")
            return None, None
            
        try:
            response = json.loads(result.stdout)
            return response, 200
        except json.JSONDecodeError:
            print(f"⚠️ Не JSON ответ: {result.stdout}")
            return result.stdout, 200
            
    except subprocess.TimeoutExpired:
        print(f"⏰ Таймаут запроса к {endpoint}")
        return None, None
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return str(e), None

def test_boss_creation():
    """Тестируем создание босса"""
    print("👹 ТЕСТ СОЗДАНИЯ БОССА")
    print("=" * 50)
    
    # Создаём простого босса
    boss_data = {
        "entity_data": {
            "name": "Test Boss",
            "description": "A simple test boss",
            "personality": {
                "core_traits": ["aggressive", "proud"],
                "speech_patterns": ["speaks with authority"],
                "likes": ["combat", "power"],
                "dislikes": ["weakness", "cowards"],
                "fears": ["losing"],
                "goals": ["dominate"],
                "backstory": "A powerful warrior who seeks to test his strength",
                "example_phrases": ["You dare challenge me?"]
            },
            "current_state": {
                "current_mood": "confident",
                "current_activity": "waiting for challengers"
            },
            "importance_level": 8
        },
        "entity_type": "npc",
        "actor_id": str(uuid.uuid4()),
        "session_id": str(uuid.uuid4())
    }
    
    print(f"📤 Отправляем данные:")
    print(f"   Имя: {boss_data['entity_data']['name']}")
    print(f"   Тип: {boss_data['entity_type']}")
    print(f"   Описание: {boss_data['entity_data']['description']}")
    print(f"   Важность: {boss_data['entity_data']['importance_level']}")
    print(f"   Настроение: {boss_data['entity_data']['current_state']['current_mood']}")
    
    response, status = make_request("/api/v1/entities", "POST", boss_data)
    
    print(f"\n📥 Ответ:")
    print(f"   Статус: {status}")
    
    if response:
        print(f"   Тип ответа: {type(response)}")
        if isinstance(response, dict):
            print(f"   Ключи: {list(response.keys())}")
            print(f"   Полный ответ: {json.dumps(response, indent=2)}")
        else:
            print(f"   Содержимое: {response}")
    else:
        print(f"   ❌ Нет ответа")
    
    return response, status

def test_entity_endpoints(boss_id=None):
    """Тестируем различные эндпоинты для сущностей"""
    print("\n🔍 ТЕСТ ЭНДПОИНТОВ СУЩНОСТЕЙ")
    print("=" * 50)
    
    # Тест GET /entities
    print("📋 Получаем список сущностей...")
    response, status = make_request("/api/v1/entities")
    print(f"   Статус: {status}")
    if response:
        if isinstance(response, list):
            print(f"   Найдено сущностей: {len(response)}")
            if response:
                print(f"   Типы сущностей:")
                entity_types = {}
                for entity in response:
                    entity_type = entity.get('entity_type', 'unknown')
                    entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
                for entity_type, count in entity_types.items():
                    print(f"     - {entity_type}: {count}")
        else:
            print(f"   Неожиданный формат ответа: {type(response)}")
            print(f"   Ответ: {response}")
    else:
        print(f"   ❌ Нет ответа")
    
    # Тест GET /entities/{id} с реальным ID
    if boss_id:
        print(f"\n🔍 Проверяем созданного босса (ID: {boss_id})...")
        response, status = make_request(f"/api/v1/entities/{boss_id}")
        print(f"   Статус: {status}")
        if response:
            print(f"   Найден босс: {response.get('entity', {}).get('name', 'Unknown')}")
            print(f"   Описание: {response.get('entity', {}).get('description', 'No description')}")
        else:
            print(f"   ❌ Босс не найден")
    
    # Тест GET /entities/{id} с несуществующим ID
    print(f"\n🔍 Проверяем несуществующую сущность...")
    test_id = str(uuid.uuid4())
    response, status = make_request(f"/api/v1/entities/{test_id}")
    print(f"   Статус: {status}")
    if response:
        print(f"   Ответ: {response}")

if __name__ == "__main__":
    print("🎯 ТЕСТ СОЗДАНИЯ NPC")
    print("=" * 60)
    
    # Тест создания босса
    boss_response, boss_status = test_boss_creation()
    
    # Извлекаем ID созданного босса
    boss_id = None
    if boss_response and isinstance(boss_response, dict):
        boss_id = boss_response.get('entity', {}).get('id')
    
    # Тест эндпоинтов
    test_entity_endpoints(boss_id)
    
    print("\n✅ Тест завершён!") 
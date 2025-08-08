#!/usr/bin/env python3
"""
Тест разрешения NPC по описательным словам
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

async def test_npc_resolution():
    """Тест разрешения NPC"""
    print("🔍 ТЕСТ РАЗРЕШЕНИЯ NPC")
    print("=" * 40)
    
    # Получаем список NPC
    print("\n📋 Получаем список NPC...")
    response, status = make_request("/entities")
    if response:
        npcs = [entity for entity in response if entity['entity_type'] == 'npc']
        print(f"✅ Найдено NPC: {len(npcs)}")
        for npc in npcs[:5]:  # Показываем первые 5
            print(f"   - {npc['entity']['name']} (ID: {npc['entity']['id']})")
    else:
        print(f"❌ Ошибка получения NPC: {status}")
        return
    
    # Тестируем различные команды
    test_commands = [
        {
            "command": "говорю с Barliman: привет!",
            "description": "Точное имя NPC",
            "expected": "Должен найти NPC"
        },
        {
            "command": "говорю с барменом: привет!",
            "description": "Описательное слово 'бармен'",
            "expected": "Должен связать с Barliman"
        },
        {
            "command": "говорю с трактирщиком: как дела?",
            "description": "Описательное слово 'трактирщик'",
            "expected": "Должен связать с Barliman"
        },
        {
            "command": "говорю с хозяином таверны: расскажи новости",
            "description": "Описательная фраза",
            "expected": "Должен связать с Barliman"
        }
    ]
    
    player_id = "317a99dc-1c26-412e-a23d-1a2ee3ba25fa"  # Используем существующего игрока
    
    for i, test in enumerate(test_commands, 1):
        print(f"\n🔄 Тест {i}: {test['description']}")
        print(f"📝 Команда: '{test['command']}'")
        print(f"🎯 Ожидание: {test['expected']}")
        
        game_request = {
            "world_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "player_id": player_id,
            "command": test['command']
        }
        
        response, status = make_request("/game/command", method="POST", data=game_request)
        if response:
            print(f"✅ Успех: {response['success']}")
            print(f"🤖 Ответ: {response['content'][:100]}...")
            print(f"📊 Тип действия: {response['action_type']}")
            print(f"🎯 Уверенность: {response['confidence']:.2f}")
            
            if 'resolved_entities' in response:
                npc_id = response['resolved_entities'].get('npc_id')
                if npc_id:
                    print(f"🎯 NPC найден: {npc_id}")
                else:
                    print(f"❌ NPC не найден")
            else:
                print(f"❌ Нет информации о разрешенных сущностях")
        else:
            print(f"❌ Ошибка: {status}")
    
    # Анализ проблемы
    print("\n🔧 АНАЛИЗ ПРОБЛЕМЫ")
    print("=" * 30)
    
    print("1. Семантический парсер не связывает описательные слова с именами NPC")
    print("2. Нужно улучшить классификацию сущностей")
    print("3. Нужно добавить поиск по описанию/роли NPC")
    print("4. relationship_to_player не влияет на ответ (пока)")
    
    # Предложения по улучшению
    print("\n💡 ПРЕДЛОЖЕНИЯ ПО УЛУЧШЕНИЮ")
    print("=" * 40)
    
    improvements = [
        "1. Добавить синонимы для NPC в метаданные",
        "2. Улучшить классификацию entity_type для описательных слов",
        "3. Добавить поиск NPC по роли/профессии",
        "4. Интегрировать relationship_to_player в AI ответы",
        "5. Добавить fallback поиск по векторной базе"
    ]
    
    for improvement in improvements:
        print(f"   {improvement}")
    
    print("\n✅ Тест завершен!")

if __name__ == "__main__":
    asyncio.run(test_npc_resolution()) 
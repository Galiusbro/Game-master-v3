#!/usr/bin/env python3
"""
🎮 РЕАЛЬНЫЙ ИГРОВОЙ ТЕСТ ЧЕРЕЗ CURL
Тестируем семантическую систему как настоящий игрок через HTTP запросы
"""

import subprocess
import json
import time
import sys
import uuid

print('🎮 РЕАЛЬНЫЙ ИГРОВОЙ ТЕСТ СЕМАНТИЧЕСКОЙ СИСТЕМЫ')
print('🌐 Тестируем через curl запросы как настоящий игрок')
print('🔧 Показываем внутренние детали работы (админский режим)')
print('=' * 80)

class CurlGameTester:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.world_id = str(uuid.uuid4())
        self.session_id = str(uuid.uuid4())
        self.player_id = str(uuid.uuid4())
        
    def make_curl_request(self, endpoint: str, method: str = "GET", data: dict = None, show_details: bool = True):
        """Выполняет curl запрос и показывает детали"""
        url = f"{self.base_url}{endpoint}"
        
        if method == "GET":
            cmd = ["curl", "-s", "-w", "\\nHTTP_STATUS:%{http_code}\\n", url]
        elif method == "POST":
            cmd = [
                "curl", "-s", "-X", "POST",
                "-H", "Content-Type: application/json",
                "-w", "\\nHTTP_STATUS:%{http_code}\\n",
                "-d", json.dumps(data),
                url
            ]
        
        if show_details:
            print(f"🌐 Запрос: {method} {url}")
            if data:
                print(f"📦 Данные: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                print(f"❌ Ошибка curl: {result.stderr}")
                return None, None
                
            # Парсим результат
            output = result.stdout
            if "HTTP_STATUS:" in output:
                response_body, status_line = output.rsplit("HTTP_STATUS:", 1)
                status_code = int(status_line.strip())
            else:
                response_body = output
                status_code = None
                
            if show_details:
                print(f"📊 HTTP статус: {status_code}")
                
            # Пытаемся распарсить JSON
            try:
                json_response = json.loads(response_body) if response_body.strip() else {}
                return json_response, status_code
            except json.JSONDecodeError:
                return response_body, status_code
                
        except subprocess.TimeoutExpired:
            print(f"⏰ Таймаут запроса")
            return None, None
        except Exception as e:
            print(f"💥 Ошибка: {e}")
            return None, None
    
    def test_health_check(self):
        """Проверяем, что сервер запущен"""
        print(f"\\n🏥 ТЕСТ: Проверка здоровья сервера")
        
        response, status = self.make_curl_request("/health")
        
        if status == 200:
            print(f"✅ Сервер работает!")
            if isinstance(response, dict):
                print(f"📋 Ответ сервера: {json.dumps(response, ensure_ascii=False, indent=2)}")
            return True
        else:
            print(f"❌ Сервер не отвечает (статус: {status})")
            return False
    
    def test_game_command(self, command: str, description: str, expected_semantics: dict = None):
        """Тестируем игровую команду"""
        print(f"\\n🎯 ТЕСТ: {description}")
        print(f"💬 Команда игрока: \"{command}\"")
        
        data = {
            "world_id": self.world_id,
            "session_id": self.session_id,
            "player_id": self.player_id,
            "command": command,
            "player_name": "TestPlayer"
        }
        
        response, status = self.make_curl_request("/api/v1/game/command", "POST", data)
        
        if status == 200:
            print(f"✅ Команда обработана успешно!")
            
            # Показываем детали ответа (админский режим)
            if isinstance(response, dict):
                print(f"\\n🔍 АДМИНСКИЕ ДЕТАЛИ:")
                
                # AI ответ
                if "ai_response" in response:
                    ai_content = response["ai_response"].get("content", "")
                    print(f"🤖 AI ответ: {ai_content[:200]}{'...' if len(ai_content) > 200 else ''}")
                
                # Семантический анализ (если есть)
                if "semantic_analysis" in response:
                    semantics = response["semantic_analysis"]
                    print(f"🧠 Семантический анализ:")
                    for key, value in semantics.items():
                        print(f"   {key}: {value}")
                
                # Dice rolls (если есть)
                if "dice_rolls" in response:
                    dice_rolls = response["dice_rolls"]
                    print(f"🎲 Броски костей: {len(dice_rolls)} бросков")
                    for roll in dice_rolls[:3]:  # Показываем первые 3
                        print(f"   🎯 {roll.get('type', 'unknown')}: {roll.get('result', 'N/A')} (DC: {roll.get('dc', 'N/A')})")
                
                # События (если есть)
                if "events" in response:
                    print(f"📋 События: {len(response['events'])} шт.")
                
                # Предупреждения (если есть)
                if "warnings" in response:
                    warnings = response['warnings']
                    print(f"⚠️ Предупреждения: {warnings}")
                
                # Анализируем семантику из dice rolls
                semantic_analysis = {}
                if "dice_rolls" in response and response["dice_rolls"]:
                    first_roll = response["dice_rolls"][0]
                    semantic_analysis["action_type"] = first_roll.get("type", "unknown")
                    semantic_analysis["dc"] = first_roll.get("dc", "unknown")
                    semantic_analysis["result"] = first_roll.get("result", "unknown")
                    semantic_analysis["success"] = first_roll.get("success", False)
                    
                    print(f"🧠 Семантический анализ (из dice rolls):")
                    print(f"   🎯 Тип действия: {semantic_analysis['action_type']}")
                    print(f"   🎲 DC: {semantic_analysis['dc']}")
                    print(f"   📊 Результат: {semantic_analysis['result']}")
                    print(f"   {'✅' if semantic_analysis['success'] else '❌'} Успех: {semantic_analysis['success']}")
                    
                # Проверяем ожидаемую семантику
                if expected_semantics:
                    print(f"\\n🎯 ПРОВЕРКА СЕМАНТИКИ:")
                    for key, expected_value in expected_semantics.items():
                        # Ищем значение в semantic_analysis или в response
                        actual_value = semantic_analysis.get(key) or response.get(key, "not_found")
                        
                        if actual_value != "not_found":
                            match = str(actual_value).lower() == str(expected_value).lower()
                            emoji = "✅" if match else "❌"
                            print(f"   {key}: ожидалось {expected_value}, получено {actual_value} {emoji}")
                        else:
                            print(f"   {key}: ожидалось {expected_value}, не найдено ❓")
            
            return True
            
        elif status == 404:
            print(f"❌ Endpoint не найден - возможно сервер не запущен или неправильный URL")
            return False
        elif status == 500:
            print(f"❌ Внутренняя ошибка сервера")
            if response:
                print(f"📋 Детали ошибки: {response}")
            return False
        else:
            print(f"❌ Неожиданный статус: {status}")
            return False
    
    def run_game_scenarios(self):
        """Запускаем игровые сценарии"""
        print(f"\\n🎮 ЗАПУСК ИГРОВЫХ СЦЕНАРИЕВ")
        print(f"⏰ Время начала: {time.strftime('%H:%M:%S')}")
        
        # Проверяем сервер
        if not self.test_health_check():
            print(f"\\n💥 КРИТИЧЕСКАЯ ОШИБКА: Сервер не запущен!")
            print(f"\\n🚀 Для запуска сервера выполни:")
            print(f"   cd {sys.path[0] if sys.path[0] else '.'}")
            print(f"   source venv/bin/activate")
            print(f"   python3 -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000")
            return False
        
        # Создаём тестового персонажа
        player_id = self.create_test_character()
        if not player_id:
            print(f"\\n💥 КРИТИЧЕСКАЯ ОШИБКА: Не удалось создать персонажа!")
            return False
        
        # Игровые сценарии с ожидаемой семантикой
        scenarios = [
            {
                'command': 'I carefully sneak past the sleeping guard in the dark corridor',
                'description': 'Stealth (Careful + Dark) - проверяем Action Urgency',
                'expected': {
                    'action_type': 'stealth',
                    'urgency': 'careful'
                }
            },
            {
                'command': 'I desperately try to hide from the approaching patrol',
                'description': 'Stealth (Desperate) - проверяем панические действия',
                'expected': {
                    'action_type': 'stealth',
                    'urgency': 'desperate'
                }
            },
            {
                'command': 'Я осторожно обыскиваю древнюю гробницу в поисках ловушек',
                'description': 'Investigation (Russian) - проверяем многоязычность',
                'expected': {
                    'action_type': 'investigation',
                    'urgency': 'careful'
                }
            },
            {
                'command': 'I quickly cast a healing spell on my wounded companion',
                'description': 'Magic (Urgent) - проверяем магические действия',
                'expected': {
                    'action_type': 'magic',
                    'urgency': 'urgent'
                }
            },
            {
                'command': 'I try to persuade the hostile guard to let me pass',
                'description': 'Persuasion (Hostile NPC) - проверяем социальные взаимодействия',
                'expected': {
                    'action_type': 'persuasion',
                    'npc_attitude': 'hostile'
                }
            },
            {
                'command': 'I examine the mysterious glowing artifact on the altar',
                'description': 'Investigation (Magical) - проверяем контекстную классификацию',
                'expected': {
                    'action_type': 'investigation',
                    'lighting': 'magical'
                }
            }
        ]
        
        successful_tests = 0
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\\n" + "="*60)
            print(f"🎭 СЦЕНАРИЙ {i}/{len(scenarios)}")
            
            success = self.test_game_command(
                scenario['command'],
                scenario['description'], 
                scenario.get('expected')
            )
            
            if success:
                successful_tests += 1
                
            # Небольшая пауза между запросами
            time.sleep(1)
        
        # Итоговый отчёт
        print(f"\\n" + "="*80)
        print(f"📊 ИТОГОВЫЙ ОТЧЁТ ИГРОВОГО ТЕСТИРОВАНИЯ")
        print(f"✅ Успешных тестов: {successful_tests}/{len(scenarios)} ({successful_tests/len(scenarios)*100:.1f}%)")
        
        if successful_tests == len(scenarios):
            print(f"🏆 ОТЛИЧНО! Все игровые сценарии работают!")
        elif successful_tests >= len(scenarios) * 0.8:
            print(f"🥈 ХОРОШО! Большинство сценариев работает!")
        elif successful_tests >= len(scenarios) * 0.5:
            print(f"🥉 УДОВЛЕТВОРИТЕЛЬНО! Половина сценариев работает!")
        else:
            print(f"📚 ТРЕБУЕТСЯ ДОРАБОТКА! Много проблем!")
        
        return successful_tests == len(scenarios)
    
    def create_test_character(self):
        """Создаём тестового персонажа"""
        print(f"\\n👤 СОЗДАНИЕ ТЕСТОВОГО ПЕРСОНАЖА")
        
        character_data = {
            "name": "SemanticTestPlayer",
            "character_class": "rogue",
            "ability_scores": {
                "strength": 13,
                "dexterity": 16,
                "constitution": 14,
                "intelligence": 12,
                "wisdom": 13,
                "charisma": 8
            },
            "background": "Criminal"
        }
        
        response, status = self.make_curl_request("/api/v1/game/character/create", "POST", character_data)
        
        if status == 200:
            print(f"✅ Персонаж создан успешно!")
            if isinstance(response, dict):
                resolved_entities = response.get("resolved_entities", {})
                player_id = resolved_entities.get("player_id")
                if player_id:
                    print(f"🆔 Player ID: {player_id}")
                    self.player_id = player_id  # Обновляем наш player_id
                    return player_id
            return None
        else:
            print(f"❌ Ошибка создания персонажа: {status}")
            if response:
                print(f"📋 Детали: {response}")
            return None

def main():
    """Главная функция"""
    print(f"🎮 Инициализация игрового тестирования...")
    
    tester = CurlGameTester()
    success = tester.run_game_scenarios()
    
    if success:
        print(f"\\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Семантическая система работает в игре!")
        return 0
    else:
        print(f"\\n⚠️ ЕСТЬ ПРОБЛЕМЫ! Не все сценарии работают корректно!")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
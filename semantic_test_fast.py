#!/usr/bin/env python3
"""
🚀 БЫСТРЫЙ ТЕСТ СЕМАНТИЧЕСКОЙ СИСТЕМЫ
Проверяем только семантическую классификацию без AI запросов
"""

import json
import subprocess
import sys
import time
import uuid

class FastSemanticTester:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.world_id = str(uuid.uuid4())
        self.session_id = str(uuid.uuid4())
        self.player_id = None
        
    def make_curl_request(self, endpoint, method="GET", data=None):
        """Делаем curl запрос"""
        if method == "GET":
            cmd = ["curl", "-s", f"{self.base_url}{endpoint}"]
        else:
            cmd = ["curl", "-s", "-X", method, "-H", "Content-Type: application/json", 
                   "-d", json.dumps(data), f"{self.base_url}{endpoint}"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                return None, None
                
            try:
                response = json.loads(result.stdout)
                return response, 200
            except json.JSONDecodeError:
                return result.stdout, 200
                
        except subprocess.TimeoutExpired:
            return None, None
        except Exception as e:
            return str(e), None

    def test_health_check(self):
        """Проверяем здоровье сервера"""
        print(f"\n🏥 ТЕСТ: Проверка здоровья сервера")
        response, status = self.make_curl_request("/health")
        
        if status == 200:
            print(f"✅ Сервер работает!")
            return True
        else:
            print(f"❌ Сервер недоступен!")
            return False

    def create_test_character(self):
        """Создаём тестового персонажа"""
        print(f"\n👤 СОЗДАНИЕ ТЕСТОВОГО ПЕРСОНАЖА")
        
        character_data = {
            "name": "FastTestPlayer",
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
                    self.player_id = player_id
                    return player_id
            return None
        else:
            print(f"❌ Ошибка создания персонажа: {status}")
            return None

    def test_semantic_command(self, command: str, description: str, expected_action: str):
        """Тестируем семантическую команду с отключенным AI"""
        print(f"\n🎯 ТЕСТ: {description}")
        print(f"💬 Команда: \"{command}\"")
        
        data = {
            "world_id": self.world_id,
            "session_id": self.session_id,
            "player_id": self.player_id,
            "command": command,
            "player_name": "FastTestPlayer",
            "disable_ai": True  # Отключаем AI для быстрого теста
        }
        
        start_time = time.time()
        response, status = self.make_curl_request("/api/v1/game/command", "POST", data)
        end_time = time.time()
        
        print(f"⏱️ Время обработки: {(end_time - start_time):.2f}с")
        
        if status == 200:
            print(f"✅ Команда обработана успешно!")
            
            if isinstance(response, dict):
                # Анализируем семантику из dice rolls
                if "dice_rolls" in response and response["dice_rolls"]:
                    first_roll = response["dice_rolls"][0]
                    detected_action = first_roll.get("type", "unknown")
                    dc = first_roll.get("dc", "unknown")
                    result = first_roll.get("result", "unknown")
                    success = first_roll.get("success", False)
                    
                    print(f"🧠 Семантический анализ:")
                    print(f"   🎯 Обнаруженное действие: {detected_action}")
                    print(f"   🎲 DC: {dc}")
                    print(f"   📊 Результат броска: {result}")
                    print(f"   {'✅' if success else '❌'} Успех: {success}")
                    
                    # Проверяем ожидаемое действие
                    if detected_action.lower() == expected_action.lower():
                        print(f"✅ Семантика КОРРЕКТНА! Ожидали {expected_action}, получили {detected_action}")
                        return True
                    else:
                        print(f"❌ Семантика НЕКОРРЕКТНА! Ожидали {expected_action}, получили {detected_action}")
                        return False
                else:
                    print(f"⚠️ Нет данных о бросках костей")
                    return False
            else:
                print(f"⚠️ Неожиданный формат ответа")
                return False
                
        else:
            print(f"❌ Ошибка: HTTP {status}")
            return False

    def run_fast_semantic_tests(self):
        """Запускаем быстрые семантические тесты"""
        print(f"🚀 БЫСТРЫЕ СЕМАНТИЧЕСКИЕ ТЕСТЫ")
        print(f"⏰ Время начала: {time.strftime('%H:%M:%S')}")
        
        # Проверяем сервер
        if not self.test_health_check():
            return False
        
        # Создаём персонажа
        if not self.create_test_character():
            return False
        
        # Семантические тесты
        test_scenarios = [
            {
                'command': 'I carefully sneak past the guard',
                'description': 'Stealth Action Test',
                'expected_action': 'stealth'
            },
            {
                'command': 'I examine the mysterious artifact',
                'description': 'Investigation Action Test', 
                'expected_action': 'investigation'
            },
            {
                'command': 'I try to persuade the merchant',
                'description': 'Persuasion Action Test',
                'expected_action': 'persuasion'
            },
            {
                'command': 'I cast a healing spell',
                'description': 'Magic Action Test',
                'expected_action': 'magic'
            },
            {
                'command': 'I attack the orc with my sword',
                'description': 'Combat Action Test',
                'expected_action': 'combat'
            }
        ]
        
        successful_tests = 0
        total_tests = len(test_scenarios)
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n{'='*60}")
            print(f"🎭 СЦЕНАРИЙ {i}/{total_tests}")
            
            success = self.test_semantic_command(
                scenario['command'],
                scenario['description'],
                scenario['expected_action']
            )
            
            if success:
                successful_tests += 1
        
        # Итоговый отчёт
        print(f"\n{'='*80}")
        print(f"📊 ИТОГОВЫЙ ОТЧЁТ СЕМАНТИЧЕСКОГО ТЕСТИРОВАНИЯ")
        success_rate = (successful_tests / total_tests) * 100
        print(f"✅ Успешных тестов: {successful_tests}/{total_tests} ({success_rate:.1f}%)")
        
        if success_rate >= 80:
            print(f"🏆 ОТЛИЧНО! Семантическая система работает превосходно!")
        elif success_rate >= 60:
            print(f"🥉 ХОРОШО! Семантическая система работает неплохо!")
        else:
            print(f"📚 ТРЕБУЕТСЯ ДОРАБОТКА! Много ошибок в семантике!")
        
        return success_rate >= 80

def main():
    """Главная функция"""
    print(f"🎮 БЫСТРОЕ ТЕСТИРОВАНИЕ СЕМАНТИЧЕСКОЙ СИСТЕМЫ")
    print(f"🌐 Проверяем только семантику без AI запросов")
    print(f"🔧 Показываем детали классификации")
    print(f"="*80)
    
    tester = FastSemanticTester()
    
    try:
        success = tester.run_fast_semantic_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print(f"\n🛑 Тест прерван пользователем")
        return 2
    except Exception as e:
        print(f"\n💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")
        return 3

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
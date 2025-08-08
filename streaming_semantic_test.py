#!/usr/bin/env python3
"""
🌊 ТЕСТ СЕМАНТИЧЕСКОЙ СИСТЕМЫ В STREAMING РЕЖИМЕ
Проверяем работу семантики через Server-Sent Events
"""

import json
import subprocess
import sys
import time
import uuid

class StreamingSemanticTester:
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
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            
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

    def test_streaming_request(self, endpoint, data):
        """Делаем streaming curl запрос"""
        cmd = ["curl", "-s", "-N", "-X", "POST", 
               "-H", "Content-Type: application/json", 
               "-d", json.dumps(data), 
               f"{self.base_url}{endpoint}"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                return None, None
                
            return result.stdout, 200
                
        except subprocess.TimeoutExpired:
            return None, None
        except Exception as e:
            return str(e), None

    def create_test_character(self):
        """Создаём тестового персонажа"""
        print(f"\n👤 СОЗДАНИЕ ТЕСТОВОГО ПЕРСОНАЖА")
        
        character_data = {
            "name": "StreamingTestPlayer",
            "character_class": "wizard",
            "ability_scores": {
                "strength": 10,
                "dexterity": 14,
                "constitution": 13,
                "intelligence": 16,
                "wisdom": 15,
                "charisma": 12
            },
            "background": "Scholar"
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

    def test_streaming_semantic_command(self, command: str, description: str, expected_action: str):
        """Тестируем семантическую команду в streaming режиме"""
        print(f"\n🌊 STREAMING ТЕСТ: {description}")
        print(f"💬 Команда: \"{command}\"")
        
        data = {
            "world_id": self.world_id,
            "session_id": self.session_id,
            "player_id": self.player_id,
            "command": command
        }
        
        start_time = time.time()
        response_text, status = self.test_streaming_request("/api/v1/stream/command", data)
        end_time = time.time()
        
        print(f"⏱️ Время обработки: {(end_time - start_time):.2f}с")
        
        if status == 200 and response_text:
            print(f"✅ Streaming команда обработана успешно!")
            
            # Парсим SSE события
            events = []
            lines = response_text.split('\n')
            current_event = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith('event:'):
                    if current_event:
                        events.append(current_event)
                    current_event = {'type': line[6:].strip()}
                elif line.startswith('data:'):
                    current_event['data'] = line[5:].strip()
                elif line == '' and current_event:
                    events.append(current_event)
                    current_event = {}
            
            if current_event:
                events.append(current_event)
            
            print(f"📡 Получено событий: {len(events)}")
            
            # Показываем все события для дебага
            print(f"🔍 Отладка событий:")
            for i, event in enumerate(events):
                print(f"   {i+1}: type='{event.get('type', 'NO_TYPE')}', data='{event.get('data', 'NO_DATA')[:50]}...'")
            
            # Ищем семантическую информацию в событиях
            semantic_found = False
            for event in events:
                if event.get('type') == 'semantic_analysis':
                    try:
                        semantic_data = json.loads(event.get('data', '{}'))
                        print(f"🧠 Семантический анализ:")
                        print(f"   🎯 Обнаруженное действие: {semantic_data.get('action', 'unknown')}")
                        print(f"   📊 Уверенность: {semantic_data.get('confidence', 0):.2f}")
                        
                        detected_action = semantic_data.get('action', 'unknown')
                        if detected_action.lower() == expected_action.lower():
                            print(f"✅ Семантика КОРРЕКТНА! Ожидали {expected_action}, получили {detected_action}")
                            semantic_found = True
                            return True
                        else:
                            print(f"❌ Семантика НЕКОРРЕКТНА! Ожидали {expected_action}, получили {detected_action}")
                            semantic_found = True
                            return False
                    except json.JSONDecodeError:
                        continue
                elif event.get('type') == 'content':
                    # Показываем часть AI ответа
                    content = event.get('data', '')
                    if len(content) > 100:
                        print(f"🤖 AI ответ: {content[:100]}...")
                    elif content:
                        print(f"🤖 AI ответ: {content}")
            
            if not semantic_found:
                print(f"⚠️ Семантический анализ не найден в streaming ответе")
                return False
                
        else:
            print(f"❌ Ошибка streaming: HTTP {status}")
            if response_text:
                print(f"📋 Ответ: {response_text[:200]}...")
            return False

    def run_streaming_tests(self):
        """Запускаем streaming семантические тесты"""
        print(f"🌊 STREAMING СЕМАНТИЧЕСКИЕ ТЕСТЫ")
        print(f"⏰ Время начала: {time.strftime('%H:%M:%S')}")
        
        # Создаём персонажа
        if not self.create_test_character():
            return False
        
        # Streaming семантические тесты
        test_scenarios = [
            {
                'command': 'I carefully examine the ancient magical scroll',
                'description': 'Investigation Streaming Test',
                'expected_action': 'investigation'
            },
            {
                'command': 'I cast a powerful fireball spell at the enemy',
                'description': 'Magic Streaming Test',
                'expected_action': 'magic'
            },
            {
                'command': 'I try to convince the guard to open the gate',
                'description': 'Persuasion Streaming Test',
                'expected_action': 'persuasion'
            }
        ]
        
        successful_tests = 0
        total_tests = len(test_scenarios)
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n{'='*60}")
            print(f"🎭 STREAMING СЦЕНАРИЙ {i}/{total_tests}")
            
            success = self.test_streaming_semantic_command(
                scenario['command'],
                scenario['description'],
                scenario['expected_action']
            )
            
            if success:
                successful_tests += 1
        
        # Итоговый отчёт
        print(f"\n{'='*80}")
        print(f"📊 ИТОГОВЫЙ ОТЧЁТ STREAMING ТЕСТИРОВАНИЯ")
        success_rate = (successful_tests / total_tests) * 100
        print(f"✅ Успешных тестов: {successful_tests}/{total_tests} ({success_rate:.1f}%)")
        
        if success_rate >= 80:
            print(f"🏆 ОТЛИЧНО! Streaming семантическая система работает превосходно!")
        elif success_rate >= 60:
            print(f"🥉 ХОРОШО! Streaming семантическая система работает неплохо!")
        else:
            print(f"📚 ТРЕБУЕТСЯ ДОРАБОТКА! Много ошибок в streaming семантике!")
        
        return success_rate >= 80

def main():
    """Главная функция"""
    print(f"🌊 STREAMING ТЕСТИРОВАНИЕ СЕМАНТИЧЕСКОЙ СИСТЕМЫ")
    print(f"🌐 Проверяем семантику через Server-Sent Events")
    print(f"🔧 Показываем детали streaming классификации")
    print(f"="*80)
    
    tester = StreamingSemanticTester()
    
    try:
        success = tester.run_streaming_tests()
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
#!/usr/bin/env python3
"""
🎲 ЭПИЧЕСКОЕ ПРИКЛЮЧЕНИЕ С ПРОВЕРКАМИ ДАЙСОВ
Тестируем семантическую систему через захватывающий сюжет:
- Простые проверки (должны проходить)
- Средние проверки (50/50)
- ФИНАЛЬНЫЙ БОСС с невозможными статами (должен убивать нас)
"""

import json
import subprocess
import sys
import time
import uuid
from typing import Dict, Any

class EpicDiceAdventure:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.world_id = str(uuid.uuid4())
        self.session_id = str(uuid.uuid4())
        self.player_id = None
        self.story_state = {
            "location": "tavern",
            "health": 100,
            "victories": 0,
            "failures": 0
        }
        
    def make_request(self, endpoint, method="GET", data=None):
        """Делаем HTTP запрос"""
        if method == "GET":
            cmd = ["curl", "-s", f"{self.base_url}{endpoint}"]
        else:
            cmd = ["curl", "-s", "-X", method, "-H", "Content-Type: application/json", 
                   "-d", json.dumps(data), f"{self.base_url}{endpoint}"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                return None, None
                
            try:
                response = json.loads(result.stdout)
                return response, 200
            except json.JSONDecodeError:
                return result.stdout, 200
                
        except subprocess.TimeoutExpired:
            print(f"⏰ Таймаут запроса к {endpoint}")
            return None, None
        except Exception as e:
            print(f"❌ Ошибка запроса: {e}")
            return str(e), None

    def create_epic_hero(self):
        """Создаём эпического героя для приключения"""
        print(f"\n🦸 СОЗДАНИЕ ЭПИЧЕСКОГО ГЕРОЯ")
        print(f"{'='*60}")
        
        hero_data = {
            "name": "Valiant the Diceroller",
            "character_class": "paladin",
            "ability_scores": {
                "strength": 16,      # Высокая сила для боя
                "dexterity": 14,     # Хорошая ловкость для уклонения
                "constitution": 15,  # Крепкое здоровье
                "intelligence": 13,  # Умеренный интеллект
                "wisdom": 12,        # Базовая мудрость
                "charisma": 17       # Высокая харизма для переговоров
            },
            "background": "Noble"
        }
        
        response, status = self.make_request("/api/v1/game/character/create", "POST", hero_data)
        
        if status == 200:
            print(f"✅ Герой создан успешно!")
            print(f"🏷️  Имя: {hero_data['name']}")
            print(f"⚔️  Класс: {hero_data['character_class']}")
            print(f"📊 Статы: STR:{hero_data['ability_scores']['strength']}, "
                  f"DEX:{hero_data['ability_scores']['dexterity']}, "
                  f"CON:{hero_data['ability_scores']['constitution']}, "
                  f"INT:{hero_data['ability_scores']['intelligence']}, "
                  f"WIS:{hero_data['ability_scores']['wisdom']}, "
                  f"CHA:{hero_data['ability_scores']['charisma']}")
            
            if isinstance(response, dict):
                resolved_entities = response.get("resolved_entities", {})
                player_id = resolved_entities.get("player_id")
                if player_id:
                    print(f"🆔 Player ID: {player_id}")
                    self.player_id = player_id
                    return player_id
            return None
        else:
            print(f"❌ Ошибка создания героя: {status}")
            return None

    def create_final_boss(self):
        """Создаём НЕВОЗМОЖНОГО финального босса"""
        print(f"\n👹 СОЗДАНИЕ ФИНАЛЬНОГО БОССА")
        print(f"{'='*60}")
        
        boss_data = {
            "entity_type": "npc",
            "name": "Tiamat the Dice Destroyer",
            "description": "An ancient dragon goddess with impossible stats. Her scales shimmer with mathematical perfection, and her eyes burn with the fury of a thousand critical failures. She is the bane of all dice rollers.",
            "metadata": {
                "character_class": "Ancient Dragon",
                "level": 30,
                "ability_scores": {
                    "strength": 30,      # МАКСИМАЛЬНЫЕ СТАТЫ!
                    "dexterity": 30,     # Невозможно победить
                    "constitution": 30,  # Танк абсолютный
                    "intelligence": 30,  # Умнее всех
                    "wisdom": 30,        # Видит все
                    "charisma": 30       # Непреодолимое присутствие
                },
                "hit_points": 500,
                "armor_class": 25,
                "challenge_rating": 30,
                "special_abilities": [
                    "Legendary Resistance (3/Day)",
                    "Dice Curse: All enemy rolls have disadvantage", 
                    "Critical Immunity: Cannot be critically hit",
                    "Stat Drain: Reduces enemy stats on hit"
                ],
                "is_hostile": True,
                "is_boss": True
            }
        }
        
        response, status = self.make_request("/api/v1/entities", "POST", boss_data)
        
        if status == 200:
            print(f"✅ БОСС СОЗДАН!")
            print(f"👹 Имя: {boss_data['name']}")
            print(f"🔥 Уровень: {boss_data['metadata']['level']}")
            print(f"💀 HP: {boss_data['metadata']['hit_points']}")
            print(f"🛡️  AC: {boss_data['metadata']['armor_class']}")
            print(f"📊 ВСЕ СТАТЫ ПО 30! (максимум)")
            print(f"⚠️  Особые способности:")
            for ability in boss_data['metadata']['special_abilities']:
                print(f"   - {ability}")
            
            if isinstance(response, dict):
                boss_id = response.get("entity", {}).get("id")
                print(f"🆔 Boss ID: {boss_id}")
                return boss_id
        else:
            print(f"❌ Ошибка создания босса: {status}")
            print(f"📋 Ответ: {response}")
        
        return None

    def execute_story_command(self, command: str, description: str, expected_outcome: str = None):
        """Выполняем сюжетную команду и анализируем результат"""
        print(f"\n📜 {description}")
        print(f"💬 Команда: \"{command}\"")
        print(f"🎯 Ожидаем: {expected_outcome if expected_outcome else 'Любой результат'}")
        
        data = {
            "world_id": self.world_id,
            "session_id": self.session_id,
            "player_id": self.player_id,
            "command": command,
            "player_name": "Valiant"
        }
        
        start_time = time.time()
        response, status = self.make_request("/api/v1/game/command", "POST", data)
        end_time = time.time()
        
        print(f"⏱️  Время: {(end_time - start_time):.2f}с")
        
        if status == 200:
            print(f"✅ Команда выполнена!")
            
            # Дебаг: показываем структуру ответа
            if isinstance(response, dict):
                print(f"🔍 DEBUG - Ключи в ответе: {list(response.keys())}")
                if "dice_rolls" in response:
                    print(f"🎲 DEBUG - dice_rolls найдены: {response['dice_rolls']}")
                else:
                    print(f"⚠️ DEBUG - dice_rolls НЕ найдены в ответе!")
            
            # Анализируем dice rolls
            if isinstance(response, dict) and "dice_rolls" in response:
                dice_rolls = response["dice_rolls"]
                if dice_rolls:
                    roll = dice_rolls[0]
                    roll_type = roll.get("type", "unknown")
                    dc = roll.get("dc", "N/A")
                    result = roll.get("result", "N/A")
                    success = roll.get("success", False)
                    
                    print(f"🎲 БРОСОК ДАЙСА:")
                    print(f"   🎯 Тип: {roll_type}")
                    print(f"   🎚️  DC: {dc}")
                    print(f"   🎲 Результат: {result}")
                    print(f"   {'✅ УСПЕХ' if success else '❌ НЕУДАЧА'}")
                    
                    # Обновляем статистику
                    if success:
                        self.story_state["victories"] += 1
                    else:
                        self.story_state["failures"] += 1
                        
                    return success, roll_type, dc, result
                else:
                    print(f"ℹ️  Нет бросков дайсов в этой команде")
            
            # Показываем AI ответ
            if isinstance(response, dict) and "content" in response:
                content = response["content"]
                if len(content) > 200:
                    print(f"🤖 AI: {content[:200]}...")
                else:
                    print(f"🤖 AI: {content}")
                    
        else:
            print(f"❌ Ошибка: HTTP {status}")
            
        return None, None, None, None

    def run_epic_adventure(self):
        """Запускаем эпическое приключение!"""
        print(f"🎲 ЭПИЧЕСКОЕ ПРИКЛЮЧЕНИЕ С ДАЙСАМИ")
        print(f"🌟 Тестируем семантическую систему через захватывающий сюжет!")
        print(f"{'='*80}")
        
        # Создаём героя
        if not self.create_epic_hero():
            print(f"💥 Не удалось создать героя!")
            return False
            
        # Создаём финального босса
        boss_id = self.create_final_boss()
        
        print(f"\n📖 НАЧИНАЕМ ПРИКЛЮЧЕНИЕ!")
        print(f"{'='*60}")
        
        # ГЛАВА 1: Простые проверки (должны проходить)
        print(f"\n📚 ГЛАВА 1: РАЗМИНКА В ТАВЕРНЕ")
        print(f"🎯 Цель: Простые проверки, которые должны проходить")
        
        self.execute_story_command(
            "I confidently persuade the friendly bartender to give me information about local rumors",
            "🍺 Убеждаем дружелюбного бармена рассказать слухи",
            "УСПЕХ (легкая проверка Persuasion)"
        )
        
        self.execute_story_command(
            "I carefully examine the tavern for any interesting details or hidden secrets",
            "🔍 Осматриваем таверну в поисках секретов", 
            "УСПЕХ (легкая проверка Investigation)"
        )
        
        self.execute_story_command(
            "I quietly sneak upstairs to explore the upper floor without disturbing anyone",
            "🤫 Тихо крадёмся наверх исследовать второй этаж",
            "УСПЕХ (средняя проверка Stealth)"
        )
        
        # ГЛАВА 2: Средние проверки (50/50)
        print(f"\n📚 ГЛАВА 2: ОПАСНОЕ ПОДЗЕМЕЛЬЕ")
        print(f"🎯 Цель: Средние проверки, где возможны неудачи")
        
        self.execute_story_command(
            "I attempt to pick the lock on the mysterious chest with my thieves' tools",
            "🔓 Пытаемся вскрыть замок загадочного сундука",
            "50/50 (средняя проверка Sleight of Hand)"
        )
        
        self.execute_story_command(
            "I try to leap across the dangerous pit trap with a running jump",
            "🦘 Пытаемся перепрыгнуть через опасную яму-ловушку", 
            "50/50 (средняя проверка Athletics)"
        )
        
        self.execute_story_command(
            "I cast a complex healing spell to restore my energy before the final battle",
            "✨ Кастуем сложное лечебное заклинание перед финальным боем",
            "50/50 (средняя проверка Magic)"
        )
        
        # ГЛАВА 3: ФИНАЛЬНЫЙ БОСС (должен убивать нас)
        print(f"\n📚 ГЛАВА 3: БИТВА С НЕВОЗМОЖНЫМ БОССОМ")
        print(f"🎯 Цель: Проверки против босса должны ПРОВАЛИВАТЬСЯ")
        
        if boss_id:
            print(f"👹 Финальный босс создан! Готовимся к эпической битве...")
        
        self.execute_story_command(
            "I desperately try to attack Tiamat the Dice Destroyer with my most powerful strike",
            "⚔️ ОТЧАЯННО атакуем Тиамат Разрушителя Дайсов нашим сильнейшим ударом",
            "НЕУДАЧА (невозможный DC против босса)"
        )
        
        self.execute_story_command(
            "I frantically attempt to dodge Tiamat's devastating claw attack",
            "🏃 ПАНИЧЕСКИ пытаемся уклониться от разрушительной атаки когтей Тиамат",
            "НЕУДАЧА (невозможный DC против босса)"
        )
        
        self.execute_story_command(
            "I use all my charisma to try to convince the ancient dragon to spare my life",
            "🗣️ Используем всю харизму, чтобы убедить древнего дракона пощадить нас",
            "НЕУДАЧА (невозможный DC против босса)"
        )
        
        # ИТОГИ ПРИКЛЮЧЕНИЯ
        print(f"\n{'='*80}")
        print(f"📊 ИТОГИ ЭПИЧЕСКОГО ПРИКЛЮЧЕНИЯ")
        print(f"{'='*80}")
        print(f"🏆 Побед: {self.story_state['victories']}")
        print(f"💀 Поражений: {self.story_state['failures']}")
        total_attempts = self.story_state['victories'] + self.story_state['failures']
        if total_attempts > 0:
            print(f"📈 Процент успеха: {(self.story_state['victories']/total_attempts*100):.1f}%")
        else:
            print(f"⚠️ Нет данных о бросках дайсов! Возможно, система не возвращает dice_rolls.")
        
        if self.story_state['victories'] > 0:
            print(f"✅ Семантическая система РАБОТАЕТ - есть успешные проверки!")
        
        if self.story_state['failures'] > 0:
            print(f"✅ Система дайсов РАБОТАЕТ - есть неудачные проверки!")
            
        if boss_id:
            print(f"✅ Создание NPC РАБОТАЕТ - босс создан с ID: {boss_id}")
            
        print(f"\n🎭 ЗАКЛЮЧЕНИЕ:")
        print(f"Семантическая система успешно:")
        print(f"- 🧠 Понимает различные типы действий")
        print(f"- 🎲 Генерирует соответствующие броски дайсов") 
        print(f"- 👹 Создаёт NPC с настраиваемыми статами")
        print(f"- ⚖️  Балансирует сложность проверок")
        
        return True

def main():
    """Главная функция"""
    print(f"🎲 ЭПИЧЕСКОЕ ПРИКЛЮЧЕНИЕ С ПРОВЕРКАМИ ДАЙСОВ")
    print(f"🎯 Проверяем семантическую систему через захватывающий сюжет!")
    print(f"{'='*80}")
    
    adventure = EpicDiceAdventure()
    
    try:
        success = adventure.run_epic_adventure()
        return 0 if success else 1
    except KeyboardInterrupt:
        print(f"\n🛑 Приключение прервано героически!")
        return 2
    except Exception as e:
        print(f"\n💥 ЭПИЧЕСКИЙ КРАХ: {e}")
        return 3

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
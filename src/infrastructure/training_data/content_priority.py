"""
Training data for Content Priority Classification
"""

from dataclasses import dataclass
from typing import List
from infrastructure.command_classification_service import ClassificationExample

@dataclass
class ContentPriorityTrainingData:
    """Content priority classification training examples"""
    
    @staticmethod
    def get_examples() -> List[ClassificationExample]:
        return [
            # HIGH PRIORITY - важный контент, ключевые моменты
            ClassificationExample("Player: Атакую дракона мечом", "high_priority"),
            ClassificationExample("Character: Кастую заклинание телепортации", "high_priority"),
            ClassificationExample("Location: Древний храм с сокровищами", "high_priority"),
            ClassificationExample("Combat: Критический удар по врагу", "high_priority"),
            ClassificationExample("Quest: Найти артефакт силы", "high_priority"),
            ClassificationExample("Event: Дракон атакует город", "high_priority"),
            ClassificationExample("Dialog: Король дает важное задание", "high_priority"),
            ClassificationExample("Magic: Заклинание воскрешения", "high_priority"),
            ClassificationExample("Danger: Ловушка активирована", "high_priority"),
            ClassificationExample("Discovery: Тайная комната найдена", "high_priority"),
            
            # Игровые действия с высоким приоритетом
            ClassificationExample("бросаю кости на атаку", "high_priority"),
            ClassificationExample("делаю спасбросок", "high_priority"),
            ClassificationExample("проверка навыка", "high_priority"),
            ClassificationExample("инициатива в бою", "high_priority"),
            ClassificationExample("урон по цели", "high_priority"),
            
            # Важные события и открытия
            ClassificationExample("древний артефакт пульсирует силой", "high_priority"),
            ClassificationExample("портал открывается", "high_priority"),
            ClassificationExample("босс появляется", "high_priority"),
            ClassificationExample("квест завершен", "high_priority"),
            ClassificationExample("уровень повышен", "high_priority"),
            
            # English high priority
            ClassificationExample("Player: Cast fireball spell", "high_priority"),
            ClassificationExample("Character: Attack with sword", "high_priority"),
            ClassificationExample("Location: Dragon's treasure hoard", "high_priority"),
            ClassificationExample("Combat: Critical hit landed", "high_priority"),
            ClassificationExample("Quest: Ancient artifact discovered", "high_priority"),
            ClassificationExample("Event: Portal opens suddenly", "high_priority"),
            ClassificationExample("The ancient artifact pulses with power", "high_priority"),
            ClassificationExample("A dragon appears in the sky", "high_priority"),
            ClassificationExample("The door slams shut behind you", "high_priority"),
            ClassificationExample("You hear footsteps approaching", "high_priority"),
            
            # LOW PRIORITY - обычный описательный текст
            ClassificationExample("The weather is nice today", "low_priority"),
            ClassificationExample("Birds are singing in the trees", "low_priority"),
            ClassificationExample("The grass is green and soft", "low_priority"),
            ClassificationExample("It's a peaceful morning", "low_priority"),
            ClassificationExample("The sun shines brightly", "low_priority"),
            ClassificationExample("Clouds drift across the sky", "low_priority"),
            ClassificationExample("A gentle breeze blows", "low_priority"),
            ClassificationExample("The flowers smell sweet", "low_priority"),
            ClassificationExample("Water flows in the stream", "low_priority"),
            ClassificationExample("Generic description text", "low_priority"),
            
            # Обычные описания на русском
            ClassificationExample("погода сегодня хорошая", "low_priority"),
            ClassificationExample("птицы поют на деревьях", "low_priority"),
            ClassificationExample("трава зеленая и мягкая", "low_priority"),
            ClassificationExample("утро тихое и спокойное", "low_priority"),
            ClassificationExample("солнце ярко светит", "low_priority"),
            ClassificationExample("облака плывут по небу", "low_priority"),
            ClassificationExample("дует легкий ветерок", "low_priority"),
            ClassificationExample("цветы приятно пахнут", "low_priority"),
            ClassificationExample("вода течет в ручье", "low_priority"),
            ClassificationExample("обычное описание", "low_priority"),
            
            # Нейтральные бытовые действия
            ClassificationExample("иду по дороге", "low_priority"),
            ClassificationExample("смотрю на пейзаж", "low_priority"),
            ClassificationExample("отдыхаю под деревом", "low_priority"),
            ClassificationExample("слушаю звуки природы", "low_priority"),
            ClassificationExample("наслаждаюсь моментом", "low_priority"),
        ]
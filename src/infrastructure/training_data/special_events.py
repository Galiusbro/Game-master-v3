"""
Training data for Special Event Detection
"""

from dataclasses import dataclass
from typing import List
from infrastructure.command_classification_service import ClassificationExample

@dataclass
class SpecialEventTrainingData:
    """Special event detection training examples"""
    
    @staticmethod
    def get_examples() -> List[ClassificationExample]:
        return [
            # DEATH EVENTS - события смерти
            ClassificationExample("игрок умер от урона", "death_event"),
            ClassificationExample("персонаж погиб в бою", "death_event"),
            ClassificationExample("герой пал от ран", "death_event"),
            ClassificationExample("смерть настигла воина", "death_event"),
            ClassificationExample("жизнь покинула тело", "death_event"),
            ClassificationExample("последний вздох героя", "death_event"),
            ClassificationExample("дух покинул бренное тело", "death_event"),
            ClassificationExample("player died from damage", "death_event"),
            ClassificationExample("character was killed", "death_event"),
            ClassificationExample("hero fell in battle", "death_event"),
            ClassificationExample("death claimed the warrior", "death_event"),
            ClassificationExample("life left the body", "death_event"),
            ClassificationExample("final breath escaped", "death_event"),
            ClassificationExample("перестал дышать", "death_event"),
            ClassificationExample("скончался от ран", "death_event"),
            ClassificationExample("испустил дух", "death_event"),
            ClassificationExample("отправился в мир иной", "death_event"),
            
            # RESURRECTION EVENTS - события воскрешения
            ClassificationExample("воскрешение героя", "resurrection_event"),
            ClassificationExample("возвращение к жизни", "resurrection_event"),
            ClassificationExample("магическое исцеление", "resurrection_event"),
            ClassificationExample("божественное вмешательство", "resurrection_event"),
            ClassificationExample("дух вернулся в тело", "resurrection_event"),
            ClassificationExample("жизнь вернулась", "resurrection_event"),
            ClassificationExample("пробуждение от смерти", "resurrection_event"),
            ClassificationExample("resurrection of hero", "resurrection_event"),
            ClassificationExample("return to life", "resurrection_event"),
            ClassificationExample("divine intervention", "resurrection_event"),
            ClassificationExample("spirit returns to body", "resurrection_event"),
            ClassificationExample("awakening from death", "resurrection_event"),
            ClassificationExample("magical healing", "resurrection_event"),
            ClassificationExample("оживление", "resurrection_event"),
            ClassificationExample("возрождение", "resurrection_event"),
            ClassificationExample("восстание из мертвых", "resurrection_event"),
            ClassificationExample("второе рождение", "resurrection_event"),
            
            # SCROLL USAGE - использование свитков воскрешения
            ClassificationExample("I use the scroll of resurrection", "resurrection_event"),
            ClassificationExample("I activate the resurrection scroll", "resurrection_event"),
            ClassificationExample("I read the scroll of revival", "resurrection_event"),
            ClassificationExample("я использую свиток воскрешения", "resurrection_event"),
            ClassificationExample("активирую свиток возрождения", "resurrection_event"),
            ClassificationExample("читаю свиток оживления", "resurrection_event"),
            ClassificationExample("применяю магический свиток", "resurrection_event"),
            ClassificationExample("use resurrection scroll", "resurrection_event"),
            ClassificationExample("activate revival scroll", "resurrection_event"),
            ClassificationExample("consume scroll of life", "resurrection_event"),
            ClassificationExample("invoke the scroll", "resurrection_event"),
            ClassificationExample("я кастую свиток воскрешения", "resurrection_event"),
            ClassificationExample("использую магический свиток жизни", "resurrection_event"),
        ]
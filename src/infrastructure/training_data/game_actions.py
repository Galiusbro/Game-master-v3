"""
Training data for Game Action Classification
"""

from dataclasses import dataclass
from typing import List
from infrastructure.command_classification_service import ClassificationExample
from infrastructure.command_classification_service import GameAction

@dataclass
class GameActionTrainingData:
    """Game action classification training examples"""
    
    @staticmethod
    def get_examples() -> List[ClassificationExample]:
        return [
            # DIALOGUE - разговоры и социальные взаимодействия
            ClassificationExample("говорю с трактирщиком", GameAction.DIALOGUE.value),
            ClassificationExample("спрашиваю о квесте", GameAction.DIALOGUE.value),
            ClassificationExample("отвечаю на вопрос", GameAction.DIALOGUE.value),
            ClassificationExample("рассказываю историю", GameAction.DIALOGUE.value),
            ClassificationExample("приветствую стражника", GameAction.DIALOGUE.value),
            ClassificationExample("беседую с мудрецом", GameAction.DIALOGUE.value),
            ClassificationExample("talk to the bartender", GameAction.DIALOGUE.value),
            ClassificationExample("ask about the quest", GameAction.DIALOGUE.value),
            ClassificationExample("greet the merchant", GameAction.DIALOGUE.value),
            ClassificationExample("tell a story", GameAction.DIALOGUE.value),
            ClassificationExample("answer the question", GameAction.DIALOGUE.value),
            
            # MOVEMENT - перемещение и навигация
            ClassificationExample("иду к двери", GameAction.MOVEMENT.value),
            ClassificationExample("поворачиваю направо", GameAction.MOVEMENT.value),
            ClassificationExample("спускаюсь в подвал", GameAction.MOVEMENT.value),
            ClassificationExample("выхожу из таверны", GameAction.MOVEMENT.value),
            ClassificationExample("направляюсь к замку", GameAction.MOVEMENT.value),
            ClassificationExample("возвращаюсь в город", GameAction.MOVEMENT.value),
            ClassificationExample("go to the door", GameAction.MOVEMENT.value),
            ClassificationExample("move forward", GameAction.MOVEMENT.value),
            ClassificationExample("walk to the castle", GameAction.MOVEMENT.value),
            ClassificationExample("return to town", GameAction.MOVEMENT.value),
            ClassificationExample("head north", GameAction.MOVEMENT.value),
            ClassificationExample("leave the tavern", GameAction.MOVEMENT.value),
            
            # SEARCH - поиск и исследование
            ClassificationExample("осматриваю комнату", GameAction.SEARCH.value),
            ClassificationExample("ищу тайные двери", GameAction.SEARCH.value),
            ClassificationExample("проверяю сундук", GameAction.SEARCH.value),
            ClassificationExample("изучаю древние руны", GameAction.SEARCH.value),
            ClassificationExample("examine the room", GameAction.SEARCH.value),
            ClassificationExample("search for traps", GameAction.SEARCH.value),
            ClassificationExample("look around", GameAction.SEARCH.value),
            ClassificationExample("investigate the noise", GameAction.SEARCH.value),
            ClassificationExample("check the chest", GameAction.SEARCH.value),
            ClassificationExample("study the map", GameAction.SEARCH.value),
            
            # COMBAT - бой и атаки
            ClassificationExample("атакую орка", GameAction.COMBAT.value),
            ClassificationExample("наношу удар мечом", GameAction.COMBAT.value),
            ClassificationExample("защищаюсь щитом", GameAction.COMBAT.value),
            ClassificationExample("стреляю из лука", GameAction.COMBAT.value),
            ClassificationExample("attack the goblin", GameAction.COMBAT.value),
            ClassificationExample("swing my sword", GameAction.COMBAT.value),
            ClassificationExample("defend with shield", GameAction.COMBAT.value),
            ClassificationExample("cast fireball", GameAction.COMBAT.value),
            ClassificationExample("shoot an arrow", GameAction.COMBAT.value),
            ClassificationExample("fight the dragon", GameAction.COMBAT.value),
            
            # TRADE - торговля и обмен
            ClassificationExample("покупаю зелье", GameAction.TRADE.value),
            ClassificationExample("продаю старое оружие", GameAction.TRADE.value),
            ClassificationExample("торгуюсь с купцом", GameAction.TRADE.value),
            ClassificationExample("обмениваю артефакты", GameAction.TRADE.value),
            ClassificationExample("buy health potion", GameAction.TRADE.value),
            ClassificationExample("sell old armor", GameAction.TRADE.value),
            ClassificationExample("negotiate price", GameAction.TRADE.value),
            ClassificationExample("trade items", GameAction.TRADE.value),
            ClassificationExample("purchase supplies", GameAction.TRADE.value),
            ClassificationExample("barter with merchant", GameAction.TRADE.value),
            
            # MAGIC - магия и заклинания
            ClassificationExample("кастую заклинание исцеления", GameAction.MAGIC.value),
            ClassificationExample("читаю магический свиток", GameAction.MAGIC.value),
            ClassificationExample("использую телепортацию", GameAction.MAGIC.value),
            ClassificationExample("призываю элементаля", GameAction.MAGIC.value),
            ClassificationExample("cast healing spell", GameAction.MAGIC.value),
            ClassificationExample("use magic missile", GameAction.MAGIC.value),
            ClassificationExample("read the scroll", GameAction.MAGIC.value),
            ClassificationExample("summon familiar", GameAction.MAGIC.value),
            ClassificationExample("enchant weapon", GameAction.MAGIC.value),
            ClassificationExample("dispel magic", GameAction.MAGIC.value),
            
            # STEALTH - скрытность и воровство
            ClassificationExample("прячусь в тени", GameAction.STEALTH.value),
            ClassificationExample("подкрадываюсь к врагу", GameAction.STEALTH.value),
            ClassificationExample("крадусь по коридору", GameAction.STEALTH.value),
            ClassificationExample("взламываю замок", GameAction.STEALTH.value),
            ClassificationExample("карманничаю", GameAction.STEALTH.value),
            ClassificationExample("hide in shadows", GameAction.STEALTH.value),
            ClassificationExample("sneak past guards", GameAction.STEALTH.value),
            ClassificationExample("pick the lock", GameAction.STEALTH.value),
            ClassificationExample("pickpocket the merchant", GameAction.STEALTH.value),
            ClassificationExample("move silently", GameAction.STEALTH.value),
            
            # INVESTIGATION - детальное исследование
            ClassificationExample("examine the mysterious artifact", GameAction.INVESTIGATION.value),
            ClassificationExample("investigate the glowing object", GameAction.INVESTIGATION.value),
            ClassificationExample("inspect the ancient altar", GameAction.INVESTIGATION.value),
            ClassificationExample("study the magical runes", GameAction.INVESTIGATION.value),
            ClassificationExample("analyze the strange device", GameAction.INVESTIGATION.value),
            ClassificationExample("осматриваю загадочный артефакт", GameAction.INVESTIGATION.value),
            ClassificationExample("исследую светящийся предмет", GameAction.INVESTIGATION.value),
            ClassificationExample("изучаю древний алтарь", GameAction.INVESTIGATION.value),
            ClassificationExample("анализирую странное устройство", GameAction.INVESTIGATION.value),
            ClassificationExample("обыскиваю древнюю гробницу", GameAction.INVESTIGATION.value),
            
            # PERSUASION - убеждение и переговоры
            ClassificationExample("try to persuade the guard", GameAction.PERSUASION.value),
            ClassificationExample("convince the merchant", GameAction.PERSUASION.value),
            ClassificationExample("negotiate with the captain", GameAction.PERSUASION.value),
            ClassificationExample("reason with the hostile NPC", GameAction.PERSUASION.value),
            ClassificationExample("attempt to convince them", GameAction.PERSUASION.value),
            ClassificationExample("пытаюсь убедить стражника", GameAction.PERSUASION.value),
            ClassificationExample("убеждаю торговца", GameAction.PERSUASION.value),
            ClassificationExample("веду переговоры с капитаном", GameAction.PERSUASION.value),
            ClassificationExample("пытаюсь договориться", GameAction.PERSUASION.value),
            
            # More MAGIC examples
            ClassificationExample("quickly cast a healing spell", GameAction.MAGIC.value),
            ClassificationExample("cast healing spell on companion", GameAction.MAGIC.value),
            ClassificationExample("use magic to heal wounds", GameAction.MAGIC.value),
            ClassificationExample("perform healing ritual", GameAction.MAGIC.value),
            ClassificationExample("быстро кастую лечебное заклинание", GameAction.MAGIC.value),
            ClassificationExample("использую магию исцеления", GameAction.MAGIC.value),
        ]
"""
Training data for Action Urgency Detection Classification
"""

from dataclasses import dataclass
from typing import List
from infrastructure.command_classification_service import ClassificationExample

@dataclass
class ActionUrgencyTrainingData:
    """Action urgency classification training examples"""
    
    @staticmethod
    def get_examples() -> List[ClassificationExample]:
        return [
            # === CASUAL - неспешные, обычные действия ===
            
            # Relaxed exploration
            ClassificationExample("I take a look around the room", "casual"),
            ClassificationExample("Я осматриваюсь по сторонам", "casual"),
            ClassificationExample("I walk over to the merchant", "casual"),
            ClassificationExample("Я подхожу к торговцу", "casual"),
            ClassificationExample("I chat with the innkeeper", "casual"),
            ClassificationExample("Я болтаю с трактирщиком", "casual"),
            
            # Leisurely activities
            ClassificationExample("I browse through the available items", "casual"),
            ClassificationExample("Я просматриваю доступные предметы", "casual"),
            ClassificationExample("I sit down and rest for a while", "casual"),
            ClassificationExample("Я присаживаюсь и отдыхаю немного", "casual"),
            ClassificationExample("I enjoy a meal at the tavern", "casual"),
            ClassificationExample("Я наслаждаюсь едой в таверне", "casual"),
            
            # Normal conversation
            ClassificationExample("I ask about the local rumors", "casual"),
            ClassificationExample("Я спрашиваю о местных слухах", "casual"),
            ClassificationExample("I tell them about my travels", "casual"),
            ClassificationExample("Я рассказываю им о своих путешествиях", "casual"),
            ClassificationExample("I strike up a friendly conversation", "casual"),
            ClassificationExample("Я завожу дружескую беседу", "casual"),
            
            # === CAREFUL - осторожные, продуманные действия ===
            
            # Deliberate examination
            ClassificationExample("I carefully examine the ancient runes", "careful"),
            ClassificationExample("Я осторожно изучаю древние руны", "careful"),
            ClassificationExample("I slowly approach the suspicious door", "careful"),
            ClassificationExample("Я медленно приближаюсь к подозрительной двери", "careful"),
            ClassificationExample("I methodically search through the debris", "careful"),
            ClassificationExample("Я методично обыскиваю обломки", "careful"),
            
            # Cautious movement
            ClassificationExample("I tread lightly across the creaking floorboards", "careful"),
            ClassificationExample("Я осторожно ступаю по скрипящим половицам", "careful"),
            ClassificationExample("I quietly sneak past the sleeping guard", "careful"),
            ClassificationExample("Я тихо прокрадываюсь мимо спящего стражника", "careful"),
            ClassificationExample("I cautiously peek around the corner", "careful"),
            ClassificationExample("Я осторожно заглядываю за угол", "careful"),
            
            # Thoughtful planning
            ClassificationExample("I study the situation before acting", "careful"),
            ClassificationExample("Я изучаю ситуацию перед действием", "careful"),
            ClassificationExample("I take time to consider my options", "careful"),
            ClassificationExample("Я трачу время на обдумывание вариантов", "careful"),
            ClassificationExample("I plan my approach carefully", "careful"),
            ClassificationExample("Я тщательно планирую свой подход", "careful"),
            
            # === URGENT - срочные, быстрые действия ===
            
            # Time pressure
            ClassificationExample("I quickly search for an exit", "urgent"),
            ClassificationExample("Я быстро ищу выход", "urgent"),
            ClassificationExample("I rush to help the wounded ally", "urgent"),
            ClassificationExample("Я спешу помочь раненому союзнику", "urgent"),
            ClassificationExample("I hurry to catch up with the group", "urgent"),
            ClassificationExample("Я тороплюсь догнать группу", "urgent"),
            
            # Fast reactions
            ClassificationExample("I immediately draw my weapon", "urgent"),
            ClassificationExample("Я немедленно обнажаю оружие", "urgent"),
            ClassificationExample("I swiftly dodge the falling debris", "urgent"),
            ClassificationExample("Я быстро уклоняюсь от падающих обломков", "urgent"),
            ClassificationExample("I rapidly cast a healing spell", "urgent"),
            ClassificationExample("Я быстро произношу заклинание лечения", "urgent"),
            
            # Emergency responses
            ClassificationExample("I shout a warning to my companions", "urgent"),
            ClassificationExample("Я кричу предупреждение товарищам", "urgent"),
            ClassificationExample("I sprint toward the sound of combat", "urgent"),
            ClassificationExample("Я бегу на звук боя", "urgent"),
            ClassificationExample("I grab the rope before it falls", "urgent"),
            ClassificationExample("Я хватаю верёвку, прежде чем она упадёт", "urgent"),
            
            # === DESPERATE - отчаянные, панические действия ===
            
            # Life or death situations
            ClassificationExample("I frantically search for any way out", "desperate"),
            ClassificationExample("Я отчаянно ищу любой выход", "desperate"),
            ClassificationExample("I desperately try to stop the bleeding", "desperate"),
            ClassificationExample("Я отчаянно пытаюсь остановить кровотечение", "desperate"),
            ClassificationExample("I throw myself at the closing door", "desperate"),
            ClassificationExample("Я бросаюсь к закрывающейся двери", "desperate"),
            
            # Panic actions
            ClassificationExample("I wildly swing at anything that moves", "desperate"),
            ClassificationExample("Я дико размахиваю по всему, что движется", "desperate"),
            ClassificationExample("I scream for help at the top of my lungs", "desperate"),
            ClassificationExample("Я кричу о помощи во весь голос", "desperate"),
            ClassificationExample("I claw desperately at the locked door", "desperate"),
            ClassificationExample("Я отчаянно царапаю запертую дверь", "desperate"),
            
            # Last resort attempts
            ClassificationExample("I make a final desperate leap", "desperate"),
            ClassificationExample("Я делаю последний отчаянный прыжок", "desperate"),
            ClassificationExample("I risk everything on this one chance", "desperate"),
            ClassificationExample("Я рискую всем ради этого единственного шанса", "desperate"),
            ClassificationExample("I fight with the fury of the cornered", "desperate"),
            ClassificationExample("Я сражаюсь с яростью загнанного в угол", "desperate"),
            
            # === Contextual examples showing urgency modifiers ===
            
            # Stealth with different urgency levels
            ClassificationExample("I take my time to move silently", "careful"),
            ClassificationExample("Я не тороплюсь, двигаясь бесшумно", "careful"),
            ClassificationExample("I need to sneak past quickly", "urgent"),
            ClassificationExample("Мне нужно быстро прокрасться мимо", "urgent"),
            ClassificationExample("I desperately try to hide from the patrol", "desperate"),
            ClassificationExample("Я отчаянно пытаюсь спрятаться от патруля", "desperate"),
            
            # Combat with different approaches
            ClassificationExample("I carefully aim my shot", "careful"),
            ClassificationExample("Я тщательно целюсь", "careful"),
            ClassificationExample("I need to attack before they notice", "urgent"),
            ClassificationExample("Мне нужно атаковать, пока они не заметили", "urgent"),
            ClassificationExample("I attack wildly in blind panic", "desperate"),
            ClassificationExample("Я атакую дико в слепой панике", "desperate"),
            
            # Social interactions with different pressures
            ClassificationExample("I engage in pleasant small talk", "casual"),
            ClassificationExample("Я веду приятную светскую беседу", "casual"),
            ClassificationExample("I need to convince them quickly", "urgent"),
            ClassificationExample("Мне нужно быстро их убедить", "urgent"),
            ClassificationExample("I plead desperately for their help", "desperate"),
            ClassificationExample("Я отчаянно умоляю их о помощи", "desperate"),
            
            # Exploration with time constraints
            ClassificationExample("I leisurely explore the ancient library", "casual"),
            ClassificationExample("Я неспешно исследую древнюю библиотеку", "casual"),
            ClassificationExample("I systematically check each room for traps", "careful"),
            ClassificationExample("Я систематически проверяю каждую комнату на ловушки", "careful"),
            ClassificationExample("I must find the artifact before dawn", "urgent"),
            ClassificationExample("Я должен найти артефакт до рассвета", "urgent"),
            ClassificationExample("The ceiling is collapsing, I search frantically", "desperate"),
            ClassificationExample("Потолок обрушается, я отчаянно ищу", "desperate"),
        ]
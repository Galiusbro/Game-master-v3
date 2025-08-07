"""
Training data for Ability Detection Classification
"""

from dataclasses import dataclass
from typing import List
from infrastructure.command_classification_service import ClassificationExample
from domain.entities import AbilityScore

@dataclass
class AbilityDetectionTrainingData:
    """Ability detection training examples"""
    
    @staticmethod
    def get_examples() -> List[ClassificationExample]:
        return [
            # STRENGTH - сила, физическая мощь
            ClassificationExample("ломаю дверь силой", AbilityScore.STRENGTH.value),
            ClassificationExample("разбиваю стену кулаком", AbilityScore.STRENGTH.value),
            ClassificationExample("поднимаю тяжелый камень", AbilityScore.STRENGTH.value),
            ClassificationExample("сгибаю железные прутья", AbilityScore.STRENGTH.value),
            ClassificationExample("толкаю валун", AbilityScore.STRENGTH.value),
            ClassificationExample("бью с силой", AbilityScore.STRENGTH.value),
            ClassificationExample("break the chains", AbilityScore.STRENGTH.value),
            ClassificationExample("smash the wall", AbilityScore.STRENGTH.value),
            ClassificationExample("lift heavy boulder", AbilityScore.STRENGTH.value),
            ClassificationExample("bend iron bars", AbilityScore.STRENGTH.value),
            ClassificationExample("force the door open", AbilityScore.STRENGTH.value),
            ClassificationExample("crushing blow", AbilityScore.STRENGTH.value),
            
            # DEXTERITY - ловкость, быстрота, точность
            ClassificationExample("уворачиваюсь от удара", AbilityScore.DEXTERITY.value),
            ClassificationExample("делаю акробатический трюк", AbilityScore.DEXTERITY.value),
            ClassificationExample("быстро перепрыгиваю пропасть", AbilityScore.DEXTERITY.value),
            ClassificationExample("ловко балансирую на канате", AbilityScore.DEXTERITY.value),
            ClassificationExample("метко стреляю из лука", AbilityScore.DEXTERITY.value),
            ClassificationExample("точно попадаю в цель", AbilityScore.DEXTERITY.value),
            ClassificationExample("изящно танцую", AbilityScore.DEXTERITY.value),
            ClassificationExample("dodge the attack", AbilityScore.DEXTERITY.value),
            ClassificationExample("perform acrobatics", AbilityScore.DEXTERITY.value),
            ClassificationExample("balance on tightrope", AbilityScore.DEXTERITY.value),
            ClassificationExample("shoot with precision", AbilityScore.DEXTERITY.value),
            ClassificationExample("nimble movement", AbilityScore.DEXTERITY.value),
            ClassificationExample("graceful dance", AbilityScore.DEXTERITY.value),
            
            # INTELLIGENCE - интеллект, знания, анализ
            ClassificationExample("вспоминаю древние знания", AbilityScore.INTELLIGENCE.value),
            ClassificationExample("анализирую магические символы", AbilityScore.INTELLIGENCE.value),
            ClassificationExample("решаю сложную головоломку", AbilityScore.INTELLIGENCE.value),
            ClassificationExample("изучаю старинные тексты", AbilityScore.INTELLIGENCE.value),
            ClassificationExample("расшифровываю код", AbilityScore.INTELLIGENCE.value),
            ClassificationExample("понимаю механизм", AbilityScore.INTELLIGENCE.value),
            ClassificationExample("вычисляю траекторию", AbilityScore.INTELLIGENCE.value),
            ClassificationExample("recall the legend", AbilityScore.INTELLIGENCE.value),
            ClassificationExample("analyze the symbols", AbilityScore.INTELLIGENCE.value),
            ClassificationExample("solve the puzzle", AbilityScore.INTELLIGENCE.value),
            ClassificationExample("decipher the code", AbilityScore.INTELLIGENCE.value),
            ClassificationExample("understand mechanism", AbilityScore.INTELLIGENCE.value),
            ClassificationExample("calculate trajectory", AbilityScore.INTELLIGENCE.value),
            
            # WISDOM - мудрость, восприятие, интуиция
            ClassificationExample("замечаю опасность", AbilityScore.WISDOM.value),
            ClassificationExample("чувствую подвох", AbilityScore.WISDOM.value),
            ClassificationExample("слышу тихие звуки", AbilityScore.WISDOM.value),
            ClassificationExample("ощущаю магическую ауру", AbilityScore.WISDOM.value),
            ClassificationExample("предчувствую беду", AbilityScore.WISDOM.value),
            ClassificationExample("понимаю мотивы", AbilityScore.WISDOM.value),
            ClassificationExample("медитирую", AbilityScore.WISDOM.value),
            ClassificationExample("sense the trap", AbilityScore.WISDOM.value),
            ClassificationExample("notice the ambush", AbilityScore.WISDOM.value),
            ClassificationExample("hear faint sounds", AbilityScore.WISDOM.value),
            ClassificationExample("feel magical presence", AbilityScore.WISDOM.value),
            ClassificationExample("intuitive understanding", AbilityScore.WISDOM.value),
            ClassificationExample("wise judgment", AbilityScore.WISDOM.value),
            
            # CHARISMA - харизма, убеждение, лидерство
            ClassificationExample("убеждаю стражника пропустить", AbilityScore.CHARISMA.value),
            ClassificationExample("очаровываю принцессу", AbilityScore.CHARISMA.value),
            ClassificationExample("вдохновляю союзников", AbilityScore.CHARISMA.value),
            ClassificationExample("командую отрядом", AbilityScore.CHARISMA.value),
            ClassificationExample("произношу речь", AbilityScore.CHARISMA.value),
            ClassificationExample("завоевываю доверие", AbilityScore.CHARISMA.value),
            ClassificationExample("демонстрирую уверенность", AbilityScore.CHARISMA.value),
            ClassificationExample("persuade the merchant", AbilityScore.CHARISMA.value),
            ClassificationExample("charm the noble", AbilityScore.CHARISMA.value),
            ClassificationExample("inspire the troops", AbilityScore.CHARISMA.value),
            ClassificationExample("lead the party", AbilityScore.CHARISMA.value),
            ClassificationExample("give rousing speech", AbilityScore.CHARISMA.value),
            ClassificationExample("display confidence", AbilityScore.CHARISMA.value),
            
            # CONSTITUTION - выносливость, здоровье (если есть)
            ClassificationExample("выдерживаю яд", AbilityScore.CONSTITUTION.value),
            ClassificationExample("сопротивляюсь болезни", AbilityScore.CONSTITUTION.value),
            ClassificationExample("долго бегу без устали", AbilityScore.CONSTITUTION.value),
            ClassificationExample("переношу боль", AbilityScore.CONSTITUTION.value),
            ClassificationExample("resist poison", AbilityScore.CONSTITUTION.value),
            ClassificationExample("endure hardship", AbilityScore.CONSTITUTION.value),
            ClassificationExample("marathon running", AbilityScore.CONSTITUTION.value),
            ClassificationExample("withstand pain", AbilityScore.CONSTITUTION.value),
        ]
"""
Training data for Lighting Condition Classification
"""

from dataclasses import dataclass
from typing import List
from infrastructure.command_classification_service import ClassificationExample

@dataclass
class LightingConditionTrainingData:
    """Lighting condition classification training examples"""
    
    @staticmethod
    def get_examples() -> List[ClassificationExample]:
        return [
            # DARK - темные условия
            ClassificationExample("комната погружена в темноту", "dark"),
            ClassificationExample("темный коридор без света", "dark"),
            ClassificationExample("мрачная пещера", "dark"),
            ClassificationExample("тени окутывают помещение", "dark"),
            ClassificationExample("подвал без освещения", "dark"),
            ClassificationExample("ночная улица", "dark"),
            ClassificationExample("темный лес", "dark"),
            ClassificationExample("черная как смоль комната", "dark"),
            ClassificationExample("освещение отсутствует", "dark"),
            ClassificationExample("кромешная тьма", "dark"),
            ClassificationExample("сумрачное помещение", "dark"),
            ClassificationExample("плохо освещенная зона", "dark"),
            ClassificationExample("тусклый свет едва пробивается", "dark"),
            ClassificationExample("глубокие тени повсюду", "dark"),
            ClassificationExample("мрак окутал локацию", "dark"),
            
            # English dark conditions
            ClassificationExample("room is shrouded in darkness", "dark"),
            ClassificationExample("dark corridor without light", "dark"),
            ClassificationExample("gloomy cave entrance", "dark"),
            ClassificationExample("shadows envelop the area", "dark"),
            ClassificationExample("dimly lit basement", "dark"),
            ClassificationExample("nighttime street", "dark"),
            ClassificationExample("dark forest path", "dark"),
            ClassificationExample("pitch black room", "dark"),
            ClassificationExample("no lighting present", "dark"),
            ClassificationExample("complete darkness", "dark"),
            ClassificationExample("murky atmosphere", "dark"),
            ClassificationExample("poorly lit zone", "dark"),
            ClassificationExample("faint light barely visible", "dark"),
            ClassificationExample("deep shadows everywhere", "dark"),
            ClassificationExample("gloom covers the location", "dark"),
            
            # BRIGHT - яркие условия
            ClassificationExample("комната залита солнечным светом", "bright"),
            ClassificationExample("яркое освещение повсюду", "bright"),
            ClassificationExample("солнце ярко светит", "bright"),
            ClassificationExample("дневной свет проникает в окна", "bright"),
            ClassificationExample("хорошо освещенный зал", "bright"),
            ClassificationExample("множество факелов освещают путь", "bright"),
            ClassificationExample("магический свет наполняет пространство", "bright"),
            ClassificationExample("кристаллы светятся ярким светом", "bright"),
            ClassificationExample("солнечная поляна", "bright"),
            ClassificationExample("ослепительный блеск", "bright"),
            ClassificationExample("лучи света пронизывают комнату", "bright"),
            ClassificationExample("великолепное освещение", "bright"),
            ClassificationExample("свет отражается от стен", "bright"),
            ClassificationExample("яркие лампы горят", "bright"),
            ClassificationExample("световые заклинания активны", "bright"),
            
            # English bright conditions  
            ClassificationExample("room is bathed in sunlight", "bright"),
            ClassificationExample("bright illumination everywhere", "bright"),
            ClassificationExample("sun shines brilliantly", "bright"),
            ClassificationExample("daylight streams through windows", "bright"),
            ClassificationExample("well-lit hall", "bright"),
            ClassificationExample("many torches light the way", "bright"),
            ClassificationExample("magical light fills the space", "bright"),
            ClassificationExample("crystals glow with bright light", "bright"),
            ClassificationExample("sunny clearing", "bright"),
            ClassificationExample("dazzling brilliance", "bright"),
            ClassificationExample("rays of light pierce the room", "bright"),
            ClassificationExample("excellent lighting", "bright"),
            ClassificationExample("light reflects off walls", "bright"),
            ClassificationExample("bright lamps are burning", "bright"),
            ClassificationExample("light spells are active", "bright"),
            
            # NORMAL - нормальное освещение
            ClassificationExample("обычное освещение в комнате", "normal"),
            ClassificationExample("стандартное освещение", "normal"),
            ClassificationExample("умеренный свет", "normal"),
            ClassificationExample("достаточно света для осмотра", "normal"),
            ClassificationExample("нейтральное освещение", "normal"),
            ClassificationExample("видимость хорошая", "normal"),
            ClassificationExample("освещение позволяет видеть детали", "normal"),
            ClassificationExample("комфортный уровень света", "normal"),
            ClassificationExample("обычный дневной свет", "normal"),
            ClassificationExample("стандартные условия видимости", "normal"),
            ClassificationExample("средний уровень освещенности", "normal"),
            ClassificationExample("приемлемая видимость", "normal"),
            
            # English normal conditions
            ClassificationExample("regular lighting in room", "normal"),
            ClassificationExample("standard illumination", "normal"),
            ClassificationExample("moderate light level", "normal"),
            ClassificationExample("enough light to see", "normal"),
            ClassificationExample("neutral lighting", "normal"),
            ClassificationExample("visibility is good", "normal"),
            ClassificationExample("lighting allows seeing details", "normal"),
            ClassificationExample("comfortable light level", "normal"),
            ClassificationExample("ordinary daylight", "normal"),
            ClassificationExample("standard visibility conditions", "normal"),
            ClassificationExample("average lighting level", "normal"),
            ClassificationExample("acceptable visibility", "normal"),
            
            # MAGICAL - магическое освещение
            ClassificationExample("магический свет пульсирует", "magical"),
            ClassificationExample("заколдованные кристаллы светятся", "magical"),
            ClassificationExample("руны излучают свечение", "magical"),
            ClassificationExample("мистический свет наполняет воздух", "magical"),
            ClassificationExample("волшебное сияние", "magical"),
            ClassificationExample("аркано светящиеся символы", "magical"),
            ClassificationExample("энергия света танцует в воздухе", "magical"),
            ClassificationExample("сверхъестественное освещение", "magical"),
            ClassificationExample("духовный свет", "magical"),
            ClassificationExample("божественное сияние", "magical"),
            
            # English magical conditions
            ClassificationExample("magical light pulses", "magical"),
            ClassificationExample("enchanted crystals glow", "magical"),
            ClassificationExample("runes emit radiance", "magical"),
            ClassificationExample("mystical light fills the air", "magical"),
            ClassificationExample("magical radiance", "magical"),
            ClassificationExample("arcane glowing symbols", "magical"),
            ClassificationExample("energy light dances in air", "magical"),
            ClassificationExample("supernatural illumination", "magical"),
            ClassificationExample("spiritual light", "magical"),
            ClassificationExample("divine radiance", "magical"),
        ]
"""
Training data for Content Quality Analysis Classification
"""

from dataclasses import dataclass
from typing import List
from infrastructure.command_classification_service import ClassificationExample

@dataclass
class ContentQualityTrainingData:
    """Content quality analysis training examples"""
    
    @staticmethod
    def get_examples() -> List[ClassificationExample]:
        return [
            # === HIGH QUALITY - высококачественный контент ===
            
            # Rich storytelling and immersive descriptions
            ClassificationExample("The ancient oak door creaks open, revealing a chamber filled with swirling mists and the faint scent of forgotten magic", "high_quality"),
            ClassificationExample("Дракон медленно поворачивает свою массивную голову, его золотые глаза изучают вас с древней мудростью", "high_quality"),
            ClassificationExample("The tavern keeper's weathered hands shake as he pours the ale, memories of old battles flickering in his tired eyes", "high_quality"),
            ClassificationExample("Волшебник шепчет заклинание, и воздух вокруг него начинает мерцать серебристыми искрами", "high_quality"),
            
            # Detailed character development and emotions
            ClassificationExample("Sir Gareth's voice trembles with barely contained rage as he recounts the destruction of his homeland", "high_quality"),
            ClassificationExample("Эльфийская принцесса изящно кланяется, но в её изумрудных глазах читается глубокая печаль", "high_quality"),
            ClassificationExample("The old sage closes the tome with reverence, dust motes dancing in the candlelight around his wrinkled features", "high_quality"),
            ClassificationExample("Торговец нервно теребит свою бороду, взвешивая риски предложенной сделки", "high_quality"),
            
            # Complex world-building and atmosphere
            ClassificationExample("The city's clockwork mechanisms tick in perfect harmony, steam rising from countless copper pipes that snake between buildings", "high_quality"),
            ClassificationExample("В глубинах подземелья слышится эхо капающей воды и далёкие стоны неупокоенных духов", "high_quality"),
            ClassificationExample("Magical runes pulse with ethereal light along the temple walls, each symbol telling a story of divine intervention", "high_quality"),
            ClassificationExample("Лунный свет проникает сквозь витражи, окрашивая мраморный пол собора в радужные оттенки", "high_quality"),
            
            # Engaging dialogue and character interactions
            ClassificationExample("'The path ahead is treacherous,' warns the ranger, his scarred hand gesturing toward the mist-shrouded mountains", "high_quality"),
            ClassificationExample("'Не стоит будить спящего дракона,' - мудро замечает старый гном, постукивая своим посохом", "high_quality"),
            ClassificationExample("The queen's advisor leans close, whispering urgent secrets that could change the fate of the kingdom", "high_quality"),
            ClassificationExample("Бард настраивает лютню и начинает рассказывать легенду о героях прошлого", "high_quality"),
            
            # Rich sensory details and immersion
            ClassificationExample("The forge burns hot, filling the air with the acrid smell of molten metal and the rhythmic hammering of the smith", "high_quality"),
            ClassificationExample("Аромат свежеиспечённого хлеба смешивается с запахом трав и специй на рыночной площади", "high_quality"),
            ClassificationExample("Thunder rolls across the battlefield as lightning illuminates the clash of steel and the cries of warriors", "high_quality"),
            ClassificationExample("Морской бриз приносит запах соли и водорослей, чайки кричат над пристанью", "high_quality"),
            
            # === MEDIUM QUALITY - среднее качество ===
            
            # Basic but functional descriptions
            ClassificationExample("The room is large with stone walls and several torches for lighting", "medium_quality"),
            ClassificationExample("Комната большая с каменными стенами и факелами", "medium_quality"),
            ClassificationExample("You see a merchant selling various items at his stall", "medium_quality"),
            ClassificationExample("Торговец продаёт разные товары в своей лавке", "medium_quality"),
            
            # Simple character interactions
            ClassificationExample("The guard asks to see your identification papers", "medium_quality"),
            ClassificationExample("Стражник просит показать документы", "medium_quality"),
            ClassificationExample("The innkeeper offers you a room for the night", "medium_quality"),
            ClassificationExample("Трактирщик предлагает комнату на ночь", "medium_quality"),
            
            # Straightforward narrative
            ClassificationExample("You enter the dungeon and see a long corridor ahead", "medium_quality"),
            ClassificationExample("Вы входите в подземелье и видите длинный коридор", "medium_quality"),
            ClassificationExample("The battle begins as enemies approach your position", "medium_quality"),
            ClassificationExample("Битва начинается, враги приближаются", "medium_quality"),
            
            # Adequate but unremarkable content
            ClassificationExample("The wizard casts a spell and damage is dealt to the target", "medium_quality"),
            ClassificationExample("Волшебник произносит заклинание и наносит урон", "medium_quality"),
            ClassificationExample("You successfully pick the lock and open the chest", "medium_quality"),
            ClassificationExample("Вы успешно взламываете замок и открываете сундук", "medium_quality"),
            
            # === LOW QUALITY - низкое качество ===
            
            # Generic and uninspired content
            ClassificationExample("You go to the place and do the thing", "low_quality"),
            ClassificationExample("Идёшь туда и делаешь это", "low_quality"),
            ClassificationExample("Something happens and then you continue", "low_quality"),
            ClassificationExample("Что-то происходит и ты продолжаешь", "low_quality"),
            
            # Repetitive or lazy descriptions
            ClassificationExample("You see a room. It has stuff in it. You can interact with the stuff.", "low_quality"),
            ClassificationExample("Видишь комнату. Там есть вещи. Можешь взаимодействовать с вещами.", "low_quality"),
            ClassificationExample("The NPC says words to you about the quest thing", "low_quality"),
            ClassificationExample("НПС говорит слова про квест", "low_quality"),
            
            # Confusing or poorly structured content
            ClassificationExample("And then the but however maybe sword fight dragon possibly", "low_quality"),
            ClassificationExample("А потом но однако может меч драться дракон возможно", "low_quality"),
            ClassificationExample("Error: content not found, please try again later", "low_quality"),
            ClassificationExample("Ошибка: контент не найден, попробуйте позже", "low_quality"),
            
            # Inappropriate or off-topic content
            ClassificationExample("I can't help with that request as it violates content policy", "low_quality"),
            ClassificationExample("Не могу помочь с этим запросом из-за политики контента", "low_quality"),
            ClassificationExample("Sorry, I don't understand what you're asking for", "low_quality"),
            ClassificationExample("Извините, не понимаю о чём вы спрашиваете", "low_quality"),
            
            # Broken or nonsensical responses
            ClassificationExample("The character does undefined behavior with null reference exception", "low_quality"),
            ClassificationExample("Персонаж делает неопределённое поведение с исключением", "low_quality"),
            ClassificationExample("Lorem ipsum dolor sit amet consectetur adipiscing", "low_quality"),
            ClassificationExample("Текст-рыба для заполнения пустого места", "low_quality"),
            
            # === EXCELLENT QUALITY - превосходное качество ===
            
            # Masterful storytelling with deep immersion
            ClassificationExample("As the last note of the bard's lament fades into the smoky tavern air, even the most hardened warriors find tears glistening in their eyes, remembering fallen comrades and battles long past", "excellent_quality"),
            ClassificationExample("Когда последняя нота песни барда растворяется в дымном воздухе таверны, даже самые закалённые воины чувствуют, как слёзы наворачиваются на глаза при воспоминании о павших товарищах", "excellent_quality"),
            
            # Profound character development and psychology
            ClassificationExample("The necromancer's hands tremble not from fear, but from the weight of a thousand souls he's bound to his will, each whisper of the dead a reminder of the humanity he sacrificed for power", "excellent_quality"),
            ClassificationExample("Руки некроманта дрожат не от страха, а от тяжести тысячи душ, связанных его волей, каждый шёпот мёртвых напоминает о человечности, принесённой в жертву ради силы", "excellent_quality"),
            
            # Breathtaking world-building and atmosphere
            ClassificationExample("The floating city of Aethermoor drifts through clouds of crystallized starlight, its gossamer bridges singing in harmonies that mortal ears can barely comprehend, while below, the world turns in blissful ignorance of the celestial ballet above", "excellent_quality"),
            ClassificationExample("Парящий город Эфирмор дрейфует сквозь облака кристаллизованного звёздного света, его паутинные мосты поют в гармониях, которые смертные уши едва способны постичь", "excellent_quality"),
            
            # Emotionally resonant and memorable moments
            ClassificationExample("In that moment, as the dragon's ancient eyes meet yours, you understand that this is not just a beast to be slain, but a keeper of memories older than kingdoms, a living library of forgotten wisdom", "excellent_quality"),
            ClassificationExample("В этот миг, когда древние глаза дракона встречаются с вашими, вы понимаете, что это не просто зверь для убийства, а хранитель памяти старше королевств, живая библиотека забытой мудрости", "excellent_quality"),
        ]
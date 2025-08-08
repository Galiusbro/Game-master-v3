"""
Training data for Entity State Detection Classification
"""

from dataclasses import dataclass
from typing import List
from infrastructure.command_classification_service import ClassificationExample

@dataclass
class EntityStateTrainingData:
    """Entity state detection training examples"""
    
    @staticmethod
    def get_examples() -> List[ClassificationExample]:
        return [
            # === DEAD/DECEASED - мёртвые состояния ===
            
            # Direct death descriptions
            ClassificationExample("The lifeless body of the innkeeper lies motionless on the floor", "dead"),
            ClassificationExample("Безжизненное тело трактирщика неподвижно лежит на полу", "dead"),
            ClassificationExample("His eyes are closed forever, no breath escapes his lips", "dead"),
            ClassificationExample("Его глаза закрыты навсегда, дыхание не покидает губ", "dead"),
            ClassificationExample("The warrior has fallen, never to rise again", "dead"),
            ClassificationExample("Воин пал и больше никогда не поднимется", "dead"),
            
            # Cold and stillness descriptions
            ClassificationExample("Cold flesh, no warmth of life remains", "dead"),
            ClassificationExample("Холодная плоть, тепло жизни не осталось", "dead"),
            ClassificationExample("The body lies in eternal stillness", "dead"),
            ClassificationExample("Тело покоится в вечной неподвижности", "dead"),
            ClassificationExample("No pulse beats in the silent chest", "dead"),
            ClassificationExample("Пульс не бьётся в безмолвной груди", "dead"),
            
            # Death-related states and conditions
            ClassificationExample("The merchant's corpse shows signs of recent violence", "dead"),
            ClassificationExample("Труп торговца показывает следы недавнего насилия", "dead"),
            ClassificationExample("Blood pools around the motionless figure", "dead"),
            ClassificationExample("Кровь собирается вокруг неподвижной фигуры", "dead"),
            ClassificationExample("The guard will never speak again", "dead"),
            ClassificationExample("Стражник никогда больше не заговорит", "dead"),
            
            # Spiritual departure descriptions
            ClassificationExample("His spirit has departed this mortal realm", "dead"),
            ClassificationExample("Его дух покинул этот смертный мир", "dead"),
            ClassificationExample("Life has fled from this broken shell", "dead"),
            ClassificationExample("Жизнь покинула эту разбитую оболочку", "dead"),
            ClassificationExample("The soul no longer inhabits this vessel", "dead"),
            ClassificationExample("Душа больше не обитает в этом сосуде", "dead"),
            
            # Decomposition and decay
            ClassificationExample("The body shows signs of decay and decomposition", "dead"),
            ClassificationExample("Тело показывает признаки разложения и распада", "dead"),
            ClassificationExample("Pale skin has taken on a deathly pallor", "dead"),
            ClassificationExample("Бледная кожа приобрела смертную бледность", "dead"),
            ClassificationExample("Rigor mortis has set into the limbs", "dead"),
            ClassificationExample("Трупное окоченение охватило конечности", "dead"),
            
            # Complete cessation of all processes - CLEAR dead markers
            ClassificationExample("No breath, no pulse, no movement - completely dead", "dead"),
            ClassificationExample("Нет дыхания, нет пульса, нет движения - полностью мёртв", "dead"),
            ClassificationExample("All vital functions have permanently ceased", "dead"),
            ClassificationExample("Все жизненные функции навсегда прекратились", "dead"),
            ClassificationExample("The body lies in absolute stillness, devoid of life", "dead"),
            ClassificationExample("Тело лежит в абсолютной неподвижности, лишённое жизни", "dead"),
            ClassificationExample("Death has already claimed this vessel completely", "dead"),
            ClassificationExample("Смерть уже полностью забрала этот сосуд", "dead"),
            
            # === ALIVE/LIVING - живые состояния ===
            
            # Active life signs
            ClassificationExample("The innkeeper greets you with a warm smile and bright eyes", "alive"),
            ClassificationExample("Трактирщик приветствует вас тёплой улыбкой и яркими глазами", "alive"),
            ClassificationExample("His chest rises and falls with steady breathing", "alive"),
            ClassificationExample("Его грудь поднимается и опускается в ровном дыхании", "alive"),
            ClassificationExample("The merchant's heart beats strong and steady", "alive"),
            ClassificationExample("Сердце торговца бьётся сильно и ровно", "alive"),
            
            # Movement and activity
            ClassificationExample("She walks with confident strides across the room", "alive"),
            ClassificationExample("Она идёт уверенными шагами через комнату", "alive"),
            ClassificationExample("The guard patrols his post with vigilant attention", "alive"),
            ClassificationExample("Стражник патрулирует свой пост с бдительным вниманием", "alive"),
            ClassificationExample("His hands gesture expressively as he speaks", "alive"),
            ClassificationExample("Его руки выразительно жестикулируют, когда он говорит", "alive"),
            
            # Consciousness and awareness
            ClassificationExample("Alert eyes scan the surroundings with intelligence", "alive"),
            ClassificationExample("Внимательные глаза сканируют окружение с пониманием", "alive"),
            ClassificationExample("The wizard responds thoughtfully to your questions", "alive"),
            ClassificationExample("Волшебник вдумчиво отвечает на ваши вопросы", "alive"),
            ClassificationExample("She laughs heartily at the bard's joke", "alive"),
            ClassificationExample("Она от души смеётся над шуткой барда", "alive"),
            
            # Warmth and vitality
            ClassificationExample("Warm breath mists in the cold air", "alive"),
            ClassificationExample("Тёплое дыхание туманится на холодном воздухе", "alive"),
            ClassificationExample("Color fills his cheeks with healthy vitality", "alive"),
            ClassificationExample("Цвет наполняет его щёки здоровой жизненностью", "alive"),
            ClassificationExample("The pulse throbs visibly in her neck", "alive"),
            ClassificationExample("Пульс заметно пульсирует на её шее", "alive"),
            
            # Speech and communication
            ClassificationExample("The bard sings with passion and energy", "alive"),
            ClassificationExample("Бард поёт со страстью и энергией", "alive"),
            ClassificationExample("His voice carries warmth and emotion", "alive"),
            ClassificationExample("Его голос несёт тепло и эмоции", "alive"),
            ClassificationExample("She whispers secrets with conspiratorial delight", "alive"),
            ClassificationExample("Она шепчет секреты с заговорщицким восторгом", "alive"),
            
            # === UNCONSCIOUS - без сознания ===
            
            # Temporary unconsciousness
            ClassificationExample("The warrior lies unconscious but breathing steadily", "unconscious"),
            ClassificationExample("Воин лежит без сознания, но дышит ровно", "unconscious"),
            ClassificationExample("She has fainted but her pulse remains strong", "unconscious"),
            ClassificationExample("Она упала в обморок, но пульс остаётся сильным", "unconscious"),
            ClassificationExample("Knocked out cold, but still very much alive", "unconscious"),
            ClassificationExample("Вырублен наглухо, но всё ещё жив", "unconscious"),
            
            # Sleep states
            ClassificationExample("The guard sleeps peacefully at his post", "unconscious"),
            ClassificationExample("Стражник мирно спит на своём посту", "unconscious"),
            ClassificationExample("Deep in slumber, chest rising and falling rhythmically", "unconscious"),
            ClassificationExample("Глубоко спит, грудь поднимается и опускается ритмично", "unconscious"),
            ClassificationExample("Dreams play across his sleeping features", "unconscious"),
            ClassificationExample("Сны играют на его спящих чертах", "unconscious"),
            
            # Magical unconsciousness
            ClassificationExample("Held in magical stasis, alive but unaware", "unconscious"),
            ClassificationExample("Находится в магическом стазисе, жив но без сознания", "unconscious"),
            ClassificationExample("The enchantment keeps her in deep sleep", "unconscious"),
            ClassificationExample("Заклятие держит её в глубоком сне", "unconscious"),
            ClassificationExample("Paralyzed by magic but fully conscious inside", "unconscious"),
            ClassificationExample("Парализован магией, но внутри полностью в сознании", "unconscious"),
            
            # Knocked out but alive - CRITICAL for fixing error
            ClassificationExample("Knocked out from the heavy blow but clearly still living", "unconscious"),
            ClassificationExample("Вырублен тяжёлым ударом, но явно ещё жив", "unconscious"),
            ClassificationExample("Unconscious from the impact but breathing steadily", "unconscious"),
            ClassificationExample("Без сознания от удара, но дышит ровно", "unconscious"),
            ClassificationExample("Knocked unconscious but vital signs remain strong", "unconscious"),
            ClassificationExample("Потерял сознание, но жизненные показатели сильные", "unconscious"),
            ClassificationExample("Out cold but definitely alive and breathing", "unconscious"),
            ClassificationExample("Отключился, но определённо жив и дышит", "unconscious"),
            ClassificationExample("Stunned unconscious but pulse beats normally", "unconscious"),
            ClassificationExample("Оглушён до бесчувствия, но пульс бьётся нормально", "unconscious"),
            
            # === DYING - умирающие состояния ===
            
            # Final moments
            ClassificationExample("Drawing his last labored breaths", "dying"),
            ClassificationExample("Делает последние тяжёлые вдохи", "dying"),
            ClassificationExample("Life ebbs away like sand through fingers", "dying"),
            ClassificationExample("Жизнь утекает как песок сквозь пальцы", "dying"),
            ClassificationExample("The light fades slowly from her eyes", "dying"),
            ClassificationExample("Свет медленно угасает в её глазах", "dying"),
            
            # Critical injuries
            ClassificationExample("Bleeding heavily, consciousness slipping away", "dying"),
            ClassificationExample("Сильно кровоточит, сознание ускользает", "dying"),
            ClassificationExample("Mortally wounded, time running short", "dying"),
            ClassificationExample("Смертельно ранен, время на исходе", "dying"),
            ClassificationExample("The poison courses through his weakening body", "dying"),
            ClassificationExample("Яд течёт по его слабеющему телу", "dying"),
            
            # Poison and disease processes - CRITICAL for fixing error  
            ClassificationExample("The poison spreads rapidly through his weakening system", "dying"),
            ClassificationExample("Яд быстро распространяется по его слабеющему организму", "dying"),
            ClassificationExample("Toxins course through her failing body", "dying"),
            ClassificationExample("Токсины текут по её отказывающему телу", "dying"),
            ClassificationExample("Disease ravages his weakening constitution", "dying"),
            ClassificationExample("Болезнь разрушает его слабеющее здоровье", "dying"),
            ClassificationExample("Venom works its deadly way through his system", "dying"),
            ClassificationExample("Яд прокладывает смертельный путь по его организму", "dying"),
            
            # Active dying processes
            ClassificationExample("Strength ebbs away with each labored breath", "dying"),
            ClassificationExample("Силы утекают с каждым тяжёлым вдохом", "dying"),
            ClassificationExample("Life force drains steadily from the wounded body", "dying"),
            ClassificationExample("Жизненная сила неуклонно покидает раненое тело", "dying"),
            ClassificationExample("Vitality fades as the wounds take their toll", "dying"),
            ClassificationExample("Жизненность угасает, раны берут своё", "dying"),
            
            # Transition states
            ClassificationExample("Hovering between life and death", "dying"),
            ClassificationExample("Балансирует между жизнью и смертью", "dying"),
            ClassificationExample("Fighting desperately to cling to life", "dying"),
            ClassificationExample("Отчаянно борется, цепляясь за жизнь", "dying"),
            ClassificationExample("The soul prepares to depart", "dying"),
            ClassificationExample("Душа готовится к отбытию", "dying"),
            
            # Clear distinction from dead - still has processes
            ClassificationExample("Though dying, he still struggles against fate", "dying"),
            ClassificationExample("Хотя умирает, он всё ещё борется с судьбой", "dying"),
            ClassificationExample("Death approaches but has not yet claimed him", "dying"),
            ClassificationExample("Смерть приближается, но ещё не забрала его", "dying"),
        ]
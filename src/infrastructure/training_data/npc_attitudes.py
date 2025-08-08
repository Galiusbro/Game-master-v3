"""
Training data for NPC Attitude Detection Classification
"""

from dataclasses import dataclass
from typing import List
from infrastructure.command_classification_service import ClassificationExample

@dataclass
class NPCAttitudeTrainingData:
    """NPC attitude classification training examples"""
    
    @staticmethod
    def get_examples() -> List[ClassificationExample]:
        return [
            # === FRIENDLY - дружелюбные NPC ===
            
            # Warm greetings and welcomes
            ClassificationExample("The innkeeper greets you with a warm smile and open arms", "friendly"),
            ClassificationExample("Трактирщик приветствует вас тёплой улыбкой и распростёртыми объятиями", "friendly"),
            ClassificationExample("She waves enthusiastically as you approach", "friendly"),
            ClassificationExample("Она энергично машет рукой, когда вы приближаетесь", "friendly"),
            ClassificationExample("His face lights up with genuine joy upon seeing you", "friendly"),
            ClassificationExample("Его лицо озаряется искренней радостью при виде вас", "friendly"),
            
            # Helpful behavior
            ClassificationExample("The merchant eagerly shows you his finest wares", "friendly"),
            ClassificationExample("Торговец с энтузиазмом показывает вам свои лучшие товары", "friendly"),
            ClassificationExample("She offers helpful advice with a kind expression", "friendly"),
            ClassificationExample("Она предлагает полезный совет с добрым выражением лица", "friendly"),
            ClassificationExample("The guard provides directions with a cheerful disposition", "friendly"),
            ClassificationExample("Стражник даёт направления с весёлым расположением духа", "friendly"),
            
            # Positive body language
            ClassificationExample("He leans forward with interest, eyes sparkling", "friendly"),
            ClassificationExample("Он наклоняется вперёд с интересом, глаза искрятся", "friendly"),
            ClassificationExample("Her posture is open and welcoming", "friendly"),
            ClassificationExample("Её поза открыта и приветлива", "friendly"),
            ClassificationExample("The baker hums happily while working", "friendly"),
            ClassificationExample("Пекарь весело напевает во время работы", "friendly"),
            
            # === NEUTRAL - нейтральные NPC ===
            
            # Professional interactions
            ClassificationExample("The clerk processes your request with quiet efficiency", "neutral"),
            ClassificationExample("Клерк обрабатывает ваш запрос с тихой эффективностью", "neutral"),
            ClassificationExample("She acknowledges your presence with a polite nod", "neutral"),
            ClassificationExample("Она признаёт ваше присутствие вежливым кивком", "neutral"),
            ClassificationExample("The official reviews your documents without comment", "neutral"),
            ClassificationExample("Чиновник просматривает ваши документы без комментариев", "neutral"),
            
            # Calm and composed - УСИЛЕННЫЕ примеры нейтральности
            ClassificationExample("His expression remains calm and unreadable", "neutral"),
            ClassificationExample("Его выражение остаётся спокойным и нечитаемым", "neutral"),
            ClassificationExample("She maintains professional distance", "neutral"),
            ClassificationExample("Она соблюдает профессиональную дистанцию", "neutral"),
            ClassificationExample("The guard stands at attention, neither welcoming nor hostile", "neutral"),
            ClassificationExample("Стражник стоит по стойке смирно, ни приветливо, ни враждебно", "neutral"),
            ClassificationExample("The merchant calculates with cold professional efficiency", "neutral"),
            ClassificationExample("Торговец рассчитывает с холодной профессиональной эффективностью", "neutral"),
            ClassificationExample("He acknowledges you with a brief, respectful nod", "neutral"),
            ClassificationExample("Он признаёт вас кратким, уважительным кивком", "neutral"),
            ClassificationExample("The warrior shows respect but maintains battle readiness", "neutral"),
            ClassificationExample("Воин проявляет уважение, но сохраняет боевую готовность", "neutral"),
            ClassificationExample("The soldier respects your skill while staying alert", "neutral"),
            ClassificationExample("Солдат уважает ваше мастерство, оставаясь начеку", "neutral"),
            ClassificationExample("He acknowledges your ability but remains professionally ready", "neutral"),
            ClassificationExample("Он признаёт ваши способности, но остаётся профессионально готовым", "neutral"),
            
            # Indifferent behavior
            ClassificationExample("He continues his work, barely glancing in your direction", "neutral"),
            ClassificationExample("Он продолжает работу, едва взглянув в вашу сторону", "neutral"),
            ClassificationExample("The shopkeeper waits patiently for your decision", "neutral"),
            ClassificationExample("Лавочник терпеливо ждёт вашего решения", "neutral"),
            ClassificationExample("Her tone is matter-of-fact and businesslike", "neutral"),
            ClassificationExample("Её тон деловой и по существу", "neutral"),
            
            # === HOSTILE - враждебные NPC ===
            
            # Aggressive behavior
            ClassificationExample("The bandit snarls and reaches for his weapon", "hostile"),
            ClassificationExample("Бандит рычит и тянется к оружию", "hostile"),
            ClassificationExample("She glares at you with undisguised hatred", "hostile"),
            ClassificationExample("Она смотрит на вас с неприкрытой ненавистью", "hostile"),
            ClassificationExample("His hand moves threateningly to his sword hilt", "hostile"),
            ClassificationExample("Его рука угрожающе движется к рукояти меча", "hostile"),
            
            # Verbal aggression
            ClassificationExample("The orc growls menacing threats in your direction", "hostile"),
            ClassificationExample("Орк рычит угрожающие угрозы в вашу сторону", "hostile"),
            ClassificationExample("She spits curses and insults at your approach", "hostile"),
            ClassificationExample("Она плюётся проклятиями и оскорблениями при вашем приближении", "hostile"),
            ClassificationExample("His voice drips with venom and malice", "hostile"),
            ClassificationExample("Его голос сочится ядом и злобой", "hostile"),
            
            # Combat readiness - РАЗЛИЧИЕ от angry
            ClassificationExample("The warrior assumes a fighting stance", "hostile"),
            ClassificationExample("Воин принимает боевую стойку", "hostile"),
            ClassificationExample("She draws her blade with murderous intent", "hostile"),
            ClassificationExample("Она вытаскивает клинок с убийственными намерениями", "hostile"),
            ClassificationExample("The enemy prepares to attack without warning", "hostile"),
            ClassificationExample("Враг готовится атаковать без предупреждения", "hostile"),
            ClassificationExample("Cold hatred burns in his eyes as he reaches for steel", "hostile"),
            ClassificationExample("Холодная ненависть горит в его глазах, когда он тянется к стали", "hostile"),
            ClassificationExample("She prepares to strike with calculated malice", "hostile"),
            ClassificationExample("Она готовится нанести удар с расчётливой злобой", "hostile"),
            
            # === SUSPICIOUS - подозрительные NPC ===
            
            # Wary behavior
            ClassificationExample("The merchant eyes you warily, hand near his coin purse", "suspicious"),
            ClassificationExample("Торговец настороженно смотрит на вас, рука возле кошелька", "suspicious"),
            ClassificationExample("She watches your every move with careful attention", "suspicious"),
            ClassificationExample("Она следит за каждым вашим движением с осторожным вниманием", "suspicious"),
            ClassificationExample("His gaze follows you suspiciously around the room", "suspicious"),
            ClassificationExample("Его взгляд подозрительно следует за вами по комнате", "suspicious"),
            
            # Guarded responses
            ClassificationExample("The informant speaks in hushed, cautious tones", "suspicious"),
            ClassificationExample("Информатор говорит приглушённым, осторожным тоном", "suspicious"),
            ClassificationExample("She answers your questions with obvious reluctance", "suspicious"),
            ClassificationExample("Она отвечает на ваши вопросы с явной неохотой", "suspicious"),
            ClassificationExample("He keeps glancing toward the exits nervously", "suspicious"),
            ClassificationExample("Он нервно поглядывает на выходы", "suspicious"),
            
            # Defensive posture - УСИЛЕННЫЕ примеры с оружием
            ClassificationExample("The stranger maintains a defensive posture", "suspicious"),
            ClassificationExample("Незнакомец сохраняет оборонительную позу", "suspicious"),
            ClassificationExample("Her arms are crossed, creating a barrier", "suspicious"),
            ClassificationExample("Её руки скрещены, создавая барьер", "suspicious"),
            ClassificationExample("He steps back slightly, increasing distance", "suspicious"),
            ClassificationExample("Он слегка отступает, увеличивая дистанцию", "suspicious"),
            ClassificationExample("The fence keeps one hand near his weapon while talking cautiously", "suspicious"),
            ClassificationExample("Скупщик держит одну руку возле оружия, осторожно разговаривая", "suspicious"),
            ClassificationExample("She rests her hand on her dagger hilt, watching warily", "suspicious"),
            ClassificationExample("Она кладёт руку на рукоять кинжала, настороженно наблюдая", "suspicious"),
            ClassificationExample("The rogue keeps his hand on his weapon hilt defensively", "suspicious"),
            ClassificationExample("Плут держит руку на рукояти оружия для защиты", "suspicious"),
            ClassificationExample("She touches her blade handle while speaking cautiously", "suspicious"),
            ClassificationExample("Она касается рукояти клинка, осторожно разговаривая", "suspicious"),
            ClassificationExample("The guard rests his hand on his sword pommel while watching", "suspicious"),
            ClassificationExample("Стражник кладёт руку на навершие меча, наблюдая", "suspicious"),
            ClassificationExample("She keeps her fingers near her weapon, ready but not threatening", "suspicious"),
            ClassificationExample("Она держит пальцы возле оружия, готовая, но не угрожая", "suspicious"),
            
            # === HELPFUL - готовые помочь NPC ===
            
            # Eager assistance
            ClassificationExample("The guide offers detailed directions and useful tips", "helpful"),
            ClassificationExample("Проводник предлагает подробные направления и полезные советы", "helpful"),
            ClassificationExample("She provides valuable information without being asked", "helpful"),
            ClassificationExample("Она предоставляет ценную информацию, не дожидаясь просьбы", "helpful"),
            ClassificationExample("The sage shares his knowledge freely and generously", "helpful"),
            ClassificationExample("Мудрец свободно и щедро делится своими знаниями", "helpful"),
            
            # Proactive support - УСИЛЕННЫЕ примеры помощи
            ClassificationExample("He anticipates your needs and offers solutions", "helpful"),
            ClassificationExample("Он предвидит ваши потребности и предлагает решения", "helpful"),
            ClassificationExample("The healer tends to your wounds with caring expertise", "helpful"),
            ClassificationExample("Целитель заботливо лечит ваши раны с экспертностью", "helpful"),
            ClassificationExample("She goes out of her way to assist your quest", "helpful"),
            ClassificationExample("Она прилагает особые усилия, чтобы помочь вашему квесту", "helpful"),
            ClassificationExample("The guide volunteers to lead you through dangerous territory", "helpful"),
            ClassificationExample("Проводник вызывается провести вас через опасную территорию", "helpful"),
            ClassificationExample("Despite nervousness, she provides crucial information willingly", "helpful"),
            ClassificationExample("Несмотря на нервозность, она охотно предоставляет важную информацию", "helpful"),
            ClassificationExample("The informant offers vital details despite obvious anxiety", "helpful"),
            ClassificationExample("Информатор предлагает важные детали, несмотря на очевидное беспокойство", "helpful"),
            ClassificationExample("Though nervous, he volunteers to guide you safely", "helpful"),
            ClassificationExample("Хотя нервничает, он вызывается безопасно провести вас", "helpful"),
            ClassificationExample("She shares critical knowledge while trembling with fear", "helpful"),
            ClassificationExample("Она делится важными знаниями, дрожа от страха", "helpful"),
            ClassificationExample("The escort volunteers to lead you through perilous paths", "helpful"),
            ClassificationExample("Эскорт вызывается провести вас по опасным тропам", "helpful"),
            ClassificationExample("He offers to guide you despite the obvious dangers", "helpful"),
            ClassificationExample("Он предлагает провести вас, несмотря на очевидные опасности", "helpful"),
            ClassificationExample("The pathfinder volunteers to escort you through hostile territory", "helpful"),
            ClassificationExample("Следопыт вызывается сопроводить вас через враждебную территорию", "helpful"),
            ClassificationExample("She offers to lead you safely through the dangerous region", "helpful"),
            ClassificationExample("Она предлагает безопасно провести вас через опасный регион", "helpful"),
            
            # Generous nature
            ClassificationExample("The benefactor offers resources without expecting payment", "helpful"),
            ClassificationExample("Благотворитель предлагает ресурсы, не ожидая оплаты", "helpful"),
            ClassificationExample("He shares his supplies willingly", "helpful"),
            ClassificationExample("Он охотно делится своими припасами", "helpful"),
            ClassificationExample("The ally provides crucial support in times of need", "helpful"),
            ClassificationExample("Союзник оказывает решающую поддержку в трудные времена", "helpful"),
            
            # === ANGRY - разгневанные NPC ===
            
            # Visible rage
            ClassificationExample("The lord's face turns red with indignation", "angry"),
            ClassificationExample("Лицо лорда краснеет от негодования", "angry"),
            ClassificationExample("She clenches her fists, trembling with fury", "angry"),
            ClassificationExample("Она сжимает кулаки, дрожа от ярости", "angry"),
            ClassificationExample("His eyes blaze with righteous anger", "angry"),
            ClassificationExample("Его глаза пылают праведным гневом", "angry"),
            
            # Raised voice and shouting
            ClassificationExample("The captain shouts orders with barely contained rage", "angry"),
            ClassificationExample("Капитан кричит приказы с едва сдерживаемой яростью", "angry"),
            ClassificationExample("She raises her voice in furious protest", "angry"),
            ClassificationExample("Она повышает голос в яростном протесте", "angry"),
            ClassificationExample("His words come out in an angry torrent", "angry"),
            ClassificationExample("Его слова льются гневным потоком", "angry"),
            
            # Aggressive gestures
            ClassificationExample("The noble pounds his fist on the table", "angry"),
            ClassificationExample("Дворянин ударяет кулаком по столу", "angry"),
            ClassificationExample("She points an accusing finger with violent emphasis", "angry"),
            ClassificationExample("Она указывает обвиняющим пальцем с яростным акцентом", "angry"),
            ClassificationExample("He storms around the room in a fit of rage", "angry"),
            ClassificationExample("Он мечется по комнате в приступе ярости", "angry"),
            
            # === FEARFUL - испуганные NPC ===
            
            # Physical signs of fear
            ClassificationExample("The peasant trembles visibly in your presence", "fearful"),
            ClassificationExample("Крестьянин заметно дрожит в вашем присутствии", "fearful"),
            ClassificationExample("Her voice shakes with terror", "fearful"),
            ClassificationExample("Её голос дрожит от ужаса", "fearful"),
            ClassificationExample("His eyes dart around frantically, seeking escape", "fearful"),
            ClassificationExample("Его глаза беспокойно бегают, ища выход", "fearful"),
            
            # Cowering behavior
            ClassificationExample("The servant cowers and backs away slowly", "fearful"),
            ClassificationExample("Слуга съёживается и медленно отступает", "fearful"),
            ClassificationExample("She hunches her shoulders defensively", "fearful"),
            ClassificationExample("Она оборонительно поднимает плечи", "fearful"),
            ClassificationExample("He pleads for mercy with tears in his eyes", "fearful"),
            ClassificationExample("Он умоляет о пощаде со слезами в глазах", "fearful"),
            
            # Panic responses
            ClassificationExample("The witness speaks in hurried, panicked whispers", "fearful"),
            ClassificationExample("Свидетель говорит торопливым, паническим шёпотом", "fearful"),
            ClassificationExample("She clutches at anything nearby for protection", "fearful"),
            ClassificationExample("Она хватается за всё рядом в поисках защиты", "fearful"),
            ClassificationExample("His breathing becomes rapid and shallow", "fearful"),
            ClassificationExample("Его дыхание становится частым и поверхностным", "fearful"),
        ]
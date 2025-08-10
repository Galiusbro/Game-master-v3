"""
Training data for Entity Type Classification

ВАЖНО: Таверна - это LOCATION (место), не NPC!
"""

from dataclasses import dataclass
from typing import List
from infrastructure.command_classification_service import ClassificationExample
from domain.entities import EntityType

@dataclass
class EntityTypeTrainingData:
    """Entity type classification training examples"""
    
    @staticmethod
    def get_examples() -> List[ClassificationExample]:
        return [
            # === NPCs - ПЕРСОНАЖИ И СУЩЕСТВА ===
            
            # Профессии и роли
            ClassificationExample("трактирщик приветствует гостей", EntityType.NPC.value),
            ClassificationExample("бармен наливает эль", EntityType.NPC.value),
            ClassificationExample("барменша улыбается гостям", EntityType.NPC.value),
            ClassificationExample("трактирщица ведёт счет заказам", EntityType.NPC.value),
            ClassificationExample("хозяин таверны проверяет запасы", EntityType.NPC.value),
            ClassificationExample("хозяйка таверны разговаривает с посетителями", EntityType.NPC.value),
            ClassificationExample("официант приносит эль", EntityType.NPC.value),
            ClassificationExample("официантка убирает стол", EntityType.NPC.value),
            ClassificationExample("буфетчик раскладывает кружки", EntityType.NPC.value),
            ClassificationExample("привратник стоит у двери", EntityType.NPC.value),
            # Морфологические формы (склонения)
            ClassificationExample("барменом доволен клиент", EntityType.NPC.value),
            ClassificationExample("поговорить с барменом", EntityType.NPC.value),
            ClassificationExample("спросить у бармена", EntityType.NPC.value),
            ClassificationExample("подойти к бармену", EntityType.NPC.value),
            ClassificationExample("о бармене ходят слухи", EntityType.NPC.value),
            ClassificationExample("нет бармена на месте", EntityType.NPC.value),
            ClassificationExample("трактирщиком восхищаются", EntityType.NPC.value),
            ClassificationExample("с трактирщиком обсудить заказ", EntityType.NPC.value),
            ClassificationExample("к трактирщику обратиться", EntityType.NPC.value),
            ClassificationExample("у трактирщика спросить цену", EntityType.NPC.value),
            ClassificationExample("о трактирщике хорошие отзывы", EntityType.NPC.value),
            ClassificationExample("нет трактирщика в зале", EntityType.NPC.value),
            ClassificationExample("с официантом поговорить", EntityType.NPC.value),
            ClassificationExample("к официанту подойти", EntityType.NPC.value),
            ClassificationExample("у официанта спросить меню", EntityType.NPC.value),
            ClassificationExample("об официанте шутят", EntityType.NPC.value),
            ClassificationExample("нет официанта поблизости", EntityType.NPC.value),
            # Охрана / guard (русские формы)
            ClassificationExample("охранник стоит на посту", EntityType.NPC.value),
            ClassificationExample("со стражником разговаривают", EntityType.NPC.value),
            ClassificationExample("к охраннику обратиться", EntityType.NPC.value),
            ClassificationExample("у стражника спросить дорогу", EntityType.NPC.value),
            ClassificationExample("о стражнике ходят слухи", EntityType.NPC.value),
            ClassificationExample("нет охранника поблизости", EntityType.NPC.value),
            # English guard variants
            ClassificationExample("guard stands watch", EntityType.NPC.value),
            ClassificationExample("talk to the guard", EntityType.NPC.value),
            ClassificationExample("ask the guard for directions", EntityType.NPC.value),
            ClassificationExample("кузнец кует оружие", EntityType.NPC.value),
            ClassificationExample("торговец показывает товары", EntityType.NPC.value),
            ClassificationExample("стражник патрулирует улицы", EntityType.NPC.value),
            ClassificationExample("маг изучает заклинания", EntityType.NPC.value),
            ClassificationExample("жрец проводит службу", EntityType.NPC.value),
            ClassificationExample("вор крадется в тени", EntityType.NPC.value),
            ClassificationExample("воин точит меч", EntityType.NPC.value),
            ClassificationExample("лучник натягивает тетиву", EntityType.NPC.value),
            
            # Магические существа и персонажи
            ClassificationExample("волшебник кастует заклинание", EntityType.NPC.value),
            ClassificationExample("колдун варит зелье", EntityType.NPC.value),
            ClassificationExample("чародей читает свиток", EntityType.NPC.value),
            ClassificationExample("архимаг открывает портал", EntityType.NPC.value),
            ClassificationExample("некромант поднимает мертвых", EntityType.NPC.value),
            
            # Драконы и крупные существа
            ClassificationExample("дракон рычит на героев", EntityType.NPC.value),
            ClassificationExample("дракон охраняет сокровища", EntityType.NPC.value),
            ClassificationExample("дракон атакует деревню", EntityType.NPC.value),
            ClassificationExample("дракон спит в пещере", EntityType.NPC.value),
            ClassificationExample("древний дракон пробуждается", EntityType.NPC.value),
            ClassificationExample("молодой дракон учится летать", EntityType.NPC.value),
            
            # Монстры и враги
            ClassificationExample("орк размахивает топором", EntityType.NPC.value),
            ClassificationExample("гоблин убегает от света", EntityType.NPC.value),
            ClassificationExample("великан бросает камни", EntityType.NPC.value),
            ClassificationExample("тролль регенерирует раны", EntityType.NPC.value),
            ClassificationExample("скелет скрипит костями", EntityType.NPC.value),
            ClassificationExample("зомби медленно идет", EntityType.NPC.value),
            
            # Расы и народы
            ClassificationExample("эльф поет древнюю песню", EntityType.NPC.value),
            ClassificationExample("гном копает туннель", EntityType.NPC.value),
            ClassificationExample("хоббит готовит ужин", EntityType.NPC.value),
            ClassificationExample("человек идет по дороге", EntityType.NPC.value),
            ClassificationExample("полуорк точит оружие", EntityType.NPC.value),
            
            # English NPCs
            ClassificationExample("bartender serves drinks", EntityType.NPC.value),
            ClassificationExample("innkeeper welcomes guests", EntityType.NPC.value),
            ClassificationExample("blacksmith forges weapons", EntityType.NPC.value),
            ClassificationExample("merchant offers goods", EntityType.NPC.value),
            ClassificationExample("guard patrols the streets", EntityType.NPC.value),
            ClassificationExample("wizard studies spells", EntityType.NPC.value),
            ClassificationExample("priest blesses travelers", EntityType.NPC.value),
            ClassificationExample("dragon breathes fire", EntityType.NPC.value),
            ClassificationExample("orc swings axe", EntityType.NPC.value),
            ClassificationExample("elf sings melodies", EntityType.NPC.value),
            
            # === LOCATIONS - МЕСТА (включая таверны!) ===
            
            # Заведения и постройки - ОЧЕНЬ ВАЖНО!
            ClassificationExample("таверна полна шумных посетителей", EntityType.LOCATION.value),
            ClassificationExample("таверна 'Пьяный дракон' открыта", EntityType.LOCATION.value),
            ClassificationExample("таверна находится в центре города", EntityType.LOCATION.value),
            ClassificationExample("таверна выглядит уютно и тепло", EntityType.LOCATION.value),
            ClassificationExample("старая таверна скрипит досками", EntityType.LOCATION.value),
            ClassificationExample("трактир полон путешественников", EntityType.LOCATION.value),
            ClassificationExample("трактир 'Золотая подкова'", EntityType.LOCATION.value),
            ClassificationExample("трактир расположен у дороги", EntityType.LOCATION.value),
            
            # Другие заведения
            ClassificationExample("кузница дымится от жара", EntityType.LOCATION.value),
            ClassificationExample("магазин открыт для покупателей", EntityType.LOCATION.value),
            ClassificationExample("лавка торговца полна товаров", EntityType.LOCATION.value),
            ClassificationExample("храм освящен богами", EntityType.LOCATION.value),
            ClassificationExample("библиотека хранит древние знания", EntityType.LOCATION.value),
            ClassificationExample("арена готова к боям", EntityType.LOCATION.value),
            
            # Крупные строения
            ClassificationExample("замок возвышается на холме", EntityType.LOCATION.value),
            ClassificationExample("замок окружен рвом", EntityType.LOCATION.value),
            ClassificationExample("крепость защищает границы", EntityType.LOCATION.value),
            ClassificationExample("башня тянется к небу", EntityType.LOCATION.value),
            ClassificationExample("дворец сияет золотом", EntityType.LOCATION.value),
            
            # Жилые постройки
            ClassificationExample("дом стоит у дороги", EntityType.LOCATION.value),
            ClassificationExample("хижина скрыта в лесу", EntityType.LOCATION.value),
            ClassificationExample("хата ведьмы на болоте", EntityType.LOCATION.value),
            ClassificationExample("коттедж покрыт плющом", EntityType.LOCATION.value),
            
            # Поселения
            ClassificationExample("город шумит и суетится", EntityType.LOCATION.value),
            ClassificationExample("деревня спит в лунном свете", EntityType.LOCATION.value),
            ClassificationExample("поселок окружен полями", EntityType.LOCATION.value),
            ClassificationExample("столица империи величественна", EntityType.LOCATION.value),
            
            # Комнаты и внутренние помещения
            ClassificationExample("комната освещена свечами", EntityType.LOCATION.value),
            ClassificationExample("зал эхом отвечает на шаги", EntityType.LOCATION.value),
            ClassificationExample("спальня устлана коврами", EntityType.LOCATION.value),
            ClassificationExample("кухня пахнет специями", EntityType.LOCATION.value),
            ClassificationExample("подвал темен и сыр", EntityType.LOCATION.value),
            ClassificationExample("чердак полон пыли", EntityType.LOCATION.value),
            
            # Улицы и дороги
            ClassificationExample("улица вымощена камнем", EntityType.LOCATION.value),
            ClassificationExample("переулок узок и темен", EntityType.LOCATION.value),
            ClassificationExample("площадь полна торговцев", EntityType.LOCATION.value),
            ClassificationExample("дорога ведет в горы", EntityType.LOCATION.value),
            ClassificationExample("тропа петляет между деревьев", EntityType.LOCATION.value),
            
            # Природные локации
            ClassificationExample("лес шумит листвой", EntityType.LOCATION.value),
            ClassificationExample("поле колышется на ветру", EntityType.LOCATION.value),
            ClassificationExample("гора возвышается над облаками", EntityType.LOCATION.value),
            ClassificationExample("река течет к морю", EntityType.LOCATION.value),
            ClassificationExample("озеро отражает небо", EntityType.LOCATION.value),
            ClassificationExample("пещера уходит в глубину", EntityType.LOCATION.value),
            ClassificationExample("болото затянуто туманом", EntityType.LOCATION.value),
            ClassificationExample("пустыня простирается до горизонта", EntityType.LOCATION.value),
            
            # English Locations
            ClassificationExample("tavern is crowded with adventurers", EntityType.LOCATION.value),
            ClassificationExample("inn looks cozy and warm", EntityType.LOCATION.value),
            ClassificationExample("forge is hot and smoky", EntityType.LOCATION.value),
            ClassificationExample("shop is busy with customers", EntityType.LOCATION.value),
            ClassificationExample("temple glows with divine light", EntityType.LOCATION.value),
            ClassificationExample("castle towers over the valley", EntityType.LOCATION.value),
            ClassificationExample("house stands by the road", EntityType.LOCATION.value),
            ClassificationExample("city bustles with activity", EntityType.LOCATION.value),
            ClassificationExample("village is quiet and peaceful", EntityType.LOCATION.value),
            ClassificationExample("forest whispers ancient secrets", EntityType.LOCATION.value),
            
            # === ITEMS - ПРЕДМЕТЫ И ВЕЩИ ===
            
            # Оружие
            ClassificationExample("меч лежит на столе", EntityType.ITEM.value),
            ClassificationExample("меч остро заточен", EntityType.ITEM.value),
            ClassificationExample("топор тяжел в руках", EntityType.ITEM.value),
            ClassificationExample("кинжал скрыт в ножнах", EntityType.ITEM.value),
            ClassificationExample("лук натянут и готов", EntityType.ITEM.value),
            ClassificationExample("копье направлено на врага", EntityType.ITEM.value),
            ClassificationExample("булава украшена рунами", EntityType.ITEM.value),
            
            # Доспехи и защита
            ClassificationExample("щит блестит в лунном свете", EntityType.ITEM.value),
            ClassificationExample("броня защищает от ударов", EntityType.ITEM.value),
            ClassificationExample("шлем скрывает лицо", EntityType.ITEM.value),
            ClassificationExample("кольчуга звенит при движении", EntityType.ITEM.value),
            
            # Зелья и расходники - ВАЖНО!
            ClassificationExample("зелье исцеления стоит на полке", EntityType.ITEM.value),
            ClassificationExample("зелье булькает в колбе", EntityType.ITEM.value),
            ClassificationExample("лечебное зелье светится", EntityType.ITEM.value),
            ClassificationExample("магическое зелье дымится", EntityType.ITEM.value),
            ClassificationExample("зелье яда темно-зеленое", EntityType.ITEM.value),
            ClassificationExample("зелье маны переливается синим", EntityType.ITEM.value),
            ClassificationExample("эликсир силы бурлит в бутылке", EntityType.ITEM.value),
            
            # Магические предметы
            ClassificationExample("свиток древних знаний", EntityType.ITEM.value),
            ClassificationExample("кольцо силы сверкает", EntityType.ITEM.value),
            ClassificationExample("амулет защиты светится", EntityType.ITEM.value),
            ClassificationExample("посох мага украшен кристаллом", EntityType.ITEM.value),
            ClassificationExample("жезл волшебника", EntityType.ITEM.value),
            ClassificationExample("магический кристалл", EntityType.ITEM.value),
            
            # Книги и свитки
            ClassificationExample("книга заклинаний толстая", EntityType.ITEM.value),
            ClassificationExample("томик стихов изящен", EntityType.ITEM.value),
            ClassificationExample("манускрипт древен", EntityType.ITEM.value),
            ClassificationExample("дневник путешественника", EntityType.ITEM.value),
            
            # Инструменты и утварь
            ClassificationExample("факел освещает путь", EntityType.ITEM.value),
            ClassificationExample("веревка крепкая и надежная", EntityType.ITEM.value),
            ClassificationExample("кирка для копания", EntityType.ITEM.value),
            ClassificationExample("сумка для путешествий", EntityType.ITEM.value),
            
            # Сокровища и ценности
            ClassificationExample("золотая монета блестит", EntityType.ITEM.value),
            ClassificationExample("драгоценный камень сверкает", EntityType.ITEM.value),
            ClassificationExample("жемчужина переливается", EntityType.ITEM.value),
            ClassificationExample("артефакт обладает мощью", EntityType.ITEM.value),
            ClassificationExample("сокровище стоит целое состояние", EntityType.ITEM.value),
            ClassificationExample("реликвия хранит память", EntityType.ITEM.value),
            
            # Общие определения предметов
            ClassificationExample("предмет странный и неизвестный", EntityType.ITEM.value),
            ClassificationExample("вещь ценная и редкая", EntityType.ITEM.value),
            ClassificationExample("инвентарь героя полон", EntityType.ITEM.value),
            
            # English Items
            ClassificationExample("sword gleams in sunlight", EntityType.ITEM.value),
            ClassificationExample("shield protects from harm", EntityType.ITEM.value),
            ClassificationExample("potion bubbles mysteriously", EntityType.ITEM.value),
            ClassificationExample("scroll crackles with magic", EntityType.ITEM.value),
            ClassificationExample("ring sparkles with power", EntityType.ITEM.value),
            ClassificationExample("amulet glows softly", EntityType.ITEM.value),
            ClassificationExample("book contains ancient wisdom", EntityType.ITEM.value),
            ClassificationExample("artifact pulses with energy", EntityType.ITEM.value),
            ClassificationExample("treasure gleams like gold", EntityType.ITEM.value),
            ClassificationExample("weapon is sharp and deadly", EntityType.ITEM.value),

            # === UNKNOWN / НЕ СУЩНОСТЬ ===
            # Добавляем стоп-слова и служебные слова, чтобы классификатор возвращал UNKNOWN,
            # снижая ложные срабатывания (например, предлог "с").
            ClassificationExample("и", "UNKNOWN"),
            ClassificationExample("а", "UNKNOWN"),
            ClassificationExample("но", "UNKNOWN"),
            ClassificationExample("же", "UNKNOWN"),
            ClassificationExample("ли", "UNKNOWN"),
            ClassificationExample("то", "UNKNOWN"),
            ClassificationExample("в", "UNKNOWN"),
            ClassificationExample("во", "UNKNOWN"),
            ClassificationExample("на", "UNKNOWN"),
            ClassificationExample("над", "UNKNOWN"),
            ClassificationExample("под", "UNKNOWN"),
            ClassificationExample("за", "UNKNOWN"),
            ClassificationExample("из", "UNKNOWN"),
            ClassificationExample("у", "UNKNOWN"),
            ClassificationExample("к", "UNKNOWN"),
            ClassificationExample("ко", "UNKNOWN"),
            ClassificationExample("от", "UNKNOWN"),
            ClassificationExample("о", "UNKNOWN"),
            ClassificationExample("об", "UNKNOWN"),
            ClassificationExample("по", "UNKNOWN"),
            ClassificationExample("со", "UNKNOWN"),
            ClassificationExample("с", "UNKNOWN"),
            ClassificationExample("про", "UNKNOWN"),
            ClassificationExample("для", "UNKNOWN"),
            ClassificationExample("без", "UNKNOWN"),
            ClassificationExample("между", "UNKNOWN"),
            ClassificationExample("через", "UNKNOWN"),
            ClassificationExample("при", "UNKNOWN"),
            ClassificationExample("из-за", "UNKNOWN"),
            ClassificationExample("из-под", "UNKNOWN"),
            ClassificationExample("что", "UNKNOWN"),
            ClassificationExample("кто", "UNKNOWN"),
            ClassificationExample("где", "UNKNOWN"),
            ClassificationExample("как", "UNKNOWN"),
            ClassificationExample("когда", "UNKNOWN"),
            ClassificationExample("почему", "UNKNOWN"),
            # English stopwords
            ClassificationExample("and", "UNKNOWN"),
            ClassificationExample("or", "UNKNOWN"),
            ClassificationExample("but", "UNKNOWN"),
            ClassificationExample("with", "UNKNOWN"),
            ClassificationExample("to", "UNKNOWN"),
            ClassificationExample("of", "UNKNOWN"),
            ClassificationExample("in", "UNKNOWN"),
            ClassificationExample("on", "UNKNOWN"),
            ClassificationExample("at", "UNKNOWN"),
            ClassificationExample("by", "UNKNOWN"),
            ClassificationExample("for", "UNKNOWN"),
            ClassificationExample("from", "UNKNOWN"),
            ClassificationExample("as", "UNKNOWN"),
            ClassificationExample("about", "UNKNOWN"),
        ]
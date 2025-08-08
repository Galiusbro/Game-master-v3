"""
Training data for Location Type Classification
"""

from dataclasses import dataclass
from typing import List
from infrastructure.command_classification_service import ClassificationExample

@dataclass
class LocationTypeTrainingData:
    """Location type classification training examples"""
    
    @staticmethod
    def get_examples() -> List[ClassificationExample]:
        return [
            # === DUNGEON - подземелья, пещеры, гробницы ===
            
            # Classic dungeons - УСИЛЕННЫЕ примеры с проходами
            ClassificationExample("A dark stone corridor stretches ahead, lit by flickering torches", "dungeon"),
            ClassificationExample("Тёмный каменный коридор тянется вперёд, освещённый мерцающими факелами", "dungeon"),
            ClassificationExample("Ancient stone walls covered in moss and mysterious runes", "dungeon"),
            ClassificationExample("Древние каменные стены, покрытые мхом и таинственными рунами", "dungeon"),
            ClassificationExample("The underground chamber echoes with dripping water", "dungeon"),
            ClassificationExample("Подземная камера эхом отзывается капающей водой", "dungeon"),
            ClassificationExample("Damp stone passages lead deeper into the dungeon complex", "dungeon"),
            ClassificationExample("Влажные каменные проходы ведут глубже в подземный комплекс", "dungeon"),
            ClassificationExample("Narrow stone corridors wind through the ancient structure", "dungeon"),
            ClassificationExample("Узкие каменные коридоры вьются через древнее сооружение", "dungeon"),
            ClassificationExample("Stone passages wind deeper through the underground complex", "dungeon"),
            ClassificationExample("Каменные проходы вьются глубже через подземный комплекс", "dungeon"),
            
            # Caves and natural dungeons
            ClassificationExample("A winding cave passage carved by underground rivers", "dungeon"),
            ClassificationExample("Извилистый пещерный проход, вырезанный подземными реками", "dungeon"),
            ClassificationExample("Stalactites hang from the cavern ceiling like stone teeth", "dungeon"),
            ClassificationExample("Сталактиты свисают с потолка пещеры, как каменные зубы", "dungeon"),
            ClassificationExample("The natural cave opens into a vast underground cathedral", "dungeon"),
            ClassificationExample("Природная пещера открывается в огромный подземный собор", "dungeon"),
            
            # Tombs and crypts
            ClassificationExample("Ancient sarcophagi line the walls of this burial chamber", "dungeon"),
            ClassificationExample("Древние саркофаги выстроились вдоль стен погребальной камеры", "dungeon"),
            ClassificationExample("The crypt is filled with the scent of old incense and decay", "dungeon"),
            ClassificationExample("Склеп наполнен ароматом старых благовоний и тления", "dungeon"),
            ClassificationExample("Marble tombs bear the names of long-dead nobles", "dungeon"),
            ClassificationExample("Мраморные гробницы несут имена давно умерших дворян", "dungeon"),
            
            # === TOWN - города, деревни, поселения ===
            
            # Town centers and streets
            ClassificationExample("The busy marketplace buzzes with merchants hawking their wares", "town"),
            ClassificationExample("Оживлённый рынок гудит от торговцев, расхваливающих свои товары", "town"),
            ClassificationExample("Cobblestone streets wind between timber-framed buildings", "town"),
            ClassificationExample("Мощёные улицы вьются между зданиями с деревянным каркасом", "town"),
            ClassificationExample("The town square features a central fountain and gathering area", "town"),
            ClassificationExample("Городская площадь украшена центральным фонтаном и местом для собраний", "town"),
            
            # Taverns and inns
            ClassificationExample("The Prancing Pony tavern welcomes weary travelers", "town"),
            ClassificationExample("Таверна 'Скачущий пони' приветствует усталых путешественников", "town"),
            ClassificationExample("Warm light spills from the inn's windows onto the street", "town"),
            ClassificationExample("Тёплый свет льётся из окон гостиницы на улицу", "town"),
            ClassificationExample("The common room fills with laughter and conversation", "town"),
            ClassificationExample("Общий зал наполняется смехом и разговорами", "town"),
            
            # Shops and crafters - УСИЛЕННЫЕ русские примеры
            ClassificationExample("The blacksmith's forge glows red-hot in the workshop", "town"),
            ClassificationExample("Кузня кузнеца раскалена докрасна в мастерской", "town"),
            ClassificationExample("The village smithy rings with hammer blows on the anvil", "town"),
            ClassificationExample("Деревенская кузница звенит от ударов молота по наковальне", "town"),
            ClassificationExample("The town blacksmith works iron on his anvil", "town"),
            ClassificationExample("Городской кузнец обрабатывает железо на наковальне", "town"),
            ClassificationExample("Sparks fly from the village forge as metal is shaped", "town"),
            ClassificationExample("Искры летят из деревенской кузни, когда формуют металл", "town"),
            ClassificationExample("The smithy echoes with rhythmic hammering sounds", "town"),
            ClassificationExample("Кузница эхом отзывается ритмичными ударами молота", "town"),
            ClassificationExample("Shelves of potions and herbs line the alchemist's shop", "town"),
            ClassificationExample("Полки с зельями и травами выстроились в лавке алхимика", "town"),
            ClassificationExample("The baker's shop fills the street with the aroma of fresh bread", "town"),
            ClassificationExample("Пекарня наполняет улицу ароматом свежего хлеба", "town"),
            
            # Craftsmen in town context - КРИТИЧЕСКИЕ примеры
            ClassificationExample("The town carpenter builds furniture for local families", "town"),
            ClassificationExample("Городской плотник изготавливает мебель для местных семей", "town"),
            ClassificationExample("Village woodworker crafts tools and household items", "town"),
            ClassificationExample("Деревенский столяр мастерит инструменты и предметы быта", "town"),
            ClassificationExample("The skilled craftsman works wood with precise techniques", "town"),
            ClassificationExample("Умелый ремесленник обрабатывает дерево точными приёмами", "town"),
            
            # === WILDERNESS - дикая природа, леса, горы ===
            
            # Forests
            ClassificationExample("Ancient oak trees form a canopy overhead", "wilderness"),
            ClassificationExample("Древние дубы образуют навес над головой", "wilderness"),
            ClassificationExample("A winding forest path disappears into the undergrowth", "wilderness"),
            ClassificationExample("Извилистая лесная тропа исчезает в подлеске", "wilderness"),
            ClassificationExample("Shafts of sunlight pierce the dense forest canopy", "wilderness"),
            ClassificationExample("Лучи солнца пронизывают густой лесной полог", "wilderness"),
            
            # Mountains and hills
            ClassificationExample("Rocky outcrops jut from the mountainside", "wilderness"),
            ClassificationExample("Скалистые выступы торчат из склона горы", "wilderness"),
            ClassificationExample("The mountain path winds steeply upward", "wilderness"),
            ClassificationExample("Горная тропа круто поднимается вверх", "wilderness"),
            ClassificationExample("Snow-capped peaks stretch to the horizon", "wilderness"),
            ClassificationExample("Заснеженные вершины тянутся до горизонта", "wilderness"),
            
            # Plains and fields
            ClassificationExample("Rolling grasslands extend as far as the eye can see", "wilderness"),
            ClassificationExample("Холмистые луга простираются, насколько хватает глаз", "wilderness"),
            ClassificationExample("Wild flowers dot the meadow with splashes of color", "wilderness"),
            ClassificationExample("Дикие цветы усеивают луг яркими пятнами", "wilderness"),
            ClassificationExample("A gentle breeze rustles through the tall grass", "wilderness"),
            ClassificationExample("Лёгкий ветерок шелестит в высокой траве", "wilderness"),
            
            # Natural features and springs - УСИЛЕННЫЕ примеры
            ClassificationExample("Natural hot springs bubble up from the earth", "wilderness"),
            ClassificationExample("Природные горячие источники бурлят из земли", "wilderness"),
            ClassificationExample("Geothermal springs steam in the mountain valley", "wilderness"),
            ClassificationExample("Геотермальные источники парят в горной долине", "wilderness"),
            ClassificationExample("Mineral-rich springs flow from natural rock formations", "wilderness"),
            ClassificationExample("Богатые минералами источники текут из природных скальных образований", "wilderness"),
            ClassificationExample("Hot water bubbles up through cracks in the wilderness floor", "wilderness"),
            ClassificationExample("Горячая вода бурлит через трещины в дикой местности", "wilderness"),
            ClassificationExample("Steam rises from thermal pools in the forest clearing", "wilderness"),
            ClassificationExample("Пар поднимается от термальных бассейнов на лесной поляне", "wilderness"),
            ClassificationExample("A waterfall cascades down the rocky cliff face", "wilderness"),
            ClassificationExample("Водопад каскадом спускается по скалистому утёсу", "wilderness"),
            
            # === INDOOR - помещения, комнаты, интерьеры ===
            
            # Residential rooms
            ClassificationExample("A cozy sitting room with a crackling fireplace", "indoor"),
            ClassificationExample("Уютная гостиная с потрескивающим камином", "indoor"),
            ClassificationExample("The bedroom contains a comfortable four-poster bed", "indoor"),
            ClassificationExample("В спальне стоит удобная кровать с балдахином", "indoor"),
            ClassificationExample("Bookshelves line the walls of the private study", "indoor"),
            ClassificationExample("Книжные полки выстроились вдоль стен частного кабинета", "indoor"),
            
            # Formal halls and chambers
            ClassificationExample("The grand hall features soaring vaulted ceilings", "indoor"),
            ClassificationExample("Большой зал украшен высокими сводчатыми потолками", "indoor"),
            ClassificationExample("Ornate tapestries hang from the throne room walls", "indoor"),
            ClassificationExample("Богато украшенные гобелены висят на стенах тронного зала", "indoor"),
            ClassificationExample("Marble columns support the cathedral's nave", "indoor"),
            ClassificationExample("Мраморные колонны поддерживают неф собора", "indoor"),
            
            # Workshops and functional rooms
            ClassificationExample("The laboratory is filled with bubbling alchemical apparatus", "indoor"),
            ClassificationExample("Лаборатория наполнена булькающими алхимическими приборами", "indoor"),
            ClassificationExample("Scrolls and tomes cover every surface of the scriptorium", "indoor"),
            ClassificationExample("Свитки и фолианты покрывают каждую поверхность скриптория", "indoor"),
            ClassificationExample("The ancient library holds thousands of mystical volumes", "indoor"),
            ClassificationExample("Древняя библиотека хранит тысячи мистических фолиантов", "indoor"),
            ClassificationExample("The kitchen bustles with preparation for the evening meal", "indoor"),
            ClassificationExample("Кухня суетится в подготовке к вечерней трапезе", "indoor"),
            
            # === UNDERGROUND - подземные локации (не dungeon) ===
            
            # Sewers and tunnels
            ClassificationExample("Murky water flows through the stone sewer channels", "underground"),
            ClassificationExample("Мутная вода течёт по каменным канализационным каналам", "underground"),
            ClassificationExample("The maintenance tunnel runs beneath the city streets", "underground"),
            ClassificationExample("Служебный туннель проходит под городскими улицами", "underground"),
            ClassificationExample("Rats scurry through the damp underground passages", "underground"),
            ClassificationExample("Крысы снуют по влажным подземным проходам", "underground"),
            
            # Underground cities and settlements
            ClassificationExample("The dwarven city is carved directly into the mountain", "underground"),
            ClassificationExample("Дварфийский город вырезан прямо в горе", "underground"),
            ClassificationExample("Glowing crystals illuminate the underground marketplace", "underground"),
            ClassificationExample("Светящиеся кристаллы освещают подземный рынок", "underground"),
            ClassificationExample("Stone bridges span the vast underground chasm", "underground"),
            ClassificationExample("Каменные мосты перекинуты через огромную подземную пропасть", "underground"),
            
            # === MAGICAL_REALM - магические локации ===
            
            # Planar locations
            ClassificationExample("Reality seems to shift and bend in this ethereal plane", "magical_realm"),
            ClassificationExample("Реальность, кажется, искажается и изгибается в этом эфирном плане", "magical_realm"),
            ClassificationExample("The Feywild grove pulses with primal magical energy", "magical_realm"),
            ClassificationExample("Роща Дикого Края пульсирует изначальной магической энергией", "magical_realm"),
            ClassificationExample("Floating islands drift through the astral void", "magical_realm"),
            ClassificationExample("Парящие острова дрейфуют в астральной пустоте", "magical_realm"),
            
            # Magical constructs and phenomena
            ClassificationExample("The wizard's tower defies physics with its impossible architecture", "magical_realm"),
            ClassificationExample("Башня волшебника бросает вызов физике своей невозможной архитектурой", "magical_realm"),
            ClassificationExample("Arcane symbols glow and pulse with their own inner light", "magical_realm"),
            ClassificationExample("Магические символы светятся и пульсируют собственным внутренним светом", "magical_realm"),
            ClassificationExample("The pocket dimension contains a miniature forest", "magical_realm"),
            ClassificationExample("Карманное измерение содержит миниатюрный лес", "magical_realm"),
            
            # Elemental realms
            ClassificationExample("Flames dance without fuel in the elemental plane of fire", "magical_realm"),
            ClassificationExample("Пламя танцует без топлива в элементальном плане огня", "magical_realm"),
            ClassificationExample("Crystalline structures of pure ice form impossible geometries", "magical_realm"),
            ClassificationExample("Кристаллические структуры чистого льда образуют невозможные геометрии", "magical_realm"),
            ClassificationExample("The air itself shimmers with visible magical currents", "magical_realm"),
            ClassificationExample("Сам воздух мерцает видимыми магическими потоками", "magical_realm"),
        ]
### Цель

Пошагово сгенерировать и развернуть мир: от географии и политики до городов, улиц, зданий, домохозяйств и NPC по `NPC.md`, с хранением в графе и RAG‑слоем в векторке.

### Этап 0. Подготовка

- Определить параметры мира: seed, климат/магия, техуровень.
- Решить масштабы: кол-во континентов/стран/городов для MVP.
- Подготовить коллекции в Qdrant: `world_entities`, `world_docs`.

Параметры мира (дефолты):

```json
{
  "seed": "gmv3",
  "setting": "classic_fantasy",
  "magic_level": "medium",
  "tech_level": "medieval",
  "naming_style": "slavic",
  "content_rating": "teen",

  "world": {
    "continents": 2,
    "water_ratio": 0.65,
    "mountain_density": 0.4
  },
  "politics": {
    "countries_per_continent": 3,
    "factions_top": 5,
    "lawfulness": "moderate"
  },
  "settlements": {
    "per_country": { "min": 1, "avg": 3, "max": 6 },
    "road_density": 0.5,
    "wilderness_danger": 0.4,
    "monstrous_fauna": 0.35
  },
  "economy": { "currency": ["gold", "silver", "copper"] },
  "religion": { "pantheon": "small" },

  "start_region": "auto",
  "mvp_limits": { "graph_nodes_target": 8000, "locale": "ru" }
}
```

### Этап 1. Онтология (схема графа)

- Ноды: World, Continent, Region, Biome, Ocean/Sea/Lake, River, Country, Province, City/Town/Village/Camp/Ruin/Dungeon, District, Street, Building, Room, POI, Road, Faction, Household, NPC, Item.
- Рёбра: CONTAINS/LOCATED_IN, ADJACENT_TO/CONNECTS_TO, FLOWS_TO/FEEDS, CONTROLS/CLAIMS, HAS_DISTRICT/HAS_BUILDING, OWNS/EMPLOYS, ROUTE.
- Минимальные атрибуты на уровне сущностей (плотность, опасность, экономика, и т.п.).

Критерий готовности: схема зафиксирована в коде и в `docs/` (короткая таблица сущность→поля).

#### Схема данных (минимум по сущностям)

Примечание по типам: для совместимости с текущим `EntityType` все гео/города/улицы/здания/реки/дороги/POI представляем как `EntityType.LOCATION` с уточняющим полем `location_kind`.

- LOCATION (базовый шаблон для всех мест)

  - required: `name`, `location_kind` ("world|continent|region|biome|ocean|sea|lake|river|country|province|city|town|village|camp|ruin|dungeon|district|street|building|room|poi|road"), `description`
  - common: `parent_id` (LOCATED_IN), `coordinates` (центр, опционально bbox), `tags[]`, `is_safe: bool`, `danger_level: 0..1`, `economy_tags[]`, `population_estimate: int`
  - region/biome: `climate`, `biome_type`
  - ocean/sea/lake: `salinity`, `avg_depth_m`
  - river: `length_km`, `source_location_id`, `mouth_location_id`, `passes_regions[]`
  - country: `government`, `laws[]`, `capital_id`
  - district: `kind (market|docks|noble|slums|temple)`, `density`
  - street: `length_m`, `traffic_level`
  - building: `kind (inn|shop|house|temple|guardhouse|workshop)`, `owner_id?`, `business_profile?`
  - room: `room_kind`, `floor`
  - poi: `poi_type`, `hook_tags[]`
  - road: `from_id`, `to_id`, `distance_km`, `safety`, `terrain`

- NPC (см. NPC.md)

  - `roles[]`, `aliases[]`, `capabilities{}` (trade/service/social/...)
  - `state.current_location_id`, `disposition_to_player{}`, `relationship_to_player{}`
  - `possessions[]` (entity ids)

- ITEM

  - как в домене: `item_type`, `owner_id?`, `location_id?`, `value`, `properties{}`

- HOUSEHOLD (можно как LOCATION с `location_kind=household` или как вспомогательная сущность)

  - `members[npc_id]`, `home_building_id`, `wealth_level`

- FACTION (для MVP — как метаданные у country/city/NPC; при необходимости — выделим сущность)
  - `name`, `tenets[]`, `reputation_rules`, связи `CONTROLS/CLAIMS`

#### Связи (графовые рёбра)

- `CONTAINS (A→B)` / `LOCATED_IN (B→A)`

  - World→Continent→Region→City/Town→District→Street→Building→Room
  - Country→City/Town/Village, City→POI/Building, Region→River/POI

- `ADJACENT_TO (A↔B)`

  - Region↔Region, City↔City, District↔District

- `CONNECTS_TO (A↔B)`

  - Road↔City/Town/Village/POI (дороги)

- `FLOWS_TO (River→Sea/Lake)` / `FEEDS (River→River)`

- `CONTROLS (Country/Faction→Region/City)` / `CLAIMS (Faction→Region)`

- `OWNS (NPC/Household→Item/Building)`

- `EMPLOYS (NPC/Business→NPC)`

- `HAS_POI (City/Region→POI)`

Свойства рёбер (минимум):

- `ROUTE/CONNECTS_TO`: `distance_km`, `safety`, `travel_time_est`
- `CONTROLS/CLAIMS`: `since_year`, `strength`
- `ADJACENT_TO`: `border_type (land|river|sea|mountain)`

#### Маппинг в Qdrant (payload для поиска)

- Общие поля: `entity_type`, `name`, `description`, `location_kind`, `parent_id`, `current_location_id?`, `aliases[]`, `roles[]?`, `tags[]`, `importance_level`
- Для фильтров: `location_kind`, `country_id`, `region_id`, `is_safe`, `danger_level`, для NPC — `is_alive`, `roles[]`
- Текст для эмбеддингов: `name + location_kind + краткое описание + теги + (для NPC: roles/aliases/состояние)`

#### Инварианты (валидация генерации)

- У реки есть `source_location_id` и `mouth_location_id`, `length_km>0`
- Город/деревня LOCATED_IN страну и регион; дороги CONNECTS_TO валидные узлы
- District LOCATED_IN City; Building LOCATED_IN District/Street; Room LOCATED_IN Building
- NPC `state.current_location_id` указывает на существующий узел

### Этап 2. Макрогеография

- Генерируем высоты → вода (океаны/моря/озёра) → реки → биомы/климат → регионы.
- Связи: Region ADJACENT_TO, River FLOWS_TO/FEEDS.

Выход: континенты, моря/озёра, реки, регионы с биомами в графе.

Детали реализации (MVP):

#### 2.1 Параметры и сетка

- Размер карты (MVP): `grid_size = 512x512` (можно 256x256 для быстрых прогонов)
- Система координат: нормированные `u,v ∈ [0,1]` (опционально — проекция в lat/lon)
- Детализация: 1 клетка ≈ 1–5 км (зависит от целевого масштаба мира)
- Детерминизм: все генераторы используют общий `seed`

#### 2.2 Карта высот (heightmap)

- Метод: фрактальный шум (Perlin/Simplex) + оконтуривание «континентов» маской низкой частоты
- Шаги:
  1. `base = fractal_noise(octaves=5, scale=~1.2)`
  2. `continents = noise_low_freq(scale=~0.3)` → нормализовать, поднять континентальные участки
  3. `height = normalize(0.7*base + 0.3*continents)`
  4. Эрозия (MVP опционально): 1–2 итерации термальной/гидро-эрозии

Выход: `height[u,v] ∈ [0,1]`

#### 2.3 Вода и береговая линия

- Уровень моря: по квантилю `sea_level = quantile(height, water_ratio)` (см. Этап 0: `water_ratio`)
- Маска океанов/морей: `is_water = height < sea_level`
- Поиск замкнутых бассейнов → озёра: заливка депрессий (flood fill) с минимальным переливом
- Классификация: крупные водоёмы → Ocean/Sea; средние → Lake (по площади/связности)

#### 2.4 Гидрология (реки)

- Направление стока: D8/D∞ по отрицательному градиенту `height`
- Накопление стока: `flow_accumulation` (кол-во ячеек, стекающих в точку)
- Истоки рек: локальные максимумы накопления выше `acc_threshold` на суше
- Трассировка русел: идти по направлению стока до моря/озера; соединять притоки
- Порог видимых рек/притоков: по масштабу мира (например, ≥ 200–500 ячеек накопления)
- Связи: River `FLOWS_TO` Sea/Lake; притоки `FEEDS` в основной поток

Атрибуты реки (минимум): `name`, `length_km (по полилинии)`, `source_location_id`, `mouth_location_id`, `passes_regions[]`

#### 2.5 Климат и биомы

- Климатические факторы:
  - Широта (если используем lat): `latitude_factor = |lat|`
  - Высота: `elevation_factor = height`
  - Влажность: `moisture ~ distance_to_coast^-1 + flow_accumulation_scaled`
  - Дождь в подветренной стороне гор (орографический эффект) — опционально
- Классификация биомов (упрощённо, Köppen-like):
  - Пустыни/полупустыни: низкая влажность, высокая температура
  - Саванны/степи: средняя влажность, тёплые
  - Леса (бореальные/умеренные/тропические): средняя/высокая влажность + широта/высота
  - Тундра/альпийские: низкая температура (высота/широта)
  - Болотистые: высокая влажность и низкая высота окрестности

#### 2.6 Регионы

- Сегментация регионов:
  - Watershed / Voronoi по сэмплам центров на суше (с весами по населяемости)
  - Учёт биома: стараться не смешивать разные биомы в одном регионе (порог доли)
- Связности: `ADJACENT_TO` между соседними полигонами
- Атрибуты региона: `biome`, `climate`, `danger_level`, `economy_tags` (рыболовство у побережья, земледелие в равнинах и т.д.)

#### 2.7 Сохранение в граф (минимальный пайплайн)

1. Создать `World` (LOCATION: `location_kind=world`)
2. Создать `Continent` ноды (по компонентам крупной суши)
3. Создать `Ocean/Sea/Lake` (по компонентам воды, по площади классифицировать)
4. Создать `Region` ноды (по сегментации) и связать `LOCATED_IN` Continent
5. Создать `River` (как LOCATION с полилинией в `metadata.geometry`), связать `FLOWS_TO/FEEDS`, `LOCATED_IN` Regions
6. Установить `ADJACENT_TO` между Region; для берегов — Region↔Sea/Lake (опц.)

Поля координат/геометрии:

- В `LOCATION.metadata` хранить `center: [u,v]`, `bbox: [min_u,min_v,max_u,max_v]`, для рек — `polyline: [[u,v], ...]`

#### 2.8 Индексация в Qdrant

- Коллекция `world_entities`: индексировать `World/Continent/Region/Ocean/Sea/Lake/River` как `EntityType.LOCATION`
- `payload`: `entity_type`, `location_kind`, `parent_id`, `tags`, `biome/climate` (если есть)
- Текст: `name + location_kind + краткое описание + биом/климат`

#### 2.9 Интерфейсы генераторов (скелеты)

Логика будет в модуле `core/worldgen/` (предложение):

- `generate_heightmap(seed, grid_size, params) -> np.ndarray`
- `derive_water_masks(height, water_ratio) -> {sea_level, is_water, lakes_mask}`
- `compute_flow(height) -> {flow_dir, flow_accum}`
- `extract_rivers(flow_dir, flow_accum, thresholds) -> List[RiverPolyline]`
- `compute_climate(height, coast_distance, flow_accum, params) -> {temperature, moisture}`
- `classify_biomes(temperature, moisture, height) -> biome_map`
- `segment_regions(biome_map, land_mask, params) -> List[RegionPolygon]`
- `persist_macrograph(height, masks, rivers, regions) -> List[Entity]` (через `world_service`)

#### 2.10 Инварианты и проверки (MVP)

- Доля воды ≈ `water_ratio ± 5%`
- Все реки начинаются на суше и впадают в море/озеро, длина > 0
- У каждого региона есть `biome`, `LOCATED_IN` континент; регионы связны
- Не менее N «прибрежных» регионов с доступом к морю

#### Примечания для текстовой ДнД (упрощения под нарратив)

- Масштаб MVP небольшой: 1–2 континента, карта `256×256`, 3–5 стран, 5–10 городов
- Координаты — абстракция: важнее `travel_time`, `danger`, чем метры и полигоны
- Эрозию/сложную гидрологию можно упростить — главное правдоподобные реки/берега
- На уровне регионов держать: encounter tables, weather tables, rumor hooks (по 3–5 на регион)
- Для города бюджет контента: 1 innkeeper, 1 healer, 1 blacksmith, 1 guard captain, 3–6 гражданских NPC
- Каждая локация должна иметь 2–3 POI/квест‑хука для немедленного геймплея
- Имена и лор — в стиле RU/славянских имен (настройка `naming_style`)
- Контентные суммаризации (RAG) держать короткими (≤ 300–600 токенов на срез)

### Этап 3. Политика

- Цель: страны/фракции/законы и контроль территорий, влияющие на торговлю, магию, криминал, безопасность дорог

#### 3.1 Генерация стран и границ

- Опора на гео: границы вдоль рек/гор/берегов, заполнение суши до целевого числа стран
- У каждой страны: `government (monarchy|theocracy|city_states|tribal)`, `lawfulness (strict|moderate|lenient)`, `magic_legality (banned|licensed|free)`
- `capital_id` выбирается среди крупнейших городов/узлов дорог

#### 3.2 Фракции и влияние

- Топ‑уровневые фракции (5±2): `church`, `merchants guild`, `mages circle`, `nobles`, `guard`, `thieves guild`
- Поля: `tenets[]`, `reputation_rules`, `claims/controls` на регионы/города, `relationships{faction→opinion}`
- Связи: `CONTROLS (Faction→City/Region)`, `CLAIMS (Faction→Region)`

#### 3.3 Законы и правоприменение

- Базовые законы: `trade_tax`, `contraband_list`, `magic_permits_required`, `curfew`, `weapons_open_carry`
- Наказания: `fine|confiscation|imprisonment|banishment|execution` (таблицы по тяжести)
- Применимость по зонам: столица строже, приграничье мягче; в доках больше контрабанды

#### 3.4 Гарнизоны, безопасность и дороги

- `guard_presence` на город/дорогу (0..1), влияет на шанс встречи/проверки
- Дороги: `toll_tax`, `patrol_frequency`, `danger_along_route` (модификатор encounter rate)

#### 3.5 Экономика и торговля (заготовки)

- Товары по регионам: `surplus/deficit` теги (рыба, зерно, железо, текстиль)
- Базовые коэффициенты цен по стране/городу; пошлины на вход/рынок

#### 3.6 Сохранение в граф

1. Создать `Country` как LOCATION (`location_kind=country`), `LOCATED_IN` Continent
2. Установить `CONTROLS (Country→Region/City)` по покрытию
3. Создать/связать фракции (как сущности или метаданные) с `CONTROLS/CLAIMS`
4. Записать законы/налоги в `metadata.laws` страны/города

#### 3.7 Индексация в Qdrant

- В `payload`: `location_kind=country|city|road`, `lawfulness`, `magic_legality`, `guard_presence`, `taxes`
- Текст: кратко «правила мира» для RAG (что легально, где опасно, кто контролирует)

#### 3.8 Инварианты

- Каждая страна имеет столицу; каждая столица LOCATED_IN страну
- У дорог между крупными городами есть `patrol_frequency`; у приграничных регионов — фракции с `CLAIMS`
- Магия: режим единообразен внутри страны, исключения — у особых фракций/городов‑государств

- Генерируем страны/королевства по гео‑естественным границам.
- Связь: Country CONTROLS Region/City; фракции/законы (минимум: законность торговли, магии).

Выход: страны/провинции, столицы, связи контроля.

### Этап 4. Поселения и дороги

- Распределяем City/Town/Village/Camp/Ruin по устьям рек, побережьям, перекрёсткам.
- Генерируем Road/Route (дистанция, опасность, покрытие).

Выход: сеть городов/дорог, метрики маршрутов.

Детали реализации (MVP):

#### 4.1 Размещение поселений

- Кандидаты: точки рядом с побережьем/устьями рек/перекрёстками естественных долин
- Скоринговая функция (0..1):
  - - расстояние до воды (близко — лучше), + устье реки, + умеренная высота/склон (жить возможно)
  - - биом пригодный (равнины/леса), – болота/крутые горы/пустыни (если нет особых причин)
  - - близость к другим поселениям с понижающим коэффициентом (центр‑спутники)
- Выбор точек: Poisson‑disk/blue‑noise, чтобы не было скученности, с квотами на страну
- Классы размеров: City (топ‑N по скору), Town (следующие), Village (остальные), Camp/Ruin (специальные места)

Квоты и соотношения (MVP):

- Ратио типов: `cities:towns:villages ≈ 1:3:8`
- Квоты на страну (по умолчанию, масштабируется площадью/населяемостью):
  - cities: 1–2
  - towns: 2–5
  - villages: 6–15
  - camps/ruins: 3–7

Порядок размещения:

1. Города — устья рек/побережье/узлы дорог (высокий скор)
2. Города помельче (towns) — перекрёстки и стратегические точки между городами
3. Деревни (villages) — пригодные биомы (земледелие/пастбища) вокруг городов/дорог
4. Camps/Ruins — по опасным/уединённым местам и вдоль дорог (узкие места)

Атрибуты (минимум):

- City/Town/Village: `pop_estimate`, `economy_tags[]`, `has_walls`, `danger_level`, `guard_presence`
- Camp: `faction|bandits`, `lifetime`, `loot_tags`, `danger_level`
- Ruin/Dungeon: `origin`, `depth|risk`, `hook_tags`

#### 4.2 Районы и базовые здания (ускорённо)

- Для City/Town: создать 3–5 District по шаблону места (coast→docks, crossroads→market, capital→noble)
- На каждый District — 5–15 Building по роли района: inn/shop/temple/guardhouse/house
- В каждом крупном городе: гарантировать `inn`, `healer`, `blacksmith`, `guardhouse`

#### 4.3 Генерация дорог

- Цели соединения:
  1. Столица ↔ столицы соседних стран (если рядом)
  2. Столица ↔ города своей страны
  3. Города ↔ ближайшие 1–2 соседних города (k‑NN)
- Стоимость клетки: `cost = base + slope_penalty + biome_penalty + river_cross_penalty`
- Прокладка маршрутов: A\* / Dijkstra по стоимости; избегать воды/крутых склонов
- Параметры дороги: `distance_km`, `terrain`, `safety` (от опасности регионов), `patrol_frequency` (выше у столичных трасс), `toll_tax` (если строгость/налоговая политика страны)

#### 4.4 Спец‑объекты

- POI вдоль дорог каждые X км: посты, таверны, святилища, руины
- Camps (разбойники/наёмники) в «узких местах» с низкой охраной/высокой опасностью

#### 4.5 Сохранение в граф

1. Создать поселения как LOCATION с `location_kind=city|town|village|camp|ruin|dungeon`, `LOCATED_IN` Country/Region
2. Для городов: District/Street/Building по минимуму (см. Этап 5)
3. Создать дороги как LOCATION `location_kind=road`, связать `CONNECTS_TO` (from/to), заполнить свойства
4. Прописать `HAS_POI` для городов/регионов, где есть POI

#### 4.6 Индексация в Qdrant

- В `payload`: `location_kind`, `country_id`, `region_id`, `economy_tags`, `guard_presence`, `danger_level`, для дорог — `safety`, `toll_tax`
- Текст: `name + settlement class + краткое экономическое описание + безопасность`

#### 4.7 Инварианты

- В каждой стране ≥ 1 города; столица соединена дорогами с ≥ 2 узлами
- Дороги не пересекают море/озёра без мостов (MVP — «обход» воды)
- На расстоянии ≤ 1 дня пути от столицы есть хотя бы 1 безопасный трактир/пост
- Каждый крупный город имеет базовые сервисы (inn/healer/blacksmith/guard)
- Соотношения соблюдены: `villages ≥ towns ≥ cities`
- На 1 town приходится ≥ 2 деревни в радиусе ≤ 1 дня пути

### Этап 5. Городская структура

- District: market/docks/noble/slums/temple и плотность.
- Street: названия, длина, трафик.
- Building: kind (inn/shop/house/temple/guardhouse), опционально `business_profile`.
- Room/Interior (точечно для ключевых POI/иннов).

Выход: районы→улицы→здания с типами.

Детали реализации (MVP):

#### 5.1 Районы (Districts)

- Кол-во по классу поселения:
  - City: 5–9, Town: 3–5, Village: 1–2 (можно без районов)
- Типы и доли (шаблоны):
  - port/coast: docks (30%), market (20%), common (30%), noble (10%), temple (10%)
  - crossroads: market (30%), common (40%), crafts (15%), temple (10%), slums (5%)
  - capital: noble (25%), admin (15%), market (20%), crafts (15%), common (15%), temple (10%)
- Атрибуты: `kind`, `density`, `guard_presence`, `danger_level`, `economy_tags[]`
- Связи: `ADJACENT_TO` между соседними районами; `LOCATED_IN` город

#### 5.2 Улицы (Streets)

- Каркас: 2–4 магистрали (primary) + 6–20 второстепенных (secondary) для City; для Town меньше
- Именование: генератор по `naming_style` (RU/славянские: «Набережная», «Кузнечная», «Торговая»)
- Параметры: `length_m`, `traffic_level (0..1)`, `has_market_stalls: bool`
- Связность: граф улиц должен быть связным, магистрали соединяют ключевые узлы (рынок, доки, ворота, площадь)

#### 5.3 Здания (Buildings)

- Плотность по типу района: market/crafts/common высокие; noble/temple низкие
- Распределение типов:
  - inn (1–2 на город, ≥1 в City), shop (разные специализации), temple, guardhouse, workshop, house
- `business_profile` для коммерческих зданий:
  - `shop_kind (general|blacksmith|alchemist|healer|stable|fisher|warehouse)`
  - `service_capability` (лечить, ремонт, обучение, транспорт)
  - `trade_capability` (is_professional, offers[], pricing_policy)
- Гарантии:
  - City: inn, healer, blacksmith, guardhouse, market square
  - Town: inn, healer or apothecary, guardhouse
  - Village: tavern/inn (маленькая), shrine

#### 5.4 Интерьеры (Rooms) — точечно

- Inn: common_room, 3–8 guest_rooms, kitchen, cellar
- Temple: sanctuary, sacristy, archive (если capital), garden (опц.)
- Guardhouse: office, barracks, cells (1–4)
- Shop: counter, storage, workshop
- Связи: `LOCATED_IN` Building → Rooms; метаданные для спавна NPC/сцен

#### 5.5 Городские POI и хуки

- Town/City square, statue/monument, notice_board (квестовые объявления)
- Rumor spots: tavern, docks, market; разместить 3–5 `hook_tags` на город
- Local laws summary: комендантский час, налоги рынка, разрешение магии (для RAG)

#### 5.6 Сохранение в граф

1. Создать District как LOCATION `location_kind=district` → `LOCATED_IN` city
2. Создать Street как LOCATION `location_kind=street` → `LOCATED_IN` city, `ADJACENT_TO`/"узлы"
3. Создать Building как LOCATION `location_kind=building` → `LOCATED_IN` district|street
4. Создать Room как LOCATION `location_kind=room` → `LOCATED_IN` building (для ключевых зданий)
5. Прописать `HAS_POI` на город/районы (площади, памятники, рынки)

#### 5.7 Индексация в Qdrant

- `payload`: `location_kind`, `city_id`, `district_id`, `street_id`, `business_profile.shop_kind`, `service_capability.kind`
- Текст: краткое назначение, ориентиры («Кузнечная, рядом с рынком», «Набережная у доков»)

#### 5.8 Инварианты

- Граф улиц связен, районы соединены минимум двумя улицами
- Требуемые сервисы присутствуют по классу города
- Названия уникальны в пределах города (улицы/здания)
- У POI есть хотя бы 1–2 связанных hook_tags

#### 5.9 Таблицы случайных событий (по району)

- market: карманники, глашатай, спор торговцев
- docks: драка грузчиков, контрабандисты, патруль
- noble: кортеж, стража, слухи дворца
- slums: попрошайки, засада, пожар

#### 5.10 Шаблоны городов (архетипы)

- port_city: доки, рыбный рынок, верфи, святилище моря, контрабанда
- crossroads_city: большая площадь, караван‑сараи, ярмарки, гильдии
- capital_city: дворец, админ‑квартал, большой храм, академия/магическая фракция
- mining_town: шахты, кузницы, склад угля/руды, таверны рабочих
- religious_center: храмы, процессии, паломники, скрипторий/библиотека

### Этап 6. Домохозяйства, бизнесы, POI

- Household в жилых зданиях; бизнесы в коммерческих по district kind.
- POI (храмы, шахты, руины, памятники) с hook_tags.

Выход: насыщение города сущностями для геймплея.

Детали реализации (MVP):

#### 6.1 Домохозяйства (Households)

- Создаём для жилых зданий (Building.kind=house) 1 домохозяйство
- Атрибуты: `home_building_id`, `members_count (1–6)`, `wealth_level (poor|common|well_off|noble)`
- Распределение по районам:
  - noble → `well_off|noble`, common/slums → `poor|common`, crafts → `common`
- Генерируем базовый `storage_profile` (еда/хозяйственные вещи) — пригодится для краж/бартера

#### 6.2 Бизнесы (Shops/Services)

- Для Building с commercial типом создаём `business_profile`:
  - `shop_kind: general|blacksmith|alchemist|healer|stable|fisher|warehouse|inn|tavern`
  - `trade_capability`: `is_professional=true`, `offers[]` (набор типовых предметов), `pricing_policy`
  - `service_capability` (для healer|stable|inn|tavern|workshop): прайсы, кулдауны, материалы
- Мини‑каталоги (статические списки для MVP):
  - general: еда, простые припасы, верёвка, факелы
  - blacksmith: оружие начального уровня, инструменты, ремонт
  - alchemist: зелья простого уровня (healing, antitoxin), реагенты
  - healer: лечение, травы, мази; `service_capability`
  - stable: аренда/покупка лошадей (через `service_capability` и `possessions`), подкова/подковка
  - inn/tavern: комнаты, еда/напитки, слухи (rumor hooks)

#### 6.3 Городские и окрестные POI

- Внутри города: площади, памятники, колодцы, сторожевые башни, складские дворы
- За городом (в радиусе 1–2 дней): фермы, шахты, святилища, руины, охотничьи становища
- Для каждого POI задать `hook_tags` (3–5) и `danger_level`; опционально `faction_presence`

#### 6.4 Инвентари и владения

- `possessions` у бизнесов/домохозяйств: список Item.id (или шаблонов) с `owner_id`
- У `stable`/ферм могут быть животные (как Item/Entity `mount`), доступные к аренде/покупке
- Синхронизация с `trade_capability.offers` (каталог берётся из реальных `possessions` или формируется как витрина)

#### 6.5 Сохранение в граф

1. Для каждого жилого здания → создать Household (как LOCATION `location_kind=household` или метаданные у Building)
2. Для каждого коммерческого здания → записать `business_profile`, `trade/service_capability`
3. Создать POI как LOCATION `location_kind=poi` → `LOCATED_IN` city/region; связать `HAS_POI`
4. Создать базовые Items (минимальные наборы) → `owner_id` = Household/Business/NPC

#### 6.6 Индексация в Qdrant

- В `payload`: `location_kind`, `business_profile.shop_kind`, `service_capability.kind`, `household.wealth_level`, `hook_tags`
- Текст: краткое описание услуг/ассортимента/назначения POI
- Фильтры: поиск «лекарь в городе», «постоялый двор у дороги», «руины рядом»

#### 6.7 Инварианты

- В каждом City: ≥1 inn, ≥1 healer, ≥1 blacksmith, ≥1 guardhouse
- В каждом Town: ≥1 inn, ≥1 healer/apothecary
- Окрестности (≤1 день пути): ≥2 внешних POI (ферма/шахта/святилище/руины)
- Бизнесы имеют непротиворечивые каталоги (цена>0, запас≥0)

#### 6.8 Таблицы взаимодействий (MVP)

- inn/tavern: слухи, работа носильщиком/охранником, драка, игра в кости
- healer: лечение/торг травами, редкий спрос на ингредиенты
- blacksmith: заказ ремонта/кузни, нужда в руде/угле
- stable: аренда/покупка лошади, доставка посылки

### Этап 7. NPC по `NPC.md`

Детали реализации (MVP):

#### 7.1 Распределение и плотности

- В жилых зонах (District.kind=common/crafts/slums) спавнить гражданских NPC (household members, ремесленники)
- В коммерческих зданиях — профильные NPC (innkeeper, blacksmith, healer, shopkeepers)
- В доках/рынках — носильщики, рыбаки, торговцы, стража
- В храмах — жрецы/аколиты; в guardhouse — стража/офицеры
- Плотности (ориентир на город): City 40–120 NPC, Town 15–40, Village 5–15

#### 7.2 Роли и онтология

- `roles[]` из канона: `innkeeper|healer|blacksmith|guard|merchant|priest|fisher|farmer|noble|bandit|sailor|rumor_monger|stable_master|alchemist|apprentice`
- `aliases[]` и локальные прозвища; RU‑лемматизация для поиска/матчинга
- Фракции: `guard`, `merchants_guild`, `church`, `mages_circle`, `thieves_guild`, `nobles`

#### 7.3 Capabilities (см. NPC.md)

- Обязательные поля у NPC: `capabilities{}` (trade/service/social/...)
- Проф. торговцы: `trade_capability.is_professional=true`, `offers[]` из `business_profile`
- Услуги (лекарь/конюшня/кузня): `service_capability` со списком услуг и условиями
- Ad‑hoc сделки: у гражданских `willingness_to_sell_personal` и `possessions` (лошадь у крестьянина)

#### 7.4 Социальные параметры

- `state.disposition_to_player{}` и производное `relationship_to_player` (friendly/neutral/hostile)
- Соц‑чеки: Persuasion/Deception/Intimidation/Performance, кулдауны, влияние фракций/законов
- Romance (опционально): `romance_capability` с гейтами (репутация/культура/табу)

#### 7.5 Имена, описание и лор

- Имена по `naming_style=slavic` (генератор префиксов/суффиксов), прозвища по профессии/особенностям
- `personality.core_traits`, `speech_patterns`, `backstory` — короткие (1–2 предложения), для RAG хватит
- Слухи/темы (2–4) завязать на локальные POI/фракции/дороги

#### 7.6 Связи и владения

- `LOCATED_IN` Room/Building/District; цикличное обновление `current_location_id` для расписаний (после MVP)
- `OWNS` предметы/животных/здания (для ремесленников/землевладельцев)
- `EMPLOYS` — наёмники, ученики

#### 7.7 Сохранение в граф

1. Создать NPC сущности с полями из `NPC.md` (roles, aliases, capabilities, state, possessions)
2. Привязать к локациям (`current_location_id`), связать `OWNS/EMPLOYS` при наличии
3. Для проф. торговцев — связать с Building/business_profile (согласовать `offers`)

#### 7.8 Индексация в Qdrant

- Коллекция `world_entities`: индексировать NPC с `payload`:
  - `entity_type=npc`, `roles[]`, `aliases[]`, `current_location_id`, `faction`, `is_alive`, `importance_level`
- Текст для эмбеддингов: `name + roles + aliases + краткое описание + настроения/занятие`
- Фильтры: `roles[]`, `current_location_id`, `faction`

#### 7.9 Инварианты

- В каждом City: ≥1 innkeeper, ≥1 healer, ≥1 blacksmith, ≥1 guard_captain/guard
- В каждом Town: ≥1 innkeeper, ≥1 healer/apothecary, ≥1 guard sergeant
- NPC в помещениях, соответствующих роли (innkeeper в таверне, healer в лечебнице/храме)
- У проф. торговцев `offers[]` непротиворечивы ценам/запасам; у гражданских — `possessions` согласованы с бытом

Выход: живой населённый слой с ролями/возможностями, совместимый с интентами и поиском.

### Этап 8. Индексация и RAG

- Индексируем все сущности в Qdrant:`world_entities` (name/aliases/desc/roles, ключевые поля в payload).
- Загружаем `NPC.md` и «библию мира» в `world_docs` (порезанные секции).
- Настраиваем фильтры: entity_type, current_location_id, roles.

Критерий: быстрый релевантный поиск и извлечение контекста.

### Этап 9. Сервисы и API

- Эндпойнты:
  - generate_world(seed, params)
  - get_world_slice(entity_id, depth, types) — срез для промптов
  - search_entities(query, filters)
- Интеграция в `ai_service`: системные правила + RAG по `world_docs` и фактам из `world_entities`.

Выход: генерация и доступ к миру из игрового API.

### Этап 10. Тесты и валидация

- Юнит‑тесты генераторов (распределения, связность графа).
- Интеграционные: end‑to‑end цепочка генерация→индексация→поиск.
- Инварианты: города у дорог/воды; реки впадают; маршруты связны; роли NPC согласованы с зданиями/районами.

### Этап 11. Улучшения (после MVP)

- Гибридный поиск (named vectors + sparse + rerank).
- Расписания NPC (день/ночь), открытые часы, сцены/ограничения.
- Экономика: цены/логистика по дорогам, дефицит/излишки.
- Соц‑сеть NPC↔NPC (родство, союзы, вражда).
- Динамические события и симуляция.

### Разделение по неделям (ориентир)

- Неделя 1: Этапы 1–3 (онтология, гео, политика)
- Неделя 2: Этапы 4–5 (поселения, дороги, городская структура)
- Неделя 3: Этап 6–7 (домохозяйства, NPC по `NPC.md`)
- Неделя 4: Этап 8–9 (индексация, RAG, API) + тесты (Этап 10)

### Критерии готовности MVP

- Мир с 1–2 континентами, 3–5 стран, 5–10 городов, дорогами и базовыми районами.
- В каждом крупном городе: 1 innkeeper, 1 healer, 1 blacksmith, 1 guard captain; несколько гражданских NPC.
- Поиск NPC по роли+локации работает; `world_docs` подключены к генерации.
- Команда игрока “поговорить с трактирщиком”/“купить зелье у лекаря”/“купить лошадь у крестьянина” — резолвится и отрабатывает базовый флоу.

- Итог: строим мир как граф (источник истины), индексируем в векторку для RAG и навигации, NPC — по модульным capabilities из `NPC.md`.

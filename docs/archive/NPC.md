## NPC: архитектура, данные и взаимодействия

Краткий, практичный план, как описывать и обрабатывать NPC «от паука до короля». Этот документ — рабочая спецификация для внедрения без потерь деталей.

## Цели

- Общее ядро для любых NPC: животные, крестьяне, торговцы, лекари, короли, злодеи
- Единая схема данных и гибкая маршрутизация действий игрока
- Поддержка профессиональной торговли и ad-hoc сделок (переговоры за личное имущество)
- Детерминированные проверки и броски (правила), нарратив — LLM

## Данные NPC (минимальное ядро)

- **identity**: `name`, `aliases[]`, `titles[]` (опционально), `description`
- **taxonomy**: `species` (human, spider, undead …), `sapience_level` (non_sapient | animal | sentient), `faction`
- **roles**: `roles[]` — канонические роли для поиска/фильтров (например: `innkeeper`, `healer`, `blacksmith`, `guard`, `king`)
- **capabilities**: массив профилей возможностей (см. ниже)
- **state**: `current_location_id`, `mood`, `activity`, `disposition_to_player{player_id→-100..100}`, `relationship_to_player{player_id→label}`, `social_cooldowns{}`
- **possessions**: список владений (например, лошадь, телега, дом) — не магазин, а личное имущество
- **interaction_profile**: готовность к торгу/уступкам, пороги репутации, склонность к бартеру, законопослушность

Пример (логическая форма, не строгое API):

```json
{
  "name": "Олаф",
  "aliases": ["трактирщик", "бармен"],
  "roles": ["innkeeper", "rumor_monger"],
  "taxonomy": {
    "species": "human",
    "sapience_level": "sentient",
    "faction": "townsfolk"
  },
  "state": {
    "current_location_id": "UUID",
    "mood": "busy",
    "activity": "serving"
  },
  "capabilities": {
    /* см. раздел Capabilities */
  },
  "possessions": [
    { "entity_id": "<horse_uuid>", "type": "item", "kind": "mount" }
  ],
  "interaction_profile": {
    "willingness_to_sell_personal": 0.2,
    "barter": true,
    "lawfulness": 0.7
  }
}
```

## Capabilities (способности NPC)

Хранятся как вложенные профили. Добавляйте по мере надобности.

- **trade_capability**: торговля товарами

  - `is_professional: bool` — проф. торговец (витрина/склад) или нет
  - `offers[]` — каталог (для проф. торговцев), с ценой/стоком/требованиями
  - `pricing_policy` — коэффициенты к базовым ценам, скидки/надбавки (репутация, редкость)
  - `willingness_to_sell_personal: 0..1` — готовность продавать личные вещи (для непроф. продавцов)
  - `barter_policy` — бартер допускается или нет
  - `legal_constraints` — ограничения по закону/фракции

- **service_capability**: услуги (лекарь, тренер, ремесленник, транспорт)

  - `services[]` — id/название, цена, материалы/условия, риск, кулдауны, расписание

- **social_capability**: социальные действия и гейты

  - требования/кулдауны к Persuasion/Deception/Intimidation/Performance; эффекты на disposition/relationship

- **romance_capability** (опционально):

  - условия допуска (возраст, табу, культура), прогрессия стадий, кулдауны, события

- **authority_capability** (власть/протокол):

  - аудитории, доступ, охрана, санкции, дипломатия

- **combat_capability**: параметры боя/агрессии/эскалации

- **knowledge/rumor_capability**: знания, слухи, темы

- **quest_giver_capability**: выдача/приём квестов, требования допуска

- **hireling_capability**: наём спутников/охранников, условия контракта

- **transport_capability**: перевозки, аренда, маршруты

- **crafting_capability**: ремонт/создание, требования, время

Мини-формат для хранения (пример):

```json
"capabilities": {
  "trade": {
    "is_professional": true,
    "offers": [{"item_id": "<uuid>", "price": 15, "stock": 3, "tags": ["food"]}],
    "pricing_policy": {"base_coef": 1.0, "reputation_discounts": {"friendly": -0.1}},
    "willingness_to_sell_personal": 0.1,
    "barter_policy": {"enabled": true}
  },
  "service": {
    "services": [{"id": "healing", "price": 25, "requires": ["herbs"], "cooldown_sec": 300}]
  }
}
```

## Интенты и слоты (NLU)

- **Основные интенты**: `TalkToNPC`, `Ask`, `Buy`, `Sell`, `Service`, `Steal`, `Attack`, `CastSpell`, `Move`, `Inspect`, `UseItem`, `PickUp`, `Give`, `SkillCheck`, `Rest`, `Inventory`, `Hire`, `Negotiate`.
- **Слоты**: `target_npc` (id/роль/алиас), `item`, `quantity`, `service_id`, `price`, `location`, `topic`.
- Маппинг: интент → capability/flow:
  - `Buy/Sell` → `trade_capability` (если prof) либо `negotiation_flow` (ad‑hoc у непроф.)
  - `Service` → `service_capability`
  - Социальные: → `social_capability` (+ броски/кулдауны)
  - Бой: → `combat_capability`

## Поиск/резолв NPC (Qdrant)

- Векторный поиск по тексту с фильтрами. Рекомендуемые поля в payload:
  - `entity_type`, `name`, `description`, `aliases[]`, `roles[]`, `current_location_id`, `is_alive`, `importance_level`
- Формирование текста для эмбеддинга: `name + roles + aliases + краткое описание + состояние`
- Фильтры: по `current_location_id`, `roles[]`, `is_alive`, сцене (в бою не торгует)
- Улучшения (по желанию): named vectors `alias_vec`/`desc_vec`, sparse + hybrid, rerank top‑N

Пример вызова (псевдо):

```json
{
  "vector": embedding("трактирщик бармен"),
  "limit": 5,
  "filter": {"must": [
    {"key": "entity_type", "match": {"value": "npc"}},
    {"key": "current_location_id", "match": {"value": "<player_loc_uuid>"}},
    {"key": "roles", "match": {"any": ["innkeeper", "barkeep"]}}
  ]}
}
```

## Фокус диалога и дизамбигуация

- В сессии хранить `focus_npc_id`: после успешного `TalkToNPC`
- Если игрок пишет `Buy` без NPC — использовать `focus_npc_id`
- При >1 кандидате в резолве — задавать уточнение (в мире): «Двое трактирщиков: Борис у площади, Марта на пристани. К кому?»

## Торговля: два пути

1. **Проф. торговля** (`trade_capability.is_professional=true`):
   - `start_trade(npc)` → витрина (категории/товары/цены)
   - `buy(item_id, qty)` / `sell(item_id, qty)` → проверки золота/лимитов/легальности → мутации → лог
2. **Ad-hoc сделка** (непроф. продавец, личные владения):
   - `negotiation_flow`: проверка `possessions` цели, `willingness_to_sell_personal`, законность
   - Скилл‑чеки (Persuasion/Insight/Intimidation) с модификаторами контекста
   - Цена = базовая × политика; успех → перевод владения, события/репутация

Кейс «купить лошадь у крестьянина» попадает во 2) путь.

## Социалка: дружба/вражда/романтика

- Использовать `disposition_to_player` и производные `relationship_to_player` («friendly/neutral/hostile»)
- Социальные проверки через кубы: skill (Persuasion/Deception/Intimidation/Performance) против DC, модификаторы: отношение, освещённость, толпа, сцена
- `romance_capability` — доп. гейты и прогрессия

## Кубы и правила (детерминировано)

- Все исходы, где есть шанс, решаются правилами/кубами (d20) с логированием seed/модификаторов
- LLM генерирует описание, но не «решает» исход

## Контекст и ограничения

- Сцена/время: ночью закрыто, в бою — нет торговли/услуг
- Закон/фракции: нелегальные сделки блокируются/наказываются
- Репутация/обещания/долги: влияют на цены/доступ/отношения
- Heat/suspicion: растущая подозрительность в локации

## Онтология и RU-нормализация

- Словарь синонимов ролей: «бармен/трактирщик/кабакер» → `innkeeper`
- Лемматизация (pymorphy2) для нормализации пользовательских фраз и алиасов

## Чек‑лист внедрения

- **Domain (`domain.entities.NPC`)**:
  - Добавить поля: `roles: List[str]`, `aliases: List[str]`, `capabilities: Dict[str, Any]`, `possessions: List[UUID] | List[Dict]]`
  - В `NPCState`: уже есть `current_location_id`, отношения/диспозиции — использовать
- **Vector DB (`infrastructure/vector_db.py`)**:
  - Включить `roles`, `aliases`, `current_location_id`, флаги из capabilities в `payload`
  - В `searchable_text` добавлять `roles/aliases` и краткие свойства способностей
  - При резолве NPC с ролью — фильтр `roles` + `current_location_id`
- **Semantic Parser (`core/semantic_parser.py`)**:
  - Добавить извлечение роли/предмета в слоты; при пустом NPC — использовать `focus_npc_id`
  - При множественных кандидатах — возвращать флаг дизамбигуации
- **Handlers**:
  - `dialogue_handler`: настраивать `focus_npc_id`; соц‑интенты (befriend и др.) через social engine
  - `trade_handler`: два пути — `start_trade` (проф.) и `negotiation_flow` (ad‑hoc)
  - `service_handler` (новый): услуги по `service_capability`
- **Session/Cache**:
  - Хранить/обновлять `focus_npc_id`, историю последних NPC
- **Tests**:
  - Резолв ролей по локации; дизамбигуация; покупка у проф. торговца и ad‑hoc у непроф.
  - Соц‑чеки, кулдауны, влияние на disposition/relationship

## Набор действий, поддерживаемых NPC

- Социалка: приветствие, беседа, вопросы, убеждение, обман, запугивание, выступление, дружба, романтика, подарки
- Торговля: проф. витрина и ad‑hoc сделки за личные вещи
- Услуги: лечение, обучение, ремесло, транспорт
- Квесты: выдача/сдача/обновление
- Бой/силовые: эскалация, сдача, арест (для стражи)
- Знания/слухи: подсказки/сплетни
- Наём/спутники: условия контракта
- Транспорт/владения: покупка/аренда лошадей, лодок, жилья

Эта схема масштабируется и покрывает «паук → крестьянин → король» за счёт ролей, модульных способностей и политик взаимодействия.

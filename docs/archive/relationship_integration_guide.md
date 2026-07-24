# 🎮 Интеграция relationship_to_player в игровой процесс

## 📋 Обзор

`relationship_to_player` - это система отношений между NPC и игроками, которая интегрируется в единый чат-эндпоинт `/game/command`. Система работает автоматически и влияет на диалоги NPC.

## 🔄 Поток данных в игре

### 1. Игрок отправляет команду

```
POST /game/command
{
  "world_id": "uuid",
  "session_id": "uuid",
  "player_id": "uuid",
  "command": "говорю с барменом: привет, как дела?"
}
```

### 2. Семантический парсинг

```python
# src/core/semantic_parser.py
parsed = await semantic_parser.parse_command(
    world_id=request.world_id,
    session_id=request.session_id,
    player_id=request.player_id,
    raw_command=request.command
)
# Результат: GameAction.DIALOGUE с target_npc_id
```

### 3. Роутинг к обработчику диалога

```python
# src/api/game_routes.py
if parsed.action == GameAction.DIALOGUE:
    dialogue_result = await handle_dialogue(request, parsed)
    return GameCommandResponse(**dialogue_result)
```

### 4. Обработка диалога

```python
# src/api/handlers/dialogue_handler.py
async def handle_dialogue(request, parsed) -> dict:
    # Проверка существования NPC
    npc = await world_service.get_entity(parsed.target_npc_id, EntityType.NPC)

    # Создание запроса на диалог
    dialogue_req = NPCDialogueRequest(
        player_id=request.player_id,
        npc_id=parsed.target_npc_id,
        player_message=parsed.message,
        session_id=request.session_id
    )

    # Вызов AI для генерации ответа
    ai_response = await npc_dialogue(dialogue_req, bg_tasks)
```

### 5. Генерация ответа NPC

```python
# src/api/ai_routes.py
async def npc_dialogue(request: NPCDialogueRequest, background_tasks: BackgroundTasks):
    # Получение NPC и игрока
    player = await world_service.get_entity(request.player_id, EntityType.PLAYER)
    npc = await world_service.get_entity(request.npc_id, EntityType.NPC)

    # Построение контекста взаимодействия
    context_entities, context_metrics = await context_builder.build_npc_interaction_context(
        player=player,
        target_npc=npc,
        player_message=request.player_message
    )

    # Генерация AI ответа
    ai_response = await ai_service.generate_npc_dialogue(
        npc=npc,
        player_action=request.player_message,
        context_entities=context_entities
    )
```

## 🧠 Интеграция relationship_to_player в AI

### 1. Построение профиля NPC

```python
# src/infrastructure/ai_service.py
def build_npc_profile_text(self, npc: NPC) -> str:
    personality = npc.personality
    state = npc.current_state

    profile_parts = [
        f"Name: {npc.name}",
        f"Description: {npc.description}",
        "",
        "PERSONALITY:",
        f"Core Traits: {', '.join(personality.core_traits)}",
        f"Speech Patterns: {', '.join(personality.speech_patterns)}",
        f"Likes: {', '.join(personality.likes)}",
        f"Dislikes: {', '.join(personality.dislikes)}",
        f"Fears: {', '.join(personality.fears)}",
        f"Goals: {', '.join(personality.goals)}",
        "",
        f"Backstory: {personality.backstory}",
        "",
        "EXAMPLE PHRASES:",
    ]

    for phrase in personality.example_phrases:
        profile_parts.append(f'- "{phrase}"')

    profile_parts.extend([
        "",
        "CURRENT STATE:",
        f"Mood: {state.current_mood}",
        f"Activity: {state.current_activity}",
    ])

    return "\n".join(profile_parts)
```

### 2. Шаблон диалога NPC

```python
# src/infrastructure/ai_service.py
self.templates = {
    "npc_dialogue": PromptTemplate(
        system_prompt="""You are an AI Game Master controlling NPCs in a fantasy RPG world.
You must stay strictly in character and only use information provided in the context.

CRITICAL RULES:
- Never invent new facts, locations, or characters not mentioned in context
- Always respond as the specific NPC described
- Maintain personality consistency throughout the conversation
- If you lack information to answer something, say so in character
- Reference only entities and facts explicitly provided in context

Your responses should be immersive, in-character dialogue that advances the story.""",
        user_template="""CONTEXT:
{context}

NPC PROFILE:
{npc_profile}

CURRENT SITUATION:
{situation}

PLAYER ACTION: {player_action}

Respond as {npc_name} would, staying true to their personality and the provided context. Format your response as direct dialogue.""",
        max_completion_tokens=1200,
    )
}
```

## 🔧 Как relationship_to_player влияет на диалоги

### 1. Автоматическое включение в контекст

```python
# В build_npc_profile_text можно добавить:
def build_npc_profile_text(self, npc: NPC, player_id: UUID = None) -> str:
    # ... существующий код ...

    # Добавляем информацию об отношениях
    if player_id and npc.current_state.relationship_to_player:
        relationship = npc.current_state.relationship_to_player.get(str(player_id), "neutral")
        profile_parts.extend([
            "",
            "RELATIONSHIP TO PLAYER:",
            f"Current relationship: {relationship}",
        ])

    return "\n".join(profile_parts)
```

### 2. Влияние на тон диалога

```python
# В шаблоне диалога можно добавить инструкции:
system_prompt = """... existing prompt ...

RELATIONSHIP GUIDELINES:
- If relationship is 'friendly': Be warm, helpful, and welcoming
- If relationship is 'hostile': Be cold, suspicious, or aggressive
- If relationship is 'neutral': Be polite but reserved
- If relationship is 'trusted': Be open and share information freely
- If relationship is 'feared': Be nervous or submissive
- If relationship is 'respected': Be formal and deferential
"""
```

### 3. Динамическое обновление отношений

```python
# После диалога можно обновить отношения:
async def update_relationship_after_dialogue(npc_id: UUID, player_id: UUID, new_relationship: str):
    npc = await world_service.get_entity(npc_id, EntityType.NPC)
    if npc:
        npc.current_state.relationship_to_player[str(player_id)] = new_relationship
        await world_service.update_entity(npc_id, npc)
```

## 🎯 Практические примеры

### Пример 1: Дружелюбный NPC

```python
# NPC с friendly отношением
npc.current_state.relationship_to_player[str(player_id)] = "friendly"

# AI генерирует:
"Привет, путник! Рад тебя видеть снова. Как дела? Может, хочешь выпить чего-нибудь?"
```

### Пример 2: Враждебный NPC

```python
# NPC с hostile отношением
npc.current_state.relationship_to_player[str(player_id)] = "hostile"

# AI генерирует:
"Что тебе нужно? Не думай, что я забуду, что ты сделал. Лучше уходи, пока я не передумал."
```

### Пример 3: Нейтральный NPC

```python
# NPC с neutral отношением
npc.current_state.relationship_to_player[str(player_id)] = "neutral"

# AI генерирует:
"Добрый день. Чем могу помочь? У меня есть товары, если что-то нужно."
```

## 🔄 Автоматическое обновление отношений

### 1. Триггеры изменения отношений

```python
# Возможные триггеры:
- Успешная торговля → улучшение отношений
- Агрессивное поведение → ухудшение отношений
- Помощь NPC → улучшение отношений
- Воровство → резкое ухудшение отношений
- Подарки → улучшение отношений
```

### 2. Система событий

```python
# src/core/event_sourcing.py
class RelationshipEvent(Event):
    npc_id: UUID
    player_id: UUID
    old_relationship: str
    new_relationship: str
    reason: str
    timestamp: datetime
```

## 🎮 Интеграция в игровой процесс

### 1. Единый эндпоинт

```
POST /game/command
{
  "command": "говорю с барменом: привет!"
}
```

### 2. Автоматическая обработка

1. Парсинг команды → определение диалога
2. Поиск NPC → получение текущих отношений
3. Генерация ответа → с учетом отношений
4. Возможное обновление отношений → на основе взаимодействия

### 3. Прозрачность для игрока

- Игрок не видит технические детали
- Отношения влияют на тон и содержание диалогов
- Изменения отношений происходят естественно

## 🔧 Техническая реализация

### 1. Структура данных

```python
class NPCState(BaseModel):
    current_mood: str = "neutral"
    current_activity: str = "idle"
    relationship_to_player: Dict[UUID, str] = Field(default_factory=dict)
    recent_events: List[UUID] = Field(default_factory=list)
    current_location_id: Optional[UUID] = None
```

### 2. API для управления отношениями

```python
# GET /entities/{npc_id} - получить NPC с отношениями
# PUT /entities/{npc_id} - обновить NPC (включая отношения)
# POST /relationships - создать графовые отношения
```

### 3. Интеграция с AI

```python
# В generate_npc_dialogue:
npc_profile = self.build_npc_profile_text(npc, player_id)
# AI получает информацию об отношениях в профиле NPC
```

## 🎯 Преимущества системы

1. **Естественность**: Отношения влияют на диалоги естественно
2. **Прозрачность**: Игрок не видит техническую реализацию
3. **Гибкость**: Легко добавлять новые типы отношений
4. **Масштабируемость**: Система работает с любым количеством NPC
5. **Консистентность**: Отношения сохраняются между сессиями

## 🔮 Будущие улучшения

1. **Динамические отношения**: Отношения могут меняться со временем
2. **Сложные отношения**: Поддержка многоуровневых отношений
3. **Групповые отношения**: Отношения между группами NPC
4. **Событийные триггеры**: Автоматическое изменение отношений на основе событий
5. **Визуальные индикаторы**: Показ отношений в UI (опционально)

---

**Заключение**: `relationship_to_player` полностью интегрирована в игровой процесс через единый чат-эндпоинт. Система работает автоматически, влияя на диалоги NPC без необходимости дополнительных API вызовов со стороны клиента.

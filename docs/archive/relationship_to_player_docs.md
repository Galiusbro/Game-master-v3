# Relationship to Player - Документация

## 📋 Обзор

`relationship_to_player` - это система отслеживания отношений между NPC и игроками в Game Master V3.

## 🏗️ Архитектура

### Структура данных

```python
class NPCState(BaseModel):
    """Dynamic state of an NPC"""
    current_mood: str = "neutral"
    current_activity: str = "idle"
    relationship_to_player: Dict[UUID, str] = Field(default_factory=dict)  # player_id -> relationship
    recent_events: List[UUID] = Field(default_factory=list)
    current_location_id: Optional[UUID] = None
```

### Типы отношений

```python
# Примеры значений relationship_to_player
relationship_types = {
    "friendly": "дружелюбное отношение",
    "hostile": "враждебное отношение",
    "neutral": "нейтральное отношение",
    "trusted": "доверяет",
    "feared": "боится",
    "respected": "уважает",
    "despised": "презирает",
    "loved": "любит",
    "hated": "ненавидит",
    "admired": "восхищается",
    "pity": "жалеет"
}
```

## 🔧 Как это работает

### 1. В коде Python

```python
# Получение NPC
npc = await world_service.get_entity(npc_id, EntityType.NPC)

# Установка отношения
npc.current_state.relationship_to_player[player_id] = "friendly"

# Получение отношения
relationship = npc.current_state.relationship_to_player.get(player_id, "neutral")

# Обновление отношения
npc.current_state.relationship_to_player[player_id] = "hostile"
```

### 2. В JSON API

```json
{
  "current_state": {
    "current_mood": "happy",
    "current_activity": "greeting visitors",
    "relationship_to_player": {
      "player_uuid_string": "friendly"
    },
    "recent_events": [],
    "current_location_id": null
  }
}
```

### 3. В Neo4j Graph Database

```cypher
// Создание отношения между NPC и игроком
MATCH (npc:Entity {id: "npc_uuid"})
MATCH (player:Entity {id: "player_uuid"})
CREATE (npc)-[r:KNOWS {relationship: "friendly", trust_level: 5}]->(player)
```

## 🚨 Проблема с UUID сериализацией

### Проблема

При попытке обновить NPC через API возникает ошибка:

```
keys must be str, int, float, bool or None, not UUID
```

### Причина

- В коде `relationship_to_player` определен как `Dict[UUID, str]`
- При сериализации в JSON UUID объекты не могут быть ключами
- JSON требует строковые ключи

### Решение

Нужно конвертировать UUID в строки при работе с JSON:

```python
# Правильное использование в API
npc['current_state']['relationship_to_player'][str(player_id)] = "friendly"

# В коде Python можно использовать UUID объекты
npc.current_state.relationship_to_player[player_id] = "friendly"
```

## 📊 Примеры использования

### Создание NPC с отношениями

```python
npc_data = {
    "entity_data": {
        "name": "Barliman Butterbur",
        "description": "Tavern keeper",
        "current_state": {
            "current_mood": "content",
            "current_activity": "cleaning glasses",
            "relationship_to_player": {
                "player_uuid_string": "friendly"  # Строковый ключ
            },
            "recent_events": [],
            "current_location_id": None
        }
    },
    "entity_type": "npc"
}
```

### Обновление отношений

```python
# Получаем NPC
response = requests.get(f"{BASE_URL}/entities/{npc_id}")
npc = response.json()['entity']

# Обновляем отношения (используем строковые ключи)
npc['current_state']['relationship_to_player'][str(player_id)] = "trusted"

# Отправляем обновление
update_data = {
    "entity_data": npc,
    "actor_id": str(uuid.uuid4()),
    "session_id": str(uuid.uuid4())
}
response = requests.put(f"{BASE_URL}/entities/{npc_id}", json=update_data)
```

### Проверка отношений

```python
# Получаем отношение NPC к игроку
npc = await world_service.get_entity(npc_id, EntityType.NPC)
relationship = npc.current_state.relationship_to_player.get(player_id, "neutral")

if relationship == "friendly":
    print("NPC дружелюбен к игроку")
elif relationship == "hostile":
    print("NPC враждебен к игроку")
else:
    print(f"NPC относится {relationship} к игроку")
```

## 🔄 Интеграция с системой отношений

### Graph Database Relations

Система также поддерживает отношения в графовой базе данных:

```python
# Создание отношения в графе
await world_service.create_relationship(
    from_entity_id=npc_id,
    to_entity_id=player_id,
    relationship_type="KNOWS",
    properties={
        "relationship": "friendly",
        "trust_level": 5,
        "first_met": "today"
    },
    actor_id=actor_id
)
```

### Event Logging

Все изменения отношений логируются:

```python
# Автоматическое логирование при обновлении NPC
await event_store.log_change(
    event_id=event_id,
    entity_type=EntityType.NPC,
    entity_id=npc_id,
    action_type=ActionType.WORLD_CHANGE,
    before_state={"relationship_to_player": {}},
    after_state={"relationship_to_player": {str(player_id): "friendly"}},
    session_id=session_id
)
```

## 🎯 Лучшие практики

### 1. Используйте строковые ключи в API

```python
# ✅ Правильно
npc['current_state']['relationship_to_player'][str(player_id)] = "friendly"

# ❌ Неправильно
npc['current_state']['relationship_to_player'][player_id] = "friendly"
```

### 2. Проверяйте существование отношений

```python
# Безопасное получение отношения
relationship = npc.current_state.relationship_to_player.get(player_id, "neutral")
```

### 3. Используйте константы для типов отношений

```python
RELATIONSHIP_TYPES = {
    "FRIENDLY": "friendly",
    "HOSTILE": "hostile",
    "NEUTRAL": "neutral",
    "TRUSTED": "trusted"
}
```

### 4. Логируйте изменения отношений

```python
# Логирование изменения отношения
logger.info(f"NPC {npc.name} теперь относится {new_relationship} к игроку {player_id}")
```

## 🔮 Будущие улучшения

1. **Типизированные отношения** - enum для типов отношений
2. **Временные отношения** - отношения с истечением срока действия
3. **Сложные отношения** - отношения с дополнительными параметрами
4. **Групповые отношения** - отношения к группам игроков
5. **Динамические отношения** - автоматическое изменение отношений на основе действий

## 📝 Заключение

`relationship_to_player` - это мощная система для отслеживания отношений между NPC и игроками. Основная проблема заключается в правильной сериализации UUID в JSON, что решается использованием строковых ключей при работе с API.

# Game Master V3 - AI-Powered RPG System

Новое поколение ИИ-гейм-мастера с живым, персистентным миром.

## ✨ Ключевые особенности

- **🌍 Живой мир**: Все изменения сохраняются и влияют на будущие события
- **🧠 Semantic Search**: Умный поиск по смыслу через Vector DB
- **📈 Graph Relations**: Сложные связи между всеми объектами мира
- **📝 Event Sourcing**: Полная история изменений с возможностью отката
- **👥 Multi-player**: Консистентный мир для множественных игроков
- **🔍 Anti-hallucination**: Валидация ответов ИИ против базы знаний

## 🏗️ Архитектура

- **Graph DB**: Neo4j для связей между сущностями
- **Vector DB**: Qdrant для semantic search
- **Event Store**: PostgreSQL для event sourcing
- **Cache**: Redis для производительности
- **API**: FastAPI с async/await
- **Monitoring**: Prometheus + Grafana

## 📁 Структура проекта

```
game_master_v3/
├── src/
│   ├── api/              # REST API endpoints
│   ├── core/             # Основная бизнес-логика
│   ├── domain/           # Entities и domain models
│   ├── infrastructure/   # Database integrations
│   └── tests/           # Unit & integration tests
├── docker/              # Docker compose + configs
├── scripts/             # Utility scripts
├── config/              # Settings и конфигурация
└── docs/               # Архитектурная документация
```

## 🚀 Быстрый старт

### Предварительные требования

- Docker & Docker Compose
- Python 3.11+
- Make (опционально)

### Установка и запуск

```bash
# 1. Клонировать и перейти в директорию
cd game_master_v3

# 2. Запустить все сервисы и инициализировать данные
make dev

# ИЛИ вручную:
make start          # Запуск Docker services
make install        # Установка Python зависимостей
make init          # Инициализация БД с примером мира
```

### Проверка работы

```bash
# Статус сервисов
make status

# Логи
make logs

# Пример использования API
python example_usage.py
```

## 📡 Доступные сервисы

После запуска доступны:

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Prometheus Metrics**: http://localhost:8000/metrics
- **Neo4j Browser**: http://localhost:7474 (neo4j/gamemaster123)
- **Qdrant Dashboard**: http://localhost:6333/dashboard
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

## 🧪 Тестирование

```bash
# Запуск unit tests
make test

# Пример использования API
python example_usage.py

# Тестирование AI возможностей (требует OpenAI API key)
export OPENAI_API_KEY='your-api-key-here'
make demo-ai
```

## 🛠️ Development

### Команды Make

```bash
make help          # Показать все команды
make start         # Запустить сервисы
make stop          # Остановить сервисы
make clean         # Очистить данные
make init          # Инициализировать БД
make logs          # Показать логи
make api           # Запуск API локально
make reset         # Полный сброс и перезапуск
```

### Архитектурные фазы

✅ **Phase 1**: Core data layer + basic orchestrator  
✅ **Phase 2**: AI integration + quality control  
⏳ **Phase 3**: Performance & scale optimization  
⏳ **Phase 4**: Game logic & balance

## 🎮 Пример использования

Создан мир с таверной "The Prancing Pony", где есть:

- 🏠 **Локация**: The Prancing Pony tavern
- 👤 **NPC**: Barliman Butterbur (трактирщик)
- 🍺 **Предмет**: Mug of Ale
- 🎭 **Игрок**: Adventurer

```python
# Поиск по миру
POST /api/v1/search
{
  "query": "tavern ale bartender",
  "limit": 5
}

# Получение контекста локации
GET /api/v1/entities/{tavern_id}/context

# История изменений
GET /api/v1/entities/{entity_id}/history

# AI Features (Phase 2) - требует OPENAI_API_KEY
# NPC диалоги
POST /api/v1/ai/npc/dialogue
{
  "player_id": "uuid",
  "npc_id": "uuid",
  "player_message": "Hello! Tell me about this place."
}

# Описание мира
POST /api/v1/ai/world/describe
{
  "player_id": "uuid",
  "request": "Describe what I see around me"
}

# Предварительный просмотр контекста ИИ
GET /api/v1/ai/context/preview/{player_id}

# Prometheus метрики
GET /metrics
```

## 📊 Мониторинг

Система предоставляет детальные Prometheus метрики:

### AI Operations

- `gamemaster_ai_requests_total` - Общее количество AI запросов
- `gamemaster_ai_request_duration_seconds` - Время выполнения AI запросов
- `gamemaster_ai_tokens_total` - Количество использованных токенов
- `gamemaster_ai_confidence_score` - Показатели уверенности AI
- `gamemaster_ai_hallucinations_total` - Обнаруженные галлюцинации

### Context Building

- `gamemaster_context_entities_total` - Количество сущностей в контексте
- `gamemaster_context_build_duration_seconds` - Время сборки контекста

### Database Operations

- `gamemaster_db_operations_total` - Операции с базами данных
- `gamemaster_db_operation_duration_seconds` - Время выполнения запросов

Доступ к метрикам: http://localhost:8000/metrics

## 📚 Документация

- [Техническая архитектура](docs/tech.md)
- [Концепция продукта](docs/description.md)
- [Q&A по реализации](docs/QA.md)

## 🤝 Contributing

Проект находится в активной разработке. Основные компоненты Phase 1 реализованы и готовы для тестирования и развития.

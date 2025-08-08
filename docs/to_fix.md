Qdrant: клиент 1.15.1, сервер 1.7.3. Это несовпадение версий может в будущем дать сбои.

1. 🤖 AI Response Quality (game_routes.py)

   - Определение качества ответов ИИ
   - Замена keywords: 'can't assist', 'sorry'

2. 💡 Lighting Conditions (semantic_parser.py)

   - Определение освещения локации
   - Замена keywords: 'dark', 'bright', 'shadow'

3. 💀 Entity State Detection (clean_all_barliman.py)

   - Состояние NPC (живой/мертвый)
   - Замена keywords: 'lifeless', 'motionless'

4. 📊 Content Quality Analysis (ai_quality_analysis.py)

   - Семантическая оценка качества контента
   - Замена списков индикаторов

   🎯 3. ПРИОРИТЕТНЫЕ ВОЗМОЖНОСТИ:
   🥇 HIGH PRIORITY:
   🏰 Location Type Classification - заменит hardcoded проверки в \_determine_game_context
   😤 NPC Attitude Detection - решит TODO в semantic_parser.py и game_routes.py
   ⚡ Action Urgency - улучшит DC calculation и time management
   🥈 MEDIUM PRIORITY:
   🎨 Description Tone Matching - сделает AI responses более консистентными
   🧙‍♂️ Magic Type Detection - улучшит magic system
   ⚔️ Combat Intensity - для dynamic encounter scaling
   🥉 FUTURE ENHANCEMENTS:
   📚 Knowledge Domain - что знает персонаж (history, arcana, nature)
   🎭 Social Context - formal/informal speech detection
   🌟 Item Rarity - automatic loot classification
   💡 РЕКОМЕНДАЦИЯ:
   Начнем с топ-3 категорий:
   🏰 Location Type - больше всего hardcoded логики
   😤 NPC Attitude - много TODO заменим
   ⚡ Action Urgency - улучшит gameplay mechanics
   Какую категорию хочешь реализовать первой? 🚀
   Location Type выглядит самой полезной - она заменит много hardcoded проверок и улучшит context determination!

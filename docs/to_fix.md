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

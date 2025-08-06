# D&D 5e Mechanics Implementation

## 🎯 What We've Implemented

### 1. **Complete D&D 5e Character System**

**Domain Entities (`src/domain/entities.py`):**

- `PlayerStats` - Full D&D 5e character statistics
- `AbilityScore` enum - STR, DEX, CON, INT, WIS, CHA
- `SkillType` enum - All 18 D&D skills
- `CharacterClass` enum - Fighter, Rogue, Wizard, etc.
- `DiceRoll` - Complete dice roll tracking with metadata
- `ActionSequence` - Complex multi-roll action resolution

**Key Features:**

- Ability scores (3-20 range)
- Calculated modifiers `((score - 10) // 2)`
- Skill bonuses (ability + proficiency if trained)
- Saving throws
- Hit points, AC, proficiency bonus
- Class-specific proficiencies

### 2. **Advanced Dice Engine**

**Core System (`src/core/dice_engine.py`):**

- `DiceEngine` - Central dice rolling system
- Supports complex notation: `1d20+5`, `2d6+3`, etc.
- Advantage/Disadvantage (roll twice, take higher/lower)
- Critical hits (natural 20) and fumbles (natural 1)
- Automatic DC (Difficulty Class) determination

**Dice Roll Types:**

- Ability checks
- Skill checks
- Saving throws
- Attack rolls
- Damage rolls
- Initiative

**Smart DC Assignment:**

- Easy: DC 10
- Medium: DC 15
- Hard: DC 20
- Contextual modifiers (lighting, NPC attitude, etc.)

### 3. **Natural Language Processing**

**Enhanced Semantic Parser (`src/core/semantic_parser.py`):**

- Detects skill checks in natural language
- Maps commands to appropriate skills
- Estimates difficulty automatically
- Context-aware parsing

**Examples:**

- "I sneak past the guard" → Stealth check
- "I try to convince him" → Persuasion check
- "I carefully examine the lock" → Investigation check
- "I attempt to pickpocket" → Sleight of Hand check

### 4. **AI Integration**

**Enhanced AI Service (`src/infrastructure/ai_service.py`):**

- New `dice_outcome_narration` template
- Contextual narrative based on dice results
- Special handling for critical success/failure
- Anti-hallucination for dice outcomes

**AI understands:**

- Success vs failure
- Degree of success (high vs low rolls)
- Critical successes (natural 20)
- Critical failures (natural 1)

### 5. **Complete API**

**Character Management (`src/api/game_routes.py`):**

- `POST /game/character/create` - Create D&D characters
- `GET /game/character/{id}/stats` - View full character sheet
- `POST /game/character/{id}/level-up` - Level advancement

**Enhanced Game Commands:**

- Automatic skill check detection
- Dice roll integration
- Result narration
- Roll history tracking

## 🎮 How It Works In Practice

### Example Flow:

1. **Player says:** "I try to sneak past the guard"

2. **System processes:**

   ```
   Semantic Parser → "STEALTH action detected"
   Dice Engine → "1d20 + DEX mod + proficiency vs DC 15"
   Roll Result → "17 (SUCCESS)"
   AI Service → "Narrate successful stealth"
   ```

3. **Player gets:**
   ```
   🎲 Stealth Check: 17 vs DC 15 (SUCCESS)
   📖 "You move like a shadow, your footsteps silent on the stone floor.
       The guard remains oblivious as you slip past..."
   ```

### Character Creation:

```json
{
  "name": "Sneaky Pete",
  "character_class": "rogue",
  "ability_scores": {
    "strength": 12,
    "dexterity": 17,
    "constitution": 14,
    "intelligence": 13,
    "wisdom": 15,
    "charisma": 10
  }
}
```

**Result:** Full D&D character with:

- Calculated HP (8 + CON mod)
- AC (10 + DEX mod)
- Class proficiencies (Rogue gets Stealth, Sleight of Hand, etc.)
- Skill bonuses automatically calculated

## 🔧 Technical Architecture

### SOLID Principles Followed:

- **Single Responsibility:** Each class has one purpose
- **Open/Closed:** Easy to add new skills, classes, rules
- **Liskov Substitution:** All dice rolls follow same interface
- **Interface Segregation:** Specific enums for different concepts
- **Dependency Inversion:** Core logic doesn't depend on infrastructure

### Extensibility:

- Add new character classes → Update `CharacterClass` enum
- Add new skills → Update `SkillType` enum and skill mapping
- Add new dice types → Extend `DiceRollType` enum
- Custom rules → Extend `DiceEngine.resolve_complex_action()`

## 🧪 Testing

Run the demo:

```bash
# Ensure system is running
make dev

# Test D&D mechanics
python example_dnd_usage.py
```

**What the demo tests:**

- ✅ Character creation
- ✅ Skill detection from natural language
- ✅ Automatic dice rolling
- ✅ AI narrative generation
- ✅ Roll history tracking
- ✅ Full character sheet display

## 🚀 Next Steps

**Phase 1 Complete:** Basic D&D system ✅

**Phase 2 Ideas:**

- Combat system (initiative, attacks, damage)
- Magic system (spell slots, spell checks)
- Equipment system (weapons, armor, bonuses)
- Advanced NPCs with stats
- Multi-target actions
- Reactions and opportunities

**Phase 3 Ideas:**

- Character advancement (XP, leveling, feat selection)
- Multiple character classes
- Multiclassing support
- Custom backgrounds and races
- Advanced spellcasting

## 💬 Natural Language Examples

The system now understands:

**Russian:**

- "подкрадываюсь к стражнику" → Stealth check
- "пытаюсь убедить торговца" → Persuasion check
- "внимательно осматриваю комнату" → Investigation check

**English:**

- "I sneak past the guards" → Stealth check
- "I try to convince the merchant" → Persuasion check
- "I carefully examine the room" → Investigation check

**Action Words:**

- "attempt", "try", "check" → Triggers dice rolls
- "carefully", "thoroughly" → May add bonuses/advantages
- "quickly", "hastily" → May add penalties/disadvantages

---

The system is now a **true D&D 5e digital game master** that understands natural language, automatically handles complex dice mechanics, and provides rich narrative feedback! 🎲⚔️🧙‍♂️

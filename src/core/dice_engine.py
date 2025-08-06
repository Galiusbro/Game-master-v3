"""
Dice Rolling Engine for Game Master V3
Handles all dice mechanics, skill checks, and complex action resolution
"""
import logging
import random
import re
from typing import Dict, List, Optional, Tuple, Union
from uuid import UUID, uuid4
from datetime import datetime

from domain.entities import (
    DiceRoll, DiceRollType, ActionSequence, Player, NPC, AbilityScore, SkillType
)

logger = logging.getLogger(__name__)


class DiceNotationError(Exception):
    """Raised when dice notation is invalid"""
    pass


class DifficultyClass:
    """Standard D&D 5e Difficulty Classes"""
    TRIVIAL = 5
    EASY = 10
    MEDIUM = 15
    HARD = 20
    VERY_HARD = 25
    NEARLY_IMPOSSIBLE = 30


class DiceEngine:
    """Core dice rolling and action resolution engine"""
    
    def __init__(self):
        self.random = random.Random()
        # Seed with current time for true randomness
        self.random.seed()
    
    def roll_dice(self, notation: str) -> List[int]:
        """
        Roll dice from notation like '1d20', '2d6+3', '1d8+STR'
        Returns list of raw dice values (not including modifiers)
        """
        # Parse notation: XdY+Z or XdY-Z or just XdY
        pattern = r'(\d+)d(\d+)(?:([+-])(\d+))?'
        match = re.match(pattern, notation.lower().replace(' ', ''))
        
        if not match:
            raise DiceNotationError(f"Invalid dice notation: {notation}")
        
        num_dice = int(match.group(1))
        die_size = int(match.group(2))
        
        if num_dice <= 0 or die_size <= 0:
            raise DiceNotationError(f"Invalid dice parameters: {num_dice}d{die_size}")
        
        if num_dice > 100 or die_size > 1000:
            raise DiceNotationError(f"Dice parameters too large: {num_dice}d{die_size}")
        
        # Roll the dice
        results = []
        for _ in range(num_dice):
            roll = self.random.randint(1, die_size)
            results.append(roll)
        
        return results
    
    def parse_modifier(self, notation: str) -> int:
        """Extract modifier from dice notation"""
        pattern = r'\d+d\d+([+-]\d+)'
        match = re.search(pattern, notation.lower().replace(' ', ''))
        
        if match:
            modifier_str = match.group(1)
            return int(modifier_str)
        
        return 0
    
    def make_ability_check(
        self,
        character: Player,
        ability: AbilityScore,
        dc: int,
        advantage: bool = False,
        disadvantage: bool = False,
        description: str = ""
    ) -> DiceRoll:
        """Make a D&D 5e ability check"""
        
        if advantage and disadvantage:
            # Advantage and disadvantage cancel out
            advantage = disadvantage = False
        
        # Roll d20 (or 2d20 for advantage/disadvantage)
        if advantage or disadvantage:
            rolls = [self.random.randint(1, 20), self.random.randint(1, 20)]
            if advantage:
                dice_result = max(rolls)
            else:  # disadvantage
                dice_result = min(rolls)
        else:
            dice_result = self.random.randint(1, 20)
            rolls = [dice_result]
        
        # Calculate modifier
        ability_modifier = character.stats.get_ability_modifier(ability)
        
        # Total result
        total = dice_result + ability_modifier
        
        # Create roll object
        roll = DiceRoll(
            roll_type=DiceRollType.ABILITY_CHECK,
            dice_notation=f"1d20+{ability_modifier}" + (" (advantage)" if advantage else " (disadvantage)" if disadvantage else ""),
            raw_results=rolls,
            modifiers=ability_modifier,
            total=total,
            difficulty_class=dc,
            advantage=advantage,
            disadvantage=disadvantage,
            is_success=total >= dc,
            is_critical=dice_result == 20,
            is_fumble=dice_result == 1,
            roller_id=character.id,
            description=description or f"{ability.value.title()} check"
        )
        
        logger.info(f"Ability check: {ability.value} DC {dc} -> {total} ({'Success' if roll.is_success else 'Failure'})")
        return roll
    
    def make_skill_check(
        self,
        character: Player,
        skill: SkillType,
        dc: int,
        advantage: bool = False,
        disadvantage: bool = False,
        description: str = ""
    ) -> DiceRoll:
        """Make a D&D 5e skill check"""
        
        if advantage and disadvantage:
            advantage = disadvantage = False
        
        # Roll d20
        if advantage or disadvantage:
            rolls = [self.random.randint(1, 20), self.random.randint(1, 20)]
            if advantage:
                dice_result = max(rolls)
            else:
                dice_result = min(rolls)
        else:
            dice_result = self.random.randint(1, 20)
            rolls = [dice_result]
        
        # Calculate skill bonus
        skill_bonus = character.stats.get_skill_bonus(skill)
        
        # Total result
        total = dice_result + skill_bonus
        
        roll = DiceRoll(
            roll_type=DiceRollType.SKILL_CHECK,
            dice_notation=f"1d20+{skill_bonus}" + (" (advantage)" if advantage else " (disadvantage)" if disadvantage else ""),
            raw_results=rolls,
            modifiers=skill_bonus,
            total=total,
            difficulty_class=dc,
            advantage=advantage,
            disadvantage=disadvantage,
            is_success=total >= dc,
            is_critical=dice_result == 20,
            is_fumble=dice_result == 1,
            roller_id=character.id,
            description=description or f"{skill.value.replace('_', ' ').title()} check"
        )
        
        logger.info(f"Skill check: {skill.value} DC {dc} -> {total} ({'Success' if roll.is_success else 'Failure'})")
        return roll
    
    def make_saving_throw(
        self,
        character: Player,
        ability: AbilityScore,
        dc: int,
        advantage: bool = False,
        disadvantage: bool = False,
        description: str = ""
    ) -> DiceRoll:
        """Make a D&D 5e saving throw"""
        
        if advantage and disadvantage:
            advantage = disadvantage = False
        
        # Roll d20
        if advantage or disadvantage:
            rolls = [self.random.randint(1, 20), self.random.randint(1, 20)]
            if advantage:
                dice_result = max(rolls)
            else:
                dice_result = min(rolls)
        else:
            dice_result = self.random.randint(1, 20)
            rolls = [dice_result]
        
        # Calculate saving throw bonus
        save_bonus = character.stats.get_saving_throw_bonus(ability)
        
        # Total result
        total = dice_result + save_bonus
        
        roll = DiceRoll(
            roll_type=DiceRollType.SAVING_THROW,
            dice_notation=f"1d20+{save_bonus}" + (" (advantage)" if advantage else " (disadvantage)" if disadvantage else ""),
            raw_results=rolls,
            modifiers=save_bonus,
            total=total,
            difficulty_class=dc,
            advantage=advantage,
            disadvantage=disadvantage,
            is_success=total >= dc,
            is_critical=dice_result == 20,
            is_fumble=dice_result == 1,
            roller_id=character.id,
            description=description or f"{ability.value.title()} saving throw"
        )
        
        logger.info(f"Saving throw: {ability.value} DC {dc} -> {total} ({'Success' if roll.is_success else 'Failure'})")
        return roll
    
    def make_attack_roll(
        self,
        attacker: Player,
        target_ac: int,
        weapon_bonus: int = 0,
        advantage: bool = False,
        disadvantage: bool = False,
        description: str = ""
    ) -> DiceRoll:
        """Make an attack roll"""
        
        if advantage and disadvantage:
            advantage = disadvantage = False
        
        # Roll d20
        if advantage or disadvantage:
            rolls = [self.random.randint(1, 20), self.random.randint(1, 20)]
            if advantage:
                dice_result = max(rolls)
            else:
                dice_result = min(rolls)
        else:
            dice_result = self.random.randint(1, 20)
            rolls = [dice_result]
        
        # Calculate attack bonus (STR/DEX + proficiency + weapon bonus)
        # TODO: Determine if STR or DEX based on weapon type
        str_modifier = attacker.stats.get_ability_modifier(AbilityScore.STRENGTH)
        attack_bonus = str_modifier + attacker.stats.proficiency_bonus + weapon_bonus
        
        # Total result
        total = dice_result + attack_bonus
        
        roll = DiceRoll(
            roll_type=DiceRollType.ATTACK_ROLL,
            dice_notation=f"1d20+{attack_bonus}" + (" (advantage)" if advantage else " (disadvantage)" if disadvantage else ""),
            raw_results=rolls,
            modifiers=attack_bonus,
            total=total,
            difficulty_class=target_ac,
            advantage=advantage,
            disadvantage=disadvantage,
            is_success=total >= target_ac,
            is_critical=dice_result == 20,
            is_fumble=dice_result == 1,
            roller_id=attacker.id,
            description=description or "Attack roll"
        )
        
        logger.info(f"Attack roll: {total} vs AC {target_ac} ({'Hit' if roll.is_success else 'Miss'})")
        return roll
    
    def make_damage_roll(
        self,
        attacker: Player,
        damage_dice: str,
        damage_type: str = "physical",
        critical: bool = False,
        description: str = ""
    ) -> DiceRoll:
        """Make a damage roll"""
        
        # Parse damage dice (e.g., "1d8+3")
        dice_results = self.roll_dice(damage_dice)
        modifier = self.parse_modifier(damage_dice)
        
        # Critical hits double the dice (not the modifier)
        if critical:
            extra_dice = self.roll_dice(damage_dice.split('+')[0].split('-')[0])  # Just the XdY part
            dice_results.extend(extra_dice)
        
        total = sum(dice_results) + modifier
        
        roll = DiceRoll(
            roll_type=DiceRollType.DAMAGE_ROLL,
            dice_notation=damage_dice + (" (critical)" if critical else ""),
            raw_results=dice_results,
            modifiers=modifier,
            total=total,
            is_critical=critical,
            roller_id=attacker.id,
            description=description or f"{damage_type.title()} damage"
        )
        
        logger.info(f"Damage roll: {damage_dice} -> {total} {damage_type} damage" + (" (critical!)" if critical else ""))
        return roll
    
    def determine_difficulty_class(
        self,
        action_description: str,
        context: Dict[str, any] = None
    ) -> int:
        """
        Automatically determine appropriate DC based on action description and context
        This is where AI-like intelligence helps set appropriate challenges
        """
        action_lower = action_description.lower()
        
        # Context modifiers
        base_dc = DifficultyClass.MEDIUM  # Default to DC 15
        
        # Stealth actions
        if any(word in action_lower for word in ['sneak', 'stealth', 'hide', 'подкрасться', 'спрятаться']):
            base_dc = DifficultyClass.MEDIUM  # DC 15
            
            # Harder in daylight, easier at night
            if context and context.get('time_of_day') == 'day':
                base_dc += 2
            elif context and context.get('time_of_day') == 'night':
                base_dc -= 2
                
        # Persuasion/Deception
        elif any(word in action_lower for word in ['persuade', 'convince', 'lie', 'deceive', 'убедить', 'обмануть']):
            base_dc = DifficultyClass.MEDIUM  # DC 15
            
            # Harder if target is hostile
            if context and context.get('target_attitude') == 'hostile':
                base_dc += 5
            elif context and context.get('target_attitude') == 'friendly':
                base_dc -= 5
                
        # Physical tasks
        elif any(word in action_lower for word in ['climb', 'jump', 'lift', 'break', 'карабкаться', 'прыгать']):
            base_dc = DifficultyClass.MEDIUM  # DC 15
            
        # Investigation/Perception
        elif any(word in action_lower for word in ['search', 'look', 'find', 'notice', 'искать', 'найти']):
            base_dc = DifficultyClass.EASY  # DC 10 - finding obvious things should be easier
            
        # Combat maneuvers
        elif any(word in action_lower for word in ['disarm', 'trip', 'grapple', 'разоружить']):
            base_dc = DifficultyClass.HARD  # DC 20 - combat maneuvers are challenging
            
        # Magic/arcane
        elif any(word in action_lower for word in ['cast', 'magic', 'spell', 'колдовать', 'магия']):
            base_dc = DifficultyClass.MEDIUM  # DC 15
            
        return max(5, min(30, base_dc))  # Clamp between 5 and 30
    
    def resolve_complex_action(
        self,
        actor: Player,
        action_description: str,
        target_id: Optional[UUID] = None,
        context: Dict[str, any] = None
    ) -> ActionSequence:
        """
        Resolve a complex action that might require multiple rolls
        This is the main entry point for natural language actions
        """
        sequence = ActionSequence(
            action_description=action_description,
            actor_id=actor.id,
            target_id=target_id
        )
        
        action_lower = action_description.lower()
        
        # Determine what type of check this is and make appropriate rolls
        if any(word in action_lower for word in ['sneak', 'stealth', 'hide', 'подкрасться']):
            # Stealth check
            dc = self.determine_difficulty_class(action_description, context)
            roll = self.make_skill_check(
                actor, 
                SkillType.STEALTH, 
                dc,
                description=f"Stealth attempt: {action_description}"
            )
            sequence.primary_roll = roll
            sequence.success = roll.is_success
            
        elif any(word in action_lower for word in ['persuade', 'convince', 'убедить']):
            # Persuasion check
            dc = self.determine_difficulty_class(action_description, context)
            roll = self.make_skill_check(
                actor,
                SkillType.PERSUASION,
                dc,
                description=f"Persuasion attempt: {action_description}"
            )
            sequence.primary_roll = roll
            sequence.success = roll.is_success
            
        elif any(word in action_lower for word in ['lie', 'deceive', 'обмануть']):
            # Deception check
            dc = self.determine_difficulty_class(action_description, context)
            roll = self.make_skill_check(
                actor,
                SkillType.DECEPTION,
                dc,
                description=f"Deception attempt: {action_description}"
            )
            sequence.primary_roll = roll
            sequence.success = roll.is_success
            
        elif any(word in action_lower for word in ['pickpocket', 'steal', 'украсть']):
            # Sleight of Hand check
            dc = self.determine_difficulty_class(action_description, context)
            roll = self.make_skill_check(
                actor,
                SkillType.SLEIGHT_OF_HAND,
                dc,
                description=f"Sleight of Hand attempt: {action_description}"
            )
            sequence.primary_roll = roll
            sequence.success = roll.is_success
            
        elif any(word in action_lower for word in ['search', 'investigate', 'examine', 'искать']):
            # Investigation check
            dc = self.determine_difficulty_class(action_description, context)
            roll = self.make_skill_check(
                actor,
                SkillType.INVESTIGATION,
                dc,
                description=f"Investigation attempt: {action_description}"
            )
            sequence.primary_roll = roll
            sequence.success = roll.is_success
            
        elif any(word in action_lower for word in ['attack', 'hit', 'strike', 'атаковать']):
            # Attack roll - need target AC
            target_ac = context.get('target_ac', 15) if context else 15
            attack_roll = self.make_attack_roll(
                actor,
                target_ac,
                description=f"Attack: {action_description}"
            )
            sequence.primary_roll = attack_roll
            sequence.success = attack_roll.is_success
            
            # If attack hits, roll damage
            if attack_roll.is_success:
                damage_dice = context.get('weapon_damage', '1d6+3') if context else '1d6+3'
                damage_roll = self.make_damage_roll(
                    actor,
                    damage_dice,
                    critical=attack_roll.is_critical,
                    description="Weapon damage"
                )
                sequence.secondary_rolls.append(damage_roll)
                
        else:
            # Default to a general ability check
            dc = self.determine_difficulty_class(action_description, context)
            # Try to guess the most appropriate ability
            if any(word in action_lower for word in ['strong', 'force', 'break', 'силой']):
                ability = AbilityScore.STRENGTH
            elif any(word in action_lower for word in ['quick', 'fast', 'dodge', 'быстро']):
                ability = AbilityScore.DEXTERITY
            elif any(word in action_lower for word in ['remember', 'know', 'recall', 'помнить']):
                ability = AbilityScore.INTELLIGENCE
            elif any(word in action_lower for word in ['notice', 'sense', 'feel', 'заметить']):
                ability = AbilityScore.WISDOM
            elif any(word in action_lower for word in ['charm', 'influence', 'очаровать']):
                ability = AbilityScore.CHARISMA
            else:
                ability = AbilityScore.WISDOM  # Default
                
            roll = self.make_ability_check(
                actor,
                ability,
                dc,
                description=f"General check: {action_description}"
            )
            sequence.primary_roll = roll
            sequence.success = roll.is_success
        
        # Set critical results
        if sequence.primary_roll:
            sequence.critical_success = sequence.primary_roll.is_critical and sequence.success
            sequence.critical_failure = sequence.primary_roll.is_fumble and not sequence.success
        
        # Add rolls to character history
        if sequence.primary_roll:
            actor.add_roll_to_history(sequence.primary_roll)
        for roll in sequence.secondary_rolls:
            actor.add_roll_to_history(roll)
        
        return sequence


# Global instance
dice_engine = DiceEngine()
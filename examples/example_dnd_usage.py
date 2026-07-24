"""
Example D&D Usage for Game Master V3
Demonstrates the new D&D mechanics including character creation and skill checks
"""
import asyncio
import json
from uuid import uuid4

import httpx

# API base URL
BASE_URL = "http://localhost:8000/api/v1"


async def main():
    """Demonstrate D&D mechanics"""
    
    async with httpx.AsyncClient() as client:
        
        print("🎮 Game Master V3 - D&D Mechanics Demo")
        print("=" * 60)
        
        # Check API health
        print("\n1. Checking API health...")
        response = await client.get("http://localhost:8000/health")
        health = response.json()
        print(f"   Status: {health['status']}")
        print(f"   World Service: {'✓' if health['world_service_initialized'] else '✗'}")
        
        if not health['world_service_initialized']:
            print("⚠️  World service not initialized. Start with 'make dev' and 'make init'")
            return
            
        # Create a new D&D character
        print("\n2. 🧙‍♂️ Creating a new D&D Rogue character...")
        character_data = {
            "name": "Sneaky Pete",
            "character_class": "rogue",
            "ability_scores": {
                "strength": 12,
                "dexterity": 17,  # High DEX for rogue
                "constitution": 14,
                "intelligence": 13,
                "wisdom": 15,
                "charisma": 10
            },
            "background": "Criminal"
        }
        
        create_response = await client.post(f"{BASE_URL}/game/character/create", json=character_data)
        
        if create_response.status_code == 200:
            character_result = create_response.json()
            player_id = character_result["resolved_entities"]["player_id"]
            print(f"   ✅ Character created: {character_result['content']}")
            print(f"   🆔 Player ID: {player_id}")
        else:
            print(f"   ❌ Character creation failed: {create_response.status_code}")
            print(f"   Error: {create_response.text}")
            return
        
        # Get character stats
        print(f"\n3. 📊 Getting character statistics...")
        stats_response = await client.get(f"{BASE_URL}/game/character/{player_id}/stats")
        
        if stats_response.status_code == 200:
            stats = stats_response.json()
            print(f"   Name: {stats['character_name']}")
            print(f"   Class: {stats['class']}")
            print(f"   Level: {stats['level']}")
            print(f"   HP: {stats['hit_points']['current']}/{stats['hit_points']['max']}")
            print(f"   AC: {stats['armor_class']}")
            print(f"   Proficiency Bonus: +{stats['proficiency_bonus']}")
            print(f"   Key Skills:")
            print(f"     • Stealth: +{stats['skills']['stealth']}")
            print(f"     • Sleight of Hand: +{stats['skills']['sleight_of_hand']}")
            print(f"     • Perception: +{stats['skills']['perception']}")
        
        # Session ID for this demo
        session_id = str(uuid4())
        world_id = str(uuid4())
        
        # Test skill checks with natural language
        skill_tests = [
            "I try to sneak past the guard silently",
            "I attempt to pickpocket the merchant's coin purse",
            "I carefully examine the door for traps",
            "I try to convince the guard to let me through",
            "I attempt to climb up the stone wall"
        ]
        
        print(f"\n4. 🎲 Testing D&D skill checks...")
        print(f"Session ID: {session_id}")
        
        for i, command in enumerate(skill_tests, 1):
            print(f"\n   Test {i}: '{command}'")
            
            game_command = {
                "world_id": world_id,
                "session_id": session_id,
                "player_id": player_id,
                "command": command
            }
            
            try:
                response = await client.post(f"{BASE_URL}/game/command", json=game_command)
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"   🎯 Action: {result['action_type']}")
                    if 'roll_total' in result.get('resolved_entities', {}):
                        roll_total = result['resolved_entities']['roll_total']
                        dc = result['resolved_entities']['dc']
                        skill_used = result['resolved_entities']['skill_used']
                        print(f"   🎲 Roll: {roll_total} vs DC {dc} ({skill_used})")
                        print(f"   {'✅ SUCCESS' if result['success'] else '❌ FAILURE'}")
                    print(f"   📖 Result: {result['content'][:100]}...")
                else:
                    print(f"   ❌ Request failed: {response.status_code}")
                    
            except Exception as e:
                print(f"   ⚠️  Error: {e}")
            
            # Brief pause between tests
            await asyncio.sleep(1)
        
        # Get updated character stats to see roll history
        print(f"\n5. 📈 Checking roll history...")
        stats_response = await client.get(f"{BASE_URL}/game/character/{player_id}/stats")
        
        if stats_response.status_code == 200:
            stats = stats_response.json()
            recent_rolls = stats.get('recent_rolls', [])
            if recent_rolls:
                print(f"   Recent rolls ({len(recent_rolls)}):")
                for roll in recent_rolls[-5:]:  # Last 5 rolls
                    success_icon = "✅" if roll['success'] else "❌"
                    critical_icon = " 🎯" if roll['critical'] else ""
                    print(f"     {success_icon} {roll['description']}: {roll['total']}{critical_icon}")
            else:
                print("   No rolls recorded yet")
        
        print(f"\n🎉 D&D mechanics demo completed!")
        print(f"   • Character creation ✅")
        print(f"   • Automatic skill detection ✅") 
        print(f"   • Dice rolling ✅")
        print(f"   • AI narration ✅")
        print(f"   • Roll history tracking ✅")


if __name__ == "__main__":
    asyncio.run(main())
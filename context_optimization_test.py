#!/usr/bin/env python3
"""
Context Optimization Test
Tests the impact of context optimization on AI response times
"""

import time
import requests
import json
from uuid import uuid4

BASE_URL = "http://localhost:8000"

def test_context_optimization():
    """Test context optimization impact"""
    print("🧠 CONTEXT OPTIMIZATION TEST")
    print("=" * 50)
    
    # Create a test character
    character_data = {
        "name": "ContextTestChar",
        "character_class": "rogue",
        "ability_scores": {
            "strength": 13,
            "dexterity": 16,
            "constitution": 14,
            "intelligence": 12,
            "wisdom": 13,
            "charisma": 8
        },
        "background": "Criminal"
    }
    
    print("1. Creating test character...")
    response = requests.post(f"{BASE_URL}/api/v1/game/character/create", json=character_data)
    
    if response.status_code != 200:
        print(f"❌ Failed to create character: {response.status_code}")
        return
    
    player_id = response.json().get("resolved_entities", {}).get("player_id")
    print(f"✅ Character created: {player_id}")
    
    # Test commands with different context sizes
    print("\n2. Testing commands with varying context complexity...")
    
    test_commands = [
        {
            "command": "I look around",
            "description": "Simple command - minimal context",
            "expected_tokens": "Low"
        },
        {
            "command": "I examine the ancient mystical door with intricate magical runes and arcane symbols carefully for any hidden mechanisms, secret compartments, magical traps, or enchantments",
            "description": "Complex command - large context",
            "expected_tokens": "High"
        },
        {
            "command": "I investigate the room thoroughly, searching every corner, examining all furniture, checking for secret passages, hidden compartments, magical auras, and any signs of recent activity or danger",
            "description": "Very complex command - maximum context", 
            "expected_tokens": "Very High"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_commands, 1):
        print(f"\n   Test {i}: {test_case['description']}")
        print(f"   Command: {test_case['command'][:60]}...")
        print(f"   Expected tokens: {test_case['expected_tokens']}")
        
        command_data = {
            "world_id": str(uuid4()),
            "session_id": str(uuid4()),
            "player_id": player_id,
            "command": test_case["command"]
        }
        
        start = time.time()
        response = requests.post(f"{BASE_URL}/api/v1/game/command", json=command_data)
        end = time.time()
        
        time_taken = end - start
        results.append({
            "description": test_case["description"],
            "expected_tokens": test_case["expected_tokens"],
            "time": time_taken,
            "status": response.status_code,
            "response": response.json() if response.status_code == 200 else None
        })
        
        if response.status_code == 200:
            resp_data = response.json()
            action = resp_data.get("action_type", "unknown")
            tokens = resp_data.get("tokens_used", 0)
            print(f"   ✅ {time_taken:.3f}s -> {action} (tokens: {tokens})")
        else:
            print(f"   ❌ {time_taken:.3f}s -> ERROR {response.status_code}")
    
    # Test repeated commands to see cache vs optimization effects
    print("\n3. Testing repeated complex command (cache effects)...")
    
    complex_command = "I examine the ancient mystical door with magical runes carefully"
    repeat_times = []
    
    for i in range(3):
        command_data = {
            "world_id": str(uuid4()),
            "session_id": str(uuid4()),
            "player_id": player_id,
            "command": complex_command
        }
        
        start = time.time()
        response = requests.post(f"{BASE_URL}/api/v1/game/command", json=command_data)
        end = time.time()
        
        time_taken = end - start
        repeat_times.append(time_taken)
        
        cache_status = "MISS" if i == 0 else "HIT (expected)"
        if response.status_code == 200:
            resp_data = response.json()
            action = resp_data.get("action_type", "unknown")
            tokens = resp_data.get("tokens_used", 0)
            print(f"   Repeat {i+1}: {time_taken:.3f}s -> {action} ({cache_status}) tokens: {tokens}")
        else:
            print(f"   Repeat {i+1}: {time_taken:.3f}s -> ERROR")
    
    # Analysis
    print("\n🎯 CONTEXT OPTIMIZATION ANALYSIS:")
    
    if len(results) >= 2:
        simple_time = results[0]["time"]
        complex_time = results[1]["time"]
        
        print(f"   📊 Simple command: {simple_time:.3f}s")
        print(f"   📊 Complex command: {complex_time:.3f}s")
        
        if complex_time > 0:
            overhead = complex_time / simple_time
            print(f"   📈 Complexity overhead: {overhead:.1f}x")
            
            if overhead < 2.0:
                print("   ✅ Context optimization is working well!")
            elif overhead < 3.0:
                print("   ⚠️  Context optimization is moderate")
            else:
                print("   ❌ Context optimization needs improvement")
    
    if len(repeat_times) >= 2:
        first_repeat = repeat_times[0]
        avg_cached = sum(repeat_times[1:]) / len(repeat_times[1:])
        
        print(f"   🔄 First complex request: {first_repeat:.3f}s")
        print(f"   ⚡ Cached requests avg: {avg_cached:.3f}s")
        
        if avg_cached > 0:
            cache_speedup = first_repeat / avg_cached
            print(f"   🚀 Cache speedup: {cache_speedup:.1f}x")
    
    # Check final cache stats
    print("\n4. Final cache statistics...")
    response = requests.get(f"{BASE_URL}/api/v1/cache/stats")
    
    if response.status_code == 200:
        stats = response.json()
        print(f"   Hit Rate: {stats.get('hit_rate_percent', 0)}%")
        print(f"   Memory Usage: {stats.get('memory_usage', '0B')}")
        print(f"   Cache Hits: {stats.get('cache_hits', 0)}")
        print(f"   Cache Misses: {stats.get('cache_misses', 0)}")
    
    print("\n🧠 Context Optimization Test Complete!")
    
    # Summary
    if results:
        avg_time = sum(r["time"] for r in results) / len(results)
        print(f"\n📈 SUMMARY:")
        print(f"   Average response time: {avg_time:.3f}s")
        
        successful = sum(1 for r in results if r["status"] == 200)
        print(f"   Success rate: {successful}/{len(results)} ({successful/len(results)*100:.1f}%)")
        
        if avg_time < 10:
            print("   ✅ Performance is EXCELLENT!")
        elif avg_time < 20:
            print("   ✅ Performance is GOOD")  
        else:
            print("   ⚠️  Performance needs improvement")

if __name__ == "__main__":
    test_context_optimization()
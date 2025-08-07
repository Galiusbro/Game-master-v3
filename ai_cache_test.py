#!/usr/bin/env python3
"""
AI Cache Performance Test
Tests the impact of AI response caching on performance
"""

import time
import requests
import json
from uuid import uuid4

BASE_URL = "http://localhost:8000"

def test_ai_cache_performance():
    """Test AI caching performance"""
    print("🧠 AI CACHE PERFORMANCE TEST")
    print("=" * 50)
    
    # Create a test character first
    character_data = {
        "name": "AICacheTest",
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
    if not player_id:
        print("❌ No player_id returned")
        return
    
    print(f"✅ Character created")
    print(f"🆔 Player ID: {player_id}")
    
    # Test identical AI requests (should be cached)
    print("\n2. Testing identical AI requests (should cache)...")
    
    # Same command repeated 5 times
    identical_command = "I examine the ancient door carefully for any magical runes or hidden mechanisms"
    times = []
    
    for i in range(5):
        command_data = {
            "world_id": str(uuid4()),
            "session_id": str(uuid4()),
            "player_id": player_id,
            "command": identical_command
        }
        
        start = time.time()
        response = requests.post(f"{BASE_URL}/api/v1/game/command", json=command_data)
        end = time.time()
        
        time_taken = end - start
        times.append(time_taken)
        
        cache_status = "MISS" if i == 0 else "HIT (expected)"
        
        if response.status_code == 200:
            action = response.json().get("action_type", "unknown")
            print(f"   Request {i+1}: {time_taken:.3f}s -> {action} ({cache_status})")
        else:
            print(f"   Request {i+1}: {time_taken:.3f}s -> ERROR {response.status_code}")
    
    # Test similar but different commands (should NOT be cached)
    print("\n3. Testing similar but different commands...")
    
    similar_commands = [
        "I examine the ancient door carefully for traps",
        "I examine the ancient door carefully for locks", 
        "I examine the ancient door carefully for secrets",
        "I examine the old door carefully for magical runes"
    ]
    
    similar_times = []
    
    for i, command in enumerate(similar_commands):
        command_data = {
            "world_id": str(uuid4()),
            "session_id": str(uuid4()),
            "player_id": player_id,
            "command": command
        }
        
        start = time.time()
        response = requests.post(f"{BASE_URL}/api/v1/game/command", json=command_data)
        end = time.time()
        
        time_taken = end - start
        similar_times.append(time_taken)
        
        if response.status_code == 200:
            action = response.json().get("action_type", "unknown")
            print(f"   Command {i+1}: {time_taken:.3f}s -> {action} (MISS expected)")
        else:
            print(f"   Command {i+1}: {time_taken:.3f}s -> ERROR {response.status_code}")
    
    # Get cache stats
    print("\n4. Cache statistics...")
    response = requests.get(f"{BASE_URL}/api/v1/cache/stats")
    
    if response.status_code == 200:
        stats = response.json()
        print(f"   Hit Rate: {stats.get('hit_rate_percent', 0)}%")
        print(f"   Cache Hits: {stats.get('cache_hits', 0)}")
        print(f"   Cache Misses: {stats.get('cache_misses', 0)}")
        print(f"   Memory Usage: {stats.get('memory_usage', '0B')}")
    
    # Analysis
    print("\n🎯 ANALYSIS:")
    
    if len(times) >= 2:
        first_time = times[0]
        avg_cached = sum(times[1:]) / len(times[1:])
        
        print(f"   🔥 First request (cache miss): {first_time:.3f}s")
        print(f"   ⚡ Cached requests average: {avg_cached:.3f}s")
        
        if avg_cached > 0:
            speedup = first_time / avg_cached
            print(f"   🚀 AI Cache Speedup: {speedup:.1f}x")
            
            if speedup > 5:
                print("   ✅ AI Caching is working EXCELLENTLY!")
            elif speedup > 2:
                print("   ✅ AI Caching is working well!")
            else:
                print("   ⚠️  AI Caching needs improvement")
        
        # Check if similar commands are properly not cached
        if len(similar_times) > 0:
            avg_similar = sum(similar_times) / len(similar_times)
            print(f"   🔄 Similar commands average: {avg_similar:.3f}s")
            
            if abs(avg_similar - first_time) < first_time * 0.3:
                print("   ✅ Similar commands correctly NOT cached")
            else:
                print("   ⚠️  Similar commands may be incorrectly cached")
    
    print("\n🧠 AI Cache Test Complete!")

if __name__ == "__main__":
    test_ai_cache_performance()
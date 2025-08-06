#!/usr/bin/env python3
"""
Cache Performance Test
Tests the impact of Redis caching on API response times
"""

import time
import requests
import json
from uuid import uuid4
import statistics

BASE_URL = "http://localhost:8000"

def time_request(url, method="GET", data=None):
    """Time a single API request"""
    start = time.time()
    
    if method == "GET":
        response = requests.get(url)
    elif method == "POST":
        response = requests.post(url, json=data)
    
    end = time.time()
    return end - start, response.status_code, response.json() if response.headers.get('content-type', '').startswith('application/json') else None

def test_cache_performance():
    """Test cache performance with repeated requests"""
    print("🚀 CACHE PERFORMANCE TEST")
    print("=" * 50)
    
    # Create a test character first
    character_data = {
        "name": "CacheTestChar",
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
    create_time, status, response = time_request(
        f"{BASE_URL}/api/v1/game/character/create",
        "POST",
        character_data
    )
    
    if status != 200:
        print(f"❌ Failed to create character: {status}")
        return
    
    player_id = response.get("resolved_entities", {}).get("player_id")
    if not player_id:
        print("❌ No player_id returned")
        return
    
    print(f"✅ Character created in {create_time:.3f}s")
    print(f"🆔 Player ID: {player_id}")
    
    # Test: Repeated character stats requests (should be cached)
    print("\n2. Testing character stats caching...")
    stats_times = []
    
    for i in range(10):
        cache_status = "MISS" if i == 0 else "HIT"
        time_taken, status, _ = time_request(f"{BASE_URL}/api/v1/game/character/{player_id}/stats")
        stats_times.append(time_taken)
        print(f"   Request {i+1}: {time_taken:.3f}s (expected {cache_status})")
    
    print(f"\n📊 Character Stats Performance:")
    print(f"   First request (cache miss): {stats_times[0]:.3f}s")
    print(f"   Average cached requests: {statistics.mean(stats_times[1:]):.3f}s")
    print(f"   Speedup: {stats_times[0] / statistics.mean(stats_times[1:]):.1f}x")
    
    # Test: Repeated game commands (entity lookups should be cached)
    print("\n3. Testing game command caching...")
    command_times = []
    
    game_commands = [
        "I examine my surroundings carefully",
        "I look for any valuable items",
        "I check for hidden passages",
        "I listen for nearby sounds"
    ]
    
    for i, command in enumerate(game_commands):
        command_data = {
            "world_id": str(uuid4()),
            "session_id": str(uuid4()),
            "player_id": player_id,
            "command": command
        }
        
        time_taken, status, response = time_request(
            f"{BASE_URL}/api/v1/game/command",
            "POST",
            command_data
        )
        command_times.append(time_taken)
        
        if status == 200:
            action = response.get("action_type", "unknown")
            print(f"   Command {i+1}: {time_taken:.3f}s -> {action}")
        else:
            print(f"   Command {i+1}: {time_taken:.3f}s -> ERROR {status}")
    
    # Now repeat the same commands (should be faster due to entity caching)
    print("\n4. Testing repeated commands (cache effects)...")
    repeated_times = []
    
    for i, command in enumerate(game_commands):
        command_data = {
            "world_id": str(uuid4()),
            "session_id": str(uuid4()),
            "player_id": player_id,
            "command": command
        }
        
        time_taken, status, response = time_request(
            f"{BASE_URL}/api/v1/game/command",
            "POST",
            command_data
        )
        repeated_times.append(time_taken)
        
        if status == 200:
            action = response.get("action_type", "unknown")
            print(f"   Repeat {i+1}: {time_taken:.3f}s -> {action}")
        else:
            print(f"   Repeat {i+1}: {time_taken:.3f}s -> ERROR {status}")
    
    print(f"\n📊 Game Command Performance:")
    print(f"   First run average: {statistics.mean(command_times):.3f}s")
    print(f"   Second run average: {statistics.mean(repeated_times):.3f}s")
    if statistics.mean(repeated_times) > 0:
        print(f"   Speedup: {statistics.mean(command_times) / statistics.mean(repeated_times):.1f}x")
    
    # Get final cache stats
    print("\n5. Final cache statistics...")
    time_taken, status, stats = time_request(f"{BASE_URL}/api/v1/cache/stats")
    
    if status == 200:
        print(f"   Hit Rate: {stats.get('hit_rate_percent', 0)}%")
        print(f"   Cache Hits: {stats.get('cache_hits', 0)}")
        print(f"   Cache Misses: {stats.get('cache_misses', 0)}")
        print(f"   Memory Usage: {stats.get('memory_usage', '0B')}")
        print(f"   Total Commands: {stats.get('total_commands', 0)}")
    else:
        print(f"   ❌ Failed to get cache stats: {status}")
    
    print("\n🎯 SUMMARY:")
    if len(stats_times) > 1 and statistics.mean(stats_times[1:]) > 0:
        stats_speedup = stats_times[0] / statistics.mean(stats_times[1:])
        print(f"   📈 Character stats caching: {stats_speedup:.1f}x faster")
    
    if len(command_times) > 0 and len(repeated_times) > 0 and statistics.mean(repeated_times) > 0:
        cmd_speedup = statistics.mean(command_times) / statistics.mean(repeated_times)
        print(f"   🎮 Game commands caching: {cmd_speedup:.1f}x faster")
    
    if status == 200:
        hit_rate = stats.get('hit_rate_percent', 0)
        if hit_rate > 0:
            print(f"   🎯 Overall cache hit rate: {hit_rate}%")
            print("   ✅ Caching is working effectively!")
        else:
            print("   ⚠️  Cache hit rate is 0% - may need tuning")
    
    print("\n🔥 Cache Performance Test Complete!")

if __name__ == "__main__":
    test_cache_performance()
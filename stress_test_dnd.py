#!/usr/bin/env python3
"""
🔥 STRESS TEST for Game Master V3 - D&D System
Attempts to break the system with edge cases and extreme scenarios
"""

import requests
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import string

BASE_URL = "http://localhost:8000"

def colored_print(text, color="white"):
    colors = {
        "red": "\033[91m",
        "green": "\033[92m", 
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "purple": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, colors['white'])}{text}{colors['reset']}")

def test_api_call(endpoint, method="GET", data=None, expected_status=200):
    """Helper function for API calls"""
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        elif method == "POST":
            response = requests.post(f"{BASE_URL}{endpoint}", json=data, timeout=10)
        
        return {
            "success": response.status_code == expected_status,
            "status": response.status_code,
            "data": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
            "time": response.elapsed.total_seconds()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "status": None,
            "data": None,
            "time": None
        }

def create_test_character():
    """Create a test character for stress testing"""
    character_data = {
        "name": f"StressTest_{random.randint(1000, 9999)}",
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
    
    result = test_api_call("/api/v1/game/character/create", "POST", character_data)
    if result["success"]:
        resolved_entities = result["data"].get("resolved_entities", {})
        return resolved_entities.get("player_id")
    return None

def stress_test_1_edge_cases():
    """Test 1: Edge cases - empty, gibberish, extreme content"""
    colored_print("\n🧪 STRESS TEST 1: Edge Cases & Invalid Input", "cyan")
    colored_print("=" * 60, "cyan")
    
    player_id = create_test_character()
    if not player_id:
        colored_print("❌ Failed to create test character", "red")
        return False
    
    test_cases = [
        # Empty/minimal input
        {"command": "", "description": "Empty command"},
        {"command": " ", "description": "Whitespace only"},
        {"command": "\n\t\r", "description": "Special whitespace"},
        
        # Gibberish 
        {"command": "ajsdkajsdkajsd", "description": "Random gibberish"},
        {"command": "🎲🧙‍♂️⚔️🐉💀", "description": "Only emojis"},
        {"command": "123456789", "description": "Only numbers"},
        
        # Extremely long text
        {"command": "I want to " + "very " * 200 + "carefully examine every single detail", "description": "Extremely long command"},
        
        # Special characters
        {"command": "I attack with ';DROP TABLE users;--", "description": "SQL injection attempt"},
        {"command": "I cast <script>alert('xss')</script>", "description": "XSS attempt"},
        {"command": "I search for ${env:OPENAI_API_KEY}", "description": "Template injection attempt"},
        
        # Non-English
        {"command": "Я хочу украсть ключи у стражника", "description": "Russian command"},
        {"command": "私は静かに歩きます", "description": "Japanese command"},
        {"command": "أريد أن أتسلل", "description": "Arabic command"},
    ]
    
    base_request = {
        "world_id": str(uuid.uuid4()),
        "session_id": str(uuid.uuid4()),
        "player_id": player_id
    }
    
    results = []
    for i, test_case in enumerate(test_cases, 1):
        colored_print(f"\n  Test 1.{i}: {test_case['description']}", "yellow")
        
        request_data = {**base_request, "command": test_case["command"]}
        result = test_api_call("/api/v1/game/command", "POST", request_data, expected_status=200)
        
        if result["success"]:
            colored_print(f"    ✅ Status: {result['status']} | Time: {result['time']:.2f}s", "green")
            action_type = result["data"].get("action_type", "unknown")
            content_preview = str(result["data"].get("content", ""))[:50] + "..."
            colored_print(f"    🎯 Action: {action_type} | Content: {content_preview}", "white")
        else:
            colored_print(f"    ❌ Failed: {result.get('error', result.get('status'))}", "red")
        
        results.append(result)
        time.sleep(0.1)  # Brief pause between requests
    
    passed = sum(1 for r in results if r["success"])
    colored_print(f"\n📊 Test 1 Results: {passed}/{len(results)} passed", "purple")
    return passed > len(results) * 0.7  # 70% pass rate

def stress_test_2_invalid_data():
    """Test 2: Invalid UUIDs and missing data"""
    colored_print("\n🧪 STRESS TEST 2: Invalid UUIDs & Missing Data", "cyan")
    colored_print("=" * 60, "cyan")
    
    test_cases = [
        # Invalid UUIDs
        {
            "data": {"world_id": "invalid-uuid", "session_id": str(uuid.uuid4()), "player_id": str(uuid.uuid4()), "command": "test"},
            "description": "Invalid world_id UUID",
            "expected_status": 422
        },
        {
            "data": {"world_id": str(uuid.uuid4()), "session_id": "not-a-uuid", "player_id": str(uuid.uuid4()), "command": "test"},
            "description": "Invalid session_id UUID", 
            "expected_status": 422
        },
        {
            "data": {"world_id": str(uuid.uuid4()), "session_id": str(uuid.uuid4()), "player_id": "fake-player", "command": "test"},
            "description": "Invalid player_id UUID",
            "expected_status": 422
        },
        
        # Missing fields
        {
            "data": {"session_id": str(uuid.uuid4()), "player_id": str(uuid.uuid4()), "command": "test"},
            "description": "Missing world_id",
            "expected_status": 422
        },
        {
            "data": {"world_id": str(uuid.uuid4()), "player_id": str(uuid.uuid4()), "command": "test"},
            "description": "Missing session_id",
            "expected_status": 422
        },
        {
            "data": {"world_id": str(uuid.uuid4()), "session_id": str(uuid.uuid4()), "command": "test"},
            "description": "Missing player_id",
            "expected_status": 422
        },
        {
            "data": {"world_id": str(uuid.uuid4()), "session_id": str(uuid.uuid4()), "player_id": str(uuid.uuid4())},
            "description": "Missing command",
            "expected_status": 422
        },
        
        # Non-existent player
        {
            "data": {"world_id": str(uuid.uuid4()), "session_id": str(uuid.uuid4()), "player_id": str(uuid.uuid4()), "command": "I attack"},
            "description": "Non-existent player_id",
            "expected_status": 404
        }
    ]
    
    results = []
    for i, test_case in enumerate(test_cases, 1):
        colored_print(f"\n  Test 2.{i}: {test_case['description']}", "yellow")
        
        result = test_api_call("/api/v1/game/command", "POST", test_case["data"], test_case["expected_status"])
        
        if result["success"]:
            colored_print(f"    ✅ Expected status {test_case['expected_status']}, got {result['status']}", "green")
        else:
            colored_print(f"    ❌ Expected {test_case['expected_status']}, got {result.get('status', 'ERROR')}: {result.get('error', '')}", "red")
        
        results.append(result)
        time.sleep(0.1)
    
    passed = sum(1 for r in results if r["success"])
    colored_print(f"\n📊 Test 2 Results: {passed}/{len(results)} passed", "purple")
    return passed == len(results)  # All should pass for proper validation

def stress_test_3_performance():
    """Test 3: Performance & Concurrency"""
    colored_print("\n🧪 STRESS TEST 3: Performance & Concurrency", "cyan")
    colored_print("=" * 60, "cyan")
    
    player_id = create_test_character()
    if not player_id:
        colored_print("❌ Failed to create test character", "red")
        return False
    
    base_request = {
        "world_id": str(uuid.uuid4()),
        "session_id": str(uuid.uuid4()),
        "player_id": player_id
    }
    
    commands = [
        "I try to sneak past the guard",
        "I examine the door for traps", 
        "I attempt to pick the lock",
        "I convince the merchant to lower the price",
        "I climb the wall carefully",
        "I search for hidden treasures",
        "I attack with my dagger",
        "I cast a spell",
        "I drink a healing potion",
        "I negotiate with the NPC"
    ]
    
    def make_request(command):
        request_data = {**base_request, "command": command}
        start_time = time.time()
        result = test_api_call("/api/v1/game/command", "POST", request_data)
        end_time = time.time()
        result["total_time"] = end_time - start_time
        return result
    
    # Sequential test
    colored_print("\n  Sequential requests:", "yellow")
    sequential_start = time.time()
    sequential_results = []
    for command in commands:
        result = make_request(command)
        sequential_results.append(result)
        if result["success"]:
            colored_print(f"    ✅ '{command[:30]}...' | {result['total_time']:.2f}s", "green")
        else:
            colored_print(f"    ❌ '{command[:30]}...' | ERROR", "red")
    sequential_total = time.time() - sequential_start
    
    # Concurrent test
    colored_print(f"\n  Concurrent requests (max 5 threads):", "yellow")
    concurrent_start = time.time()
    concurrent_results = []
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_command = {executor.submit(make_request, cmd): cmd for cmd in commands}
        for future in as_completed(future_to_command):
            command = future_to_command[future]
            try:
                result = future.result()
                concurrent_results.append(result)
                if result["success"]:
                    colored_print(f"    ✅ '{command[:30]}...' | {result['total_time']:.2f}s", "green")
                else:
                    colored_print(f"    ❌ '{command[:30]}...' | ERROR", "red")
            except Exception as e:
                colored_print(f"    💥 '{command[:30]}...' | Exception: {e}", "red")
    
    concurrent_total = time.time() - concurrent_start
    
    # Performance analysis
    seq_passed = sum(1 for r in sequential_results if r["success"])
    con_passed = sum(1 for r in concurrent_results if r["success"])
    
    colored_print(f"\n📊 Performance Results:", "purple")
    colored_print(f"   Sequential: {seq_passed}/{len(commands)} passed | {sequential_total:.2f}s total", "white")
    colored_print(f"   Concurrent: {con_passed}/{len(commands)} passed | {concurrent_total:.2f}s total", "white")
    colored_print(f"   Speedup: {sequential_total/concurrent_total:.2f}x", "white")
    
    return seq_passed > 0 and con_passed > 0

def stress_test_4_complex_scenarios():
    """Test 4: Complex multi-action commands"""
    colored_print("\n🧪 STRESS TEST 4: Complex Multi-Action Scenarios", "cyan")
    colored_print("=" * 60, "cyan")
    
    player_id = create_test_character()
    if not player_id:
        colored_print("❌ Failed to create test character", "red")
        return False
    
    base_request = {
        "world_id": str(uuid.uuid4()),
        "session_id": str(uuid.uuid4()),
        "player_id": player_id
    }
    
    complex_commands = [
        "I sneak up to the guard, carefully pickpocket his keys, then unlock the door and slip inside",
        "I examine the chest for traps, disarm them if found, pick the lock, and search for treasure inside",
        "I convince the merchant to trust me, then attempt to distract him while stealing his most valuable item",
        "I climb the tower wall, sneak past the guards on the roof, and search for a way into the building",
        "I cast an invisibility spell, sneak through the dungeon, avoid all the traps, and steal the magical artifact",
        "First I gather information about the target, then I plan my approach, sneak in during the night shift, disable the alarm, and complete my mission",
        "I want to simultaneously attack the orc while defending against the dragon's fire breath and casting a healing spell on my ally",
        "I negotiate with the king to form an alliance, while secretly planning to assassinate him during the feast tonight",
        "I need to decode the ancient runes on the wall, translate the riddle, solve the puzzle, and activate the hidden mechanism",
        "I attempt to balance on the narrow ledge while fighting off the flying creatures and casting spells to protect the bridge below"
    ]
    
    results = []
    for i, command in enumerate(complex_commands, 1):
        colored_print(f"\n  Test 4.{i}: Complex scenario", "yellow")
        colored_print(f"    Command: {command[:80]}...", "white")
        
        request_data = {**base_request, "command": command}
        result = test_api_call("/api/v1/game/command", "POST", request_data)
        
        if result["success"]:
            action_type = result["data"].get("action_type", "unknown")
            success = result["data"].get("success", False)
            content_preview = str(result["data"].get("content", ""))[:100] + "..."
            
            colored_print(f"    ✅ Action: {action_type} | Success: {success} | Time: {result['time']:.2f}s", "green")
            colored_print(f"    📖 Response: {content_preview}", "white")
        else:
            colored_print(f"    ❌ Failed: {result.get('error', result.get('status'))}", "red")
        
        results.append(result)
        time.sleep(0.2)  # Longer pause for complex requests
    
    passed = sum(1 for r in results if r["success"])
    colored_print(f"\n📊 Test 4 Results: {passed}/{len(results)} passed", "purple")
    return passed > len(results) * 0.8  # 80% pass rate for complex scenarios

def main():
    """Run all stress tests"""
    colored_print("🔥 GAME MASTER V3 - STRESS TEST SUITE", "red")
    colored_print("=" * 60, "red")
    colored_print("Attempting to break the D&D system with edge cases...\n", "white")
    
    # Check if API is available
    health_check = test_api_call("/health")
    if not health_check["success"]:
        colored_print("❌ API is not available! Make sure the server is running.", "red")
        return
    
    colored_print("✅ API is healthy, starting stress tests...", "green")
    
    # Run all tests
    test_results = []
    
    test_results.append(("Edge Cases", stress_test_1_edge_cases()))
    test_results.append(("Invalid Data", stress_test_2_invalid_data())) 
    test_results.append(("Performance", stress_test_3_performance()))
    test_results.append(("Complex Scenarios", stress_test_4_complex_scenarios()))
    
    # Summary
    colored_print(f"\n🏁 STRESS TEST SUMMARY", "red")
    colored_print("=" * 60, "red")
    
    passed_tests = 0
    for test_name, passed in test_results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        color = "green" if passed else "red"
        colored_print(f"  {test_name}: {status}", color)
        if passed:
            passed_tests += 1
    
    overall_score = passed_tests / len(test_results) * 100
    color = "green" if overall_score >= 75 else "yellow" if overall_score >= 50 else "red"
    
    colored_print(f"\n🎯 Overall Score: {passed_tests}/{len(test_results)} ({overall_score:.0f}%)", color)
    
    if overall_score >= 75:
        colored_print("🎉 System is ROBUST! Well done!", "green")
    elif overall_score >= 50:
        colored_print("⚠️  System is DECENT but needs improvement", "yellow")
    else:
        colored_print("💥 System needs SERIOUS improvements!", "red")

if __name__ == "__main__":
    main()
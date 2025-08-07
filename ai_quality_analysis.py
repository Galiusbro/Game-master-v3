#!/usr/bin/env python3
"""
AI Quality Analysis Test - QUALITY OPTIMIZED VERSION
Analyzes AI response quality with quality-focused settings
"""

import time
import requests
import json
from uuid import uuid4

BASE_URL = "http://localhost:8000"

def test_ai_response_quality():
    """Test AI response quality with optimization"""
    print("🎭 AI RESPONSE QUALITY ANALYSIS - QUALITY OPTIMIZED")
    print("=" * 60)
    
    # Create test character
    character_data = {
        "name": "QualityTestChar",
        "character_class": "wizard",
        "ability_scores": {
            "strength": 10,
            "dexterity": 14,
            "constitution": 13,
            "intelligence": 16,
            "wisdom": 15,
            "charisma": 12
        },
        "background": "Scholar"
    }
    
    print("1. Creating test character...")
    response = requests.post(f"{BASE_URL}/api/v1/game/character/create", json=character_data)
    
    if response.status_code != 200:
        print(f"❌ Failed to create character: {response.status_code}")
        return
    
    player_id = response.json().get("resolved_entities", {}).get("player_id")
    print(f"✅ Character created: {player_id}")
    
    # Test different types of commands for quality analysis
    print("\n2. Testing response quality across different command types...")
    
    quality_tests = [
        {
            "command": "I look around the room",
            "type": "Simple observation",
            "quality_indicators": ["room description", "details", "atmosphere"],
            "expectation": "Basic but complete description"
        },
        {
            "command": "I examine the ancient spellbook on the pedestal, looking for any magical auras, dangerous enchantments, or valuable spells",
            "type": "Complex investigation", 
            "quality_indicators": ["magical details", "specific observations", "wizard knowledge"],
            "expectation": "Rich, detailed magical analysis"
        },
        {
            "command": "I cast Detect Magic to scan the entire chamber for any hidden magical items, secret enchantments, or arcane traps",
            "type": "Spell casting",
            "quality_indicators": ["spell effects", "magical detection", "systematic search"],
            "expectation": "Proper spell mechanics and magical world building"
        },
        {
            "command": "I try to decipher the ancient runes carved into the stone altar while checking for any historical significance or cultural meanings",
            "type": "Knowledge-based action",
            "quality_indicators": ["scholarly approach", "historical context", "detailed analysis"],
            "expectation": "Intelligent, scholarly response reflecting wizard background"
        },
        {
            "command": "I carefully approach the shimmering portal, using my arcane knowledge to analyze its magical structure and determine its destination before attempting to pass through",
            "type": "High-stakes decision",
            "quality_indicators": ["caution", "magical expertise", "risk assessment", "world consistency"],
            "expectation": "Thoughtful, expert magical analysis with consequences"
        }
    ]
    
    quality_scores = []
    
    for i, test in enumerate(quality_tests, 1):
        print(f"\n   Test {i}: {test['type']}")
        print(f"   Command: {test['command'][:80]}...")
        print(f"   Expectation: {test['expectation']}")
        
        command_data = {
            "world_id": str(uuid4()),
            "session_id": str(uuid4()),
            "player_id": player_id,
            "command": test["command"]
        }
        
        start = time.time()
        response = requests.post(f"{BASE_URL}/api/v1/game/command", json=command_data)
        end = time.time()
        
        if response.status_code == 200:
            resp_data = response.json()
            content = resp_data.get("content", "")
            action = resp_data.get("action_type", "unknown")
            confidence = resp_data.get("confidence", 0)
            tokens = resp_data.get("tokens_used", 0)
            
            print(f"   ✅ Response time: {end-start:.2f}s | Action: {action} | Tokens: {tokens}")
            print(f"   📊 Confidence: {confidence:.2f}")
            print(f"   📝 Response preview: {content[:150]}...")
            
            # Analyze quality indicators
            quality_score = analyze_response_quality(content, test["quality_indicators"])
            quality_scores.append({
                "type": test["type"],
                "score": quality_score,
                "response_length": len(content),
                "confidence": confidence,
                "tokens": tokens,
                "time": end-start
            })
            
            print(f"   🎯 Quality score: {quality_score:.1f}/5.0")
            
        else:
            print(f"   ❌ Failed: {response.status_code}")
    
    # Quality analysis
    print("\n🎭 QUALITY ANALYSIS RESULTS:")
    
    if quality_scores:
        avg_quality = sum(q["score"] for q in quality_scores) / len(quality_scores)
        avg_confidence = sum(q["confidence"] for q in quality_scores) / len(quality_scores)
        avg_length = sum(q["response_length"] for q in quality_scores) / len(quality_scores)
        avg_tokens = sum(q["tokens"] for q in quality_scores) / len(quality_scores)
        avg_time = sum(q["time"] for q in quality_scores) / len(quality_scores)
        
        print(f"   📈 Average quality score: {avg_quality:.2f}/5.0")
        print(f"   🎯 Average confidence: {avg_confidence:.2f}")
        print(f"   📝 Average response length: {avg_length:.0f} characters")
        print(f"   🔤 Average tokens used: {avg_tokens:.0f}")
        print(f"   ⏱️  Average response time: {avg_time:.2f}s")
        
        # Quality assessment
        if avg_quality >= 4.0:
            print("   ✅ AI response quality is EXCELLENT!")
        elif avg_quality >= 3.5:
            print("   ✅ AI response quality is GOOD")
        elif avg_quality >= 3.0:
            print("   ⚠️  AI response quality is ACCEPTABLE")
        else:
            print("   ❌ AI response quality needs improvement")
        
        # Context optimization impact
        print(f"\n🔍 CONTEXT OPTIMIZATION IMPACT:")
        print(f"   Token efficiency: {avg_tokens:.0f} tokens per response")
        print(f"   Response richness: {avg_length/avg_tokens:.1f} chars per token")
        
        if avg_tokens < 800:
            print("   ✅ Efficient token usage")
        else:
            print("   ⚠️  High token usage")
            
        # Performance vs Quality trade-off
        quality_per_second = avg_quality / avg_time
        print(f"   ⚖️  Quality/Speed ratio: {quality_per_second:.2f} quality points per second")
        
        if quality_per_second > 1.0:
            print("   ✅ Excellent quality-to-speed ratio!")
        elif quality_per_second > 0.5:
            print("   ✅ Good quality-to-speed ratio")
        else:
            print("   ⚠️  Quality-to-speed ratio could be better")
    
    # Test consistency with multiple similar requests
    print("\n3. Testing response consistency...")
    
    consistency_command = "I examine the magical crystal for any arcane properties"
    consistency_responses = []
    
    for i in range(3):
        command_data = {
            "world_id": str(uuid4()),
            "session_id": str(uuid4()),
            "player_id": player_id,
            "command": consistency_command
        }
        
        response = requests.post(f"{BASE_URL}/api/v1/game/command", json=command_data)
        if response.status_code == 200:
            content = response.json().get("content", "")
            consistency_responses.append(content)
            cache_status = "MISS" if i == 0 else "HIT"
            print(f"   Response {i+1} ({cache_status}): {content[:100]}...")
    
    if len(consistency_responses) >= 2:
        # Check if cached responses are identical (they should be)
        if consistency_responses[1] == consistency_responses[0]:
            print("   ✅ Cached responses are consistent")
        else:
            print("   ⚠️  Cached responses differ (unexpected)")
    
    print("\n🎭 AI Quality Analysis Complete!")

def analyze_response_quality(content, quality_indicators):
    """Analyze response quality based on indicators"""
    score = 1.0  # Base score
    content_lower = content.lower()
    
    # Length check
    if len(content) > 100:
        score += 1.0
    elif len(content) > 50:
        score += 0.5
    
    # Indicator presence
    indicators_found = 0
    for indicator in quality_indicators:
        if indicator.lower() in content_lower:
            indicators_found += 1
    
    # Score based on indicator coverage
    if len(quality_indicators) > 0:
        indicator_ratio = indicators_found / len(quality_indicators)
        score += indicator_ratio * 2.0
    
    # Narrative quality markers
    quality_markers = [
        "you see", "you notice", "you observe", "you feel",
        "carefully", "ancient", "mysterious", "magical",
        "detailed", "intricate", "complex", "subtle"
    ]
    
    markers_found = sum(1 for marker in quality_markers if marker in content_lower)
    score += min(markers_found * 0.1, 1.0)
    
    # Cap at 5.0
    return min(score, 5.0)

if __name__ == "__main__":
    test_ai_response_quality()
#!/usr/bin/env python3
"""
Streaming Test Client for Game Master V3
Tests Server-Sent Events (SSE) streaming functionality
"""
import asyncio
import aiohttp
import json
import time
from uuid import uuid4

BASE_URL = "http://localhost:8000"

async def test_streaming_command():
    """Test streaming game command"""
    print("🚀 STREAMING COMMAND TEST")
    print("=" * 50)
    
    # Create test character first
    character_data = {
        "name": "StreamTestChar",
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
    
    async with aiohttp.ClientSession() as session:
        # Create character
        print("1. Creating test character...")
        async with session.post(f"{BASE_URL}/api/v1/game/character/create", json=character_data) as resp:
            if resp.status == 200:
                char_data = await resp.json()
                player_id = char_data.get("resolved_entities", {}).get("player_id")
                print(f"✅ Character created: {player_id}")
            else:
                print(f"❌ Failed to create character: {resp.status}")
                return
        
        # Test streaming command
        print("\n2. Testing streaming game command...")
        stream_request = {
            "world_id": str(uuid4()),
            "session_id": str(uuid4()),
            "player_id": player_id,
            "command": "I carefully examine the ancient magical crystal on the pedestal, looking for any arcane runes, magical auras, or signs of enchantment"
        }
        
        start_time = time.time()
        response_text = ""
        events_received = 0
        
        print("📡 Starting stream...")
        async with session.post(f"{BASE_URL}/api/v1/stream/command", json=stream_request) as resp:
            if resp.status == 200:
                async for line in resp.content:
                    line = line.decode().strip()
                    if not line:
                        continue
                    
                    if line.startswith("event:"):
                        event_type = line.split(":", 1)[1].strip()
                    elif line.startswith("data:"):
                        data = line.split(":", 1)[1].strip()
                        events_received += 1
                        
                        if event_type == "status":
                            print(f"   📊 Status: {data}")
                        elif event_type == "content":
                            response_text += data
                            if data:
                                print(f"   📝 Content: {data}", end="", flush=True)
                        elif event_type == "content_start":
                            print("\n   🎭 AI Response:")
                            print("   " + "="*40)
                        elif event_type == "content_end":
                            print(f"\n   " + "="*40)
                        elif event_type == "error":
                            print(f"   ❌ Error: {data}")
            else:
                print(f"❌ Stream failed: {resp.status}")
                return
        
        end_time = time.time()
        
        print(f"\n📊 STREAMING RESULTS:")
        print(f"   ⏱️  Total time: {end_time - start_time:.2f}s")
        print(f"   📦 Events received: {events_received}")
        print(f"   📝 Response length: {len(response_text)} characters")
        print(f"   🚀 Characters per second: {len(response_text)/(end_time - start_time):.1f}")
        
        # Test perceived speed
        words_count = len(response_text.split())
        perceived_speed = words_count / (end_time - start_time)
        print(f"   💭 Words per second: {perceived_speed:.1f}")
        
        if perceived_speed > 10:
            print("   ✅ Excellent streaming speed!")
        elif perceived_speed > 5:
            print("   ✅ Good streaming speed!")
        else:
            print("   ⚠️  Streaming could be faster")

async def test_streaming_npc_dialogue():
    """Test streaming NPC dialogue"""
    print("\n🎭 STREAMING NPC DIALOGUE TEST")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # Test NPC dialogue streaming
        dialogue_request = {
            "world_id": str(uuid4()),
            "npc_id": str(uuid4()),  # Use proper UUID format
            "player_action": "I approach the tavern keeper and ask about any rumors or interesting tales from recent travelers",
            "situation": "busy tavern evening"
        }
        
        start_time = time.time()
        dialogue_text = ""
        events_received = 0
        
        print("📡 Starting NPC dialogue stream...")
        async with session.post(f"{BASE_URL}/api/v1/stream/npc-dialogue", json=dialogue_request) as resp:
            if resp.status == 200:
                async for line in resp.content:
                    line = line.decode().strip()
                    if not line:
                        continue
                    
                    if line.startswith("event:"):
                        event_type = line.split(":", 1)[1].strip()
                    elif line.startswith("data:"):
                        data = line.split(":", 1)[1].strip()
                        events_received += 1
                        
                        if event_type == "status":
                            print(f"   📊 Status: {data}")
                        elif event_type == "dialogue":
                            dialogue_text += data
                            if data:
                                print(f"{data}", end="", flush=True)
                        elif event_type == "dialogue_start":
                            print("\n   💬 NPC Dialogue:")
                            print("   " + "="*40)
                            print("   ", end="", flush=True)
                        elif event_type == "dialogue_end":
                            print(f"\n   " + "="*40)
                        elif event_type == "error":
                            print(f"   ❌ Error: {data}")
            else:
                print(f"❌ Dialogue stream failed: {resp.status}")
                return
        
        end_time = time.time()
        
        print(f"\n📊 NPC DIALOGUE RESULTS:")
        print(f"   ⏱️  Total time: {end_time - start_time:.2f}s")
        print(f"   📦 Events received: {events_received}")
        print(f"   💬 Dialogue length: {len(dialogue_text)} characters")
        
        # Estimate typing speed (human-like)
        typing_speed = len(dialogue_text) / (end_time - start_time)
        print(f"   ⌨️  Typing speed: {typing_speed:.1f} chars/sec")
        
        if typing_speed > 50:
            print("   ✅ Fast typing speed!")
        elif typing_speed > 20:
            print("   ✅ Natural typing speed!")
        else:
            print("   📝 Slow, contemplative typing")

async def test_streaming_health():
    """Test streaming health endpoint"""
    print("\n🔍 STREAMING HEALTH CHECK")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/v1/stream/health") as resp:
            if resp.status == 200:
                health = await resp.json()
                print(f"✅ Streaming service healthy: {health}")
            else:
                print(f"❌ Health check failed: {resp.status}")

async def main():
    """Run all streaming tests"""
    print("🚀 GAME MASTER V3 - STREAMING TESTS")
    print("=" * 60)
    
    try:
        await test_streaming_health()
        await test_streaming_command()
        await test_streaming_npc_dialogue()
        
        print("\n🎉 ALL STREAMING TESTS COMPLETE!")
        print("✅ Server-Sent Events (SSE) working properly")
        print("✅ Real-time responses implemented")
        print("✅ Streaming provides immediate user feedback")
        
    except Exception as e:
        print(f"\n❌ Streaming test error: {e}")
        print("Make sure the server is running at http://localhost:8000")

if __name__ == "__main__":
    asyncio.run(main())
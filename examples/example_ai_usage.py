"""
Example usage of Game Master V3 AI capabilities
Demonstrates NPC dialogue, world descriptions, and context building
"""
import asyncio
import json
import os
from uuid import uuid4

import httpx

# API base URL
BASE_URL = "http://localhost:8000/api/v1"


async def main():
    """Demonstrate AI capabilities"""
    
    # Check if we need to set OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  OpenAI API key not set. AI features will not work.")
        print("   Set OPENAI_API_KEY environment variable to test AI features.")
        print("   Example: export OPENAI_API_KEY='your-api-key-here'")
        print()
    
    async with httpx.AsyncClient(timeout=30) as client:
        
        print("🤖 Game Master V3 - AI Features Demo")
        print("=" * 50)
        
        # Check AI service health
        print("\n1. Checking AI service health...")
        try:
            response = await client.get(f"{BASE_URL}/ai/health")
            health = response.json()
            print(f"   AI Service: {'✓' if health['ai_service_initialized'] else '✗'}")
            print(f"   Status: {health['status']}")
            
            if not health['ai_service_initialized']:
                print("\n   💡 AI Service not initialized. This is expected if:")
                print("      - OpenAI API key is not set")
                print("      - API key is invalid")
                print("      - Network connectivity issues")
                return
                
        except Exception as e:
            print(f"   ❌ Failed to check AI health: {e}")
            return
        
        # Get existing entities for testing
        print("\n2. Finding existing entities...")
        try:
            # Search for different entity types separately
            player_search = await client.post(f"{BASE_URL}/search", json={
                "query": "adventurer player",
                "limit": 2
            })
            
            npc_search = await client.post(f"{BASE_URL}/search", json={
                "query": "Barliman bartender",
                "limit": 2
            })
            
            location_search = await client.post(f"{BASE_URL}/search", json={
                "query": "tavern prancing pony",
                "limit": 2
            })
            
            # Check all search responses
            if (player_search.status_code != 200 or 
                npc_search.status_code != 200 or 
                location_search.status_code != 200):
                print("   ❌ Failed to search entities")
                return
                
            players = player_search.json()
            npcs = npc_search.json()
            locations = location_search.json()
            
            # Find entities
            player = players[0]["entity"] if players else None
            npc = npcs[0]["entity"] if npcs else None
            location = locations[0]["entity"] if locations else None
            
            if not player or not npc:
                print("   ❌ Could not find required entities (player and NPC)")
                return
                
            print(f"   Found Player: {player['name']}")
            print(f"   Found NPC: {npc['name']}")
            if location:
                print(f"   Found Location: {location['name']}")
                
        except Exception as e:
            print(f"   ❌ Failed to find entities: {e}")
            return
        
        # Test context preview
        print("\n3. Previewing AI context...")
        try:
            context_response = await client.get(
                f"{BASE_URL}/ai/context/preview/{player['id']}",
                params={
                    "interaction_target_id": npc['id'],
                    "search_query": "tavern conversation"
                }
            )
            
            if context_response.status_code == 200:
                context_data = context_response.json()
                metrics = context_data["metrics"]
                entities = context_data["entities"]
                
                print(f"   Context entities: {len(entities)}")
                print(f"   Estimated tokens: {metrics['tokens_estimated']}")
                print(f"   Assembly time: {metrics['assembly_time']:.3f}s")
                
                print("   Entities in context:")
                for entity in entities[:3]:  # Show first 3
                    print(f"   - {entity['name']} ({entity['type']})")
                if len(entities) > 3:
                    print(f"   ... and {len(entities) - 3} more")
                    
        except Exception as e:
            print(f"   ⚠️  Context preview failed: {e}")
        
        # Test NPC dialogue
        print("\n4. Testing NPC dialogue...")
        try:
            dialogue_request = {
                "player_id": player['id'],
                "npc_id": npc['id'],
                "player_message": "Hello! Could you tell me about this place?",
                "situation_context": "The player just entered the tavern and is looking around curiously.",
                "session_id": str(uuid4())
            }
            
            dialogue_response = await client.post(f"{BASE_URL}/ai/npc/dialogue", json=dialogue_request)
            
            if dialogue_response.status_code == 200:
                ai_result = dialogue_response.json()
                
                print(f"   💬 {npc['name']}: \"{ai_result['content']}\"")
                print(f"   Confidence: {ai_result['confidence']:.2f}")
                print(f"   Tokens used: {ai_result['tokens_used']}")
                print(f"   Response time: {ai_result['response_time']:.3f}s")
                print(f"   Context entities: {ai_result['context_entities_used']}")
                
                if ai_result['hallucination_detected']:
                    print("   ⚠️  Potential hallucination detected!")
                    for warning in ai_result['warnings']:
                        print(f"      - {warning}")
                
                if ai_result['cited_entities']:
                    print(f"   Referenced: {', '.join(ai_result['cited_entities'])}")
                    
            else:
                print(f"   ❌ Dialogue failed: {dialogue_response.status_code}")
                
        except Exception as e:
            print(f"   ❌ NPC dialogue failed: {e}")
        
        # Test world description
        print("\n5. Testing world description...")
        try:
            description_request = {
                "player_id": player['id'],
                "request": "Describe the atmosphere and what I can see around me",
                "session_id": str(uuid4())
            }
            
            description_response = await client.post(f"{BASE_URL}/ai/world/describe", json=description_request)
            
            if description_response.status_code == 200:
                ai_result = description_response.json()
                
                print(f"   🌍 World Description:")
                print(f"   {ai_result['content']}")
                print(f"   Confidence: {ai_result['confidence']:.2f}")
                print(f"   Tokens used: {ai_result['tokens_used']}")
                
                if ai_result['hallucination_detected']:
                    print("   ⚠️  Potential hallucination detected!")
                    
            else:
                print(f"   ❌ Description failed: {description_response.status_code}")
                
        except Exception as e:
            print(f"   ❌ World description failed: {e}")
        
        # Get AI statistics
        print("\n6. AI Usage Statistics...")
        try:
            stats_response = await client.get(f"{BASE_URL}/ai/admin/ai-stats")
            
            if stats_response.status_code == 200:
                stats = stats_response.json()
                
                print(f"   Total AI interactions: {stats['total_ai_interactions']}")
                print(f"   Average confidence: {stats['average_confidence']:.2f}")
                print(f"   Hallucination rate: {stats['hallucination_rate']:.1%}")
                
                if stats['recent_interactions']:
                    print("   Recent interactions:")
                    for interaction in stats['recent_interactions'][:3]:
                        print(f"   - {interaction['action_type']}: confidence {interaction['confidence']:.2f}")
                        
        except Exception as e:
            print(f"   ⚠️  Stats failed: {e}")
        
        print("\n" + "=" * 50)
        print("✅ AI Demo completed!")
        print("\n🎮 Try these AI endpoints:")
        print("   • NPC Dialogue: POST /api/v1/ai/npc/dialogue")
        print("   • World Description: POST /api/v1/ai/world/describe")
        print("   • Context Preview: GET /api/v1/ai/context/preview/{player_id}")
        print("   • AI Health: GET /api/v1/ai/health")
        print("   • AI Stats: GET /api/v1/ai/admin/ai-stats")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except httpx.ConnectError:
        print("❌ Error: Could not connect to API")
        print("   Make sure the API is running with: make api")
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
"""
Example usage of Game Master V3 API
Demonstrates basic operations with the world system
"""
import asyncio
import json
from uuid import uuid4

import httpx

# API base URL
BASE_URL = "http://localhost:8000/api/v1"


async def main():
    """Demonstrate basic API usage"""
    
    async with httpx.AsyncClient() as client:
        
        print("🎮 Game Master V3 - Example Usage")
        print("=" * 50)
        
        # Check API health
        print("\n1. Checking API health...")
        response = await client.get("http://localhost:8000/health")
        health = response.json()
        print(f"   Status: {health['status']}")
        print(f"   World Service: {'✓' if health['world_service_initialized'] else '✗'}")
        
        # Search for entities
        print("\n2. Searching for tavern...")
        search_response = await client.post(f"{BASE_URL}/search", json={
            "query": "tavern cozy ale",
            "limit": 5,
            "include_context": True
        })
        
        if search_response.status_code == 200:
            results = search_response.json()
            print(f"   Found {len(results)} results:")
            for result in results:
                entity = result["entity"]
                score = result["score"]
                print(f"   - {entity['name']} (score: {score:.3f})")
                print(f"     {entity['description'][:80]}...")
        
        # Get entity context
        if search_response.status_code == 200 and results:
            entity_id = results[0]["entity"]["id"]
            print(f"\n3. Getting context for entity {entity_id[:8]}...")
            
            context_response = await client.get(f"{BASE_URL}/entities/{entity_id}/context")
            
            if context_response.status_code == 200:
                context = context_response.json()
                print(f"   Found {len(context)} related entities:")
                for ctx_entity in context:
                    entity = ctx_entity["entity"]
                    print(f"   - {entity['name']} ({entity['type']})")
        
        # Create a new NPC
        print("\n4. Creating a new NPC...")
        new_npc_data = {
            "entity_data": {
                "name": "Mysterious Traveler",
                "description": "A cloaked figure with piercing eyes and an air of mystery.",
                "personality": {
                    "core_traits": ["mysterious", "wise", "cryptic"],
                    "speech_patterns": ["speaks in riddles", "uses archaic words"],
                    "likes": ["ancient lore", "starlight", "quiet conversations"],
                    "dislikes": ["crowds", "loud noises", "direct questions"],
                    "fears": ["being discovered", "bright light"],
                    "goals": ["share wisdom", "find the chosen one"],
                    "backstory": "An ancient being who has wandered the world for centuries.",
                    "example_phrases": [
                        "The stars whisper secrets to those who listen...",
                        "Time flows differently for those who understand its nature.",
                        "Seek not what you wish to find, but what needs to be found."
                    ]
                },
                "current_state": {
                    "current_mood": "contemplative",
                    "current_activity": "observing"
                },
                "importance_level": 5
            },
            "entity_type": "npc",
            "actor_id": str(uuid4()),
            "session_id": str(uuid4())
        }
        
        create_response = await client.post(f"{BASE_URL}/entities", json=new_npc_data)
        
        if create_response.status_code == 200:
            created_npc = create_response.json()
            npc_id = created_npc["entity"]["id"]
            print(f"   ✓ Created NPC: {created_npc['entity']['name']}")
            print(f"   ID: {npc_id}")
            
            # Get entity history
            print(f"\n5. Getting history for new NPC...")
            history_response = await client.get(f"{BASE_URL}/entities/{npc_id}/history")
            
            if history_response.status_code == 200:
                history = history_response.json()
                print(f"   Found {len(history)} history entries:")
                for entry in history:
                    print(f"   - {entry['timestamp']}: {entry['action_type']} by {entry['actor_type']}")
        
        # Get recent changes
        print("\n6. Getting recent world changes...")
        changes_response = await client.get(f"{BASE_URL}/changes/recent?limit=5")
        
        if changes_response.status_code == 200:
            changes = changes_response.json()
            print(f"   Last {len(changes)} changes:")
            for change in changes:
                entity_id_short = change['entity_id'][:8]
                print(f"   - {change['timestamp']}: {change['action_type']} on {change['entity_type']} {entity_id_short}")
        
        # Create world snapshot
        print("\n7. Creating world snapshot...")
        snapshot_response = await client.post(f"{BASE_URL}/snapshots?created_by=example_script")
        
        if snapshot_response.status_code == 200:
            snapshot = snapshot_response.json()
            print(f"   ✓ Created snapshot: {snapshot['snapshot_id']}")
            print(f"   Message: {snapshot['message']}")
        
        print("\n" + "=" * 50)
        print("✅ Example completed successfully!")
        print("\n📖 Try these URLs in your browser:")
        print("   • API Documentation: http://localhost:8000/docs")
        print("   • Neo4j Browser: http://localhost:7474")
        print("   • Qdrant Dashboard: http://localhost:6333/dashboard")
        print("   • Grafana: http://localhost:3000")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except httpx.ConnectError:
        print("❌ Error: Could not connect to API")
        print("   Make sure the API is running with: make start && make init")
        print("   Or install and run locally with: make install && make api")
    except Exception as e:
        print(f"❌ Error: {e}")
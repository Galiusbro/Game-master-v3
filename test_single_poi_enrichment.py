#!/usr/bin/env python3
"""
Test script to enrich a single POI and see the full AI response
"""
import asyncio
import sys
import os
from uuid import UUID

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.worldgen.ai_enrichment_service import ai_world_enrichment_service
from core.world_service import world_service
from infrastructure.ai_service import ai_service

async def test_single_poi():
    # Get a specific POI from our test world  
    world_id = "cd4978d5-2b83-4f37-b580-dfd00f1b63c4"
    
    # Use a known POI ID from the summary we got earlier
    poi_id = "dfa9f71b-878a-4a23-8bf2-0015994934a3"  # First POI from the enrichment summary
    
    try:
        poi = await world_service.get_entity(UUID(poi_id))
        if not poi:
            print(f"❌ POI {poi_id} not found")
            return
    except Exception as e:
        print(f"❌ Error getting POI {poi_id}: {e}")
        return
    print(f"🎯 Testing enrichment for POI: {poi.name}")
    print(f"📍 Original description: {poi.description}")
    print(f"🆔 POI ID: {poi.id}")
    
    # Get AI service template
    template = ai_world_enrichment_service.templates["poi"]
    
    # Build context
    context = {
        "world_lore": "A fantasy world of magic and adventure",
        "regional_context": "A peaceful countryside region",
        "name": poi.name,
        "poi_type": poi.metadata.get("poi_type", "unknown"),
        "description": poi.description,
        "location_context": "Near a small village"
    }
    
    prompt = template["user"].format(**context)
    
    print(f"\n📝 Prompt sent to AI:")
    print("=" * 50)
    print(prompt)
    print("=" * 50)
    
    # Call AI
    response = await ai_service.generate_completion(
        system_prompt=template["system"],
        user_prompt=prompt,
        max_completion_tokens=500,
    )
    
    print(f"\n🤖 Full AI Response:")
    print("=" * 50)
    print(response.content)
    print("=" * 50)
    
    # Test our parsing
    print(f"\n🔍 Testing our parsing logic...")
    await ai_world_enrichment_service._apply_enrichment(poi, response.content, str(world_id))
    
    # Get updated entity
    updated_poi = await world_service.get_entity(poi.id)
    print(f"✅ Updated name: {updated_poi.name}")
    print(f"✅ Updated description: {updated_poi.description}")

if __name__ == "__main__":
    asyncio.run(test_single_poi())

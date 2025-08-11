#!/usr/bin/env python3
"""
Test script to debug settlement enrichment specifically
"""

import asyncio
import json
import sys
import os
from uuid import UUID

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.world_service import world_service
from domain.entities import EntityType
from infrastructure.ai_service import ai_service
from core.worldgen.ai_enrichment_service import AIWorldEnrichmentService

async def test_settlement_enrichment():
    """Test settlement enrichment with detailed logging"""
    
    world_id = "70925c6f-edb8-4bd5-9565-a544a79f6f25"
    
    print(f"🔍 Testing settlement enrichment for world: {world_id}")
    
    # Initialize services
    await world_service.initialize()
    await ai_service.ensure_initialized()
    
    # Find a settlement that hasn't been enriched yet
    print("🔎 Searching for settlements...")
    
    # Get all entities in the world with a broader search
    all_entities = await world_service.search_entities(
        entity_types=[EntityType.LOCATION],
        query="town city village"
    )
    
    print(f"Found {len(all_entities)} location entities")
    
    settlements = []
    for entity, score in all_entities:
        print(f"Checking entity: {entity.name} (type: {entity.type}, metadata: {entity.metadata})")
        
        if entity.metadata:
            location_kind = entity.metadata.get("location_kind", "")
            if location_kind in ["city", "town", "village"]:
                settlements.append(entity)
                print(f"✅ Found settlement: {entity.name} (ID: {entity.id}, kind: {location_kind})")
        
        # Also check for generic names that might be settlements
        if any(generic in entity.name for generic in ["Temple", "Town", "City", "Village", "Healer"]):
            settlements.append(entity)
            print(f"✅ Found potential settlement by name: {entity.name} (ID: {entity.id})")
    
    if not settlements:
        print("❌ No settlements found to test")
        # Let's try to get a specific entity we know exists
        print("🔍 Trying to find any location with 'Healer Temple 3'...")
        
        # Search more broadly
        all_locations = await world_service.search_entities(
            entity_types=[EntityType.LOCATION],
            query="Healer Temple"
        )
        
        for entity, score in all_locations:
            if "Healer Temple" in entity.name:
                settlements.append(entity)
                print(f"✅ Found by direct search: {entity.name} (ID: {entity.id})")
                break
    
    if not settlements:
        print("❌ Still no settlements found to test")
        return
    
    # Take first settlement for testing
    test_settlement = settlements[0]
    print(f"\n🎯 Testing enrichment on: {test_settlement.name}")
    print(f"   ID: {test_settlement.id}")
    print(f"   Current description: {test_settlement.description[:100]}...")
    
    # Create enrichment service and test single settlement
    enrichment_service = AIWorldEnrichmentService()
    
    # Build context (simplified)
    from core.worldgen.ai_enrichment_service import EnrichmentContext
    context = EnrichmentContext()
    context.world_lore = "A fantasy world of magic and adventure where heroes embark on epic quests."
    
    print("\n🚀 Starting enrichment...")
    
    # Test the enrichment
    await enrichment_service._enrich_settlement(UUID(str(test_settlement.id)), context)
    
    # Fetch the updated entity
    updated_settlement = await world_service.get_entity(UUID(str(test_settlement.id)), EntityType.LOCATION)
    
    print(f"\n📊 RESULTS:")
    print(f"Original name: {test_settlement.name}")
    print(f"New name: {updated_settlement.name}")
    print(f"Name changed: {'✅ YES' if test_settlement.name != updated_settlement.name else '❌ NO'}")
    
    print(f"\nOriginal description: {test_settlement.description[:200]}...")
    print(f"New description: {updated_settlement.description[:200]}...")
    print(f"Description changed: {'✅ YES' if test_settlement.description != updated_settlement.description else '❌ NO'}")
    
    if updated_settlement.metadata and updated_settlement.metadata.get("ai_enriched_content"):
        print(f"\n🤖 AI enriched content present: ✅ YES")
        ai_content = updated_settlement.metadata["ai_enriched_content"]
        print(f"AI content length: {len(ai_content)} characters")
        
        # Check if it has the expected format
        if "ENHANCED NAME:" in ai_content:
            print("✅ ENHANCED NAME format found")
        else:
            print("❌ ENHANCED NAME format missing")
            
        if "RICH DESCRIPTION:" in ai_content:
            print("✅ RICH DESCRIPTION format found")
        else:
            print("❌ RICH DESCRIPTION format missing")
    else:
        print(f"\n🤖 AI enriched content: ❌ MISSING")

if __name__ == "__main__":
    asyncio.run(test_settlement_enrichment())

#!/usr/bin/env python3
"""
Test script to debug enrichment of specific Healer Temple 3
"""

import asyncio
import sys
import os
from uuid import UUID

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.world_service import world_service
from domain.entities import EntityType
from infrastructure.ai_service import ai_service
from core.worldgen.ai_enrichment_service import AIWorldEnrichmentService, EnrichmentContext

async def test_healer_temple_enrichment():
    """Test enrichment of specific Healer Temple 3"""
    
    world_id = "70925c6f-edb8-4bd5-9565-a544a79f6f25"
    healer_temple_id = "3420699c-fd56-4a38-b23e-10c26548ad70"
    
    print(f"🔍 Testing enrichment for Healer Temple 3")
    print(f"   World ID: {world_id}")
    print(f"   Entity ID: {healer_temple_id}")
    
    # Initialize services
    await world_service.initialize()
    await ai_service.ensure_initialized()
    
    # Get the specific entity
    print("🔎 Fetching entity from database...")
    entity = await world_service.get_entity(UUID(healer_temple_id), EntityType.LOCATION)
    
    if not entity:
        print("❌ Entity not found!")
        return
        
    print(f"✅ Found entity: {entity.name}")
    print(f"   Type: {entity.type}")
    print(f"   Description: {entity.description}")
    print(f"   Metadata: {entity.metadata}")
    
    # Check location_kind
    location_kind = entity.metadata.get("location_kind", "unknown") if entity.metadata else "unknown"
    print(f"   Location kind: {location_kind}")
    
    # Create enrichment service
    enrichment_service = AIWorldEnrichmentService()
    context = EnrichmentContext()
    context.world_lore = "A fantasy world of magic and adventure where heroes embark on epic quests."
    
    print("\n🚀 Starting enrichment...")
    
    # Determine which enrichment method to use based on location_kind
    if location_kind == "building":
        print("📍 This is a building - checking if it should be enriched as POI or settlement...")
        
        # Try POI enrichment (buildings are usually POIs)
        print("🎯 Testing POI enrichment...")
        await enrichment_service._enrich_poi(UUID(healer_temple_id), context)
        
    elif location_kind in ["city", "town", "village"]:
        print("🏘️ This is a settlement - using settlement enrichment...")
        await enrichment_service._enrich_settlement(UUID(healer_temple_id), context)
        
    else:
        print(f"❓ Unknown location_kind: {location_kind}")
        print("🎯 Trying POI enrichment as fallback...")
        await enrichment_service._enrich_poi(UUID(healer_temple_id), context)
    
    # Fetch the updated entity
    print("\n📊 Checking results...")
    updated_entity = await world_service.get_entity(UUID(healer_temple_id), EntityType.LOCATION)
    
    print(f"Original name: {entity.name}")
    print(f"New name: {updated_entity.name}")
    print(f"Name changed: {'✅ YES' if entity.name != updated_entity.name else '❌ NO'}")
    
    print(f"\nOriginal description: {entity.description}")
    print(f"New description: {updated_entity.description[:200]}...")
    print(f"Description changed: {'✅ YES' if entity.description != updated_entity.description else '❌ NO'}")
    
    if updated_entity.metadata and updated_entity.metadata.get("ai_enriched_content"):
        print(f"\n🤖 AI enriched content present: ✅ YES")
        ai_content = updated_entity.metadata["ai_enriched_content"]
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
    asyncio.run(test_healer_temple_enrichment())

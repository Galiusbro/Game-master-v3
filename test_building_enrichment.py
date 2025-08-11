#!/usr/bin/env python3
"""
Test script to verify building enrichment works
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

async def test_building_enrichment():
    """Test building enrichment with detailed logging"""
    
    world_id = "70925c6f-edb8-4bd5-9565-a544a79f6f25"
    # From the export: "Blacksmith Crafts 4"
    building_id = "753ce314-04f3-4413-a363-82ad6f7e5143"
    
    print(f"🔍 Testing building enrichment")
    print(f"   World ID: {world_id}")
    print(f"   Building ID: {building_id}")
    
    # Initialize services
    await world_service.initialize()
    await ai_service.ensure_initialized()
    
    # Get the specific entity
    print("🔎 Fetching building from database...")
    building = await world_service.get_entity(UUID(building_id), EntityType.LOCATION)
    
    if not building:
        print("❌ Building not found!")
        return
        
    print(f"✅ Found building: {building.name}")
    print(f"   Type: {building.type}")
    print(f"   Description: {building.description}")
    print(f"   Metadata: {building.metadata}")
    
    # Check location_kind
    location_kind = building.metadata.get("location_kind", "unknown") if building.metadata else "unknown"
    building_type = building.metadata.get("kind", "unknown") if building.metadata else "unknown"
    print(f"   Location kind: {location_kind}")
    print(f"   Building type: {building_type}")
    
    # Create enrichment service and test
    enrichment_service = AIWorldEnrichmentService()
    context = EnrichmentContext()
    context.world_lore = "A fantasy world of magic and adventure where heroes embark on epic quests."
    
    print("\n🚀 Starting building enrichment...")
    
    # Test building enrichment
    await enrichment_service._enrich_building(UUID(building_id), context)
    
    # Fetch the updated entity
    print("\n📊 Checking results...")
    updated_building = await world_service.get_entity(UUID(building_id), EntityType.LOCATION)
    
    print(f"Original name: {building.name}")
    print(f"New name: {updated_building.name}")
    print(f"Name changed: {'✅ YES' if building.name != updated_building.name else '❌ NO'}")
    
    print(f"\nOriginal description: {building.description}")
    print(f"New description: {updated_building.description[:200]}...")
    print(f"Description changed: {'✅ YES' if building.description != updated_building.description else '❌ NO'}")
    
    if updated_building.metadata and updated_building.metadata.get("ai_enriched_content"):
        print(f"\n🤖 AI enriched content present: ✅ YES")
        ai_content = updated_building.metadata["ai_enriched_content"]
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
    asyncio.run(test_building_enrichment())

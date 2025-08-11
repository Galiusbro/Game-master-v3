#!/usr/bin/env python3
"""
Test script for AI-enhanced world generation

This script demonstrates the new AI enrichment functionality
by generating a small world and showing before/after comparisons.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.worldgen.pipeline import generate_world, WorldGenParams
from core.world_service import world_service
from domain.entities import EntityType
from uuid import UUID


async def test_ai_worldgen():
    """Test AI-enhanced world generation"""
    print("🌍 Testing AI-Enhanced World Generation")
    print("=" * 50)
    
    # Test parameters for a small world
    params = WorldGenParams(
        seed="ai_test_world",
        grid_size=128,  # Smaller for faster generation
        water_ratio=0.6,
        mountain_density=0.3,
        enable_ai_enrichment=True
    )
    
    print(f"🔧 Generation parameters:")
    print(f"   Seed: {params.seed}")
    print(f"   Grid size: {params.grid_size}")
    print(f"   AI enrichment: {params.enable_ai_enrichment}")
    print()
    
    # Generate the world
    print("🏗️ Starting world generation...")
    try:
        summary = await generate_world(params)
        print("✅ World generation completed!")
        print()
        
        # Show generation summary
        print("📊 Generation Summary:")
        print(f"   World ID: {summary['world_id']}")
        print(f"   Continents: {len(summary['continents'])}")
        print(f"   Regions: {len(summary['regions'])}")
        print(f"   Cities: {len(summary['cities'])}")
        print(f"   Towns: {len(summary['towns'])}")
        print(f"   Villages: {len(summary['villages'])}")
        print(f"   NPCs: {len(summary['npcs'])}")
        print(f"   POIs: {len(summary['poi'])}")
        
        # Show AI enrichment status
        ai_status = summary.get('ai_enrichment', {})
        if ai_status.get('enriched'):
            print(f"   🎨 AI Enrichment: ✅ SUCCESS ({ai_status.get('entities_processed', 0)} entities)")
        else:
            reason = ai_status.get('error') or ai_status.get('reason', 'unknown')
            print(f"   🎨 AI Enrichment: ❌ FAILED/DISABLED ({reason})")
        print()
        
        # Show some sample enriched entities
        await show_sample_entities(summary)
        
    except Exception as e:
        print(f"❌ World generation failed: {e}")
        import traceback
        traceback.print_exc()


async def show_sample_entities(summary):
    """Show sample enriched entities"""
    print("🎭 Sample Enriched Entities:")
    print("-" * 30)
    
    # Show world entity
    try:
        world_id = summary['world_id']
        world = await world_service.get_entity(UUID(world_id), EntityType.LOCATION)
        if world:
            print(f"🌍 WORLD: {world.name}")
            print(f"   Description: {world.description[:200]}...")
            if world.metadata and world.metadata.get('enriched_by_ai'):
                print("   ✅ AI Enhanced")
            print()
    except Exception as e:
        print(f"   ❌ Could not fetch world: {e}")
    
    # Show a continent
    if summary['continents']:
        try:
            continent_id = UUID(summary['continents'][0])
            continent = await world_service.get_entity(continent_id, EntityType.LOCATION)
            if continent:
                print(f"🏔️ CONTINENT: {continent.name}")
                print(f"   Description: {continent.description[:200]}...")
                if continent.metadata and continent.metadata.get('enriched_by_ai'):
                    print("   ✅ AI Enhanced")
                print()
        except Exception as e:
            print(f"   ❌ Could not fetch continent: {e}")
    
    # Show a city
    if summary['cities']:
        try:
            city_id = UUID(summary['cities'][0])
            city = await world_service.get_entity(city_id, EntityType.LOCATION)
            if city:
                print(f"🏰 CITY: {city.name}")
                print(f"   Description: {city.description[:200]}...")
                if city.metadata and city.metadata.get('enriched_by_ai'):
                    print("   ✅ AI Enhanced")
                print()
        except Exception as e:
            print(f"   ❌ Could not fetch city: {e}")
    
    # Show an NPC
    if summary['npcs']:
        try:
            npc_id = UUID(summary['npcs'][0])
            npc = await world_service.get_entity(npc_id, EntityType.NPC)
            if npc:
                print(f"👤 NPC: {npc.name}")
                print(f"   Description: {npc.description[:200]}...")
                if npc.metadata and npc.metadata.get('enriched_by_ai'):
                    print("   ✅ AI Enhanced")
                print()
        except Exception as e:
            print(f"   ❌ Could not fetch NPC: {e}")


async def test_without_ai():
    """Test world generation without AI enrichment for comparison"""
    print("\n" + "=" * 50)
    print("🤖 Testing WITHOUT AI Enhancement (for comparison)")
    print("=" * 50)
    
    params = WorldGenParams(
        seed="basic_test_world",
        grid_size=128,
        water_ratio=0.6,
        mountain_density=0.3,
        enable_ai_enrichment=False  # Disabled
    )
    
    try:
        summary = await generate_world(params)
        print("✅ Basic world generation completed!")
        
        # Show basic entity for comparison
        if summary['cities']:
            city_id = UUID(summary['cities'][0])
            city = await world_service.get_entity(city_id, EntityType.LOCATION)
            if city:
                print(f"\n📝 Sample Basic City: {city.name}")
                print(f"   Description: {city.description}")
                print("   ❌ No AI Enhancement")
        
    except Exception as e:
        print(f"❌ Basic world generation failed: {e}")


if __name__ == "__main__":
    print("🚀 AI World Generation Test Suite")
    print("This will test the new AI enrichment functionality")
    print()
    
    # Run tests
    asyncio.run(test_ai_worldgen())
    asyncio.run(test_without_ai())
    
    print("\n🏁 Test completed!")
    print("Check the output above to see AI enrichment in action.")

#!/usr/bin/env python3
"""
Test script for post-generation AI enrichment

This script demonstrates the two-phase approach:
1. Generate world quickly without AI enrichment
2. Apply AI enrichment afterwards as a separate step
"""

import asyncio
import sys
import requests
import json
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.world_service import world_service
from domain.entities import EntityType
from uuid import UUID


def test_api_workflow():
    """Test the API workflow for post-generation enrichment"""
    print("🚀 Testing Post-Generation AI Enrichment Workflow")
    print("=" * 60)
    
    base_url = "http://localhost:8000/api/v1"
    
    # Step 1: Generate world without AI enrichment (fast)
    print("📋 Step 1: Generate world structure (without AI)...")
    gen_payload = {
        "seed": "post_enrich_test",
        "grid_size": 96,
        "water_ratio": 0.6,
        "enable_ai_enrichment": False  # Disabled for speed
    }
    
    try:
        response = requests.post(f"{base_url}/world/generate", json=gen_payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        
        if not result["success"]:
            print(f"❌ Generation failed: {result.get('error')}")
            return
            
        world_id = result["summary"]["world_id"]
        summary = result["summary"]
        
        print(f"✅ World generated successfully!")
        print(f"   World ID: {world_id}")
        print(f"   Continents: {len(summary['continents'])}")
        print(f"   Regions: {len(summary['regions'])}")
        print(f"   Cities: {len(summary['cities'])}")
        print(f"   NPCs: {len(summary['npcs'])}")
        print(f"   AI Enriched: {summary.get('ai_enrichment', {}).get('enriched', False)}")
        print()
        
        # Step 2: Apply AI enrichment to the generated world
        print("🎨 Step 2: Apply AI enrichment to existing world...")
        enrich_payload = {"world_id": world_id}
        
        response = requests.post(f"{base_url}/world/enrich", json=enrich_payload, timeout=300)
        response.raise_for_status()
        result = response.json()
        
        if not result["success"]:
            print(f"❌ Enrichment failed: {result.get('error')}")
            return
            
        enriched_summary = result["summary"]
        
        print(f"✅ World enriched successfully!")
        print(f"   Message: {result['message']}")
        print(f"   AI Enriched: {enriched_summary.get('ai_enrichment', {}).get('enriched', False)}")
        print(f"   Entities Processed: {enriched_summary.get('ai_enrichment', {}).get('entities_processed', 0)}")
        print()
        
        # Step 3: Show comparison (this would require async context for database access)
        print("📊 Enrichment completed! Check the database for enhanced descriptions.")
        print(f"💡 You can now query world {world_id} to see AI-enhanced content.")
        
        return world_id
        
    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None


async def show_enrichment_comparison(world_id: str):
    """Show before/after comparison of entities"""
    print("\n🔍 Enrichment Comparison:")
    print("-" * 30)
    
    try:
        # Show world entity
        world = await world_service.get_entity(UUID(world_id), EntityType.LOCATION)
        if world:
            print(f"🌍 WORLD: {world.name}")
            print(f"   Description: {world.description[:150]}...")
            if world.metadata and world.metadata.get('enriched_by_ai'):
                print("   ✅ AI Enhanced")
            else:
                print("   ❌ Basic Description")
            print()
        
        # You could add more entity comparisons here
        
    except Exception as e:
        print(f"❌ Could not fetch entities: {e}")


def main():
    print("🌍 Post-Generation AI Enrichment Test")
    print("This demonstrates the flexible two-phase approach:")
    print("1. Fast world generation without AI")
    print("2. Optional AI enrichment afterwards")
    print()
    
    # Test API workflow
    world_id = test_api_workflow()
    
    if world_id:
        print("\n🎯 Commands to test manually:")
        print(f"# 1. Generate world without AI (fast)")
        print(f"curl -X POST http://localhost:8000/api/v1/world/generate \\")
        print(f"  -H 'Content-Type: application/json' \\")
        print(f"  -d '{{\"seed\":\"manual_test\",\"grid_size\":96,\"enable_ai_enrichment\":false}}'")
        print()
        print(f"# 2. Enrich with AI afterwards")
        print(f"curl -X POST http://localhost:8000/api/v1/world/enrich \\")
        print(f"  -H 'Content-Type: application/json' \\")
        print(f"  -d '{{\"world_id\":\"<WORLD_ID_FROM_STEP_1>\"}}'")
        print()
        
        # Show async comparison if possible
        try:
            asyncio.run(show_enrichment_comparison(world_id))
        except Exception as e:
            print(f"Note: Could not show comparison (needs database access): {e}")
    
    print("🏁 Test completed!")


if __name__ == "__main__":
    main()

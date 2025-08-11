#!/usr/bin/env python3
"""
Test script to verify Master Lore generation works
"""

import asyncio
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from infrastructure.ai_service import ai_service
from core.worldgen.ai_enrichment_service import AIWorldEnrichmentService

async def test_master_lore_generation():
    """Test Master Lore generation with sample world data"""
    
    print("🔍 Testing Master Lore generation")
    
    # Initialize AI service
    await ai_service.ensure_initialized()
    
    # Create sample world summary (like from our test world)
    sample_world_summary = {
        "continents": ["cont1", "cont2", "cont3"],  # 3 continents
        "regions": ["reg1", "reg2", "reg3", "reg4", "reg5"],  # 5 regions
        "cities": ["city1", "city2", "city3"],  # 3 cities
        "towns": ["town1", "town2", "town3", "town4"],  # 4 towns
        "villages": ["vil1", "vil2", "vil3", "vil4", "vil5"],  # 5 villages
        "countries": ["country1", "country2", "country3", "country4"],  # 4 countries
    }
    
    print(f"📊 Sample world stats:")
    print(f"   Continents: {len(sample_world_summary['continents'])}")
    print(f"   Regions: {len(sample_world_summary['regions'])}")
    print(f"   Settlements: {len(sample_world_summary['cities']) + len(sample_world_summary['towns']) + len(sample_world_summary['villages'])}")
    print(f"   Countries: {len(sample_world_summary['countries'])}")
    
    # Create enrichment service and test Master Lore generation
    enrichment_service = AIWorldEnrichmentService()
    
    print("\n🚀 Generating Master Lore...")
    
    try:
        master_lore = await enrichment_service._generate_master_lore(sample_world_summary)
        
        print(f"\n📜 MASTER LORE GENERATED:")
        print("=" * 80)
        print(master_lore)
        print("=" * 80)
        
        # Check if it has expected sections
        expected_sections = ["WORLD TYPE:", "CENTRAL CONFLICT:", "PLAYER GOALS:", "KEY FACTIONS:", "WORLD THEMES:", "CURRENT ERA:"]
        found_sections = []
        
        for section in expected_sections:
            if section in master_lore:
                found_sections.append(section)
                print(f"✅ Found section: {section}")
            else:
                print(f"❌ Missing section: {section}")
        
        print(f"\n📊 Results:")
        print(f"   Sections found: {len(found_sections)}/{len(expected_sections)}")
        print(f"   Master Lore length: {len(master_lore)} characters")
        print(f"   Generation successful: {'✅ YES' if len(found_sections) >= 4 else '❌ NO'}")
        
        return master_lore
        
    except Exception as e:
        print(f"❌ Failed to generate Master Lore: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(test_master_lore_generation())

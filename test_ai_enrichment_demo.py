#!/usr/bin/env python3
"""
Test script to demonstrate AI enrichment on a simple POI entity
Shows before/after comparison of AI enrichment
"""
import asyncio
import sys
import os
import json
from uuid import UUID, uuid4
from datetime import datetime

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.worldgen.ai_enrichment_service import ai_world_enrichment_service
from infrastructure.ai_service import ai_service
from domain.entities import Location, EntityType

async def test_ai_enrichment_demo():
    """Test AI enrichment on a sample POI entity"""
    
    # Create a sample POI entity (like from your JSON)
    sample_poi = Location(
        id=UUID("8f044393-981b-4337-bf52-f6df40c05ae4"),
        name="Farm near 8923ee",
        description="A farm",
        metadata={
            "location_kind": "poi",
            "parent_id": "8923ee54-c0f8-4972-b925-bc1589148f08",
            "center": [0.8628565100105349, 0.9685448436004402],
            "poi_type": "farm",
            "hook_tags": ["farming", "supply"]
        },
        created_at=datetime.fromisoformat("2025-08-10T16:05:13.424090"),
        updated_at=datetime.fromisoformat("2025-08-10T16:05:13.424092"),
        is_safe=True,
        exploration_level=0
    )
    
    print("🎯 Testing AI Enrichment Demo")
    print("=" * 80)
    
    print("📦 BEFORE ENRICHMENT:")
    print(f"Name: {sample_poi.name}")
    print(f"Description: {sample_poi.description}")
    print(f"Metadata: {json.dumps(sample_poi.metadata, indent=2)}")
    print()
    
    # Get AI service template for POI
    template = ai_world_enrichment_service.templates["poi"]
    
    # Build context for the POI
    context = {
        "world_lore": "A fantasy world of magic and adventure where ancient kingdoms rise and fall",
        "regional_context": "A peaceful countryside region with rolling hills and small farming communities",
        "name": sample_poi.name,
        "poi_type": sample_poi.metadata.get("poi_type", "unknown"),
        "description": sample_poi.description,
        "location_context": "Located near a small village, this area is known for its fertile soil"
    }
    
    # Format the prompt
    prompt = template["user"].format(**context)
    
    print("📝 PROMPT SENT TO AI:")
    print("=" * 80)
    print("SYSTEM PROMPT:")
    print(template["system"])
    print("\nUSER PROMPT:")
    print(prompt)
    print("=" * 80)
    print()
    
    try:
        # Call AI service
        response = await ai_service.generate_completion(
            system_prompt=template["system"],
            user_prompt=prompt,
            max_completion_tokens=500,
        )
        
        print("🤖 AI RESPONSE:")
        print("=" * 80)
        print(response.content)
        print("=" * 80)
        print()
        
        # Test our parsing logic
        print("🔍 TESTING PARSING LOGIC:")
        print("-" * 40)
        
        # Simulate the parsing (without database update)
        lines = response.content.split('\n')
        enhanced_name = sample_poi.name
        enhanced_description = sample_poi.description
        
        current_section = ""
        description_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            print(f"Processing line: '{line}'")
                
            # Strict header for enhanced name
            if line.upper().startswith("ENHANCED NAME:"):
                name_part = line.split(":", 1)[-1].strip()
                if name_part and name_part.lower() != "keep current" and name_part != sample_poi.name:
                    enhanced_name = name_part
                    print(f"  → Found enhanced name: '{name_part}'")
                continue

            # Fallback tolerant format like '1. ENHANCED NAME: ...'
            import re
            m = re.match(r"^\s*\d+\.?\s*ENHANCED NAME\s*:\s*(.+)$", line, re.IGNORECASE)
            if m:
                name_part = m.group(1).strip()
                if name_part and name_part.lower() != "keep current" and name_part != sample_poi.name:
                    enhanced_name = name_part
                    print(f"  → Found enhanced name (format 2): '{name_part}'")
                continue

            elif "RICH DESCRIPTION:" in line or "2." in line:
                current_section = "description"
                desc_part = line.split(":")[-1].strip()
                if desc_part:
                    description_lines.append(desc_part)
                    print(f"  → Starting description section: '{desc_part}'")
            elif current_section == "description" and not any(marker in line for marker in ["3.", "4.", "5.", "PERSONALITY:", "BACKGROUND:", "CULTURAL"]):
                description_lines.append(line)
                print(f"  → Adding to description: '{line}'")
            elif any(marker in line for marker in ["3.", "PERSONALITY:", "BACKGROUND:", "CULTURAL"]):
                current_section = "other"
                print(f"  → Switching to other section")
        
        # Update description if we found enhanced content
        if description_lines:
            enhanced_description = " ".join(description_lines)
        
        print("-" * 40)
        print()
        
        print("✨ AFTER ENRICHMENT:")
        print(f"Name: {sample_poi.name} → {enhanced_name}")
        print(f"Description: {sample_poi.description} → {enhanced_description}")
        print()
        
        if enhanced_name != sample_poi.name:
            print("✅ Name was successfully enriched!")
        else:
            print("❌ Name was NOT enriched")
            
        if enhanced_description != sample_poi.description:
            print("✅ Description was successfully enriched!")
        else:
            print("❌ Description was NOT enriched")
            
    except Exception as e:
        print(f"❌ Error during AI enrichment: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ai_enrichment_demo())

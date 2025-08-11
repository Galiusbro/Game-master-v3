from __future__ import annotations

"""AI World Enrichment Service

Provides batch AI-powered enrichment of generated world entities.
Called at the end of world generation pipeline to add rich descriptions,
names, and backstories while maintaining lore consistency.

Features:
- Batch processing for efficiency
- D&D-themed content generation
- Hierarchical context awareness (continent -> region -> city -> NPC)
- Lore consistency across all entities
"""

import asyncio
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from dataclasses import dataclass

from core.world_service import world_service
from infrastructure.ai_service import ai_service
from domain.entities import EntityType, BaseEntity


@dataclass
class EnrichmentContext:
    """Context for AI enrichment including world lore and hierarchical info"""
    world_theme: str = "classic D&D fantasy"
    naming_style: str = "fantasy medieval"
    tone: str = "immersive and atmospheric"
    world_lore: str = ""
    master_lore: str = ""  # Master Lore that guides all enrichment
    parent_context: Optional[Dict[str, Any]] = None
    sibling_entities: List[Dict[str, Any]] = None


class AIWorldEnrichmentService:
    """Service for batch AI enrichment of world entities"""
    
    def __init__(self):
        self.templates = self._init_templates()
    
    def _init_templates(self) -> Dict[str, Dict[str, str]]:
        """Initialize prompt templates for different entity types"""
        return {
            "master_lore": {
                "system": """You are a D&D World Builder creating the Master Lore - the foundational narrative framework for an entire fantasy realm.

This Master Lore will serve as the primary context for ALL subsequent world building: continents, countries, regions, settlements, NPCs, and adventures. Everything in this world should reflect and connect to this central narrative.

REQUIREMENTS:
- Establish a compelling central conflict or threat
- Define clear player goals and motivations  
- Create distinct factions with opposing interests
- Set the tone and themes for adventures
- Provide rich context for world-building""",
                
                "user": """Create the Master Lore for this fantasy world.

WORLD OVERVIEW:
Geography: {continents_count} continents, {regions_count} regions, {settlements_count} settlements
Scale: {world_scale} (small/medium/large world)
Complexity: {political_complexity} countries and factions

Generate the Master Lore with these sections:

1. WORLD TYPE: The genre and magical level (high fantasy, dark fantasy, etc.)
2. CENTRAL CONFLICT: The main threat or crisis driving adventures
3. PLAYER GOALS: What heroes are meant to accomplish in this world
4. KEY FACTIONS: 3-4 major groups with conflicting interests
5. WORLD THEMES: Core themes that define adventures and stories
6. CURRENT ERA: What historical period/crisis the world is experiencing

Make this compelling and adventure-focused. This will guide ALL other world elements.""",
            },
            
            "world": {
                "system": """You are a D&D World Builder enriching the world entity with the established Master Lore.
Your task is to create an immersive world description that reflects and supports the Master Lore themes and conflicts.

REQUIREMENTS:
- Align perfectly with the Master Lore
- Rich, atmospheric world description  
- Clear magical/technological level
- Support the central conflict and factions
- Provide historical context for the current era""",
                
                "user": """Enrich this world entity using the established Master Lore as your foundation.
CRITICAL: Start the response with a single line exactly in the form 'ENHANCED NAME: <new name or keep current>'.

MASTER LORE:
{master_lore}

WORLD STRUCTURE:
{world_structure}

GEOGRAPHIC OVERVIEW:
{geography_summary}

Generate:
1. ENHANCED NAME: A memorable name that reflects the Master Lore
2. RICH DESCRIPTION: Immersive world description aligned with Master Lore
3. HISTORICAL CONTEXT: How the current era connects to the Master Lore
4. WORLD ATMOSPHERE: The feel and mood that supports the central themes"""
            },
            
            "continent": {
                "system": """You are a D&D World Builder specializing in continental geography and cultures.
Create rich continental descriptions that reflect the Master Lore themes and conflicts.
Consider how this continent fits into the world's central narrative and factions.

REQUIREMENTS:
- Align with the Master Lore's central conflict and themes
- Reflect the established factions and world atmosphere
- Distinct cultural identity that supports the Master Lore
- Geographic and political details that create adventure opportunities""",
                
                "user": """Enrich this continent using the Master Lore as your guide.
CRITICAL: Start the response with a single line exactly in the form 'ENHANCED NAME: <new name or keep current>'.

MASTER LORE:
{master_lore}

CONTINENT DATA:
Name: {name}
Current Description: {description}
Geographic Info: {geographic_info}
Regions: {regions_summary}
Major Cities: {cities_summary}

Generate:
1. ENHANCED NAME: More evocative name if needed (or keep current)
2. RICH DESCRIPTION: Atmospheric description (1-2 paragraphs)
3. CULTURAL IDENTITY: Dominant cultures, traditions, conflicts
4. NOTABLE FEATURES: Unique landmarks, dangers, opportunities"""
            },

            "country": {
                "system": """You are a D&D World Builder creating memorable nations and kingdoms.
Each country should feel like a distinct political entity with its own culture, conflicts, and identity.
Consider government type, relationships with neighbors, and internal politics.

REQUIREMENTS:
- Clear political identity and governance style
- Cultural distinctiveness within the continent
- Internal conflicts and external relations
- Adventure opportunities through politics and intrigue""",
                
                "user": """Enrich this country within the established world.
CRITICAL: Start the response with a single line exactly in the form 'ENHANCED NAME: <new name or keep current>'.

WORLD LORE:
{world_lore}

CONTINENTAL CONTEXT:
{continental_context}

COUNTRY DATA:
Name: {name}
Current Description: {description}
Government: {government}
Lawfulness: {lawfulness}
Magic Laws: {magic_legality}
Geographic Info: {geographic_info}
Regions: {regions_summary}

Generate:
1. ENHANCED NAME: Evocative nation name that reflects its character
2. RICH DESCRIPTION: Political and cultural atmosphere
3. GOVERNMENT: Leadership structure and ruling philosophy  
4. MAJOR CONFLICTS: Internal strife and external threats
5. CULTURAL IDENTITY: What makes this nation unique""",
            },
            
            "region": {
                "system": """You are a D&D World Builder creating detailed regional descriptions.
Regions should feel like distinct areas within their continent, with unique characteristics
that make them memorable and adventure-worthy.

REQUIREMENTS:
- Consistent with continent and world lore
- Clear biome characteristics and mood
- Local conflicts and opportunities
- Specific details that bring the region to life""",
                
                "user": """Enrich this region within the established setting.
CRITICAL: Start the response with a single line exactly in the form 'ENHANCED NAME: <new name or keep current>'.

WORLD LORE:
{world_lore}

CONTINENT CONTEXT:
{continent_context}

REGION DATA:
Name: {name}
Current Description: {description}
Biome: {biome}
Geographic Info: {geographic_info}
Settlements: {settlements_summary}

Generate:
1. ENHANCED NAME: More evocative regional name if needed
2. RICH DESCRIPTION: Vivid description capturing the region's essence
3. LOCAL CHARACTERISTICS: Unique features, dangers, resources
4. REGIONAL CONFLICTS: Local tensions and adventure hooks"""
            },
            
            "settlement": {
                "system": """You are a D&D World Builder creating memorable settlements.
Each settlement should feel alive with distinct personality, conflicts, and opportunities.
Consider the settlement's role in the larger world and region.

REQUIREMENTS:
- Fits regional and world context
- Clear settlement personality and atmosphere
- Notable NPCs and factions mentioned
- Adventure hooks and local conflicts
- Appropriate scale (city/town/village)""",
                
                "user": """Enrich this settlement within the established world.
CRITICAL: Start the response with a single line exactly in the form 'ENHANCED NAME: <new name or keep current>'.

WORLD LORE:
{world_lore}

REGIONAL CONTEXT:
{regional_context}

SETTLEMENT DATA:
Name: {name}
Type: {settlement_type}
Current Description: {description}
Population: {population}
Notable Buildings: {buildings_summary}
Key NPCs: {npcs_summary}

Generate:
1. ENHANCED NAME: More evocative name if current is generic
2. RICH DESCRIPTION: Atmospheric description of the settlement
3. SETTLEMENT PERSONALITY: What makes this place unique and memorable
4. LOCAL POLITICS: Power structures, factions, conflicts
5. ADVENTURE HOOKS: Specific opportunities for player engagement"""
            },
            
            "npc": {
                "system": """You are a D&D World Builder creating memorable NPCs.
Each NPC should feel like a real person with motivations, personality, and a role
in their community. They should enhance the world's story and provide adventure opportunities.

REQUIREMENTS:
- Fits settlement and regional context
- Clear personality and motivations
- Appropriate background for their role
- Potential plot hooks and interactions
- Distinct voice and mannerisms""",
                
                "user": """Enrich this NPC within the established world.
CRITICAL: Start the response with a single line exactly in the form 'ENHANCED NAME: <new name or keep current>'.

WORLD LORE:
{world_lore}

SETTLEMENT CONTEXT:
{settlement_context}

NPC DATA:
Name: {name}
Current Description: {description}
Race: {race}
Roles: {roles}
Location: {location}
Capabilities: {capabilities}

Generate:
1. ENHANCED NAME: More flavorful name if current is generic
2. RICH DESCRIPTION: Physical appearance and first impression
3. PERSONALITY: Core traits, quirks, speech patterns
4. BACKGROUND: Personal history and motivations
5. ROLE IN COMMUNITY: How they fit into the settlement
6. PLOT HOOKS: Ways players might interact with them"""
            },
            
            "poi": {
                "system": """You are a D&D World Builder creating intriguing Points of Interest.
Each POI should be a potential adventure location with mystery, danger, or opportunity.
They should enhance the regional atmosphere and provide clear adventure hooks.

REQUIREMENTS:
- Atmospheric and mysterious
- Clear adventure potential
- Fits regional context
- Specific details that inspire exploration""",
                
                "user": """Enrich this Point of Interest.
CRITICAL: Start the response with a single line exactly in the form 'ENHANCED NAME: <new name or keep current>'.

WORLD LORE:
{world_lore}

REGIONAL CONTEXT:
{regional_context}

POI DATA:
Name: {name}
Type: {poi_type}
Current Description: {description}
Location Context: {location_context}

Generate:
1. ENHANCED NAME: Evocative name that hints at mystery
2. RICH DESCRIPTION: Atmospheric description that draws interest
3. HISTORY: Background and significance
4. CURRENT STATE: What's happening there now
5. ADVENTURE HOOKS: Clear reasons for players to investigate"""
            },
            
            "building": {
                "system": """You are a D&D World Builder creating memorable urban buildings.
Each building should feel like a lived-in part of the city with character and purpose.
Consider the building's role in the district and the lives of those who use it.

REQUIREMENTS:
- Fits the district's character and city atmosphere
- Clear purpose and daily activities
- Notable occupants or regular visitors
- Potential for player interaction or adventure seeds""",
                
                "user": """Enrich this building within the established setting.
CRITICAL: Start the response with a single line exactly in the form 'ENHANCED NAME: <new name or keep current>'.

WORLD LORE:
{world_lore}

DISTRICT CONTEXT:
{district_context}

BUILDING DATA:
Name: {name}
Type: {building_type}
Current Description: {description}
District: {district_name}
Services: {services}

Generate:
1. ENHANCED NAME: Memorable name that reflects its character
2. RICH DESCRIPTION: Vivid description of the building's appearance and atmosphere
3. OCCUPANTS: Who lives or works here regularly
4. DAILY LIFE: What happens here during a typical day
5. ADVENTURE POTENTIAL: How players might interact with this place"""
            }
        }
    
    async def enrich_world_batch(
        self,
        world_summary: Dict[str, Any],
        world_id: str
    ) -> Dict[str, Any]:
        """
        Perform batch AI enrichment of the entire generated world.
        
        Args:
            world_summary: Summary from generate_world() containing all entity IDs
            world_id: String ID of the world entity
            
        Returns:
            Updated summary with enrichment statistics
        """
        print("🎨 Starting AI world enrichment...")
        
        # 1. Generate Master Lore FIRST - this will guide all other enrichment
        print("📜 Generating Master Lore...")
        master_lore = await self._generate_master_lore(world_summary)
        
        # 2. Build world context with Master Lore
        context = await self._build_world_context(world_summary, world_id, master_lore)
        
        # 3. Enrich in hierarchical order for context consistency
        await self._enrich_world_entity(world_id, context)
        await self._enrich_continents(world_summary["continents"], context)
        await self._enrich_countries(world_summary["countries"], context)
        await self._enrich_regions(world_summary["regions"], context) 
        await self._enrich_settlements(world_summary, context)
        await self._enrich_buildings(world_summary["buildings"], context)
        await self._enrich_npcs(world_summary["npcs"], context)
        await self._enrich_pois(world_summary["poi"], context)
        
        print("✅ AI world enrichment completed!")
        
        # Return updated summary with enrichment stats
        world_summary["ai_enrichment"] = {
            "enriched": True,
            "entities_processed": (
                1 + len(world_summary["continents"]) + 
                len(world_summary["regions"]) + 
                len(world_summary["cities"]) + len(world_summary["towns"]) +
                len(world_summary["villages"]) + len(world_summary["npcs"]) +
                len(world_summary["poi"])
            )
        }
        
        return world_summary
    
    async def _generate_master_lore(self, world_summary: Dict[str, Any]) -> str:
        """Generate Master Lore for the world that will guide all other enrichment"""
        try:
            # Calculate world statistics
            continents_count = len(world_summary.get("continents", []))
            regions_count = len(world_summary.get("regions", []))
            settlements_count = (
                len(world_summary.get("cities", [])) + 
                len(world_summary.get("towns", [])) + 
                len(world_summary.get("villages", []))
            )
            countries_count = len(world_summary.get("countries", []))
            
            # Determine world scale
            if settlements_count < 10:
                world_scale = "small"
            elif settlements_count < 30:
                world_scale = "medium" 
            else:
                world_scale = "large"
            
            # Determine political complexity
            if countries_count < 3:
                political_complexity = f"{countries_count} simple"
            elif countries_count < 6:
                political_complexity = f"{countries_count} moderate"
            else:
                political_complexity = f"{countries_count} complex"
            
            template = self.templates["master_lore"]
            prompt = template["user"].format(
                continents_count=continents_count,
                regions_count=regions_count,
                settlements_count=settlements_count,
                world_scale=world_scale,
                political_complexity=political_complexity
            )
            
            response = await ai_service.generate_completion(
                system_prompt=template["system"],
                user_prompt=prompt,
                max_completion_tokens=800,
            )
            
            print(f"📜 Master Lore Generated:")
            print("System Prompt:")
            print(template["system"])
            print("\nUser Prompt:")
            print(prompt)
            print("\nMaster Lore:")
            print("=" * 80)
            print(response.content)
            print("=" * 80)
            
            return response.content
            
        except Exception as e:
            print(f"❌ Failed to generate Master Lore: {e}")
            # Fallback Master Lore
            return """WORLD TYPE: High Fantasy
CENTRAL CONFLICT: Ancient evils stir while kingdoms struggle for power
PLAYER GOALS: Protect the innocent and restore balance to the realm
KEY FACTIONS: Noble kingdoms, mysterious cults, ancient guardians, merchant guilds
WORLD THEMES: Heroism, mystery, political intrigue, ancient magic
CURRENT ERA: An age of uncertainty where heroes must rise to face growing darkness"""
    
    async def _build_world_context(self, world_summary: Dict[str, Any], world_id: str, master_lore: str = "") -> EnrichmentContext:
        """Build comprehensive context for world enrichment"""
        
        # Gather structural information
        world_structure = {
            "continents": len(world_summary["continents"]),
            "regions": len(world_summary["regions"]),
            "cities": len(world_summary["cities"]),
            "towns": len(world_summary["towns"]),
            "villages": len(world_summary["villages"]),
            "npcs": len(world_summary["npcs"]),
            "total_settlements": len(world_summary["cities"]) + len(world_summary["towns"]) + len(world_summary["villages"])
        }
        
        # Get basic geographic overview
        geography_summary = f"""
        - {world_structure['continents']} major continents
        - {world_structure['regions']} distinct regions with varied biomes
        - Sea level and water ratio: {world_summary.get('water_ratio', 'unknown')}
        - Grid size: {world_summary.get('grid_size', 'unknown')}
        """
        
        # Get settlement overview
        settlements_summary = f"""
        - {world_structure['cities']} major cities (capitals and trade centers)
        - {world_structure['towns']} towns (regional centers)
        - {world_structure['villages']} villages (rural settlements)
        - Connected by {len(world_summary['roads'])} major roads
        """
        
        return EnrichmentContext(
            world_theme="classic D&D fantasy",
            naming_style="fantasy medieval", 
            tone="immersive and atmospheric",
            master_lore=master_lore,
            parent_context={
                "world_structure": world_structure,
                "geography_summary": geography_summary,
                "settlements_summary": settlements_summary
            }
        )
    
    async def _enrich_world_entity(self, world_id: str, context: EnrichmentContext) -> None:
        """Enrich the main world entity with comprehensive lore"""
        print("🌍 Enriching world lore...")
        
        world_entity = await world_service.get_entity(UUID(world_id), EntityType.LOCATION)
        if not world_entity:
            return
        
        template = self.templates["world"]
        
        # Format prompt with Master Lore and world structure
        prompt = template["user"].format(
            master_lore=context.master_lore,
            world_structure=str(context.parent_context["world_structure"]),
            geography_summary=context.parent_context["geography_summary"]
        )
        
        # Generate enriched world lore
        try:
            response = await ai_service.generate_completion(
                system_prompt=template["system"],
                user_prompt=prompt,
                max_completion_tokens=2000,
            )
            
            # Parse and apply the enriched content
            enriched_content = response.content
            
            # Extract world name and description from response
            lines = enriched_content.split('\n')
            new_name = world_entity.name
            new_description = world_entity.description
            
            # Simple parsing - look for sections
            current_section = ""
            for line in lines:
                line = line.strip()
                if line.startswith("1. WORLD NAME:"):
                    new_name = line.replace("1. WORLD NAME:", "").strip()
                elif line.startswith("2. WORLD DESCRIPTION:"):
                    current_section = "description"
                elif line.startswith("3. CORE LORE:"):
                    current_section = "lore"
                elif current_section == "description" and line and not line.startswith(("3.", "4.", "5.")):
                    new_description += " " + line if new_description != world_entity.description else line
            
            # Update world entity
            world_entity.name = new_name
            world_entity.description = new_description
            
            # Store full lore in metadata
            if not world_entity.metadata:
                world_entity.metadata = {}
            world_entity.metadata["ai_generated_lore"] = enriched_content
            world_entity.metadata["enriched_by_ai"] = True
            
            # Update in database
            await world_service.update_entity(world_entity, actor_id=UUID(world_id))
            
            # Store lore in context for other entities
            context.world_lore = enriched_content
            
            print(f"✅ World enriched: {new_name}")
            
        except Exception as e:
            print(f"❌ Failed to enrich world: {e}")
            # Continue with basic lore
            context.world_lore = "A vast fantasy realm filled with adventure and mystery."
    
    async def _enrich_continents(self, continent_ids: List[str], context: EnrichmentContext) -> None:
        """Enrich continent entities"""
        print(f"🏔️ Enriching {len(continent_ids)} continents...")
        
        # Process continents in parallel batches
        batch_size = 3
        for i in range(0, len(continent_ids), batch_size):
            batch = continent_ids[i:i + batch_size]
            tasks = [self._enrich_continent(UUID(cid), context) for cid in batch]
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _enrich_continent(self, continent_id: UUID, context: EnrichmentContext) -> None:
        """Enrich a single continent"""
        try:
            continent = await world_service.get_entity(continent_id, EntityType.LOCATION)
            if not continent:
                return
            
            # Get related entities for context
            regions_info = await self._get_child_entities_summary(str(continent_id), "region")
            cities_info = await self._get_child_entities_summary(str(continent_id), "city")
            
            template = self.templates["continent"]
            prompt = template["user"].format(
                master_lore=context.master_lore[:1000],  # Truncate for token limits
                name=continent.name,
                description=continent.description,
                geographic_info=str(continent.metadata or {}),
                regions_summary=regions_info,
                cities_summary=cities_info
            )
            
            response = await ai_service.generate_completion(
                system_prompt=template["system"],
                user_prompt=prompt,
                max_completion_tokens=800,
            )
            
            print(f"🤖 AI Response for Continent {continent_id}:")
            print("=" * 60)
            print(response.content)
            print("=" * 60)
            # Apply enrichment
            await self._apply_enrichment(continent, response.content, str(continent_id))
            print(f"✅ Continent enriched: {continent.name}")
            
        except Exception as e:
            print(f"❌ Failed to enrich continent {continent_id}: {e}")
    
    async def _enrich_countries(self, country_ids: List[str], context: EnrichmentContext) -> None:
        """Enrich country entities"""
        print(f"🏛️ Enriching {len(country_ids)} countries...")
        
        batch_size = 3
        for i in range(0, len(country_ids), batch_size):
            batch = country_ids[i:i + batch_size]
            tasks = [self._enrich_country(UUID(cid), context) for cid in batch]
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _enrich_country(self, country_id: UUID, context: EnrichmentContext) -> None:
        """Enrich a single country"""
        try:
            country = await world_service.get_entity(country_id, EntityType.LOCATION)
            if not country:
                return

            continental_context = await self._get_parent_context(country, "continent")
            regions_info = await self._get_child_entities_summary(str(country_id), "region")
            
            government = country.metadata.get("government", "unknown") if country.metadata else "unknown"
            lawfulness = country.metadata.get("lawfulness", "unknown") if country.metadata else "unknown"
            magic_legality = country.metadata.get("magic_legality", "unknown") if country.metadata else "unknown"

            template = self.templates["country"]
            prompt = template["user"].format(
                world_lore=context.world_lore[:500],
                continental_context=continental_context,
                name=country.name,
                description=country.description,
                government=government,
                lawfulness=lawfulness,
                magic_legality=magic_legality,
                geographic_info=str(country.metadata or {}),
                regions_summary=regions_info
            )
            
            response = await ai_service.generate_completion(
                system_prompt=template["system"],
                user_prompt=prompt,
                max_completion_tokens=700,
            )
            
            print(f"🤖 AI Response for Country {country_id}:")
            print("=" * 60)
            print(response.content)
            print("=" * 60)
            await self._apply_enrichment(country, response.content, str(country_id))
            print(f"✅ Country enriched: {country.name}")
            
        except Exception as e:
            print(f"❌ Failed to enrich country {country_id}: {e}")

    async def _enrich_regions(self, region_ids: List[str], context: EnrichmentContext) -> None:
        """Enrich region entities"""
        print(f"🌲 Enriching {len(region_ids)} regions...")
        
        batch_size = 5
        for i in range(0, len(region_ids), batch_size):
            batch = region_ids[i:i + batch_size]
            tasks = [self._enrich_region(UUID(rid), context) for rid in batch]
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _enrich_region(self, region_id: UUID, context: EnrichmentContext) -> None:
        """Enrich a single region"""
        try:
            region = await world_service.get_entity(region_id, EntityType.LOCATION)
            if not region:
                return
            
            # Get parent continent context
            continent_context = await self._get_parent_context(region, "continent")
            settlements_info = await self._get_child_entities_summary(str(region_id), "settlement")
            
            template = self.templates["region"]
            prompt = template["user"].format(
                world_lore=context.world_lore[:800],
                continent_context=continent_context,
                name=region.name,
                description=region.description,
                biome=region.metadata.get("biome_type", "unknown") if region.metadata else "unknown",
                geographic_info=str(region.metadata or {}),
                settlements_summary=settlements_info
            )
            
            response = await ai_service.generate_completion(
                system_prompt=template["system"],
                user_prompt=prompt,
                max_completion_tokens=600,
            )
            
            await self._apply_enrichment(region, response.content, str(region_id))
            print(f"✅ Region enriched: {region.name}")
            
        except Exception as e:
            print(f"❌ Failed to enrich region {region_id}: {e}")
    
    async def _enrich_settlements(self, world_summary: Dict[str, Any], context: EnrichmentContext) -> None:
        """Enrich all settlements (cities, towns, villages)"""
        all_settlements = (
            world_summary["cities"] + 
            world_summary["towns"] + 
            world_summary["villages"]
        )
        
        print(f"🏘️ Enriching {len(all_settlements)} settlements...")
        
        batch_size = 4
        for i in range(0, len(all_settlements), batch_size):
            batch = all_settlements[i:i + batch_size]
            tasks = [self._enrich_settlement(UUID(sid), context) for sid in batch]
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _enrich_settlement(self, settlement_id: UUID, context: EnrichmentContext) -> None:
        """Enrich a single settlement"""
        try:
            settlement = await world_service.get_entity(settlement_id, EntityType.LOCATION)
            if not settlement:
                return
            
            regional_context = await self._get_parent_context(settlement, "region")
            buildings_info = await self._get_child_entities_summary(str(settlement_id), "building")
            npcs_info = await self._get_child_entities_summary(str(settlement_id), "npc")
            
            settlement_type = settlement.metadata.get("location_kind", "settlement") if settlement.metadata else "settlement"
            population = settlement.metadata.get("population_estimate", "unknown") if settlement.metadata else "unknown"
            
            template = self.templates["settlement"]
            prompt = template["user"].format(
                world_lore=context.world_lore[:600],
                regional_context=regional_context,
                name=settlement.name,
                settlement_type=settlement_type,
                description=settlement.description,
                population=str(population),
                buildings_summary=buildings_info,
                npcs_summary=npcs_info
            )
            
            response = await ai_service.generate_completion(
                system_prompt=template["system"],
                user_prompt=prompt,
                max_completion_tokens=800,
            )
            
            print(f"🏘️ AI Response for Settlement {settlement_id}:")
            print("System Prompt:")
            print(template["system"])
            print("\nUser Prompt:")
            print(prompt)
            print("\nAI Response:")
            print("=" * 60)
            print(response.content)
            print("=" * 60)
            
            await self._apply_enrichment(settlement, response.content, str(settlement_id))
            print(f"✅ Settlement enriched: {settlement.name}")
            
        except Exception as e:
            print(f"❌ Failed to enrich settlement {settlement_id}: {e}")
    
    async def _enrich_npcs(self, npc_ids: List[str], context: EnrichmentContext) -> None:
        """Enrich NPC entities"""
        print(f"👥 Enriching {len(npc_ids)} NPCs...")
        
        batch_size = 6
        for i in range(0, len(npc_ids), batch_size):
            batch = npc_ids[i:i + batch_size]
            tasks = [self._enrich_npc(UUID(nid), context) for nid in batch]
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _enrich_npc(self, npc_id: UUID, context: EnrichmentContext) -> None:
        """Enrich a single NPC"""
        try:
            npc = await world_service.get_entity(npc_id, EntityType.NPC)
            if not npc:
                return
            
            settlement_context = await self._get_parent_context(npc, "settlement")
            
            # Get NPC-specific data
            race = getattr(npc, 'race', 'unknown')
            roles = npc.metadata.get("roles", []) if npc.metadata else []
            capabilities = npc.metadata.get("capabilities", {}) if npc.metadata else {}
            location = getattr(npc.current_state, 'current_location_id', 'unknown') if hasattr(npc, 'current_state') else 'unknown'
            
            template = self.templates["npc"]
            prompt = template["user"].format(
                world_lore=context.world_lore[:500],
                settlement_context=settlement_context,
                name=npc.name,
                description=npc.description,
                race=str(race),
                roles=str(roles),
                location=str(location),
                capabilities=str(capabilities)
            )
            
            response = await ai_service.generate_completion(
                system_prompt=template["system"],
                user_prompt=prompt,
                max_completion_tokens=600,
            )
            
            await self._apply_enrichment(npc, response.content, str(npc_id))
            print(f"✅ NPC enriched: {npc.name}")
            
        except Exception as e:
            print(f"❌ Failed to enrich NPC {npc_id}: {e}")
    
    async def _enrich_pois(self, poi_ids: List[str], context: EnrichmentContext) -> None:
        """Enrich Points of Interest"""
        print(f"📍 Enriching {len(poi_ids)} POIs...")
        
        batch_size = 5
        for i in range(0, len(poi_ids), batch_size):
            batch = poi_ids[i:i + batch_size]
            tasks = [self._enrich_poi(UUID(pid), context) for pid in batch]
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _enrich_poi(self, poi_id: UUID, context: EnrichmentContext) -> None:
        """Enrich a single POI"""
        try:
            poi = await world_service.get_entity(poi_id, EntityType.LOCATION)
            if not poi:
                return
            
            regional_context = await self._get_parent_context(poi, "region")
            poi_type = poi.metadata.get("poi_type", "unknown") if poi.metadata else "unknown"
            location_context = poi.metadata.get("location_context", "") if poi.metadata else ""
            
            template = self.templates["poi"]
            prompt = template["user"].format(
                world_lore=context.world_lore[:500],
                regional_context=regional_context,
                name=poi.name,
                poi_type=poi_type,
                description=poi.description,
                location_context=location_context
            )
            
            response = await ai_service.generate_completion(
                system_prompt=template["system"],
                user_prompt=prompt,
                max_completion_tokens=500,
            )
            
            print(f"📍 AI Response for POI {poi_id}:")
            print("System Prompt:")
            print(template["system"])
            print("\nUser Prompt:")
            print(prompt)
            print("\nAI Response:")
            print("=" * 60)
            print(response.content)
            print("=" * 60)
            
            await self._apply_enrichment(poi, response.content, str(poi_id))
            print(f"✅ POI enriched: {poi.name}")
            
        except Exception as e:
            print(f"❌ Failed to enrich POI {poi_id}: {e}")
    
    async def _enrich_buildings(self, building_ids: List[str], context: EnrichmentContext) -> None:
        """Enrich building entities"""
        print(f"🏢 Enriching {len(building_ids)} buildings...")
        
        batch_size = 5
        for i in range(0, len(building_ids), batch_size):
            batch = building_ids[i:i + batch_size]
            tasks = [self._enrich_building(UUID(bid), context) for bid in batch]
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _enrich_building(self, building_id: UUID, context: EnrichmentContext) -> None:
        """Enrich a single building"""
        try:
            building = await world_service.get_entity(building_id, EntityType.LOCATION)
            if not building:
                return
            
            district_context = await self._get_parent_context(building, "district")
            building_type = building.metadata.get("kind", "unknown") if building.metadata else "unknown"
            services = str(building.metadata.get("service_capability", "")) if building.metadata else ""
            
            # Get district name for context
            district_name = "Unknown District"
            if building.metadata and building.metadata.get("parent_id"):
                try:
                    district_entity = await world_service.get_entity(UUID(building.metadata["parent_id"]), EntityType.LOCATION)
                    if district_entity:
                        district_name = district_entity.name
                except:
                    pass
            
            template = self.templates["building"]
            prompt = template["user"].format(
                world_lore=context.world_lore[:500],
                district_context=district_context,
                name=building.name,
                building_type=building_type,
                description=building.description,
                district_name=district_name,
                services=services
            )
            
            response = await ai_service.generate_completion(
                system_prompt=template["system"],
                user_prompt=prompt,
                max_completion_tokens=600,
            )
            
            print(f"🏢 AI Response for Building {building_id}:")
            print("System Prompt:")
            print(template["system"])
            print("\nUser Prompt:")
            print(prompt)
            print("\nAI Response:")
            print("=" * 60)
            print(response.content)
            print("=" * 60)
            
            await self._apply_enrichment(building, response.content, str(building_id))
            print(f"✅ Building enriched: {building.name}")
            
        except Exception as e:
            print(f"❌ Failed to enrich building {building_id}: {e}")
    
    async def _get_child_entities_summary(self, parent_id: str, child_type: str) -> str:
        """Get summary of child entities for context"""
        try:
            # This is a simplified approach - in reality you'd want to query relationships
            # For now, return a placeholder
            return f"Several {child_type}s in this area"
        except Exception:
            return f"Unknown {child_type}s"
    
    async def _get_parent_context(self, entity: BaseEntity, parent_type: str) -> str:
        """Get parent entity context for enrichment"""
        try:
            if entity.metadata and "parent_id" in entity.metadata:
                parent_id = entity.metadata["parent_id"]
                parent = await world_service.get_entity(UUID(parent_id))
                if parent:
                    return f"{parent.name}: {parent.description}"
            return f"Part of a {parent_type} in this world"
        except Exception:
            return f"Located in a {parent_type}"
    
    async def _apply_enrichment(self, entity: BaseEntity, enriched_content: str, actor_id: str) -> None:
        """Apply AI-generated enrichment to an entity"""
        try:
            # Parse the enriched content and extract key parts
            import re
            lines = enriched_content.split('\n')
            
            # Look for enhanced name and description
            enhanced_name = entity.name
            enhanced_description = entity.description
            
            current_section = ""
            description_lines = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Strict header for enhanced name
                if line.upper().startswith("ENHANCED NAME:"):
                    name_part = line.split(":", 1)[-1].strip()
                    if name_part and name_part.lower() != "keep current" and name_part != entity.name:
                        enhanced_name = name_part
                    continue

                # Fallback tolerant format like '1. ENHANCED NAME: ...'
                m = re.match(r"^\s*\d+\.?\s*ENHANCED NAME\s*:\s*(.+)$", line, re.IGNORECASE)
                if m:
                    name_part = m.group(1).strip()
                    if name_part and name_part.lower() != "keep current" and name_part != entity.name:
                        enhanced_name = name_part
                    continue
                elif "RICH DESCRIPTION:" in line or "2." in line:
                    current_section = "description"
                    desc_part = line.split(":")[-1].strip()
                    if desc_part:
                        description_lines.append(desc_part)
                elif current_section == "description" and not any(marker in line for marker in ["3.", "4.", "5.", "PERSONALITY:", "BACKGROUND:", "CULTURAL"]):
                    description_lines.append(line)
                elif any(marker in line for marker in ["3.", "PERSONALITY:", "BACKGROUND:", "CULTURAL"]):
                    current_section = "other"
            
            # Update description if we found enhanced content
            if description_lines:
                enhanced_description = " ".join(description_lines)
            
            # Apply updates
            entity.name = enhanced_name
            entity.description = enhanced_description
            
            # Store full AI content in metadata
            if not entity.metadata:
                entity.metadata = {}
            entity.metadata["ai_enriched_content"] = enriched_content
            entity.metadata["enriched_by_ai"] = True
            
            # Update in database
            await world_service.update_entity(entity, actor_id=UUID(actor_id))
            
        except Exception as e:
            print(f"❌ Failed to apply enrichment: {e}")


# Global instance
ai_world_enrichment_service = AIWorldEnrichmentService()

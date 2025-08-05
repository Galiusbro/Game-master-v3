"""
Database initialization script for Game Master V3
Sets up all databases and creates initial world data
"""
import asyncio
import logging
import sys
from pathlib import Path
from uuid import uuid4

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from config.settings import settings
from core.world_service import world_service
from domain.entities import (
    EntityType, Location, NPC, NPCPersonality, NPCState, Player, Item, ItemType
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_sample_world():
    """Create sample world data for testing"""
    
    # Create a starting location
    tavern = Location(
        name="The Prancing Pony",
        description="A cozy tavern with warm firelight and the smell of ale. Travelers gather here to share stories and rest.",
        metadata={
            "type": "tavern",
            "atmosphere": "cozy",
            "safety_level": "safe",
        }
    )
    
    # Create sample NPC
    bartender_personality = NPCPersonality(
        core_traits=["friendly", "observant", "discreet"],
        speech_patterns=["speaks with a slight accent", "often hums while working"],
        likes=["good stories", "honest customers", "quiet evenings"],
        dislikes=["troublemakers", "unpaid tabs", "loud arguments"],
        fears=["losing his tavern", "bandits"],
        goals=["keep the tavern profitable", "help travelers"],
        backstory="Former adventurer who settled down to run this tavern after an injury ended his traveling days.",
        example_phrases=[
            "Welcome to the Prancing Pony, friend!",
            "What can I get you to drink?",
            "Heard any interesting tales on the road?",
        ]
    )
    
    bartender_state = NPCState(
        current_mood="content",
        current_activity="cleaning glasses",
        current_location_id=tavern.id,
    )
    
    bartender = NPC(
        name="Barliman Butterbur",
        description="A stout, cheerful man with graying hair and a welcoming smile. His hands are always busy, either serving drinks or cleaning.",
        personality=bartender_personality,
        current_state=bartender_state,
        importance_level=3,
    )
    
    # Create sample item
    ale_mug = Item(
        name="Mug of Ale",
        description="A sturdy wooden mug filled with amber ale, topped with a frothy head.",
        item_type=ItemType.CONSUMABLE,
        location_id=tavern.id,
        value=2,
        properties={
            "consumable": True,
            "effect": "restores 5 health",
            "taste": "bitter but refreshing",
        }
    )
    
    # Create sample player
    player = Player(
        name="Adventurer",
        description="A brave soul seeking adventure and fortune.",
        current_location_id=tavern.id,
        health=100,
        max_health=100,
    )
    
    # System actor for world creation
    system_actor = uuid4()
    
    try:
        # Create all entities
        logger.info("Creating sample world entities...")
        
        created_tavern = await world_service.create_entity(
            tavern, actor_id=system_actor
        )
        logger.info(f"Created tavern: {created_tavern.name}")
        
        created_bartender = await world_service.create_entity(
            bartender, actor_id=system_actor
        )
        logger.info(f"Created NPC: {created_bartender.name}")
        
        created_ale = await world_service.create_entity(
            ale_mug, actor_id=system_actor
        )
        logger.info(f"Created item: {created_ale.name}")
        
        created_player = await world_service.create_entity(
            player, actor_id=system_actor
        )
        logger.info(f"Created player: {created_player.name}")
        
        # Create relationships
        logger.info("Creating relationships...")
        
        # Bartender is located in tavern
        await world_service.create_relationship(
            from_entity_id=created_bartender.id,
            to_entity_id=created_tavern.id,
            relationship_type="LOCATED_IN",
            actor_id=system_actor,
        )
        
        # Player is located in tavern
        await world_service.create_relationship(
            from_entity_id=created_player.id,
            to_entity_id=created_tavern.id,
            relationship_type="LOCATED_IN",
            actor_id=system_actor,
        )
        
        # Ale is in tavern
        await world_service.create_relationship(
            from_entity_id=created_ale.id,
            to_entity_id=created_tavern.id,
            relationship_type="LOCATED_IN",
            actor_id=system_actor,
        )
        
        # Bartender knows player
        await world_service.create_relationship(
            from_entity_id=created_bartender.id,
            to_entity_id=created_player.id,
            relationship_type="KNOWS",
            properties={"relationship": "friendly", "first_met": "today"},
            actor_id=system_actor,
        )
        
        logger.info("Sample world created successfully!")
        
        # Create initial snapshot
        logger.info("Creating initial world snapshot...")
        snapshot_id = await world_service.create_world_snapshot(
            created_by="init_script",
            metadata={"type": "initial_world", "entities_count": 4}
        )
        logger.info(f"Created initial snapshot: {snapshot_id}")
        
        return {
            "tavern": created_tavern,
            "bartender": created_bartender,
            "ale": created_ale,
            "player": created_player,
            "snapshot_id": snapshot_id,
        }
        
    except Exception as e:
        logger.error(f"Failed to create sample world: {e}")
        raise


async def main():
    """Main initialization function"""
    logger.info("Initializing Game Master V3 databases...")
    
    try:
        # Initialize world service (this sets up all databases)
        await world_service.initialize()
        logger.info("All databases initialized successfully")
        
        # Create sample world data
        world_data = await create_sample_world()
        
        logger.info("Database initialization complete!")
        logger.info("Sample world created with:")
        logger.info(f"  - Tavern: {world_data['tavern'].name}")
        logger.info(f"  - NPC: {world_data['bartender'].name}")
        logger.info(f"  - Item: {world_data['ale'].name}")
        logger.info(f"  - Player: {world_data['player'].name}")
        logger.info(f"  - Initial snapshot: {world_data['snapshot_id']}")
        
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        sys.exit(1)
    
    finally:
        # Cleanup
        await world_service.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
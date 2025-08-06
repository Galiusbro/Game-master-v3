"""
Context Builder for Game Master V3
Intelligent context assembly for LLM prompts with graph traversal and vector search
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from pydantic import BaseModel

from config.settings import settings
from core.world_service import world_service
from domain.entities import BaseEntity, EntityType, NPC, Player, Location, Item, Event
from monitoring.metrics import track_context_building

logger = logging.getLogger(__name__)


class ContextPriority:
    """Priority levels for context entities"""
    CRITICAL = 10      # Player, current location, direct interaction target
    HIGH = 8          # NPCs in current location, quest-related entities  
    MEDIUM = 6        # Connected locations, recent events
    LOW = 4           # Background entities, historical events
    MINIMAL = 2       # Rarely relevant entities


class ContextMetrics(BaseModel):
    """Metrics for context assembly process"""
    total_entities_found: int
    entities_included: int
    tokens_estimated: int
    traversal_depth_used: int
    vector_search_results: int
    priority_breakdown: Dict[str, int]
    assembly_time: float


class SmartContextBuilder:
    """Intelligent context builder with optimization and prioritization"""
    
    def __init__(self):
        self.max_context_tokens = settings.context_max_tokens
        self.max_traversal_depth = settings.graph_traversal_max_depth
        self.max_entities = 20  # Reasonable limit for most contexts
    
    def calculate_entity_priority(
        self,
        entity: BaseEntity,
        player: Player,
        interaction_target: Optional[BaseEntity] = None,
        current_time: datetime = None
    ) -> int:
        """Calculate priority score for an entity in context"""
        priority = ContextPriority.MINIMAL
        
        current_time = current_time or datetime.utcnow()
        
        # Player themselves - always critical
        if entity.id == player.id:
            return ContextPriority.CRITICAL
        
        # Direct interaction target
        if interaction_target and entity.id == interaction_target.id:
            return ContextPriority.CRITICAL
            
        # Current location is critical
        if (hasattr(entity, 'type') and entity.type == EntityType.LOCATION and 
            entity.id == player.current_location_id):
            return ContextPriority.CRITICAL
            
        # NPCs in current location are high priority
        if (entity.type == EntityType.NPC and 
            hasattr(entity, 'current_state') and entity.current_state and
            entity.current_state.current_location_id == player.current_location_id):
            priority = ContextPriority.HIGH
            
        # Items in current location
        if (entity.type == EntityType.ITEM and
            hasattr(entity, 'location_id') and entity.location_id == player.current_location_id):
            priority = ContextPriority.HIGH
            
        # Known NPCs get medium priority
        if entity.type == EntityType.NPC and entity.id in player.known_npcs:
            priority = max(priority, ContextPriority.MEDIUM)
            
        # Active quests are high priority
        if entity.type == EntityType.QUEST and entity.id in player.active_quests:
            priority = ContextPriority.HIGH
            
        # Recent events (last 24 hours) get higher priority
        if entity.type == EntityType.EVENT:
            if hasattr(entity, 'created_at'):
                time_diff = current_time - entity.created_at
                if time_diff < timedelta(hours=1):
                    priority = max(priority, ContextPriority.HIGH)
                elif time_diff < timedelta(hours=24):
                    priority = max(priority, ContextPriority.MEDIUM)
        
        # Important NPCs get priority boost
        if (entity.type == EntityType.NPC and 
            hasattr(entity, 'importance_level') and entity.importance_level >= 7):
            priority = max(priority, ContextPriority.MEDIUM)
            
        return priority
    
    def estimate_entity_tokens(self, entity: BaseEntity) -> int:
        """Estimate token count for an entity"""
        # Simple estimation based on content length
        content_length = len(entity.name) + len(entity.description)
        
        # Add estimates for type-specific content
        if entity.type == EntityType.NPC:
            # Account for personality, state, etc.
            content_length += 200
        elif entity.type == EntityType.LOCATION:
            # Account for connections, items, NPCs present
            content_length += 100
        elif entity.type == EntityType.ITEM:
            # Account for properties
            content_length += 50
            
        # Rough token estimation (1 token ≈ 4 characters)
        return content_length // 4 + 20  # +20 for formatting
    
    async def gather_context_entities(
        self,
        player: Player,
        interaction_target: Optional[BaseEntity] = None,
        search_query: Optional[str] = None,
        include_recent_events: bool = True
    ) -> List[Tuple[BaseEntity, int]]:
        """Gather entities with priority scores"""
        entities_with_priority = []
        seen_entities: Set[UUID] = set()
        
        # 1. Always include player
        entities_with_priority.append((player, ContextPriority.CRITICAL))
        seen_entities.add(player.id)
        
        # 2. Include interaction target if specified
        if interaction_target:
            entities_with_priority.append((interaction_target, ContextPriority.CRITICAL))
            seen_entities.add(interaction_target.id)
        
        # 3. Get current location and its context
        if player.current_location_id:
            try:
                current_location = await world_service.get_entity(player.current_location_id, EntityType.LOCATION)
                if current_location and current_location.id not in seen_entities:
                    priority = self.calculate_entity_priority(current_location, player, interaction_target)
                    entities_with_priority.append((current_location, priority))
                    seen_entities.add(current_location.id)
                    
                    # Get entities in current location via graph traversal
                    location_context = await world_service.get_entity_context(
                        player.current_location_id,
                        max_depth=1,  # Only immediate connections
                        entity_types=[EntityType.NPC, EntityType.ITEM]
                    )
                    
                    for entity in location_context:
                        if entity.id not in seen_entities:
                            priority = self.calculate_entity_priority(entity, player, interaction_target)
                            entities_with_priority.append((entity, priority))
                            seen_entities.add(entity.id)
                            
            except Exception as e:
                logger.warning(f"Failed to get current location context: {e}")
        
        # 4. Semantic search if query provided
        if search_query:
            try:
                search_results = await world_service.search_entities(
                    query=search_query,
                    limit=10,
                    include_graph_context=False
                )
                
                for entity, score in search_results:
                    # Skip if entity is not a proper object (cache deserialization issue)
                    if not hasattr(entity, 'id'):
                        logger.debug(f"Skipping invalid entity in search results: {type(entity)}")
                        continue
                        
                    if entity.id not in seen_entities:
                        # Convert search score to priority boost
                        priority = self.calculate_entity_priority(entity, player, interaction_target)
                        if score > 0.8:
                            priority = min(priority + 2, ContextPriority.CRITICAL)
                        elif score > 0.6:
                            priority = min(priority + 1, ContextPriority.HIGH)
                            
                        entities_with_priority.append((entity, priority))
                        seen_entities.add(entity.id)
                        
            except Exception as e:
                logger.warning(f"Semantic search failed: {e}")
        
        # 5. Include recent events if requested
        if include_recent_events:
            try:
                recent_changes = await world_service.get_recent_changes(
                    limit=5,
                    entity_types=[EntityType.EVENT]
                )
                
                for change in recent_changes:
                    # Get the actual event entity if available
                    if change.entity_type == EntityType.EVENT:
                        try:
                            event_entity = await world_service.get_entity(change.entity_id, EntityType.EVENT)
                            if event_entity and event_entity.id not in seen_entities:
                                priority = self.calculate_entity_priority(event_entity, player, interaction_target)
                                entities_with_priority.append((event_entity, priority))
                                seen_entities.add(event_entity.id)
                        except:
                            continue  # Skip if event entity not found
                            
            except Exception as e:
                logger.warning(f"Failed to get recent events: {e}")
        
        # 6. Graph traversal from player for additional context
        try:
            player_context = await world_service.get_entity_context(
                player.id,
                max_depth=2,
                entity_types=[EntityType.NPC, EntityType.LOCATION, EntityType.QUEST, EntityType.ITEM]
            )
            
            for entity in player_context:
                if entity.id not in seen_entities:
                    priority = self.calculate_entity_priority(entity, player, interaction_target)
                    entities_with_priority.append((entity, priority))
                    seen_entities.add(entity.id)
                    
        except Exception as e:
            logger.warning(f"Player context traversal failed: {e}")
        
        return entities_with_priority
    
    @track_context_building("optimized_context")
    async def build_optimized_context(
        self,
        player: Player,
        interaction_target: Optional[BaseEntity] = None,
        search_query: Optional[str] = None,
        target_token_limit: Optional[int] = None,
        include_recent_events: bool = True
    ) -> Tuple[List[BaseEntity], ContextMetrics]:
        """Build optimized context within token limits"""
        
        start_time = time.time()
        target_tokens = target_token_limit or self.max_context_tokens
        
        # Gather all potential entities with priorities
        entities_with_priority = await self.gather_context_entities(
            player=player,
            interaction_target=interaction_target,
            search_query=search_query,
            include_recent_events=include_recent_events
        )
        
        # Sort by priority (highest first)
        entities_with_priority.sort(key=lambda x: x[1], reverse=True)
        
        # Select entities within token budget
        selected_entities = []
        total_tokens = 0
        priority_counts = {}
        
        for entity, priority in entities_with_priority:
            # Include dead NPCs in context but with lower priority (unless they're the direct interaction target)
            if (entity.type == EntityType.NPC and 
                hasattr(entity, 'is_alive') and 
                not entity.is_alive and 
                entity.id != (interaction_target.id if interaction_target else None)):
                # Lower priority for dead NPCs but still include them
                priority = min(priority, ContextPriority.MEDIUM)
                logger.debug(f"Including dead NPC in context with reduced priority: {entity.name}")
                
            # Skip dead NPCs only for direct dialogue attempts (handled in game_routes)
            # For world descriptions, we want to mention them
                
            estimated_tokens = self.estimate_entity_tokens(entity)
            
            # Always include critical entities
            if priority >= ContextPriority.CRITICAL:
                selected_entities.append(entity)
                total_tokens += estimated_tokens
                priority_counts[str(priority)] = priority_counts.get(str(priority), 0) + 1
                continue
            
            # Include others if within budget
            if total_tokens + estimated_tokens <= target_tokens and len(selected_entities) < self.max_entities:
                selected_entities.append(entity)
                total_tokens += estimated_tokens
                priority_counts[str(priority)] = priority_counts.get(str(priority), 0) + 1
            else:
                # Stop if we're running out of token budget
                break
        
        assembly_time = time.time() - start_time
        
        metrics = ContextMetrics(
            total_entities_found=len(entities_with_priority),
            entities_included=len(selected_entities),
            tokens_estimated=total_tokens,
            traversal_depth_used=2,  # Fixed for this implementation
            vector_search_results=len([e for e, _ in entities_with_priority if search_query]),
            priority_breakdown=priority_counts,
            assembly_time=assembly_time
        )
        
        logger.info(f"Context built: {len(selected_entities)}/{len(entities_with_priority)} entities, "
                   f"~{total_tokens} tokens, {assembly_time:.3f}s")
        
        return selected_entities, metrics
    
    async def build_npc_interaction_context(
        self,
        player: Player,
        target_npc: NPC,
        player_message: str
    ) -> Tuple[List[BaseEntity], ContextMetrics]:
        """Build context specifically for NPC interactions"""
        
        # Use player message as search query for relevant context
        return await self.build_optimized_context(
            player=player,
            interaction_target=target_npc,
            search_query=player_message,
            target_token_limit=int(self.max_context_tokens * 0.8),  # Leave room for NPC profile
            include_recent_events=True
        )
    
    async def build_world_exploration_context(
        self,
        player: Player,
        exploration_query: str
    ) -> Tuple[List[BaseEntity], ContextMetrics]:
        """Build context for world exploration and description"""
        
        return await self.build_optimized_context(
            player=player,
            interaction_target=None,
            search_query=exploration_query,
            target_token_limit=self.max_context_tokens,
            include_recent_events=False  # Focus on static world elements
        )


# Global context builder instance
context_builder = SmartContextBuilder()
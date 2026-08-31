"""
Play a turn without HTTP.

The game core takes a GameCommand and returns what happened. Nothing in
that path knows about FastAPI, so a chat bot, a scheduled job or a test
can drive the game exactly the way the REST API does — this script is
the smallest possible second client.

Requires the stack from docker/docker-compose.yml.

    PYTHONPATH=src python examples/play_without_http.py <player_id>
"""

import asyncio
import sys
from uuid import UUID, uuid4

from core.actions import GameCommand, execute_command
from core.world_service import world_service


async def main(player_id: UUID) -> None:
    await world_service.initialize()
    try:
        table = uuid4()  # a table is just an id until sessions become real
        world = UUID("00000000-0000-0000-0000-000000000001")

        for text in [
            "I greet the innkeeper and ask what news he has heard",
            "I search the common room",
        ]:
            result = await execute_command(
                GameCommand(
                    world_id=world,
                    session_id=table,
                    player_id=player_id,
                    text=text,
                )
            )
            rolls = result.get("dice_rolls") or []
            print(f"\n> {text}")
            print(f"  [{result['action_type']}] rolls={len(rolls)}")
            print(f"  {result['content'][:300]}")
    finally:
        await world_service.shutdown()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: play_without_http.py <player_id>")
    asyncio.run(main(UUID(sys.argv[1])))

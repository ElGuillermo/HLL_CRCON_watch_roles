"""
watch_roles.py

A plugin for HLL CRCON (https://github.com/MarechJ/hll_rcon_tool) that :
- inform players about the role they took
- warns quitting officers
- suggests support roles when needed
- (optionally) sends Discord alerts

Author: https://github.com/ElGuillermo
License: MIT-like (free use/modify/distribute with attribution)
"""

from heapq import heappush, heappop
from datetime import datetime, timedelta
import asyncio
import logging
import signal
import sys
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urlparse  # Discord feature
import discord  # Discord feature
from rcon.rcon import Rcon
from rcon.settings import SERVER_INFO
from rcon.utils import get_server_number  # Discord feature
import custom_tools.common_functions as common_functions  # Discord feature
import custom_tools.watch_roles_config as config


# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.DEBUG)


# Define a semaphore to limit concurrency
SEMAPHORE_LIMIT = 10  # Adjust this value based on your system's capacity
semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)


@dataclass
class PlayerData:
    """
    Data class to hold player information.
    """
    player_id: str
    name: str
    actual_level: int
    known_team: str
    known_unit_name: str
    known_role: str
    actual_team: str
    actual_unit_name: str
    actual_role: str
    total_abandons: int
    lasttime_abandon: Optional[datetime]
    allies_supports_needed: bool
    axis_supports_needed: bool


async def limited_task(
    task_func,
    *args,
    **kwargs
):
    """
    Wrapper to limit the number of concurrent tasks using a semaphore.
    """
    async with semaphore:
        return await task_func(*args, **kwargs)


def is_valid_url(
    url: str
) -> bool:
    """
    Validates an url
    """
    try:
        parsed = urlparse(url)
        return all([parsed.scheme, parsed.netloc])
    except Exception:
        return False


def is_support_needed(
    realtime_all: dict
) -> tuple[bool, bool]:
    """
    Check if support roles are needed
    based on the number of infantry officers and supports in each team.
    Returns a tuple of booleans indicating if allies and/or axis need supports.
    """
    counts = {"allies": {"officer": 0, "support": 0}, "axis": {"officer": 0, "support": 0}}

    for realtime_player in realtime_all["players"].values():
        tested_team, tested_role = realtime_player.get('team'), realtime_player.get('role')
        if tested_team in counts and tested_role in counts[tested_team]:
            counts[tested_team][tested_role] += 1

    allies_supports_needed = (
        counts["allies"]["support"] < config.REQUIRED_SUPPORTS.get(counts["allies"]["officer"], 0)
    )
    axis_supports_needed = (
        counts["axis"]["support"] < config.REQUIRED_SUPPORTS.get(counts["axis"]["officer"], 0)
    )

    return allies_supports_needed, axis_supports_needed


def is_role_in_squad(
    player: PlayerData,
    realtime_all: dict,
    target_role: str = "support"
) -> bool:
    """
    Check if there is already a player with the given role in the same squad (team + unit).
    Skips:
    - The current player
    - Players not assigned to a unit (unit_name is None)
    - Players in the 'command' unit
    - Players with incomplete data
    Early return if the current player's role is already the target_role.
    """
    # Player is either unassigned or commander
    if not player.actual_unit_name or player.actual_unit_name == "command":
        return False

    # Player already has the role
    if player.actual_role == target_role:
        return True

    for realtime_player in realtime_all.get("players", {}).values():
        try:
            tested_player_id = realtime_player["player_id"]
            tested_team = realtime_player["team"]
            tested_unit = realtime_player["unit_name"]
            tested_role = realtime_player["role"]
        except KeyError:
            continue  # Skip players with incomplete data

        # Don't test
        if (
            tested_player_id == player.player_id
            or not tested_unit  # Unassigned
            or tested_unit == "command"  # Commander
        ):
            continue

        # Someone plays target_role in same team, same squad as player
        if (
            tested_team == player.actual_team
            and tested_unit == player.actual_unit_name
            and tested_role == target_role
        ):
            return True

    return False


def clean_old_entries(
    known_all: dict,
    delay: int = config.AUTO_CLEANING_TIME,
    priority_queue: list = []
) -> dict:
    """
    Remove entries from known_all that haven't changed in the last 'delay' minutes.
    Uses a priority queue to efficiently track the oldest entries.
    """
    max_age = datetime.now() - timedelta(minutes=delay)

    # Add all entries to the priority queue if it's empty
    if not priority_queue:
        for player_id, known_player in known_all.items():
            heappush(priority_queue, (known_player['lasttime_role_change'], player_id))

    # Remove outdated entries
    while priority_queue and priority_queue[0][0] < max_age:
        _, player_id = heappop(priority_queue)
        if player_id in known_all:
            known_player = known_all.pop(player_id)
            logger.debug(
                "💤 '%s' (%s) - not watched anymore",
                known_player.get('name', '(unknown)'),
                known_player.get('level', '(unknown)')
            )
            logger.debug("known_all dict now contains %s entries", len(known_all))

    return known_all


def is_recent_abandon(
    lasttime_abandon: Optional[datetime],
    watch_interval: int
) -> bool:
    """
    Check if an abandonment occurred since the last check
    """
    return bool(
        lasttime_abandon
        and (datetime.now() - lasttime_abandon < timedelta(seconds=watch_interval))
    )


async def send_message_async(
    rcon: Rcon,
    player: PlayerData,
    realtime_all: dict,
    watch_interval: int
) -> None:
    """
    Asynchronously send a message to the player based on their role and status.
    """
    msg = ""

    # Warn quitting officers
    if (
        is_recent_abandon(player.lasttime_abandon, watch_interval)
        and (
            config.ALWAYS_WARN_BAD_OFFICERS
            or player.actual_level < config.MIN_IMMUNE_LEVEL
        )
    ):
        msg += config.MESSAGE_TEXT.get("officer_quitter", '(Missing translation)')
        msg += config.MESSAGE_TEXT.get('nb_squads_abandoned', '(Missing translation)')
        msg += f" : {player.total_abandons}\n----------\n"

    # Suggest taking support role
    if (
        player.actual_role in config.SUPPORT_CANDIDATES
        and (
            (player.actual_team == "allies" and player.allies_supports_needed)
            or (player.actual_team == "axis" and player.axis_supports_needed)
        )
        and not is_role_in_squad(player, realtime_all, "support")
        and (
            config.ALWAYS_SUGGEST_SUPPORT
            or player.actual_level < config.MIN_IMMUNE_LEVEL
        )
    ):
        msg += config.MESSAGE_TEXT.get("support_needed", '(Missing translation)')

    # Actual role guidance
    if (
        player.actual_unit_name
        and player.actual_level < config.MIN_IMMUNE_LEVEL
    ):
        msg += config.MESSAGE_TEXT.get(player.actual_role, '(Missing translation)')

    # Send in-game message
    if msg:
        try:
            await asyncio.to_thread(
                rcon.message_player,
                player_id=player.player_id,
                message=msg,
                by=config.BOT_NAME
            )
        except Exception as e:
            logger.warning(
                "⚠️ '%s' (%s) - Couldn't send message : %s",
                player.name,
                player.actual_level,
                str(e)
            )


async def send_discord_alert_async(
    player: PlayerData,
    watch_interval: int = 30
) -> None:
    """
    Asynchronously send a Discord alert when an officer quits.
    """
    try:
        server_number = int(get_server_number())
        config_entry = config.SERVER_CONFIG[server_number - 1]

        if (
            isinstance(config_entry, list)
            and len(config_entry) == 2
            and isinstance(config_entry[0], str)
            and is_valid_url(config_entry[0])
            and isinstance(config_entry[1], bool)
        ):
            webhook_url, alerts_enabled = config_entry
        else:
            raise ValueError("Invalid Discord config structure")

    except (IndexError, ValueError, TypeError) as e:
        logger.error("Invalid Discord config for server %s : %s", server_number, str(e))
        return

    if not alerts_enabled or not is_recent_abandon(player.lasttime_abandon, watch_interval):
        return

    embed_desc = (
        f"Level : {player.actual_level}\n"
        f"{config.MESSAGE_TEXT.get('nb_squads_abandoned', '(Missing translation)')} : "
        f"{player.total_abandons}\n"
        f"{player.known_team}/{player.known_unit_name}/{player.known_role}"
        f" ➡️ "
        f"{player.actual_team}/{player.actual_unit_name}/{player.actual_role}"
    )
    embed = discord.Embed(
        title=player.name,
        url=common_functions.get_external_profile_url(player.player_id, player.name),
        description=embed_desc,
        color=0xffffff
    )
    embed.set_author(
        name=config.BOT_NAME,
        url=common_functions.DISCORD_EMBED_AUTHOR_URL,
        icon_url=common_functions.DISCORD_EMBED_AUTHOR_ICON_URL
    )
    embed.set_thumbnail(url=common_functions.get_avatar_url(player.player_id))

    try:
        webhook = discord.SyncWebhook.from_url(webhook_url)
        await asyncio.to_thread(common_functions.discord_embed_send, embed, webhook)
    except Exception as e:
        logger.warning(
            "⚠️ '%s' (%s) - Couldn't send Discord alert : %s",
            player.name,
            player.actual_level,
            str(e)
        )


async def track_role_changes_async() -> None:
    """
    Main function to track role changes and send alerts.
    'realtime_all' dict : realtime players data
    'known_all' dict : players data as it was at the end of last loop

    Infinite loop :
    - Get realtime players data
        - Evaluate support needs
    - Clean obsoleted 'known_all' entries
    - For each player on server
        - (new player) Create entry in 'known_all'
        - Compare realtime/historical data
        - If player changed team/unit/role
            - Update 'known_all'
            - Send message
            - Send Discord alert (quitting officers)
    """
    watch_interval = min(30, config.WATCH_INTERVAL)
    rcon = Rcon(SERVER_INFO)
    known_all: dict[str, dict[str, Any]] = {}

    while True:

        # Get realtime players data
        try:
            realtime_all = await asyncio.to_thread(rcon.get_detailed_players)
        except Exception as e:
            logger.error("get_detailed_players() failed: %s", str(e))
            await asyncio.sleep(watch_interval)
            continue

        # Evaluate support needs
        allies_supports_needed, axis_supports_needed = is_support_needed(realtime_all)

        # Clean obsoleted entries in 'known_all'
        priority_queue = []
        known_all = clean_old_entries(known_all, priority_queue=priority_queue)

        now_dt = datetime.now()

        tasks = []

        # For each player on server
        for realtime_player in realtime_all["players"].values():

            # Validate realtime data
            required_keys = ['player_id', 'name', 'level', 'team', 'unit_name', 'role']
            missing = [key for key in required_keys if key not in realtime_player]
            if missing:
                logger.warning(
                    "'%s' (%s) - Skipping player : missing fields : %s",
                    realtime_player.get('name', '(unknown)'),
                    realtime_player.get('level', 'unknown'),
                    missing
                )
                continue  # Some keys are missing : skip this player

            # Extract realtime data
            player_id, name, actual_level, actual_team, actual_unit, actual_role = (
                realtime_player['player_id'],
                realtime_player['name'],
                realtime_player['level'],
                realtime_player['team'],
                realtime_player['unit_name'],
                realtime_player['role']
            )

            # (new player) Create entry in 'known_all'
            if player_id not in known_all:
                known_all[player_id] = {
                    'lasttime_role_change': now_dt,
                    'name': name,
                    'level': actual_level,
                    'team': actual_team,
                    'unit_name': actual_unit,
                    'role': actual_role,
                    'total_abandons': 0,
                    'lasttime_abandon': None
                }
                logger.debug(
                    "🛬 '%s' (%s) - %s/%s/%s",
                    name,
                    actual_level,
                    actual_team,
                    actual_unit,
                    actual_role
                )
                logger.debug("known_all dict now contains %s entries", len(known_all))
                continue  # We'll check for changes on next loop

            # Get historical data from 'known_all'
            known_playerdata = known_all[player_id]
            known_level = known_playerdata['level']
            known_team = known_playerdata['team']
            known_unit_name = known_playerdata['unit_name']
            known_role = known_playerdata['role']
            total_abandons = known_playerdata['total_abandons']
            lasttime_abandon = known_playerdata['lasttime_abandon']

            # The player levelled up
            if known_level < actual_level:
                logger.debug("💪 '%s' (%s ➡️ %s)", name, known_level, actual_level)
                known_playerdata['level'] = actual_level  # Update dict

            # The player changed team/unit/role
            role_changed = (
                known_team != actual_team
                or known_unit_name != actual_unit
                or known_role != actual_role
            )
            if role_changed:
                # common_change_str
                common_change_str = (
                    f"'{name}' ({actual_level})"
                    f" - {known_team}/{known_unit_name}/{known_role}"
                    f" ➡️ {actual_team}/{actual_unit}/{actual_role}"
                )

                # The player was an officer
                if known_role in config.OFFICERS:
                    # Update abandon count and last abandon datetime
                    total_abandons += 1
                    lasttime_abandon = now_dt
                    # Log
                    logger.info(f"🟥x{total_abandons} {common_change_str}")

                # The player wasn't an officer
                else:
                    # Log
                    logger.debug(f"🟩 {common_change_str}")

                # Create a player dataclass to be used in functions
                player = PlayerData(
                    player_id=player_id,  # from realtime
                    name=name,  # from realtime
                    actual_level=actual_level,  # from realtime
                    known_team=known_team,
                    known_unit_name=known_unit_name,
                    known_role=known_role,
                    actual_team=actual_team,  # from realtime
                    actual_unit_name=actual_unit,  # from realtime
                    actual_role=actual_role,  # from realtime
                    total_abandons=total_abandons,
                    lasttime_abandon=lasttime_abandon,
                    allies_supports_needed=allies_supports_needed,
                    axis_supports_needed=axis_supports_needed
                )

                # Update historical data in 'known_all'
                known_playerdata.update({
                    'lasttime_role_change': now_dt,
                    'team': actual_team,
                    'unit_name': actual_unit,
                    'role': actual_role,
                    'total_abandons': total_abandons,
                    'lasttime_abandon': lasttime_abandon
                })

                # Send ingame message to player and Discord alert to admins
                tasks.append(limited_task(send_message_async, rcon, player, realtime_all, watch_interval))
                tasks.append(limited_task(send_discord_alert_async, player, watch_interval))

        if tasks:
            await asyncio.gather(*tasks)

        # Wait before the next check
        await asyncio.sleep(watch_interval)


def shutdown_handler(signum, frame):
    """
    Handle shutdown signals (SIGINT, SIGTERM) to gracefully exit the program.
    """
    logger.info("Received signal %s: shutting down.", signum)
    sys.exit(0)


# Handle graceful shutdown
signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

logger.info(
    "\n-------------------------------------------------------------------------------\n"
    "%s started\n"
    "-------------------------------------------------------------------------------",
    config.BOT_NAME
)

if __name__ == "__main__":
    asyncio.run(track_role_changes_async())

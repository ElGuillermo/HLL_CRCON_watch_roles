"""
watch_roles.py

A plugin for HLL CRCON (https://github.com/MarechJ/hll_rcon_tool) that :
- warns quitting officers (and optionally sends Discord alerts)
- suggests support roles when needed
- inform players about the role they took

Author: https://github.com/ElGuillermo
License: MIT-like (free use/modify/distribute with attribution)
"""

from heapq import heappush, heappop
from datetime import datetime, timedelta, timezone
import asyncio
import logging
import signal
import sys
from dataclasses import dataclass
from time import sleep
from typing import Any, Optional
from urllib.parse import urlparse  # Discord feature
import discord  # Discord feature
from rcon.game_logs import get_recent_logs
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
    abandons_thismatch: int
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
    semaphore = asyncio.Semaphore(config.SEMAPHORE_LIMIT)
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
    counts = {
        "allies": {"officer": 0, "support": 0},
        "axis": {"officer": 0, "support": 0}
    }

    for realtime_player in realtime_all["players"].values():
        tested_team = realtime_player.get('team')
        tested_role = realtime_player.get('role')
        if tested_team in counts and tested_role in counts[tested_team]:
            counts[tested_team][tested_role] += 1

    allies_supports_needed = (
        counts["allies"]["support"]
        < config.REQUIRED_SUPPORTS.get(counts["allies"]["officer"], 0)
    )
    axis_supports_needed = (
        counts["axis"]["support"]
        < config.REQUIRED_SUPPORTS.get(counts["axis"]["officer"], 0)
    )

    return allies_supports_needed, axis_supports_needed


def was_alone_in_squad(
    playerclass: PlayerData,
    realtime_all: dict
) -> bool:
    """
    Was the player alone in its previous squad ?
    (If so : he won't get the "quitting officer" warning if he leaves it)
    """
    # He was unassigned
    if not playerclass.known_unit_name:
        return True

    # Commander is always alone in its "command" squad,
    # but he can be considered as the officer of the whole team
    if playerclass.known_unit_name == "command":
        return False

    for realtime_player in realtime_all.get("players", {}).values():
        try:
            tested_player_id = realtime_player["player_id"]
            tested_team = realtime_player["team"]
            tested_unit = realtime_player["unit_name"]
        except KeyError:
            continue  # Skip players with incomplete data

        # Don't test
        if (
            tested_player_id == playerclass.player_id
            or not tested_unit  # Unassigned
            or tested_unit == "command"  # Commander
        ):
            continue

        # Someone still plays in same team, same squad the player was in
        if (
            tested_team == playerclass.known_team
            and tested_unit == playerclass.known_unit_name
        ):
            return False

    return True


def is_this_role_taken_in_squad(
    playerclass: PlayerData,
    realtime_all: dict,
    target_role: str = "support"
) -> bool:
    """
    Is there a player with the target_role in player's squad (team + unit) ?
    """
    # Player is either unassigned or commander
    if (
        not playerclass.actual_unit_name
        or playerclass.actual_unit_name == "command"
    ):
        return False

    # Player already plays target_role
    if playerclass.actual_role == target_role:
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
            tested_player_id == playerclass.player_id
            or not tested_unit  # Unassigned
            or tested_unit == "command"  # Commander
        ):
            continue

        # Someone plays target_role in same team, same squad as player
        if (
            tested_team == playerclass.actual_team
            and tested_unit == playerclass.actual_unit_name
            and tested_role == target_role
        ):
            return True

    return False


def clean_departed_players(
    realtime_all: dict,
    known_all: dict
) -> dict:
    """
    Remove entries from departed players.
    """
    valid_player_ids = {
        realtime_player['player_id']
        for realtime_player in realtime_all.get("players", {}).values()
        if isinstance(realtime_player, dict) and 'player_id' in realtime_player
    }

    for player_id in list(known_all.keys()):
        if player_id not in valid_player_ids:
            known_player = known_all.pop(player_id)
            logger.debug(
                "🛫 '%s' (%s) - not watched anymore (departed)",
                known_player.get('name', '(unknown)'),
                known_player.get('level', '(unknown)')
            )
            logger.debug(
                "'known_all' dict now contains %s entries",
                len(known_all)
            )

    return known_all


def reset_on_match_end(
    now_dt: datetime,
    known_all: dict,
    watch_interval: int
) -> dict:
    """
    Unassign all known players at match's end,
    so they won't get warned about quitting officer role on next match start
    """
    now_ts = round(now_dt.timestamp())  # seconds since 1970-01-01T00:00:00Z
    min_timestamp = now_ts - watch_interval
    # Search if "MATCH ENDED" log occured since the last loop time
    try:
        recent_logs = get_recent_logs(
            action_filter=["MATCH ENDED"],
            min_timestamp=min_timestamp,
            exact_action=True
        )
    except Exception as error:
        logger.error("Couldn't get recent_logs : %s", error)
        return known_all

    match_end_detected = False
    for log in recent_logs["logs"]:
        if log["action"] == "MATCH ENDED":  # Should be always True for any log found
            match_end_detected = True
            match_end_timestamp = log["timestamp_ms"]
            # There is 100 secs between "MATCH ENDED" and "MATCH START"
            wake_up_time = round(match_end_timestamp / 1000) + 110
            sleep_duration = wake_up_time - now_ts
            break

    if match_end_detected:
        entries_reset = 0
        for known_player in known_all.values():
            # if updated, clean_old_entries() would never be triggered
            # known_player['lasttime_role_change'] = now_dt
            known_player['unit_name'] = None
            known_player['role'] = "rifleman"
            known_player['abandons_thismatch'] = 0
            known_player['lasttime_abandon'] = None
            entries_reset += 1
        logger.debug(
            "Match ended : %s 'known_all' entries have been reset. Waiting %s s...",
            entries_reset,
            sleep_duration
        )
        sleep(sleep_duration)

    return known_all


def clean_old_entries(
    now_dt: datetime,
    known_all: dict,
    delay: int = config.AUTO_CLEANING_TIME,
    priority_queue: list = []
) -> dict:
    """
    Remove entries that haven't changed in the last 'delay' minutes.
    Uses a priority queue to efficiently track the oldest entries.
    """
    max_age = now_dt - timedelta(minutes=delay)

    # Add all entries to the priority queue if it's empty
    if not priority_queue:
        for player_id, known_player in known_all.items():
            heappush(
                priority_queue,
                (known_player['lasttime_role_change'],
                player_id)
            )

    # Remove outdated entries
    while priority_queue and priority_queue[0][0] < max_age:
        _, player_id = heappop(priority_queue)
        if player_id in known_all:
            known_player = known_all.pop(player_id)
            logger.debug(
                "💤 '%s' (%s) - not watched anymore (obsoleted)",
                known_player.get('name', '(unknown)'),
                known_player.get('level', '(unknown)')
            )
            logger.debug(
                "'known_all' dict now contains %s entries",
                len(known_all)
            )

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
        and (
            datetime.now(timezone.utc) - lasttime_abandon
            < timedelta(seconds=watch_interval)
        )
    )


async def send_message_async(
    rcon: Rcon,
    playerclass: PlayerData,
    realtime_all: dict,
    watch_interval: int
) -> None:
    """
    Asynchronously send a message to the player based on their role and status.
    """
    msg = ""

    # Warn quitting officers
    if (
        is_recent_abandon(playerclass.lasttime_abandon, watch_interval)
        and not was_alone_in_squad(playerclass, realtime_all)
        and (
            config.ALWAYS_WARN_BAD_OFFICERS
            or playerclass.actual_level < config.MIN_IMMUNE_LEVEL
        )
    ):
        msg += config.MESSAGE_TEXT.get(
            "officer_quitter", '(Missing translation)'
        )
        msg += config.MESSAGE_TEXT.get(
            'nb_squads_abandoned', '(Missing translation)'
        )
        msg += f" : {playerclass.abandons_thismatch}\n----------\n"

    # Suggest taking support role
    if (
        (
            (
                playerclass.actual_team == "allies"
                and playerclass.allies_supports_needed
            )
            or (
                playerclass.actual_team == "axis"
                and playerclass.axis_supports_needed
            )
        )
        and not is_this_role_taken_in_squad(playerclass, realtime_all, "support")
        and playerclass.actual_role in common_functions.SUPPORT_CANDIDATES
        and (
            config.ALWAYS_SUGGEST_SUPPORT
            or playerclass.actual_level < config.MIN_IMMUNE_LEVEL
        )
    ):
        msg += config.MESSAGE_TEXT.get(
            "support_needed", '(Missing translation)'
        )

    # Actual role guidance
    if (
        playerclass.actual_unit_name
        and playerclass.actual_level < config.MIN_IMMUNE_LEVEL
    ):
        msg += config.MESSAGE_TEXT.get(
            playerclass.actual_role, '(Missing translation)'
        )

    # Send in-game message
    if msg:
        try:
            await asyncio.to_thread(
                rcon.message_player,
                player_id=playerclass.player_id,
                message=msg,
                by=config.BOT_NAME
            )
        except Exception as error:
            logger.warning(
                "⚠️ '%s' (%s) - Couldn't send message : %s",
                playerclass.name,
                playerclass.actual_level,
                str(error)
            )


async def send_discord_alert_async(
    playerclass: PlayerData,
    realtime_all: dict,
    watch_interval: int = 30
) -> None:
    """
    Asynchronously send a Discord alert when an officer quits.
    """
    if (
        not is_recent_abandon(playerclass.lasttime_abandon, watch_interval)
        or was_alone_in_squad(playerclass, realtime_all)
    ):
        return

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

    except (IndexError, ValueError, TypeError) as error:
        logger.error(
            "Invalid Discord config for server %s : %s",
            server_number,
            str(error)
        )
        return

    if not alerts_enabled:
        return

    embed_desc = (
        f"Level : {playerclass.actual_level}\n"
        f"{config.MESSAGE_TEXT.get('nb_squads_abandoned', '(Missing translation)')} : "
        f"{playerclass.abandons_thismatch}\n"
        f"{playerclass.known_team}/{playerclass.known_unit_name}/"
        f"{playerclass.known_role} ➡️ {playerclass.actual_team}"
        f"/{playerclass.actual_unit_name}/{playerclass.actual_role}"
    )
    embed = discord.Embed(
        title=playerclass.name,
        url=common_functions.get_external_profile_url(
            playerclass.player_id, playerclass.name
        ),
        description=embed_desc,
        color=0xffffff
    )
    embed.set_author(
        name=config.BOT_NAME,
        url=common_functions.DISCORD_EMBED_AUTHOR_URL,
        icon_url=common_functions.DISCORD_EMBED_AUTHOR_ICON_URL
    )
    embed.set_thumbnail(
        url=common_functions.get_avatar_url(playerclass.player_id)
    )

    try:
        webhook = discord.SyncWebhook.from_url(webhook_url)
        await asyncio.to_thread(
            common_functions.discord_embed_send, embed, webhook
        )
    except Exception as error:
        logger.warning(
            "⚠️ '%s' (%s) - Couldn't send Discord alert : %s",
            playerclass.name,
            playerclass.actual_level,
            str(error)
        )


async def track_role_changes_async() -> None:
    """
    Main function to track role changes and send messages and alerts.
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
    watch_interval = max(30, min(config.WATCH_INTERVAL, 60))  # min = 30, max = 60
    rcon = Rcon(SERVER_INFO)
    known_all: dict[str, dict[str, Any]] = {}

    # Infinite loop
    while True:

        now_dt = datetime.now(timezone.utc)

        # Clean 'known_all' obsoleted entries
        known_all = clean_old_entries(now_dt, known_all, priority_queue=[])

        # Reset 'known_all' entries on match end
        known_all = reset_on_match_end(now_dt, known_all, watch_interval)

        # Get realtime players data
        try:
            realtime_all = await asyncio.to_thread(rcon.get_detailed_players)
        except Exception as error:
            logger.error("get_detailed_players() failed: %s", str(error))
            await asyncio.sleep(watch_interval)
            continue

        # Clean 'known_all' departed players
        known_all = clean_departed_players(realtime_all, known_all)

        # Evaluate support needs
        (
            allies_supports_needed,
            axis_supports_needed
        ) = is_support_needed(realtime_all)

        tasks = []

        # For each player on server
        for realtime_player in realtime_all["players"].values():

            # Validate realtime data
            required_keys = [
                'player_id', 'name', 'level', 'team', 'unit_name', 'role'
            ]
            missing = [
                key for key in required_keys if key not in realtime_player
            ]
            if missing:
                logger.warning(
                    "'%s' (%s) - Skipping player : missing fields : %s",
                    realtime_player.get('name', '(unknown)'),
                    realtime_player.get('level', 'unknown'),
                    missing
                )
                continue  # Some keys are missing : skip this player

            # Extract realtime data
            (
                player_id, name, actual_level,
                actual_team, actual_unit, actual_role
            ) = (
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
                    'abandons_thismatch': 0,
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
                logger.debug(
                    "'known_all' dict now contains %s entries", len(known_all)
                )
                continue  # We'll check for changes on next loop

            # Get historical data from 'known_all'
            known_player = known_all[player_id]
            known_level = known_player['level']
            known_team = known_player['team']
            known_unit_name = known_player['unit_name']
            known_role = known_player['role']
            abandons_thismatch = known_player['abandons_thismatch']
            lasttime_abandon = known_player['lasttime_abandon']

            # The player levelled up
            if known_level < actual_level:
                logger.debug(
                    "💪 '%s' (%s ➡️ %s)", name, known_level, actual_level
                )
                known_player['level'] = actual_level  # Update dict

            # The player changed team/unit/role
            if (
                known_team != actual_team
                or known_unit_name != actual_unit
                or known_role != actual_role
            ):
                common_change_str = (
                    f"'{name}' ({actual_level})"
                    f" - {known_team}/{known_unit_name}/{known_role}"
                    f" ➡️ {actual_team}/{actual_unit}/{actual_role}"
                )

                # The player was an officer
                if known_role in common_functions.OFFICERS:
                    abandons_thismatch += 1
                    lasttime_abandon = now_dt
                    logger.info("🟥x%s %s", abandons_thismatch, common_change_str)

                # The player wasn't an officer
                else:
                    logger.debug("🟩 %s", common_change_str)

                # Create a player dataclass to be used in functions
                playerclass = PlayerData(
                    player_id=player_id,
                    name=name,
                    actual_level=actual_level,
                    known_team=known_team,
                    known_unit_name=known_unit_name,
                    known_role=known_role,
                    actual_team=actual_team,
                    actual_unit_name=actual_unit,
                    actual_role=actual_role,
                    abandons_thismatch=abandons_thismatch,
                    lasttime_abandon=lasttime_abandon,
                    allies_supports_needed=allies_supports_needed,
                    axis_supports_needed=axis_supports_needed
                )

                # Update 'known_all'
                known_player.update({
                    'lasttime_role_change': now_dt,
                    'team': actual_team,
                    'unit_name': actual_unit,
                    'role': actual_role,
                    'abandons_thismatch': abandons_thismatch,
                    'lasttime_abandon': lasttime_abandon
                })

                # Queue ingame messages
                tasks.append(
                    limited_task(
                        send_message_async,
                        rcon, playerclass, realtime_all, watch_interval
                    )
                )
                # Queue Discord alerts
                tasks.append(
                    limited_task(
                        send_discord_alert_async,
                        playerclass, realtime_all, watch_interval
                    )
                )

        # Send messages and alerts
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
    "\n---------------------------------------"
    "----------------------------------------\n"
    "%s started\n"
    "-----------------------------------------"
    "--------------------------------------",
    config.BOT_NAME
)

if __name__ == "__main__":
    asyncio.run(track_role_changes_async())

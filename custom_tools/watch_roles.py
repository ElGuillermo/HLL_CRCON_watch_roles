"""
watch_roles.py

A plugin for HLL CRCON (https://github.com/MarechJ/hll_rcon_tool) that :
- inform players about the role they took
- warns quitting officers
- suggests support roles when needed
- (optionally) sends Discord alerts.

Author: https://github.com/ElGuillermo
License: MIT-like (free use/modify/distribute with attribution)
"""

from datetime import datetime, timedelta
import logging
import time
import signal
import sys
from dataclasses import dataclass
import discord  # Discord feature
from rcon.rcon import Rcon
from rcon.settings import SERVER_INFO
from rcon.utils import get_server_number  # Discord feature
import custom_tools.common_functions as common_functions  # Discord feature
import custom_tools.watch_roles_config as config


@dataclass
class PlayerData:
    """
    Data class to hold player information.
    """
    player_id: str
    player_name: str
    actual_level: int
    previous_team: str
    previous_unit_name: str
    previous_role: str
    actual_team: str
    actual_unit_name: str
    actual_role: str
    nb_abandons: int
    last_abandon: datetime | None
    allies_supports_needed: bool
    axis_supports_needed: bool


def is_support_needed(detailed_players: dict) -> tuple[bool, bool]:
    """
    Check if support roles are needed
    based on the number of infantry officers and supports in each team.
    Returns a tuple of booleans indicating if allies and/or axis need supports.
    """
    counts = {"allies": {"officer": 0, "support": 0}, "axis": {"officer": 0, "support": 0}}
    for player in detailed_players["players"].values():
        team, role = player.get('team'), player.get('role')
        if team in counts and role in counts[team]:
            counts[team][role] += 1

    allies_needed = counts["allies"]["support"] < config.REQUIRED_SUPPORTS.get(counts["allies"]["officer"], 0)
    axis_needed = counts["axis"]["support"] < config.REQUIRED_SUPPORTS.get(counts["axis"]["officer"], 0)

    return allies_needed, axis_needed


def clean_old_entries(previous_data: dict, delay: int = config.AUTO_CLEANING_TIME) -> dict:
    """
    Remove entries from previous_data that haven't changed in the last 'delay' minutes.
    """
    limit = datetime.now() - timedelta(minutes=delay)
    to_delete = [player_id for player_id, player_data in previous_data.items() if player_data['last_role_change'] < limit]
    for player_id in to_delete:
        player_data = previous_data[player_id]
        logger.info("💤 '%s' (%s) - not watched anymore", player_data.get('name', '(unknown)'), player_data.get('level', '(unknown)'))
        previous_data.pop(player_id)
        logger.info("previous_data dict now contains %s entries", len(previous_data))

    return previous_data


def is_recent_abandon(last_abandon: datetime | None) -> bool:
    """
    Check if an abandon occured since last check
    """
    return bool(last_abandon and (datetime.now() - last_abandon < timedelta(seconds=config.WATCH_INTERVAL)))


def send_message(rcon: Rcon, event: PlayerData) -> None:
    """
    Send a message to the player based on their role and status.
    """
    msg = ""

    # Warn quitting officers
    if is_recent_abandon(event.last_abandon) and (config.ALWAYS_WARN_BAD_OFFICERS or event.actual_level < config.MIN_IMMUNE_LEVEL):
        msg += config.ADVICE_MESSAGE_TEXT.get("officer_quitter", '(Missing translation)')
        msg += f"{config.ADVICE_MESSAGE_TEXT.get('nb_squads_abandoned', '(Missing translation)')} : {event.nb_abandons}"

    # Suggest taking support role
    if ((event.actual_team == "allies" and event.allies_supports_needed) or (event.actual_team == "axis" and event.axis_supports_needed)) \
        and event.actual_role in config.SUPPORT_CANDIDATES and (config.ALWAYS_SUGGEST_SUPPORT or event.actual_level < config.MIN_IMMUNE_LEVEL):
        msg += config.ADVICE_MESSAGE_TEXT.get("support_needed", '(Missing translation)')

    # Actual role guidance
    if event.actual_level < config.MIN_IMMUNE_LEVEL and event.actual_unit_name:
        msg += config.ADVICE_MESSAGE_TEXT.get(event.actual_role, '(Missing translation)')

    # Send ingame message
    if msg:
        try:
            rcon.message_player(
                player_id=event.player_id,
                message=msg,
                by=config.BOT_NAME
            )
        except Exception as e:
            logger.error(
                "⚠️ '%s' (%s) - Couldn't send message : %s",
                event.player_name,
                event.actual_level,
                str(e)
            )


def send_discord_alert(event: PlayerData) -> None:
    """
    Send a Discord alert when an officer quits
    """
    # Get the config for the current server
    server_number = int(get_server_number())
    try:
        webhook_url, alerts_enabled = config.SERVER_CONFIG[server_number - 1]
    except IndexError:
        logger.error("No Discord config found for server %s", server_number)
        return

    # Checks if alerts are enabled and if an abandon occured since last check
    if not alerts_enabled or not is_recent_abandon(event.last_abandon):
        return

    # Post preparation
    embed_desc = (
        f"Level : {event.actual_level}\n"
        f"{config.ADVICE_MESSAGE_TEXT.get('nb_squads_abandoned', '(Missing translation)')} : {event.nb_abandons}\n"
        f"{event.previous_team}/{event.previous_unit_name}/{event.previous_role} ➡️ {event.actual_team}/{event.actual_unit_name}/{event.actual_role}"
    )
    embed = discord.Embed(
        title=event.player_name,
        url=common_functions.get_external_profile_url(event.player_id, event.player_name),
        description=embed_desc,
        color=0xffffff
    )
    embed.set_author(
        name=config.BOT_NAME,
        url=common_functions.DISCORD_EMBED_AUTHOR_URL,
        icon_url=common_functions.DISCORD_EMBED_AUTHOR_ICON_URL
    )
    embed.set_thumbnail(url=common_functions.get_avatar_url(event.player_id))

    # Send the post
    webhook = discord.SyncWebhook.from_url(webhook_url)
    try:
        common_functions.discord_embed_send(embed, webhook)
    except Exception as e:
        logger.error(
            "⚠️ '%s' (%s) - Couldn't send Discord alert : %s",
            event.player_name,
            event.actual_level,
            str(e)
        )


def track_role_changes() -> None:
    """
    Main function to track role changes and send alerts.
    """
    rcon = Rcon(SERVER_INFO)
    previous_data = {}

    while True:

        # Get data from game server
        try:
            detailed_players = rcon.get_detailed_players()
        except Exception as e:
            logger.error("get_detailed_players() failed: %s", str(e))
            time.sleep(config.WATCH_INTERVAL)
            continue

        # Get support needs
        allies_needed, axis_needed = is_support_needed(detailed_players)

        # Clean up old entries
        previous_data = clean_old_entries(previous_data)

        now = datetime.now()

        for player_data in detailed_players["players"].values():
            # Validate required fields
            required_fields = ['player_id', 'name', 'level', 'team', 'unit_name', 'role']
            missing = [data for data in required_fields if data not in player_data]
            if missing:
                logger.warning(
                    "'%s' (%s) - Skipping player : missing fields : %s",
                    player_data.get('name', '(unknown)'),
                    player_data.get('level', 'unknown'),
                    missing
                )
                continue

            # Extract player data
            player_id, name, level = player_data['player_id'], player_data['name'], player_data['level']
            team, unit, role = player_data['team'], player_data['unit_name'], player_data['role']

            # New player
            if player_id not in previous_data:
                previous_data[player_id] = {
                    'last_role_change': now,
                    'player_id': player_id,
                    'name': name,
                    'level': level,
                    'team': team,
                    'unit_name': unit,
                    'role': role,
                    'nb_abandons': 0,
                    'last_abandon': None
                }
                logger.info("🛬 '%s' (%s) - %s/%s/%s", name, level, team, unit, role)
                logger.info("previous_data dict now contains %s entries", len(previous_data))
                continue  # We'll check for changes on next loop

            # Unpack this player's previous data
            old = previous_data[player_id]

            # The player levelled up
            if old['level'] < level:
                logger.info("💪 '%s' (%s ➡️ %s)", name, old['level'], level)
                old['level'] = level

            # The player changed team/unit/role
            role_changed = old['team'] != team or old['unit_name'] != unit or old['role'] != role
            if role_changed:
                # Retrieve previous data
                previous_team = old['team']
                previous_unit_name = old['unit_name']
                previous_role = old['role']
                nb_abandons = old['nb_abandons']
                last_abandon = old['last_abandon']

                # The player was an officer
                if previous_role in config.OFFICERS:
                    # Update abandon count and last abandon datetime
                    nb_abandons += 1
                    last_abandon = now
                    # Log
                    logger.info(
                        "🟥x%s '%s' (%s) - %s/%s/%s ➡️ %s/%s/%s",
                        nb_abandons,
                        name,
                        level,
                        previous_team,
                        previous_unit_name,
                        previous_role,
                        team,
                        unit,
                        role
                    )
                # The player wasn't an officer
                else:
                    # Log
                    logger.info(
                        "🟩 '%s' (%s) - %s/%s/%s ➡️ %s/%s/%s",
                        name,
                        level,
                        previous_team,
                        previous_unit_name,
                        previous_role,
                        team,
                        unit,
                        role
                    )

                # Create a dataclass object
                event = PlayerData(
                    player_id=player_id,
                    player_name=name,
                    actual_level=level,
                    previous_team=previous_team,
                    previous_unit_name=previous_unit_name,
                    previous_role=previous_role,
                    actual_team=team,
                    actual_unit_name=unit,
                    actual_role=role,
                    nb_abandons=nb_abandons,
                    last_abandon=last_abandon,
                    allies_supports_needed=allies_needed,
                    axis_supports_needed=axis_needed
                )

                # Update previous data
                old.update({
                    'last_role_change': now,
                    'team': team,
                    'unit_name': unit,
                    'role': role,
                    'nb_abandons': nb_abandons,
                    'last_abandon': last_abandon
                })

                # Send ingame message to player and Discord alert to admins
                send_message(rcon, event)
                send_discord_alert(event)

        next_tick = time.time() + config.WATCH_INTERVAL
        sleep_time = max(0, next_tick - time.time())
        time.sleep(sleep_time)


def shutdown_handler(signum, frame):
    """
    Handle shutdown signals (SIGINT, SIGTERM) to gracefully exit the program.
    """
    logger.info("Received signal %s: shutting down.", signum)
    sys.exit(0)


# Setup logger
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO)

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
    track_role_changes()

"""
watch_roles.py

A plugin for HLL CRCON (https://github.com/MarechJ/hll_rcon_tool) that tracks role changes,
warns players (especially bad officers), suggests support roles when needed,
and optionally sends Discord alerts.

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
class PlayerEvent:
    """
    Data class to hold player event information.
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
    Check if support roles are needed based on the number of officers and supports in each team.
    Returns a tuple indicating if allies and axis need supports.
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
    to_delete = [pid for pid, pdata in previous_data.items() if pdata['last_role_change'] < limit]
    for pid in to_delete:
        pdata = previous_data[pid]
        logger.info("\u267b\ufe0f '%s' (%s) - not watched anymore", pdata.get('name', '(unknown)'), pdata.get('level', '(unknown)'))
        previous_data.pop(pid)
    return previous_data


def is_recent_abandon(last_abandon: datetime | None) -> bool:
    """
    Check if the last abandon was within the configured watch interval.
    """
    return bool(last_abandon and (datetime.now() - last_abandon < timedelta(seconds=config.WATCH_INTERVAL)))


def send_message(rcon: Rcon, event: PlayerEvent) -> None:
    """
    Send a message to the player based on their role and status.
    """
    msg = ""
    if is_recent_abandon(event.last_abandon) and (config.ALWAYS_WARN_BAD_OFFICERS or event.actual_level < config.MIN_IMMUNE_LEVEL):
        msg += config.ADVICE_MESSAGE_TEXT.get("officer_quitter")
        msg += f"{config.ADVICE_MESSAGE_TEXT.get('nb_squads_abandoned')} : {event.nb_abandons}"

    if ((event.actual_team == "allies" and event.allies_supports_needed) or (event.actual_team == "axis" and event.axis_supports_needed)) \
        and event.actual_role in config.SUPPORT_CANDIDATES and (config.ALWAYS_SUGGEST_SUPPORT or event.actual_level < config.MIN_IMMUNE_LEVEL):
        msg += config.ADVICE_MESSAGE_TEXT.get("support_needed")

    if event.actual_level < config.MIN_IMMUNE_LEVEL and event.actual_unit_name:
        msg += config.ADVICE_MESSAGE_TEXT.get(event.actual_role, '')

    if msg:
        try:
            rcon.message_player(player_id=event.player_id, message=msg, by=config.BOT_NAME)
        except Exception as e:
            logger.error("!!! Error while sending message to '%s' : %s", event.player_name, str(e))


def send_discord_alert(event: PlayerEvent) -> None:
    """
    Send a Discord alert for the player event.
    """
    server_number = int(get_server_number())
    try:
        webhook_url, alerts_enabled = config.SERVER_CONFIG[server_number - 1]
    except IndexError:
        logger.error("No config found for server %s", server_number)
        return

    if not alerts_enabled or not is_recent_abandon(event.last_abandon):
        return

    embed_desc = (
        f"{config.ADVICE_MESSAGE_TEXT.get('nb_squads_abandoned', 'Abandons')} : {event.nb_abandons}\n"
        f"Level : {event.actual_level}\n"
        f"{event.previous_team}/{event.previous_unit_name}/{event.previous_role} ➡️ {event.actual_team}/{event.actual_unit_name}/{event.actual_role}"
    )

    webhook = discord.SyncWebhook.from_url(webhook_url)
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

    common_functions.discord_embed_send(embed, webhook)


def track_role_changes():
    """
    Main function to track role changes and send alerts.
    """
    rcon = Rcon(SERVER_INFO)
    prev_data = {}

    while True:
        now = datetime.now()

        try:
            players = rcon.get_detailed_players()
        except Exception as e:
            logger.error("get_detailed_players() failed: %s", str(e))
            time.sleep(config.WATCH_INTERVAL)
            continue

        allies_needed, axis_needed = is_support_needed(players)
        prev_data = clean_old_entries(prev_data)

        for p in players["players"].values():
            # Validate required fields
            required_fields = ['player_id', 'name', 'level', 'team', 'unit_name', 'role']
            missing = [k for k in required_fields if k not in p]
            if missing:
                logger.warning("Skipping player missing fields %s: %s", missing, p.get('name', 'Unknown'))
                continue

            pid, name, level = p['player_id'], p['name'], p['level']
            team, unit, role = p['team'], p['unit_name'], p['role']

            if pid not in prev_data:
                prev_data[pid] = {
                    'last_role_change': now,
                    'player_id': pid,
                    'name': name,
                    'level': level,
                    'team': team,
                    'unit_name': unit,
                    'role': role,
                    'nb_abandons': 0,
                    'last_abandon': None
                }
                logger.info("\U0001f195 '%s' (%s) - %s/%s/%s", name, level, team, unit, role)
                continue

            old = prev_data[pid]

            if old['level'] < level:
                logger.info("⬆️ '%s' (level %s ➡️ %s)", name, old['level'], level)
                old['level'] = level

            role_changed = old['team'] != team or old['unit_name'] != unit or old['role'] != role
            if role_changed:
                # Capture previous values BEFORE updating
                previous_team = old['team']
                previous_unit_name = old['unit_name']
                previous_role = old['role']
                nb_abandons = old['nb_abandons']
                abandon = old['last_abandon']

                if previous_role in config.OFFICERS:
                    nb_abandons += 1
                    abandon = now
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
                else:
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

                event = PlayerEvent(
                    player_id=pid,
                    player_name=name,
                    actual_level=level,
                    previous_team=previous_team,
                    previous_unit_name=previous_unit_name,
                    previous_role=previous_role,
                    actual_team=team,
                    actual_unit_name=unit,
                    actual_role=role,
                    nb_abandons=nb_abandons,
                    last_abandon=abandon,
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
                    'last_abandon': abandon
                })

                send_message(rcon, event)
                try:
                    send_discord_alert(event)
                except Exception as e:
                    logger.error("Discord alert failed for '%s': %s", name, str(e))

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

logger.info("\n-------------------------------------------------------------------------------\n%s started\n-------------------------------------------------------------------------------", config.BOT_NAME)

if __name__ == "__main__":
    track_role_changes()

"""
watch_roles.py

A plugin for HLL CRCON (https://github.com/MarechJ/hll_rcon_tool)
that inform players about the role they took.

Source : https://github.com/ElGuillermo

Feel free to use/modify/distribute, as long as you keep this note in your code
"""

from datetime import datetime, timedelta
import logging
import time
import discord  # Discord feature
from rcon.rcon import Rcon
from rcon.settings import SERVER_INFO
from rcon.utils import get_server_number  # Discord feature
import custom_tools.common_functions as common_functions  # Discord feature
import custom_tools.watch_roles_config as config


def is_support_needed(
    detailed_players: dict,
) -> tuple:
    """
    Do we need to suggest support roles in allies and/or axis ?
    Returns a tuple (allies_supports_needed: bool, axis_supports_needed: bool)
    """
    # Count players in each team (infantry officers/supports)
    allies_infantry_officer_count = 0
    allies_support_count = 0
    axis_infantry_officer_count = 0
    axis_support_count = 0

    for player in detailed_players["players"].values():

        if player.get('team') == "allies":
            if player.get('role') == "officer":
                allies_infantry_officer_count += 1
            if player.get('role') == "support":
                allies_support_count += 1

        elif player.get('team') == "axis":
            if player.get('role') == "officer":
                axis_infantry_officer_count += 1
            if player.get('role') == "support":
                axis_support_count += 1

    # Compare required and current supports
    allies_supports_required = config.REQUIRED_SUPPORTS.get(allies_infantry_officer_count, 0)
    allies_supports_needed = allies_support_count < allies_supports_required
    axis_supports_required = config.REQUIRED_SUPPORTS.get(axis_infantry_officer_count, 0)
    axis_supports_needed = axis_support_count < axis_supports_required

    return allies_supports_needed, axis_supports_needed


def clean_old_entries(
    previous_player_data: dict,
    clean_delay:int = config.AUTO_CLEANING_TIME
) -> dict:
    """
    Clean old entries (gone players)
    Returns the cleaned previous_player_data dict
    """
    # Every entry older than this datetime will get deleted
    clean_limit = datetime.now() - timedelta(minutes=clean_delay)
    to_delete = []

    for player_id, player_data in previous_player_data.items():
        last_role_change = player_data.get('last_role_change', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        try:
            last_role_change_datetime = datetime.strptime(last_role_change, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            continue

        if last_role_change_datetime < clean_limit:
            logger.info(
                "♻️ '%s' (%s) - not watched anymore",
                player_data.get('name', "(unknown)"),
                player_data.get('level', "(unknown)"),
            )
            to_delete.append(player_id)

    for player_id in to_delete:
        previous_player_data.pop(player_id, None)

    return previous_player_data


def send_message(
    rcon: Rcon,
    message_data: tuple
):
    """
    Sends a message to the player to remind them of their responsibilities
    as an officer or to give them advice on their role.
    """
    (
        player_id,
        player_name,
        actual_level,
        _,
        _,
        _,
        actual_team,
        actual_unit_name,
        actual_role,
        nb_abandons,
        last_abandon,
        allies_supports_needed,
        axis_supports_needed
    ) = message_data

    message = ""

    # Define if the player has abandoned its squad/team since the latest loop
    last_abandon_dt = datetime.strptime(last_abandon, '%Y-%m-%d %H:%M:%S')
    abandon_delay = datetime.now() - last_abandon_dt
    if (
        abandon_delay < timedelta(seconds=config.WATCH_INTERVAL)
        and (
            config.ALWAYS_WARN_BAD_OFFICERS
            or actual_level < config.MIN_IMMUNE_LEVEL
        )
    ):
        message += config.ADVICE_MESSAGE_TEXT.get("officer_quitter")
        message += f"{config.ADVICE_MESSAGE_TEXT.get("nb_squads_abandoned")} : {nb_abandons}"

    # Suggest support roles
    if (
        (
            (actual_team == "allies" and allies_supports_needed)
            or (actual_team == "axis" and axis_supports_needed)
        )
        and actual_role in config.SUPPORT_CANDIDATES
        and (
            config.ALWAYS_SUGGEST_SUPPORT
            or actual_level < config.MIN_IMMUNE_LEVEL
        )
    ):
        message += config.ADVICE_MESSAGE_TEXT.get("support_needed")

    # Role guidance
    if actual_level < config.MIN_IMMUNE_LEVEL and actual_unit_name is not None:
        message += config.ADVICE_MESSAGE_TEXT.get(actual_role)

    # Send message
    if message != "":
        try:
            rcon.message_player(
                player_id=player_id,
                message=message,
                by=config.BOT_NAME
            )
        except Exception as error:
            logger.error("!!! Error while sending message to '%s' : %s", player_name, str(error))


def send_discord_alert(
    message_data: tuple
):
    """
    Sends a discord alert to the server admins
    """
    (
        player_id,
        player_name,
        actual_level,
        previous_team,
        previous_unit_name,
        previous_role,
        actual_team,
        actual_unit_name,
        actual_role,
        nb_abandons,
        last_abandon,
        _,
        _
    ) = message_data

    # Check if enabled on this server
    server_number = int(get_server_number())
    if not config.SERVER_CONFIG[server_number - 1][1]:
        return

    # Define if the player has abandoned its squad/team since the latest loop
    last_abandon_dt = datetime.strptime(last_abandon, '%Y-%m-%d %H:%M:%S')
    abandon_delay = datetime.now() - last_abandon_dt
    if not (
        abandon_delay < timedelta(seconds=config.WATCH_INTERVAL)
    ):
        return

    discord_webhook = config.SERVER_CONFIG[server_number - 1][0]

    # message
    embed_desc_txt = (
        f"{config.ADVICE_MESSAGE_TEXT.get("nb_squads_abandoned")} : {nb_abandons}\n"
        f"Level : {actual_level}\n"
        f"{previous_team}/{previous_unit_name}/{previous_role} ➡️ {actual_team}/{actual_unit_name}/{actual_role}"
    )

    # Create and send discord embed
    webhook = discord.SyncWebhook.from_url(discord_webhook)
    embed = discord.Embed(
        title=player_name,
        url=common_functions.get_external_profile_url(player_id, player_name),
        description=embed_desc_txt,
        color=0xffffff
    )
    embed.set_author(
        name=config.BOT_NAME,
        url=common_functions.DISCORD_EMBED_AUTHOR_URL,
        icon_url=common_functions.DISCORD_EMBED_AUTHOR_ICON_URL
    )
    embed.set_thumbnail(url=common_functions.get_avatar_url(player_id))

    common_functions.discord_embed_send(embed, webhook)


def track_role_changes():
    """
    Observes the players role changes (infinite loop)
    """
    rcon = Rcon(SERVER_INFO)
    previous_player_data = {}

    while True:  # infinite loop

        # Get players infos
        try:
            detailed_players = rcon.get_detailed_players()
        except Exception as error:
            logger.error("get_detailed_players() failed : %s", str(error))
            time.sleep(config.WATCH_INTERVAL)
            continue

        # Are supports needed ?
        allies_supports_needed, axis_supports_needed = is_support_needed(detailed_players)

        # Clean old entries
        previous_player_data = clean_old_entries(previous_player_data)

        for player in detailed_players["players"].values():
            player_id = player.get('player_id')
            player_name = player.get('name')
            actual_level = player.get('level')
            actual_team = player.get('team')
            actual_unit_name = player.get('unit_name')
            actual_role = player.get('role')

            # New player
            if player_id not in previous_player_data:
                previous_player_data[player_id] = {
                    'last_role_change': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'player_id': player_id,
                    'name': player_name,
                    'level': actual_level,
                    'team': actual_team,
                    'unit_name': actual_unit_name,
                    'role': actual_role,
                    'nb_abandons': 0,
                    'last_abandon': None
                }
                logger.info(
                    "🆕 '%s' (%s) - %s/%s/%s",
                    player_name, actual_level, actual_team, actual_unit_name, actual_role
                )
                continue  # We'll evaluate changes on next loop

            # The player levelled up
            previous_level = previous_player_data.get(player_id, {}).get('level', actual_level)

            if previous_level < actual_level:
                previous_player_data.setdefault(player_id, {})['level'] = actual_level
                # logger.info("⬆️ '%s' (level %s ➡️ %s)", player_name, previous_level, actual_level)

            # The player changed team/unit/role
            previous_team = previous_player_data.get(player_id, {}).get('team', actual_team)
            previous_unit_name = previous_player_data.get(player_id, {}).get('unit_name', actual_unit_name)
            previous_role = previous_player_data.get(player_id, {}).get('role', actual_role)
            if (
                previous_team != actual_team
                or previous_unit_name != actual_unit_name
                or previous_role != actual_role
            ):
                # Update previous_player_data dict
                last_role_change = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                previous_player_data.setdefault(player_id, {})['last_role_change'] = last_role_change
                previous_player_data.setdefault(player_id, {})['team'] = actual_team
                previous_player_data.setdefault(player_id, {})['unit_name'] = actual_unit_name
                previous_player_data.setdefault(player_id, {})['role'] = actual_role

                common_logger_message = f"'{player_name}' ({actual_level}) - {previous_team}/{previous_unit_name}/{previous_role} ➡️ {actual_team}/{actual_unit_name}/{actual_role}"

                nb_abandons = previous_player_data.get(player_id, {}).get('nb_abandons', 0)

                # He (already) was an officer before (so he abandoned his former squad/team)
                if previous_role in config.OFFICERS:
                    # Update previous_player_data dict
                    nb_abandons += 1
                    previous_player_data.setdefault(player_id, {})['nb_abandons'] = nb_abandons
                    last_abandon = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    previous_player_data.setdefault(player_id, {})['last_abandon'] = last_abandon
                    # Log
                    logger.info("🟥x%s " + common_logger_message, nb_abandons)

                # He wasn't officer
                elif previous_role not in config.OFFICERS:
                    # Log
                    logger.info("🟩 " + common_logger_message)

                # Prepare data for messages and Discord alerts
                message_data = (
                    player_id,
                    player_name,
                    actual_level,
                    previous_team,
                    previous_unit_name,
                    previous_role,
                    actual_team,
                    actual_unit_name,
                    actual_role,
                    nb_abandons,
                    previous_player_data.get(player_id, {}).get('last_abandon', None),
                    allies_supports_needed,
                    axis_supports_needed
                )

                # Send messages and Discord alerts
                send_message(rcon, message_data)
                send_discord_alert(message_data)

        time.sleep(config.WATCH_INTERVAL)


# Start logger
logger = logging.getLogger('rcon')

logger.info(
    "\n-------------------------------------------------------------------------------\n"
    "%s started\n"
    "-------------------------------------------------------------------------------",
    config.BOT_NAME
)

# Start role tracking (infinite loop)
track_role_changes()

"""
watch_roles.py

A plugin for HLL CRCON (https://github.com/MarechJ/hll_rcon_tool)
that inform players about the role they took.

Source : https://github.com/ElGuillermo

Feel free to use/modify/distribute, as long as you keep this note in your code
"""

import logging
import time
import discord  # Discord feature
from rcon.rcon import Rcon
from rcon.settings import SERVER_INFO
from rcon.utils import get_server_number  # Discord feature
import custom_tools.common_functions as common_functions  # Discord feature
import custom_tools.watch_roles_config as config


def send_message(
    rcon: Rcon,
    player_id: str,
    player_name: str,
    player_level: int,
    old_team: str,
    old_unit_name: str,
    old_role: str,
    new_team: str,
    new_unit_name: str,
    new_role: str,
    allies_supports_needed: bool = False,
    axis_supports_needed: bool = False,
    note: str = None
):
    """
    Sends a message to the player to remind them of their responsibilities
    as an officer or to give them advice on their role.
    """

    message = ""

    # Warn quitting/shifting officers
    if (
        note == "officer_quitter"
        and (
            config.ALWAYS_WARN_BAD_OFFICERS
            or player_level < config.MIN_IMMUNE_LEVEL
        )
    ):
        message += config.ADVICE_MESSAGE_TEXT.get("officer_quitter")

    # Suggest support roles
    if (
        (
            (new_team == "allies" and allies_supports_needed)
            or (new_team == "axis" and axis_supports_needed)
        )
        and new_role in config.SUPPORT_CANDIDATES
        and (
            config.ALWAYS_SUGGEST_SUPPORT
            or player_level < config.MIN_IMMUNE_LEVEL
        )
    ):
        message += config.ADVICE_MESSAGE_TEXT.get("support_needed")

    # Role guidance
    if player_level < config.MIN_IMMUNE_LEVEL and new_unit_name is not None:
        message += config.ADVICE_MESSAGE_TEXT.get(new_role)

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
    player_id: str,
    player_name: str,
    player_level: int,
    old_team: str,
    old_unit_name: str,
    old_role: str,
    new_team: str,
    new_unit_name: str,
    new_role: str,
    allies_supports_needed: bool = False,
    axis_supports_needed: bool = False,
    note: str = None
):
    """
    Sends a discord alert to the server admins
    """
    # Check if enabled on this server
    server_number = int(get_server_number())
    if not config.SERVER_CONFIG[server_number - 1][1]:
        return

    discord_webhook = config.SERVER_CONFIG[server_number - 1][0]

    # message
    embed_desc_txt = (
        f"Level: {player_level}\n"
        f"{old_team}/{old_unit_name}/{old_role} ➡️ {new_team}/{new_unit_name}/{new_role}"
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

    # Make previous dicts global
    global previous_team
    global previous_unit_name
    global previous_role

    while True:  # infinite loop

        # Get players infos
        try:
            detailed_players = rcon.get_detailed_players()
        except Exception as error:
            logger.error("get_detailed_players() failed : %s", str(error))
            time.sleep(config.WATCH_INTERVAL)
            continue

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

        # Do we need to suggest support roles ?
        allies_supports_required = config.REQUIRED_SUPPORTS.get(allies_infantry_officer_count, 4)   # defaults to 4
        allies_supports_needed = allies_support_count < allies_supports_required  # True/False
        axis_supports_required = config.REQUIRED_SUPPORTS.get(axis_infantry_officer_count, 4)
        axis_supports_needed = axis_support_count < axis_supports_required

        # Reset current dicts
        current_team = {}
        current_unit_name = {}
        current_role = {}

        for player in detailed_players["players"].values():

            player_id = player.get('player_id')
            player_name = player.get('name')
            player_level = player.get('level')

            # Get values from previous dicts
            old_team = previous_team.get(player_id)
            old_unit_name = previous_unit_name.get(player_id)
            old_role = previous_role.get(player_id)

            # Get new values
            new_team = player.get('team')
            new_unit_name = player.get('unit_name')
            new_role = player.get('role')

            # Populate current dicts
            current_team[player_id] = new_team
            current_unit_name[player_id] = new_unit_name
            current_role[player_id] = new_role

            # logs, messages and Discord alerts tuples
            logger_infos = (
                player_name,
                old_team, old_unit_name, old_role,
                new_team, new_unit_name, new_role
            )
            message_infos = (
                player_id, player_name, player_level,
                old_team, old_unit_name, old_role,
                new_team, new_unit_name, new_role,
                allies_supports_needed, axis_supports_needed
            )

            # The player changed team/unit/role
            if (
                old_team != new_team
                or old_unit_name != new_unit_name
                or old_role != new_role
            ):
                # He (already) was an officer before
                if old_role in config.OFFICERS:
                    logger.info("🟥 '%s' - %s/%s/%s ➡️ %s/%s/%s", *logger_infos)
                    send_message(rcon, *message_infos, "officer_quitter")
                    if config.USE_DISCORD:
                        send_discord_alert(*message_infos, "officer_quitter")

                # He wasn't officer
                elif old_role not in config.OFFICERS:
                    logger.info("🟩 '%s' - %s/%s/%s ➡️ %s/%s/%s", *logger_infos)
                    send_message(rcon, *message_infos)

        # Update previous dicts
        previous_team = current_team
        previous_unit_name = current_unit_name
        previous_role = current_role

        time.sleep(config.WATCH_INTERVAL)


# Start logger
logger = logging.getLogger('rcon')

logger.info(
    "\n-------------------------------------------------------------------------------\n"
    "%s started\n"
    "-------------------------------------------------------------------------------",
    config.BOT_NAME
)

# Initialize previous dicts
previous_team = {}
previous_unit_name = {}
previous_role = {}

# Start role tracking (infinite loop)
track_role_changes()

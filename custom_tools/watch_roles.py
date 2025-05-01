"""
watch_roles.py

A plugin for HLL CRCON (https://github.com/MarechJ/hll_rcon_tool)
that inform players about the role they took.

Source : https://github.com/ElGuillermo

Feel free to use/modify/distribute, as long as you keep this note in your code
"""

import logging
import time
from rcon.rcon import Rcon
from rcon.settings import SERVER_INFO
import custom_tools.watch_roles_config as config


def send_message(
    rcon: Rcon,
    player_id: str,
    player_name: str,
    player_role: str,
    player_level: int,
    player_team: str,
    player_unit_name: str,
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
    if config.ALWAYS_WARN_BAD_OFFICERS or player_level < config.MIN_IMMUNE_LEVEL:
        if note == "officer_quitter":
            message += config.ADVICE_MESSAGE_TEXT.get("officer_quitter")
        elif note == "officer_shifter":
            message += config.ADVICE_MESSAGE_TEXT.get("officer_shifter")

    # Suggest support roles
    if (
        (config.ALWAYS_SUGGEST_SUPPORT or player_level < config.MIN_IMMUNE_LEVEL)
        and player_role in config.SUPPORT_CANDIDATES
        and (
            (player_team == "allies" and allies_supports_needed)
            or (player_team == "axis" and axis_supports_needed)
        )
    ):
        message += config.ADVICE_MESSAGE_TEXT.get("support_needed")

    # Role guidance
    if player_level < config.MIN_IMMUNE_LEVEL and player_unit_name is not None:
        message += config.ADVICE_MESSAGE_TEXT.get(player_role)

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
            pass


def track_role_changes():
    """
    Observes the players role changes (infinite loop)
    """
    rcon = Rcon(SERVER_INFO)

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

        # Count players in each team (total players/officers/supports)
        # axis_count = 0
        # allies_count = 0
        allies_infantry_officer_count = 0
        allies_support_count = 0
        axis_infantry_officer_count = 0
        axis_support_count = 0
        for player in detailed_players["players"].values():

            if player.get('team') == "allies":
                # allies_count += 1
                if player.get('role') == "officer":
                    allies_infantry_officer_count += 1
                if player.get('role') == "support":
                    allies_support_count += 1

            elif player.get('team') == "axis":
                # axis_count += 1
                if player.get('role') == "officer":
                    axis_infantry_officer_count += 1
                if player.get('role') == "support":
                    axis_support_count += 1

        # Do we need to suggest support roles ?
        allies_supports_required = config.REQUIRED_SUPPORTS.get(allies_infantry_officer_count, 6)   # default to 6 if squads > 11
        allies_supports_needed = allies_support_count < allies_supports_required  # True if we need more supports
        axis_supports_required = config.REQUIRED_SUPPORTS.get(axis_infantry_officer_count, 6)
        axis_supports_needed = axis_support_count < axis_supports_required

        # Initialize/reset dicts
        current_team = {}
        current_unit_name = {}
        current_role = {}

        for player in detailed_players["players"].values():

            player_id = player.get('player_id')
            player_name = player.get('name')
            player_level = player.get('level')

            old_team = previous_team.get(player_id)
            old_unit_name = previous_unit_name.get(player_id)
            old_role = previous_role.get(player_id)

            new_team = player.get('team')
            new_unit_name = player.get('unit_name')
            new_role = player.get('role')

            current_team[player_id] = new_team
            current_unit_name[player_id] = new_unit_name
            current_role[player_id] = new_role

            logger_infos = (player_name, old_team, old_unit_name, old_role, new_team, new_unit_name, new_role)
            message_infos = (player_id, player_name, new_role, player_level, new_team, new_unit_name, allies_supports_needed, axis_supports_needed)

            # The player isn't in a team/squad (anymore)
            if new_unit_name == None:

                # He wasn't officer before
                if old_role not in config.OFFICERS:
                    pass

                # He was officer before (in another team/unit)
                elif old_role in config.OFFICERS:
                    logger.info("(officer -> unassigned) '%s' - %s/%s/%s --> %s/%s/%s", *logger_infos)
                    send_message(rcon, *message_infos, "officer_quitter")
                    # TODO Discord alert

            # The player took an officer role
            elif new_role in config.OFFICERS:

                # He wasn't officer before
                if old_role not in config.OFFICERS:
                    logger.info("(soldier -> officer) '%s' - %s/%s/%s --> %s/%s/%s", *logger_infos)
                    send_message(rcon, *message_infos)

                # He was officer before (in another team/unit)
                elif (
                    old_role in config.OFFICERS
                    and (old_team != new_team or old_unit_name != new_unit_name)
                ):
                    logger.info("(officer -> officer) '%s' - %s/%s/%s --> %s/%s/%s", *logger_infos)
                    send_message(rcon, *message_infos, "officer_shifter")
                    # TODO Discord alert

            # The player took a non-officer role
            elif new_role not in config.OFFICERS:

                # He wasn't officer before
                if old_role not in config.OFFICERS:
                    logger.info("(soldier -> soldier) '%s' - %s/%s/%s --> %s/%s/%s", *logger_infos)
                    send_message(rcon, *message_infos)

                # He was officer before
                elif old_role in config.OFFICERS:
                    logger.info("(officer -> soldier) '%s' - %s/%s/%s --> %s/%s/%s", *logger_infos)
                    send_message(rcon, *message_infos, "officer_quitter")
                    # TODO Discord alert

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

# Initialize dicts
previous_team = {}
previous_unit_name = {}
previous_role = {}

# Start role tracking (infinite loop)
track_role_changes()

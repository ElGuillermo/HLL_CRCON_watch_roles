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
    note: str = None
):
    """
    Envoie un message au joueur pour lui rappeler ses responsabilités
    en tant qu'officier ou pour lui donner des conseils sur son rôle.
    """

    message = ""
    if note == "officer_quitter":
        message += config.ADVICE_MESSAGE_TEXT.get("officer_quitter")
    elif note == "officer_shifter":
        message += config.ADVICE_MESSAGE_TEXT.get("officer_shifter")

    message += config.ADVICE_MESSAGE_TEXT.get(player_role)

    try:
        rcon.message_player(
            player_id=player_id,
            message=message,
            by=config.BOT_NAME
        )
    except Exception as error:
        logger.error(
            "%s !!! Error while sending message : %s",
            player_name,
            str(error)
        )
        pass

def track_role_changes():
    """
    Fonction pour suivre les changements de rôle des joueurs
    et envoyer un message à ceux qui prennent un rôle d'officier.
    """
    rcon = Rcon(SERVER_INFO)

    global previous_teams
    global previous_units
    global previous_roles

    while True:  # boucle infinie

        try:
            detailed_players = rcon.get_detailed_players()
        except Exception as error:
            logger.error(
                "Error while getting detailed players : %s",
                str(error)
            )
            time.sleep(config.WATCH_INTERVAL)
            continue

        current_teams = {}
        current_units = {}
        current_roles = {}

        for player in detailed_players["players"].values():
            player_id = player.get('player_id')
            player_name = player.get('name')

            old_team = previous_teams.get(player_id)
            new_team = player.get('team')
            current_teams[player_id] = new_team

            old_unit = previous_units.get(player_id)
            new_unit = player.get('unit_name')
            current_units[player_id] = new_unit

            old_role = previous_roles.get(player_id)
            new_role = player.get('role')
            current_roles[player_id] = new_role

            # The player was playing soldier and took on the role of an officer
            if (
                old_role not in config.OFFICERS
                and new_role in config.OFFICERS
            ):
                logger.info(
                    "%s (new officer) %s / %s / %s --> %s / %s / %s",
                    player_name,
                    old_team, old_unit, old_role,
                    new_team, new_unit, new_role
                )
                send_message(rcon, player_id, player_name, new_role, "officer_new")

            # The player moved from an officer role to a soldier role
            elif (
                old_role in config.OFFICERS
                and new_role not in config.OFFICERS
            ):
                logger.info(
                    "%s (quitting officer) %s / %s / %s --> %s / %s / %s",
                    player_name,
                    old_team, old_unit, old_role,
                    new_team, new_unit, new_role
                )

                send_message(rcon, player_id, player_name, new_role, "officer_quitter")
                # TODO Alerte Discord

            # The player has taken another officer role in another team/unit
            elif (
                old_role in config.OFFICERS
                and new_role in config.OFFICERS
                and (
                    old_team != new_team
                    or old_unit != new_unit
                )
            ):
                logger.info(
                    "%s (shifting officer) %s / %s / %s --> %s / %s / %s",
                    player_name,
                    old_team, old_unit, old_role,
                    new_team, new_unit, new_role
                )

                send_message(rcon, player_id, player_name, new_role, "officer_shifter")
                # TODO Alerte Discord

            # The player changed role (non-officer -> non-officer)
            elif (
                old_role not in config.OFFICERS
                and new_role not in config.OFFICERS
            ):
                logger.info(
                    "%s (soldier) %s / %s / %s --> %s / %s / %s",
                    player_name,
                    old_team, old_unit, old_role,
                    new_team, new_unit, new_role
                )

                send_message(rcon, player_id, player_name, new_role)

        previous_teams = current_teams
        previous_units = current_units
        previous_roles = current_roles

        time.sleep(config.WATCH_INTERVAL)


logger = logging.getLogger('rcon')

logger.info(
    "\n-------------------------------------------------------------------------------\n"
    "%s started\n"
    "-------------------------------------------------------------------------------",
    config.BOT_NAME
)

previous_teams = {}
previous_units = {}
previous_roles = {}

track_role_changes()

"""
watch_roles_config.py

A plugin for HLL CRCON (https://github.com/MarechJ/hll_rcon_tool)
that inform players about the role they took.

Source : https://github.com/ElGuillermo

Feel free to use/modify/distribute, as long as you keep this note in your code
"""

# The bot will check the players every X seconds
# Default : 60
WATCH_INTERVAL = 60

# The texts below are displayed to the player when they take a role.
# You can modify them to your liking.
# Check for the next setting to set the language you want to use.
# French version
ADVICE_MESSAGE_TEXT_FR = {
    "armycommander": "Tu as choisi de jouer\n- Commandant -\n----------\nTu DOIS communiquer en vocal.\nSi tu ne peux/veux pas :\ncède ta place !\n----------\nDemande aux officiers de poser des garnies\net aux ingénieurs de construire des nodes dès qu'ils le peuvent.",
    "officer": "Tu as choisi de jouer\n- Squad Leader (SL) -\n----------\nTu DOIS communiquer en vocal.\nSi tu ne peux/veux pas :\ncède ta place !\n----------\nPose des garnies à 200m des points et ton AP à 100m.\nInforme le commandant de tes actions et exécute ses ordres.",
    "officer_quitter": "Tu as quitté ton poste d'officier,\nabandonnant tes hommes.\nCe comportement n'est pas acceptable.\nLes admins ont été alertés.\n----------\n",
    "officer_shifter": "Tu as quitté ton poste d'officier,\nabandonnant tes hommes.\nCe comportement n'est pas acceptable.\nLes admins ont été alertés.\n----------\n",
    "antitank": "Tu as choisi de jouer\n- Antitank -\nRappelle-toi que le point faible des blindés est à l'arrière.",
    "automaticrifleman": "Tu as choisi de jouer\nfusilier auto -\nSécurise l'avancée de tes camarades\nProtège le SL, le soutien, les garnies et les APs.",
    "assault": "Tu as choisi de jouer\n- Assaut -\nC'est à toi d'ouvrir le front.\nInforme ton officier des ennemis que tu rencontres.",
    "heavymachinegunner": "Tu as choisi de jouer\n- Mitrailleur lourd -\nPoste-toi en arrière ou en hauteur pour couvrir tes camarades.",
    "support": "Tu as choisi de jouer\n- Soutien -\nAide le SL à avancer et pose ta caisse de supply quand une garnie peut être construite.",
    "sniper": "Tu as choisi de jouer\n- Sniper -\nFaufile-toi dans les lignes ennemies,\nélimine les cibles prioritaires\ndétruis les nodes\net informe ton SL de ce que tu vois.",
    "spotter": "Tu as choisi de jouer\n- SL reco -\n----------\nTu DOIS communiquer en vocal.\nSi tu ne peux/veux pas :\ncède ta place !\n----------\nFaufile-toi dans les lignes ennemies,\nélimine les cibles prioritaires\ndétruis les nodes\net informe le commandant de ce que tu vois",
    "rifleman": "Tu as choisi de jouer\n- Fusilier -\nC'est un rôle idéal pour débuter,\nchoisis-en un autre quand tu penses pouvoir l'assumer.",
    "crewman": "Tu as choisi de jouer\n- Tankiste -\nUne équipe de tankistes est toujours plus efficace quand elle communique.\nInforme ton chef de char de ce que tu vois.",
    "tankcommander": "Tu as choisi de jouer\n- Chef de char -\n----------\nTu DOIS communiquer en vocal.\nSi tu ne peux/veux pas :\ncède ta place !\n----------\nUne équipe de tankistes est toujours plus efficace quand elle communique.\nInforme ton commandant de ce que tu vois.",
    "engineer": "Tu as choisi de jouer\n- Ingénieur -\nTa mission première est de t'assurer que le commandant dispose de nodes.\nTu peux aussi fortifier les points et réparer les chars.",
    "medic": "Tu as choisi de jouer\n- Médecin -\nReste en arrière et soigne les blessés.\nAnnonce-toi en vocal de proximité pour éviter qu'ils se redéploient avant ton arrivée."
}

# English version
ADVICE_MESSAGE_TEXT_EN = {
    "armycommander": "You chose to play\n- Commander -\n----------\nYou MUST communicate via voice chat.\nIf you can't or won't: give up your spot!\n----------\nAsk officers to place garrisons and engineers to build nodes as soon as possible.",
    "officer": "You chose to play\n- Squad Leader (SL) -\n----------\nYou MUST communicate via voice chat.\nIf you can't or won't: give up your spot!\n----------\nPlace garrisons 200m from objectives and your OP 100m away.\nInform the commander of your actions and follow orders.",
    "officer_quitter": "You have left your officer role,\nabandoning your men.\nThis behavior is unacceptable.\nAdmins have been alerted.\n----------\n",
    "officer_shifter": "You have left your officer role,\nabandoning your men.\nThis behavior is unacceptable.\nAdmins have been alerted.\n----------\n",
    "antitank": "You chose to play\n- Anti-tank -\nRemember, the weak spot of armored vehicles is at the rear.",
    "automaticrifleman": "You chose to play\n- Automatic Rifleman -\nSecure your comrades' advance.\nProtect the SL, the support, garrisons, and OPs.",
    "assault": "You chose to play\n- Assault -\nIt's your job to lead the charge.\nInform your officer about enemies you encounter.",
    "heavymachinegunner": "You chose to play\n- Heavy Machine Gunner -\nPosition yourself in the rear or on high ground to cover your teammates.",
    "support": "You chose to play\n- Support -\nHelp the SL move forward and drop your supply crate when a garrison can be built.",
    "sniper": "You chose to play\n- Sniper -\nSneak into enemy lines,\neliminate priority targets,\ndestroy nodes,\nand report what you see to your SL.",
    "spotter": "You chose to play\n- Recon SL -\n----------\nYou MUST communicate via voice chat.\nIf you can't or won't: give up your spot!\n----------\nSneak into enemy lines,\neliminate priority targets,\ndestroy nodes,\nand report to the commander what you see.",
    "rifleman": "You chose to play\n- Rifleman -\nIt's an ideal role for beginners.\nPick a different one when you feel ready to take on more responsibility.",
    "crewman": "You chose to play\n- Tank Crew -\nA tank crew is always more effective when communicating.\nInform your tank commander of what you see.",
    "tankcommander": "You chose to play\n- Tank Commander -\n----------\nYou MUST communicate via voice chat.\nIf you can't or won't: give up your spot!\n----------\nA tank crew is always more effective when communicating.\nInform your commander of what you see.",
    "engineer": "You chose to play\n- Engineer -\nYour main mission is to ensure the commander has nodes.\nYou can also fortify points and repair tanks.",
    "medic": "You chose to play\n- Medic -\nStay in the rear and heal the wounded.\nAnnounce yourself using proximity voice chat so they don’t redeploy before you arrive."
}

# Set the language for the advice messages texts
# (Uncomment the desired language)
# ADVICE_MESSAGE_TEXT = ADVICE_MESSAGE_TEXT_FR
ADVICE_MESSAGE_TEXT = ADVICE_MESSAGE_TEXT_EN

# Officers roles (DO NOT edit this)
OFFICERS = {'armycommander', 'officer', 'tankcommander', 'spotter'}

# Bot name that will be reported in logs (no need to edit this)
BOT_NAME = "CRCON_watch_roles"

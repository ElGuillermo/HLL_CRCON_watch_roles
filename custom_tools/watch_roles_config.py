"""
watch_roles_config.py

A plugin for HLL CRCON (https://github.com/MarechJ/hll_rcon_tool)
that inform players about the role they took.

Source : https://github.com/ElGuillermo

Feel free to use/modify/distribute, as long as you keep this note in your code
"""

BOT_NAME = "CRCON_watch_roles"
WATCH_INTERVAL = 60

OFFICERS = {'armycommander', 'officer', 'tankcommander', 'spotter'}

ADVICE_MESSAGE_TEXT = {
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

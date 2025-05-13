"""
watch_roles_config.py

A plugin for HLL CRCON (https://github.com/MarechJ/hll_rcon_tool) that :
- inform players about the role they took
- warns quitting officers
- suggests support roles when needed
- (optionally) sends Discord alerts.

Author: https://github.com/ElGuillermo
License: MIT-like (free use/modify/distribute with attribution)
"""

# The bot will check the players every X seconds
# Any value lower than 30 will be ignored and defaulted to 30
# Any value higher than 60 will be ignored and defaulted to 60
# Default : 30
WATCH_INTERVAL = 30

# Players who have reached level X won't receive role guidance
# Disable : 0 (level-based messages won't be sent)
# Default : 50 (players level 1-49 will get messages)
MIN_IMMUNE_LEVEL = 50

# Always warn quitting/shifting officers (whatever their level)
# (they'll always be warned if their level is below MIN_IMMUNE_LEVEL)
# Default : True
ALWAYS_WARN_BAD_OFFICERS = True

# Should we suggest players about taking support role ?
# Define the number of supports that need to be taken as is :
# {1:1, 2:1, 3:2} means "1 infantry squad: 1 support, 2 infantry squads: 1 support, 3 infantry squads: 2 supports"
REQUIRED_SUPPORTS = {0:0, 1:1, 2:1, 3:2, 4:2, 5:3, 6:3, 7:4, 8:4, 9:5, 10:5, 11:6, 12:6}

# Always suggest players about taking support role (whatever their level)
# (they'll always be informed if their level is below MIN_IMMUNE_LEVEL)
# Default : True
ALWAYS_SUGGEST_SUPPORT = True

# Dedicated Discord's channel webhook
# (the script can work without any Discord output)
# ["https://discord.com/api/webhooks/...", True] = enabled
# ["https://discord.com/api/webhooks/...", False] = disabled
SERVER_CONFIG = [
    ["https://discord.com/api/webhooks/1367486870203793438/5whZdEnMCZb4jkyIZ_0HfjEMK8w7ohRatxfOeYxECD22GbLu_PYIUgwLE7qubBfx8ZFC", True],  # Server 1
    ["https://discord.com/api/webhooks/...", False],  # Server 2
    ["https://discord.com/api/webhooks/...", False],  # Server 3
    ["https://discord.com/api/webhooks/...", False],  # Server 4
    ["https://discord.com/api/webhooks/...", False],  # Server 5
    ["https://discord.com/api/webhooks/...", False],  # Server 6
    ["https://discord.com/api/webhooks/...", False],  # Server 7
    ["https://discord.com/api/webhooks/...", False],  # Server 8
    ["https://discord.com/api/webhooks/...", False],  # Server 9
    ["https://discord.com/api/webhooks/...", False]  # Server 10
]


# The texts below are displayed to the player.
# (Check for the next setting to set the language you want to use)

# French
MESSAGE_TEXT_FR = {
    "officer_quitter": "Tu as quitté ton poste d'officier,\nabandonnant tes hommes.\nCe comportement n'est pas acceptable.\n",
    "nb_squads_abandoned": "Nombre de squads abandonnées",
    "support_needed": "Ton équipe manque de Soutiens !\nEn jouant ce rôle, tu pourrais aider ton SL à poser des garnies !\n----------\n",
    # Officers
    "armycommander": "Tu as choisi de jouer\n- Commandant -\n\nTu DOIS communiquer en vocal.\nSi tu ne peux/veux pas :\ncède ta place !\n----------\nDemande aux officiers de poser des garnies\net aux ingénieurs de construire des nodes dès qu'ils le peuvent.",
    "officer": "Tu as choisi de jouer\n- Squad Leader (SL) -\n\nTu DOIS communiquer en vocal.\nSi tu ne peux/veux pas :\ncède ta place !\n----------\nPose des garnies à 200m des points et ton AP à 100m.\nInforme le commandant de tes actions et exécute ses ordres.",
    "tankcommander": "Tu as choisi de jouer\n- Chef de char -\n\nTu DOIS communiquer en vocal.\nSi tu ne peux/veux pas :\ncède ta place !\n----------\nUne équipe de tankistes est toujours plus efficace quand elle communique.\nInforme ton commandant de ce que tu vois.",
    "spotter": "Tu as choisi de jouer\n- SL reco -\n\nTu DOIS communiquer en vocal.\nSi tu ne peux/veux pas :\ncède ta place !\n----------\nFaufile-toi dans les lignes ennemies,\nélimine les cibles prioritaires\ndétruis les nodes\net informe le commandant de ce que tu vois",
    # Soldiers
    "antitank": "Tu as choisi de jouer\n- Antitank -\nRappelle-toi que le point faible des blindés est à l'arrière.",
    "automaticrifleman": "Tu as choisi de jouer\nfusilier auto -\nSécurise l'avancée de tes camarades\nProtège le SL, le soutien, les garnies et les APs.",
    "assault": "Tu as choisi de jouer\n- Assaut -\nC'est à toi d'ouvrir le front.\nInforme ton officier des ennemis que tu rencontres.",
    "heavymachinegunner": "Tu as choisi de jouer\n- Mitrailleur lourd -\nPoste-toi en arrière ou en hauteur pour couvrir tes camarades.",
    "support": "Tu as choisi de jouer\n- Soutien -\nAide le SL à avancer et pose ta caisse de supply quand une garnie peut être construite.",
    "rifleman": "Tu as choisi de jouer\n- Fusilier -\nC'est un rôle idéal pour débuter,\nchoisis-en un autre quand tu penses pouvoir l'assumer.",
    "engineer": "Tu as choisi de jouer\n- Ingénieur -\nTa mission première est de t'assurer que le commandant dispose de nodes.\nTu peux aussi fortifier les points et réparer les chars.",
    "medic": "Tu as choisi de jouer\n- Médecin -\nReste en arrière et soigne les blessés.\nAnnonce-toi en vocal de proximité pour éviter qu'ils se redéploient avant ton arrivée.",
    "crewman": "Tu as choisi de jouer\n- Tankiste -\nUne équipe de tankistes est toujours plus efficace quand elle communique.\nInforme ton chef de char de ce que tu vois.",
    "sniper": "Tu as choisi de jouer\n- Sniper -\nFaufile-toi dans les lignes ennemies,\nélimine les cibles prioritaires\ndétruis les nodes\net informe ton SL de ce que tu vois."
}

# English
MESSAGE_TEXT_EN = {
    "officer_quitter": "You have left your officer role,\nabandoning your men.\nThis behavior is unacceptable.\n",
    "nb_squads_abandoned": "Number of abandoned squads",
    "support_needed": "Your team needs more Supports !\nPlaying this role, you would help to build garrisons!\n----------\n",
    # Officers
    "armycommander": "You chose to play\n- Commander -\n\nYou MUST communicate via voice chat.\nIf you can't or won't: give up your spot!\n----------\nAsk officers to place garrisons and engineers to build nodes as soon as possible.",
    "officer": "You chose to play\n- Squad Leader (SL) -\n\nYou MUST communicate via voice chat.\nIf you can't or won't: give up your spot!\n----------\nPlace garrisons 200m from objectives and your OP 100m away.\nInform the commander of your actions and follow orders.",
    "tankcommander": "You chose to play\n- Tank Commander -\n\nYou MUST communicate via voice chat.\nIf you can't or won't: give up your spot!\n----------\nA tank crew is always more effective when communicating.\nInform your commander of what you see.",
    "spotter": "You chose to play\n- Recon SL -\n\nYou MUST communicate via voice chat.\nIf you can't or won't: give up your spot!\n----------\nSneak into enemy lines,\neliminate priority targets,\ndestroy nodes,\nand report to the commander what you see.",
    # Soldiers
    "antitank": "You chose to play\n- Anti-tank -\nRemember, the weak spot of armored vehicles is at the rear.",
    "automaticrifleman": "You chose to play\n- Automatic Rifleman -\nSecure your comrades' advance.\nProtect the SL, the support, garrisons, and OPs.",
    "assault": "You chose to play\n- Assault -\nIt's your job to lead the charge.\nInform your officer about enemies you encounter.",
    "heavymachinegunner": "You chose to play\n- Heavy Machine Gunner -\nPosition yourself in the rear or on high ground to cover your teammates.",
    "support": "You chose to play\n- Support -\nHelp the SL move forward and drop your supply crate when a garrison can be built.",
    "rifleman": "You chose to play\n- Rifleman -\nIt's an ideal role for beginners.\nPick a different one when you feel ready to take on more responsibility.",
    "engineer": "You chose to play\n- Engineer -\nYour main mission is to ensure the commander has nodes.\nYou can also fortify points and repair tanks.",
    "medic": "You chose to play\n- Medic -\nStay in the rear and heal the wounded.\nAnnounce yourself using proximity voice chat so they don’t redeploy before you arrive.",
    "crewman": "You chose to play\n- Tank Crew -\nA tank crew is always more effective when communicating.\nInform your tank commander of what you see.",
    "sniper": "You chose to play\n- Sniper -\nSneak into enemy lines,\neliminate priority targets,\ndestroy nodes,\nand report what you see to your SL."
}

# Spanish
MESSAGE_TEXT_ES = {
    "officer_quitter": "Has abandonado tu rol de oficial,\nabandonando a tus hombres.\nEste comportamiento es inaceptable.\n",
    "nb_squads_abandoned": "Número de escuadras abandonadas",
    "support_needed": "¡Tu equipo necesita más apoyos!\nJugando este rol ayudarías a construir guarniciones.\n----------\n",
    # Officers
    "armycommander": "Has elegido jugar como\n- Comandante -\n\nDEBES comunicarte por chat de voz.\nSi no puedes o no quieres: ¡cede tu puesto!\n----------\nPide a los oficiales que coloquen guarniciones y a los ingenieros que construyan nodos lo antes posible.",
    "officer": "Has elegido jugar como\n- Líder de escuadra (SL) -\n\nDEBES comunicarte por chat de voz.\nSi no puedes o no quieres: ¡cede tu puesto!\n----------\nColoca guarniciones a 200m de los objetivos y tu OP a 100m.\nInforma al comandante de tus acciones y sigue órdenes.",
    "tankcommander": "Has elegido jugar como\n- Comandante de tanque -\n\nDEBES comunicarte por chat de voz.\nSi no puedes o no quieres: ¡cede tu puesto!\n----------\nUna tripulación es siempre más efectiva cuando se comunica.\nInforma a tu comandante de lo que veas.",
    "spotter": "Has elegido jugar como\n- Líder de reconocimiento -\n\nDEBES comunicarte por chat de voz.\nSi no puedes o no quieres: ¡cede tu puesto!\n----------\nInfiltrate en las líneas enemigas,\nelimina objetivos prioritarios,\ndestruye nodos,\ne informa al comandante de lo que veas.",
    # Soldiers
    "antitank": "Has elegido jugar como\n- Antitanque -\nRecuerda, el punto débil de los vehículos blindados está en la parte trasera.",
    "automaticrifleman": "Has elegido jugar como\n- Fusilero automático -\nAsegura el avance de tus compañeros.\nProtege al SL, al apoyo, las guarniciones y los OPs.",
    "assault": "Has elegido jugar como\n- Asalto -\nTu trabajo es liderar la carga.\nInforma a tu oficial sobre los enemigos que encuentres.",
    "heavymachinegunner": "Has elegido jugar como\n- Ametrallador pesado -\nColócate en la retaguardia o en un terreno elevado para cubrir a tus compañeros.",
    "support": "Has elegido jugar como\n- Apoyo -\nAyuda al SL a avanzar y suelta tu caja de suministros cuando se pueda construir una guarnición.",
    "rifleman": "Has elegido jugar como\n- Fusilero -\nEs un rol ideal para principiantes.\nElige otro cuando te sientas listo para asumir más responsabilidades.",
    "engineer": "Has elegido jugar como\n- Ingeniero -\nTu misión principal es asegurar que el comandante tenga nodos.\nTambién puedes fortificar puntos y reparar tanques.",
    "medic": "Has elegido jugar como\n- Médico -\nMantente en la retaguardia y cura a los heridos.\nAnúnciate usando el chat de voz de proximidad para que no reaparezcan antes de que llegues.",
    "crewman": "Has elegido jugar como\n- Tripulación de tanque -\nUna tripulación es siempre más efectiva cuando se comunica.\nInforma a tu comandante de tanque sobre lo que veas.",
    "sniper": "Has elegido jugar como\n- Francotirador -\nInfiltrate en las líneas enemigas,\nelimina objetivos prioritarios,\ndestruye nodos,\ne informa a tu SL de lo que veas."
}

# German
MESSAGE_TEXT_DE = {
    "officer_quitter": "Du hast deine Offiziersrolle verlassen\nund deine Männer im Stich gelassen.\nDieses Verhalten ist inakzeptabel.\n",
    "nb_squads_abandoned": "Anzahl der verlassenen Trupps",
    "support_needed": "Dein Team braucht mehr Unterstützer!\nIn dieser Rolle könntest du beim Bau von Garnisonen helfen!\n----------\n",
    # Officers
    "armycommander": "Du hast gewählt zu spielen als\n- Kommandant -\n\nDU MUSST über Voice-Chat kommunizieren.\nWenn du nicht kannst oder willst: Gib deinen Platz frei!\n----------\nBitte die Offiziere, Garnisonen zu platzieren, und Ingenieure, so schnell wie möglich Versorgungsknoten zu bauen.",
    "officer": "Du hast gewählt zu spielen als\n- Truppführer (SL) -\n\nDU MUSST über Voice-Chat kommunizieren.\nWenn du nicht kannst oder willst: Gib deinen Platz frei!\n----------\nPlatziere Garnisonen 200 m vom Ziel entfernt und dein OP 100 m entfernt.\nInformiere den Kommandanten über deine Aktionen und folge seinen Befehlen.",
    "tankcommander": "Du hast gewählt zu spielen als\n- Panzerkommandant -\n\nDU MUSST über Voice-Chat kommunizieren.\nWenn du nicht kannst oder willst: Gib deinen Platz frei!\n----------\nEine Panzerbesatzung ist immer effektiver, wenn sie kommuniziert.\nInformiere deinen Kommandanten über alles, was du siehst.",
    "spotter": "Du hast gewählt zu spielen als\n- Aufklärungsführer -\n\nDU MUSST über Voice-Chat kommunizieren.\nWenn du nicht kannst oder willst: Gib deinen Platz frei!\n----------\nSchleiche dich in feindliche Linien,\nbeseitige vorrangige Ziele,\nzerstöre Knotenpunkte,\nund melde dem Kommandanten, was du siehst.",
    # Soldiers
    "antitank": "Du hast gewählt zu spielen als\n- Panzerabwehr -\nDenke daran: Die Schwachstelle gepanzerter Fahrzeuge ist das Heck.",
    "automaticrifleman": "Du hast gewählt zu spielen als\n- MG-Schütze -\nSichere den Vormarsch deiner Kameraden.\nSchütze den SL, die Unterstützer, Garnisonen und OPs.",
    "assault": "Du hast gewählt zu spielen als\n- Sturmsoldat -\nDeine Aufgabe ist es, den Angriff anzuführen.\nInformiere deinen Offizier über Feinde, denen du begegnest.",
    "heavymachinegunner": "Du hast gewählt zu spielen als\n- Schwerer MG-Schütze -\nPositioniere dich im Hinterland oder auf erhöhtem Terrain, um deine Kameraden zu decken.",
    "support": "Du hast gewählt zu spielen als\n- Unterstützer -\nHilf dem SL beim Vorrücken und wirf deine Versorgungskiste ab, wenn eine Garnison gebaut werden kann.",
    "rifleman": "Du hast gewählt zu spielen als\n- Schütze -\nDies ist eine ideale Rolle für Anfänger.\nWähle eine andere Rolle, wenn du bereit bist, mehr Verantwortung zu übernehmen.",
    "engineer": "Du hast gewählt zu spielen als\n- Ingenieur -\nDeine Hauptaufgabe ist es, dem Kommandanten Versorgungsknoten bereitzustellen.\nDu kannst auch Punkte befestigen und Panzer reparieren.",
    "medic": "Du hast gewählt zu spielen als\n- Sanitäter -\nBleib im Hinterland und heile Verwundete.\nMelde dich über den Nähe-Voice-Chat, damit sie nicht neu spawnen, bevor du ankommst.",
    "crewman": "Du hast gewählt zu spielen als\n- Panzerbesatzung -\nEine Panzerbesatzung ist immer effektiver, wenn sie kommuniziert.\nInformiere deinen Panzerkommandanten über alles, was du siehst.",
    "sniper": "Du hast gewählt zu spielen als\n- Scharfschütze -\nSchleiche dich in feindliche Linien,\nbeseitige vorrangige Ziele,\nzerstöre Knotenpunkte,\nund melde deinem SL, was du siehst."
}


# Set the language for the advice messages texts
# (Uncomment the desired language)
MESSAGE_TEXT = MESSAGE_TEXT_FR
# MESSAGE_TEXT = MESSAGE_TEXT_EN
# MESSAGE_TEXT = MESSAGE_TEXT_ES
# MESSAGE_TEXT = MESSAGE_TEXT_DE


# You shouldn't edit anything below this line
# -------------------------------------------------------------------------------------------------

# Bot name that will be displayed in logs and Discord messages
BOT_NAME = "CRCON_watch_roles"

# Autocleaning
# Unfollow players who didn't change role since X minutes
# Default : 90
AUTO_CLEANING_TIME = 90

# Limit threading concurrency
# Default : 10
SEMAPHORE_LIMIT = 10

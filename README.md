# HLL_CRCON_watch_roles

Unofficial plugin for the Hell Let Loose (HLL) [CRCON](https://github.com/MarechJ/hll_rcon_tool)

### Informs players about the role they took.

![image](https://github.com/user-attachments/assets/c7f659c9-a4c8-4b3a-b3b6-a474e18563cb) ![image](https://github.com/user-attachments/assets/6324c5da-4192-4ba4-94d4-0e1649a06f77) ![image](https://github.com/user-attachments/assets/ac838b94-7821-4a7e-aa09-296c6054bf5a) ![image](https://github.com/user-attachments/assets/ca79aaf9-c4b6-449d-ba56-e4c62352a4fa) ![image](https://github.com/user-attachments/assets/b14ca4a7-5f5e-4993-84ce-54b2e822cb1a)

---

## Features

- Give general guidance about the current role
- Display a warning to officers who abandon their squad
- Suggest infantry players to take "support" if there isn't enough of them in the team
- You can set a minimum immune level : experienced players won't get any message
- You can send reports about quitting officers in a Discord channel
- Available in 🇫🇷 French, 🇬🇧 English, 🇪🇸 Spanish and 🇩🇪 German

---

> [!IMPORTANT]
> - The shell commands given below assume your CRCON is installed in `/root/hll_rcon_tool`  
>   You may have installed your CRCON in a different folder.  
>   If so, you'll have to adapt the commands below accordingly.
>
> - Always copy/paste/execute commands :warning: one line at a time :warning:

## Installation

### 1/3 - Log into your CRCON host machine using SSH

- See [this guide](https://github.com/MarechJ/hll_rcon_tool/wiki/Troubleshooting-&-Help-‐-Common-procedures-‐-How-to-enter-a-SSH-terminal) if you need help to do it.

### 2/3 - Execute these commands in your SSH terminal

- Copy/paste/execute these commands :   
  ```shell
  cd /root/hll_rcon_tool

  wget -N https://raw.githubusercontent.com/ElGuillermo/HLL_CRCON_restart/refs/heads/main/restart.sh

  mkdir -p /root/hll_rcon_tool/custom_tools

  cd /root/hll_rcon_tool/custom_tools

  wget -N https://raw.githubusercontent.com/ElGuillermo/HLL_CRCON_custom_common_functions.py/refs/heads/main/common_functions.py

  wget -N https://raw.githubusercontent.com/ElGuillermo/HLL_CRCON_watch_roles/refs/heads/main/custom_tools/watch_roles.py

  wget -N https://raw.githubusercontent.com/ElGuillermo/HLL_CRCON_watch_roles/refs/heads/main/custom_tools/watch_roles_config.py
  ```

### 3/3 - Edit `/root/hll_rcon_tool/config/supervisord.conf`

- Add this section (wherever you want, but along with the others `[program:...]` is preferable)
  ```conf
  [program:watch_roles]
  command=python -m custom_tools.watch_roles
  environment=LOGGING_FILENAME=custom_tools_watch_roles_%(ENV_SERVER_NUMBER)s.log
  startretries=100
  startsecs=10
  autostart=true
  autorestart=true
  ```

## Configuration

### 1/2 Edit `/root/hll_rcon_tool/custom_tools/watch_roles_config.py`

- Set the parameters to fit your needs (see inner comments for guidance).

### 2/2 - Rebuild and restart CRCON Docker containers

- Copy/paste/execute these commands :  
  ```shell
  cd /root/hll_rcon_tool
  
  sh ./restart.sh
  ```

> [!TIP]
> 
>  If you don't want to use the `restart.sh` script :  
>  - Copy/paste/execute these commands :  
>  ```shell
>  cd /root/hll_rcon_tool
>
>  sudo docker compose build && sudo docker compose down && sudo docker compose up -d --remove-orphans
>  ```

---

## Maintenance

### Disable this plugin

- Revert the changes made in [Installation 3/3](#33---edit-roothll_rcon_toolconfigsupervisordconf)

--

### Modify code or settings

:exclamation: Any change to these files requires to rebuild and restart CRCON Docker containers (same procedure as in [Configuration 2/2](#22---rebuild-and-restart-crcon-docker-containers)) :
  - `/root/hll_rcon_tool/custom_tools/common_functions.py`
  - `/root/hll_rcon_tool/custom_tools/watch_roles.py`
  - `/root/hll_rcon_tool/custom_tools/watch_roles_config.py`

--

### Upgrade CRCON

This plugin requires a modification of original CRCON file(s).  
:exclamation: If any CRCON update contains a new version of this file(s), the usual CRCON upgrade procedure will **FAIL**.

To successfully upgrade your CRCON, you will need to undo the changes in :
- `/root/hll_rcon_tool/config/supervisord.conf`  

#### Undo the changes

- Copy/paste/execute these commands :  
  ```shell
  cd /root/hll_rcon_tool
  
  cp config/supervisord.conf config/supervisord.conf.backup
   
  git restore config/supervisord.conf
  ```

#### Upgrade

- Follow the official upgrade instructions given in the new CRCON version announcement.
- Don't restart CRCON Docker containers yet (don't execute `docker compose up -d`).

#### Reapply changes

- copy/paste the changes from  
  `/root/hll_rcon_tool/config/supervisord.conf.backup`  
  into  
  `/root/hll_rcon_tool/config/supervisord.conf`
- Rebuild and restart CRCON Docker containers (same procedure as in [Configuration 2/2](#22---rebuild-and-restart-crcon-docker-containers)).
- If anything works as intended, you can delete the backup file :
  - Copy/paste/execute these commands :  
    ```
    cd /root/hll_rcon_tool
  
    rm config/supervisord.conf.backup
    ```

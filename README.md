# HLL_CRCON_watch_roles
A plugin for HLL CRCON (https://github.com/MarechJ/hll_rcon_tool) that inform players about the role they took.
- Displays a warning to officers who abandon their squad
- Can suggest infantry players to take "support" if there isn't enough of them in the team
- Give general guidance about the current role
- You can set a minimum immune level : experienced players won't get any message

![image](https://github.com/user-attachments/assets/8b19af45-cbf4-4190-bf0f-2b7cae23b0cb) ![image](https://github.com/user-attachments/assets/315a93c6-9064-48df-91b3-af9c55fe181b)

## Install

> [!NOTE]
> The shell commands given below assume your CRCON is installed in `/root/hll_rcon_tool`.  
> You may have installed your CRCON in a different folder.  
>   
> If so, you'll have to adapt the commands below accordingly.

- Log into your CRCON host machine using SSH and enter these commands (one line at at time) :  

  First part  
  If you already have installed any other "custom tools" from ElGuillermo, you can skip this part.  
  (though it's always a good idea to redownload the files, as they could have been updated)
  ```shell
  cd /root/hll_rcon_tool
  wget https://raw.githubusercontent.com/ElGuillermo/HLL_CRCON_restart/refs/heads/main/restart.sh
  mkdir custom_tools
  cd custom_tools
  ```
  Second part
  ```shell
  cd /root/hll_rcon_tool/custom_tools
  wget https://raw.githubusercontent.com/ElGuillermo/HLL_CRCON_watch_roles/refs/heads/main/custom_tools/watch_roles.py
  wget https://raw.githubusercontent.com/ElGuillermo/HLL_CRCON_watch_roles/refs/heads/main/custom_tools/watch_roles_config.py
- Edit `/root/hll_rcon_tool/config/supervisord.conf` to add this bot section : 
  ```conf
  [program:watch_roles]
  command=python -m custom_tools.watch_roles
  environment=LOGGING_FILENAME=watch_roles_%(ENV_SERVER_NUMBER)s.log
  startretries=100
  startsecs=10
  autostart=true
  autorestart=true
  ```

## Config
- Edit `/root/hll_rcon_tool/custom_tools/watch_roles_config.py` and set the parameters to fit your needs.
- Restart CRCON :
  ```shell
  cd /root/hll_rcon_tool
  sh ./restart.sh
  ```

## Limitations
⚠️ Any change to these files requires a CRCON rebuild and restart (using the `restart.sh` script) to be taken in account :
- `/root/hll_rcon_tool/custom_tools/watch_roles.py`
- `/root/hll_rcon_tool/custom_tools/watch_roles_config.py`

⚠️ This plugin requires a modification of the `/root/hll_rcon_tool/config/supervisord.conf` file, which originates from the official CRCON depot.  
If any CRCON upgrade implies updating this file, the usual upgrade procedure, as given in official CRCON instructions, will **FAIL**.  
To successfully upgrade your CRCON, you'll have to revert the changes back, then reinstall this plugin.  
To revert to the original file :  
```shell
cd /root/hll_rcon_tool
git restore config/supervisord.conf
```

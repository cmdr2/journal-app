@rem type 'shell:startup' in Win+R, and put this file in that folder, to run at system startup

@echo off

@cd C:\path\to\journal-app
@wsl /path/to/wsl/user/.local/bin/uvicorn --port 9876 server:app

pause

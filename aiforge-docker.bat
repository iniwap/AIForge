@echo off  
set PYTHONPATH=src  
if "%AIFORGE_LOCALE%"=="" set AIFORGE_LOCALE=en  
python -m aiforge.utils.manage_docker_services %*
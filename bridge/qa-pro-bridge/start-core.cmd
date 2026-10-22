@echo off
rem QA pro в браузере без приложения Claude: запустить ядро моста (окно можно свернуть).
rem Разрешить папку заранее: node server\core.js --allow "C:\путь\к\папке"
cd /d "%~dp0server"
node core.js --keep

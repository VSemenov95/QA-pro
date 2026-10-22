#!/bin/sh
# QA pro в браузере без приложения Claude: запустить ядро моста, чтобы загрузчик дал странице доступ к папке или git-репозиторию контекста.
# Разрешить папку заранее: node server/core.js --allow "/путь/к/папке"
cd "$(dirname "$0")/server" && exec node core.js --keep

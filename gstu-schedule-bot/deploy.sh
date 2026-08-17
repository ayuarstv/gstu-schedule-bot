#!/bin/bash
set -e  # Остановить скрипт при ошибке

IMAGE_NAME="gstu-bot"

echo "Обновление кода..."
git pull

echo "🛑 Остановка бота..."
docker-compose stop gstu-bot

echo "🧹 Очистка dangling-образов..."
docker image prune -f

echo "🔧 Сборка Docker-образа..."
docker build -t $IMAGE_NAME .

echo "🚀 Перезапуск бота (с миграцией внутри контейнера)..."
docker-compose up -d gstu-bot

echo "✅ Бот обновлён!"

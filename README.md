# GSTU Schedule Bot

Telegram-бот для студентов ГГТУ им. П.О. Сухого.  
Позволяет быстро получать расписание занятий, искать преподавателей и оценивать их.

## Возможности

- Получение расписания по группе
- Поиск преподавателей и просмотр их рейтинга
- Оценка преподавателей
- Inline-режим для быстрого поиска
- Логирование событий (loguru)
- Хранение данных в JSON-файлах

## Быстрый старт

### 1. Клонирование репозитория

```sh
git clone https://github.com/DonTMover/gstu-schedule-bot.git
cd gstu-schedule-bot
```

### 2. Настройка переменных окружения

Создайте файл `app/.env` по примеру `app/.env.sample` и укажите токен Telegram-бота и включите Inline-Режим:

```
BOT_TOKEN=your_telegram_token
```
## Важно! Включение Inline-режима

Для работы поиска по группам и преподавателям через inline-запросы необходимо включить поддержку Inline-режима для вашего бота:

1. Откройте чат с [BotFather](https://t.me/BotFather).
2. Отправьте команду `/setinline` и выберите вашего бота.
3. Укажите placeholder (например: `Введите название группы или преподавателя`).
4. После этого inline-функции бота будут доступны через `@ваш_бот` в любом чате.


### 3. Запуск через Docker

#### Сборка и запуск

```sh
docker build -t gstu-bot .
docker-compose up -d
```

#### Быстрое обновление и деплой

```sh
./deploy.sh
```

### 4. Запуск без Docker (локально)

```sh
cd app
pip install -r requirements.txt
python bot.py
```

## Структура проекта

```
app/
  bot.py           # основной бот
  api.py           # работа с расписанием
  db.py            # работа с рейтингами
  groupes.py       # группы
  utils.py         # вспомогательные функции
  requirements.txt # зависимости
  .env             # переменные окружения
teachers-parse/
  parse.py         # парсер преподавателей
  teachers.json    # база преподавателей
  groupes.py       # группы для парсинга
docker-compose.yml
Dockerfile
deploy.sh
README.md
```

## Логирование

Все события пишутся в файл `bot.log`.  
Файл пробрасывается наружу через Docker Compose.

## Проброс данных

- `bot.log` — логи
- `db.json` — база рейтингов
- `teachers.json` — база преподавателей

## Зависимости

- [aiogram](https://github.com/aiogram/aiogram)
- [aiohttp](https://github.com/aio-libs/aiohttp)
- [loguru](https://github.com/Delgan/loguru)
- [python-dotenv](https://github.com/theskumar/python-dotenv)
- [tqdm](https://github.com/tqdm/tqdm)

## Авторы

- [@DonTMover](https://github.com/DonTMover)

---

**Для вопросов и предложений — пишите Issues или Pull Requests!**
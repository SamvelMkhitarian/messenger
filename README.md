# 💬 Messenger API
## 📖 Кратко о проекте
Messenger — это асинхронный мессенджер, построенный на FastAPI и PostgreSQL, поддерживающий приватные и групповые чаты, регистрацию, авторизацию через JWT и обмен сообщениями в реальном времени через WebSocket. Все данные хранятся в базе PostgreSQL, ORM — SQLAlchemy.

## 🧾 TODO список (основные положения)
- [x] Настроить FastAPI с Uvicorn для асинхронного запуска
- [x] Добавить регистрацию и JWT-аутентификацию
- [x] Валидация email и пароля при регистрации
- [x] Реализовать модели пользователей, чатов, сообщений, групп
- [x] Добавить создание, просмотр и присоединение к чатам
- [x] Реализовать реальное время общения через WebSocket
- [x] Защитить эндпоинты через Depends и JWT
- [x] Написать юнит-тесты (pytest + httpx)
- [x] Настроить OpenAPI-документацию
- [x] Добавить README с инструкциями по запуску

## 💻 Запуск проекта
Клонирование репозитория:
```bash
git clone https://github.com/SamvelMkhitarian/messenger.git
cd messenger
```
Установка uv:

Linux:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
Windows:
```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
Установка зависимостей через uv и pyproject.toml:
```bash
uv pip install -r pyproject.toml
```

Настройка переменных окружения:

Создайте файл .env на основе .env.example и укажите необходимые значения, такие как настройки подключения к базе данных PostgreSQL.

Запуск проекта с помощью docker-compose:
```bash
docker-compose up --build
```

Приложение будет доступно по адресу: http://localhost:8000

📜 Документация API

Документация доступна по адресу http://localhost:8000/docs, где можно ознакомиться с доступными эндпоинтами и их параметрами.

🧪 Запуск тестов
```bash
pytest
```

🛑 Остановка сервера

Для остановки сервера нажмите Ctrl + C в консоли.


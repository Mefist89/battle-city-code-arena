# 🎮 Battle City: Code Arena — Техническая Спецификация (v0.3 MVP)

## Общее описание

**Battle City: Code Arena** — образовательная игровая веб-платформа, вдохновлённая классической игрой "Танки". Проект значительно продвинулся и сейчас находится на стадии **рабочего MVP (~v0.3)**. В игре реализованы три ключевых режима, пиксельный интерфейс в стиле ретро и функционирующая интеграция фронтенда с бэкендом. 

---

## 🗂️ Структура проекта (Текущая)

```text
battle-city-code-arena/
├── frontend/               # Фронтенд (SvelteKit + Svelte 5 + PixiJS)
│   ├── src/
│   │   ├── routes/
│   │   │   ├── +page.svelte        # Главная страница (Hero, Mission Protocol)
│   │   │   ├── game/               # Game Arena (Редактор кода, PixiJS рендеринг)
│   │   │   ├── missions/           # Каталог миссий
│   │   │   ├── challenge/          # Выживание против AI
│   │   │   ├── pvp/                # Мультиплеерные комнаты (WebSockets)
│   │   │   └── layout.css          # Дизайн-система (Tailwind v4, shadcn-svelte)
│   │   └── lib/
│   └── static/             # Ассеты (Kenney CC0 спрайты, танки)
│
└── backend/                # Бэкенд API (FastAPI)
    ├── app/
    │   ├── main.py             # Точка входа (31 строка) — создание app, CORS, роутеры
    │   ├── config.py           # Конфигурация приложения
    │   ├── session_store.py    # Хранилище сессий
    │   ├── routes/             # Роутеры API
    │   │   ├── game.py         # /api/game/* — миссии
    │   │   ├── pvp.py          # /api/rooms/*, /ws/* — PvP
    │   │   └── challenge.py    # /api/challenge/* — Challenge vs AI
    │   ├── schemas/            # Pydantic-схемы
    │   │   └── game.py         # TankState, EnemyState, Command и т.д.
    │   ├── simulator/          # Игровая логика
    │   │   ├── mechanics.py    # Общие механики (перемещение, столкновения)
    │   │   ├── mission_engine.py   # Движок миссий
    │   │   ├── challenge_engine.py # Движок Challenge vs AI
    │   │   ├── pvp_engine.py       # Движок PvP (комнаты, синхронизация)
    │   │   └── python_runner.py    # Парсер/исполнитель Python-команд
    │   └── levels/             # Данные уровней
    └── requirements.txt    # Зависимости Python
```

---

## 🛠️ Технологический стек

| Слой | Технология | Описание / Версия |
|---|---|---|
| **Frontend Framework** | SvelteKit | v2.57+ |
| **Frontend Renderer** | Svelte | v5 (Runes mode) |
| **Стилизация** | TailwindCSS v4 | Кастомная дизайн-система |
| **Игровой движок** | PixiJS | v8.18 |
| **Редактор кода** | CodeMirror 6 | Поддержка Python-синтаксиса |
| **Backend Framework** | FastAPI | Python 3.10+ |
| **Связь** | REST API + WebSockets | Взаимодействие в реальном времени |

---

## 🎮 Реализованные режимы и фичи

1. **Game Arena (`/game`)** — Полноценная IDE-like среда. CodeMirror 6 с автодополнением команд (`move`, `rotate`, `scan`, `fire`), поддержкой циклов `for/range`. Пиксельный рендеринг арены через PixiJS 8.
2. **Missions (`/missions`)** — Система миссий (6 уровней), каждая со своими задачами, подсказками и различными картами стен.
3. **Challenge vs AI (`/challenge`)** — Динамичный режим выживания. ИИ-враги имеют собственную логику поиска и стрельбы по игроку при прямой видимости.
4. **PvP Rooms (`/pvp`)** — Мультиплеерные бои на базе WebSocket, создание сессий по 6-значному коду комнаты.

---

## 🔌 API Эндпоинты

| Метод | Эндпоинт | Назначение |
|---|---|---|
| `GET` | `/` | Health check состояния бэкенда |
| `GET` | `/api/game/state` | Получение текущего состояния арены |
| `POST` | `/api/game/reset` | Инициализация и сброс состояния миссии |
| `POST` | `/api/game/command` | Выполнение Python-команды танка |
| `POST` | `/api/rooms` | Создание новой PvP комнаты |
| `POST` | `/api/rooms/{code}/join` | Подключение к PvP комнате |
| `WS` | `/ws/rooms/{code}/{slot}` | WebSocket соединение для PvP синхронизации |

---

## 🚀 Инструкция по запуску

### 1. Бэкенд (FastAPI)
```bash
cd backend
.venv\Scripts\activate   # На Windows
# Или 'source .venv/bin/activate' на macOS/Linux

pip install fastapi uvicorn pydantic websockets anyio
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
API доступно на `http://localhost:8000`, документация — на `http://localhost:8000/docs`.

### 2. Фронтенд (SvelteKit)
```bash
cd frontend
npm install
npm run dev
```
Фронтенд будет доступен по адресу `http://localhost:5173`.

> [!TIP]
> Запускайте бэкенд перед фронтендом, чтобы избежать ошибок подключения к API на главной странице.

---

## ⚠️ Известные проблемы (Технический долг)
- ~~**Монолит бэкенда**~~ ✅ **Решено** — `main.py` разбит на модули: `routes/`, `simulator/`, `schemas/`, `config.py`, `session_store.py`.
- ~~**Глобальное состояние**~~ ✅ **Решено** — реализована система сессий (`SessionStore`) с UUID-идентификаторами, TTL-очисткой (30 мин) и лимитом в 200 одновременных сессий. Каждый игрок получает изолированный `MissionState` через заголовок `X-Session-Id`.
- ~~**Docker**~~ ✅ **Решено** — настроены Dockerfile для обоих сервисов (multi-stage build, non-root user, healthcheck), `.dockerignore`, и `docker-compose.yml` с именованными volumes и зависимостью по healthcheck.

---

## 🐳 Запуск через Docker

```bash
docker compose up --build
```

| Сервис | URL |
|---|---|
| Frontend | `http://localhost:3000` |
| Backend API | `http://localhost:8000` |
| API Docs (Swagger) | `http://localhost:8000/docs` |

> [!NOTE]
> Frontend стартует только после того, как backend пройдёт healthcheck.

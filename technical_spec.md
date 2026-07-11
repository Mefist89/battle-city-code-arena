# 🎮 Battle City: Code Arena — Анализ проекта

## Общее описание

**Battle City: Code Arena** — образовательная игровая платформа, вдохновлённая классической игрой "Танки". Проект находится на **ранней стадии разработки** (v0.1.0): скелет архитектуры готов, большинство директорий пока пустые.

---

## 🗂️ Структура проекта

```
battle-city-code-arena/
├── .env                    # Переменные окружения (пустой)
├── .gitignore
├── docker-compose.yml      # Docker конфиг (пустой — не настроен)
├── TZ.docx                 # Техническое задание
├── structure.docx          # Описание архитектуры
│
├── frontend/               # SvelteKit + Vite + TailwindCSS 4
│   ├── src/
│   │   ├── routes/
│   │   │   ├── +layout.svelte    # Корневой layout (иконка + CSS)
│   │   │   ├── +page.svelte      # Главная страница (PixiJS + кнопка)
│   │   │   └── layout.css        # Глобальные стили (shadcn-svelte токены)
│   │   └── lib/
│   │       ├── components/ui/    # shadcn-svelte компоненты (Button, etc.)
│   │       ├── assets/           # favicon.svg и прочие ассеты
│   │       ├── hooks/            # (пустая)
│   │       ├── index.ts
│   │       └── utils.ts
│   ├── static/               # Статические файлы (tanks.png спрайт-лист)
│   ├── package.json
│   ├── svelte.config.js
│   └── vite.config.ts
│
└── backend/                # FastAPI (Python)
    ├── app/
    │   ├── main.py           # Точка входа FastAPI
    │   ├── models/           # (пустая) — Pydantic/ORM модели
    │   ├── schemas/          # (пустая) — Pydantic схемы
    │   ├── simulator/        # (пустая) — логика симулятора игры
    │   └── levels/           # (пустая) — данные уровней
    ├── Dockerfile/           # (пустая директория — Dockerfile не создан)
    ├── requirements.txt      # (пустой — зависимости не указаны)
    └── venv/                 # Виртуальное окружение Python
```

---

## 🛠️ Технологический стек

| Часть | Технология | Версия |
|---|---|---|
| **Frontend Framework** | SvelteKit | 2.57+ |
| **Frontend Renderer** | Svelte | 5.55+ (Runes mode) |
| **Build Tool** | Vite | 8.0+ |
| **CSS** | TailwindCSS v4 | 4.2+ |
| **UI Компоненты** | shadcn-svelte | 1.2+ |
| **Иконки** | Lucide Svelte | 1.0+ |
| **Игровой движок** | PixiJS | 8.18+ |
| **Backend Framework** | FastAPI | (нет в requirements.txt) |
| **Backend язык** | Python | (venv готов) |
| **CORS** | FastAPI CORSMiddleware | настроен на `localhost:5173` |

---

## 🔌 API (текущее состояние)

| Метод | URL | Описание |
|---|---|---|
| `GET` | `http://localhost:8000/` | Health check — `{"status": "online", ...}` |
| `GET` | `http://localhost:8000/api/level/1` | Пример данных первого уровня (карта 3×5) |

---

## ⚠️ Проблемы / Что не готово

> [!WARNING]
> **requirements.txt пустой** — FastAPI и Uvicorn не указаны как зависимости. Нужно добавить вручную.

> [!CAUTION]
> **Dockerfile пустой** — Docker Compose не настроен. Контейнеризация не работает.

> [!NOTE]
> **Директории пустые** — `models/`, `schemas/`, `simulator/`, `levels/` — всё это ещё предстоит реализовать.

---

## 🚀 Как запустить: Frontend

### Требования: Node.js 18+

```powershell
# 1. Перейти в папку frontend
cd c:\Users\User\Desktop\cafe-order\battle-city-code-arena\frontend

# 2. Установить зависимости (если ещё не установлены — node_modules уже есть)
npm install

# 3. Запустить dev-сервер
npm run dev
```

**Frontend будет доступен:** [http://localhost:5173](http://localhost:5173)

---

## 🚀 Как запустить: Backend

### Требования: Python 3.10+ (venv уже создан)

### Шаг 1 — Установить зависимости FastAPI

```powershell
# Активировать виртуальное окружение
c:\Users\User\Desktop\cafe-order\battle-city-code-arena\backend\venv\Scripts\activate

# Установить FastAPI и Uvicorn
pip install fastapi uvicorn
```

### Шаг 2 — Запустить сервер

```powershell
# Из папки backend
cd c:\Users\User\Desktop\cafe-order\battle-city-code-arena\backend

# Запустить с автоперезагрузкой при изменениях
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Backend будет доступен:**
- API: [http://localhost:8000](http://localhost:8000)
- Документация Swagger: [http://localhost:8000/docs](http://localhost:8000/docs)
- Документация ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 📋 Сводная таблица запуска

| Часть | Команда | URL |
|---|---|---|
| Frontend | `npm run dev` (в папке `frontend/`) | `http://localhost:5173` |
| Backend | `uvicorn app.main:app --reload` (в папке `backend/`) | `http://localhost:8000` |

> [!TIP]
> Запускай **сначала backend**, потом **frontend** — иначе кнопка на главной странице выдаст ошибку подключения.


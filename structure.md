battle-city-code-arena/
├── backend/ # Серверная часть (FastAPI)
│ ├── app/ # Основной код приложения
│ │ ├── main.py # Точка входа в API
│ │ ├── simulator/ # Логика игры (движок, расчеты)
│ │ ├── levels/ # Хранилище уровней (JSON-файлы)
│ │ ├── models/ # Модели базы данных (SQLAlchemy)
│ │ └── schemas/ # Схемы данных (Pydantic)
│ ├── requirements.txt # Зависимости Python
│ └── Dockerfile # Образ бэкенда
│
├── frontend/ # Клиентская часть (SvelteKit)
│ ├── src/
│ │ ├── lib/ # Общие компоненты и PixiJS-код
│ │ │ └── game/ # Логика рендеринга игры
│ │ ├── routes/ # Страницы приложения
│ │ └── app.html # Шаблон страницы
│ ├── static/ # Спрайт-лист и звуки
│ ├── tailwind.config.js # Конфиг стилей
│ └── Dockerfile # Образ фронтенда
│
├── docker-compose.yml # Оркестрация (запуск всего проекта)
├── .env # Секретные ключи и настройки БД
└── .gitignore # Исключения для Git

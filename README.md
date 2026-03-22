# Книга рецептов

Веб-приложение для управления продуктами и блюдами с backend на FastAPI и frontend на React.

## Стек

- Backend: FastAPI, SQLite, Pydantic
- Frontend: React, TypeScript, Vite
- Тесты backend: pytest
- Единый запуск: корневой `npm` + `concurrently`

## Структура

- `backend/` - API, SQLite, тесты, загрузка изображений
- `frontend/` - React-клиент
- `package.json` в корне - единая точка запуска и вспомогательные команды

## Требования

- Python 3.11+
- Node.js 18+
- npm

## Быстрый старт

Установка всего проекта одной командой:

```powershell
cd C:\Users\dleme\Тестирование
npm install
npm run install:all
```

Запуск всего проекта одной командой:

```powershell
cd C:\Users\dleme\Тестирование
npm run dev
```

После запуска:

- backend: `http://127.0.0.1:8000`
- frontend: `http://127.0.0.1:5173`

## Команды

Установить зависимости backend:

```powershell
npm run install:backend
```

Если `backend/.venv` уже существует, команда переиспользует его и просто ставит зависимости.

Установить зависимости frontend:

```powershell
npm run install:frontend
```

Установить все зависимости:

```powershell
npm run install:all
```

Запустить только backend:

```powershell
npm run dev:backend
```

Запустить только frontend:

```powershell
npm run dev:frontend
```

Запустить backend и frontend вместе:

```powershell
npm run dev
```

Прогнать backend-тесты:

```powershell
npm run test
```

Собрать frontend:

```powershell
npm run build
```

## Альтернативный ручной запуск

### Backend

```powershell
cd C:\Users\dleme\Тестирование\backend
.\.venv\bin\uvicorn.exe app.main:app --reload
```

### Frontend

```powershell
cd C:\Users\dleme\Тестирование\frontend
npm run dev
```

## Что реализовано

- CRUD для продуктов
- CRUD для блюд
- Поиск по названию
- Фильтрация и сортировка на экранах списков
- Сохранение состояния фильтров в URL
- Debounce для поиска
- Автоматический черновой расчет КБЖУ блюда
- Контроль допустимых флагов блюда по составу
- Запрет удаления продукта, если он используется в блюдах
- Загрузка изображений на backend

## Хранение данных

- Основная БД: `backend/recipe_book.db`
- Загруженные файлы: `backend/uploads/`
- Тестовая БД создается локально во время тестов

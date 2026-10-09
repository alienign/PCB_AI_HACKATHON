# PCB AI Assistant — Backend/API

Backend MVP для анализа фотографий печатных плат: FastAPI → PostgreSQL → YOLO → сохранение обнаружений → HTTP API для Qt.

## Требования

- Python **3.11** (проверенная версия разработки: 3.11.9).
- PostgreSQL (в разработке использовался PostgreSQL 18).
- Git и доступ к весам модели `best.pt` из согласованного командой источника. **Веса не включены в Git.**
- Команды ниже выполняются **из каталога `backend/`** репозитория.

## 1. Установка

Создайте виртуальное окружение из корня репозитория и перейдите в backend:

```bash
python3.11 -m venv .venv311
source .venv311/bin/activate
cd backend
python -m pip install -r requirements.txt
```

На Windows способ активации окружения отличается. Библиотеки `torch`/`torchvision` могут требовать платформенно-зависимой установки; используйте официальные инструкции PyTorch для своей ОС и ускорителя.

`requirements.txt` содержит основные зависимости. `requirements-lock-macos.txt` — снимок `pip freeze` из проверенного окружения macOS/Apple Silicon, **не универсальный lock-файл**; не устанавливайте его без проверки совместимости платформы.

## 2. PostgreSQL

Убедитесь, что локальный PostgreSQL запущен, и создайте **отдельную базу** для работы приложения. Пример для установки с локальной аутентификацией macOS:

```bash
createdb pcb_ai
```

Для отдельной тестовой базы:

```bash
createdb pcb_ai_test
```

Если базы уже существуют, повторно создавать их не требуется. Если вход по локальному пользователю не настроен, используйте свои учётные данные и строку подключения PostgreSQL; не публикуйте пароли в Git.

## 3. Переменные окружения

Из каталога `backend/`:

```bash
cp .env.example .env
```

Заполните `.env`. Пример **без пароля** для PostgreSQL с локальной аутентификацией:

```env
DATABASE_URL=postgresql+psycopg:///pcb_ai
STORAGE_PATH=./storage
ML_MODEL_PATH=./models/best.pt
FRONTEND_ORIGIN=http://localhost:5173
```

При необходимости используйте полную строку вида `postgresql+psycopg://USER:PASSWORD@HOST:5432/pcb_ai`. Значение `FRONTEND_ORIGIN` — CORS-источник браузерного клиента; Qt Network обычно не зависит от браузерной CORS-политики.

**Не коммитьте `.env`, дампы PostgreSQL, загруженные изображения и `best.pt`.** Проверьте `.gitignore` перед публикацией.

## 4. Модель

Разместите согласованный и проверенный командой файл модели по пути `backend/models/best.pt` либо укажите другой путь в `ML_MODEL_PATH`. Не используйте случайные непроверенные `.pt` файлы: загрузка PyTorch-моделей из ненадёжного источника может быть опасной. Метаданные модели и её ограничения приведены в `ML_MODEL_CARD.md` проекта.

## 5. Миграции

На **рабочей** базе, указанной в `DATABASE_URL`:

```bash
python -m alembic upgrade head
python -m alembic current
```

В репозитории присутствуют `0001_initial_schema`, несколько seed-веток миграций и их merge revision **`92f662858fce`**. Применяйте `upgrade head`, а не отдельную миграцию по имени. Скрипты `0003_detection_repair_status.sql`, находящиеся в документации проекта, не следует считать автоматически применённой Alembic-миграцией.

## 6. Запуск API

Из `backend/`, при активном виртуальном окружении:

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Проверка:

```bash
curl http://127.0.0.1:8000/health
```

Ожидаемый ответ: `{"status":"ok"}`. Swagger/OpenAPI: `http://127.0.0.1:8000/docs`.

Для доступа с другого компьютера одной сети можно выбрать `--host 0.0.0.0`, **только в доверенной сети** с учётом отсутствия пользовательской авторизации в этом MVP. Не публикуйте такой сервер в интернет без дополнительных мер защиты.

## 7. API-контракт для Qt

| Метод | Маршрут | Назначение |
| --- | --- | --- |
| `GET` | `/health` | Доступность приложения (не глубокая проверка DB/ML) |
| `POST` | `/images` | `multipart/form-data`, поле `file`; PNG/JPEG до 10 МБ; возвращает `image_id` |
| `GET` | `/images/{image_id}` | Возвращает исходное изображение (бинарные JPEG/PNG); если запись или файл отсутствует — HTTP 404 |
| `POST` | `/analysis-requests` | JSON `{"image_id": 1}`; возвращает `request_id`, `status: "created"` |
| `GET` | `/analysis-requests/{request_id}` | Текущий статус `created/processing/completed/failed`, список `detections`, `error_code`, `error_message` |
| `GET` | `/analysis-requests?limit=20&offset=0` | История анализов demo account, новые первыми; `limit` от 1 до 100, `offset` от 0 |

### Получение исходного изображения из истории

Отправьте `GET /images/{image_id}`, используя **идентификатор изображения**, а не `request_id` анализа. Пример:

```bash
curl http://127.0.0.1:8000/images/1 -o board.jpg
```

При успехе сервер возвращает HTTP `200`, заголовок `Content-Type: image/jpeg` либо `image/png` и бинарное содержимое исходного файла (**не JSON**). Клиент Qt должен читать тело ответа как изображение.

Возможные ошибки:

- `404`, `{"detail":"Image not found."}` — записи с таким `image_id` нет в PostgreSQL;
- `404`, `{"detail":"Image file not found."}` — запись есть, но файл отсутствует в хранилище.

`image_id` возвращает `POST /images`; при просмотре истории нужно использовать `image_id`, связанный с соответствующим анализом.

Пример создания анализа:

```bash
curl -X POST http://127.0.0.1:8000/analysis-requests \
  -H 'Content-Type: application/json' \
  -d '{"image_id": 1}'
```

Ответ: `{"request_id": <новый_id>, "status": "created"}` — числовые идентификаторы не фиксированы.

Структура одного элемента `detections` в ответе статуса:

```json
{
  "defect_type": "short",
  "confidence": 0.94,
  "bbox": {
    "x_min": 0.1,
    "y_min": 0.2,
    "x_max": 0.3,
    "y_max": 0.4
  }
}
```

Координаты нормализованы в диапазон `0..1`. Qt отвечает за перевод в экранные координаты и русские пользовательские названия. При успешном анализе без дефектов: `status="completed"`, `detections=[]`. При ошибке: `status="failed"`, `error_code` и `error_message`.

В **текущей реализации** обычные HTTP-ошибки, такие как 400/404, и ошибки валидации 422 имеют неодинаковый формат поля `detail`; единый обработчик ошибок ещё не внедрён. Не рассчитывайте на единый `ApiErrorResponse` без отдельного согласования. Отдельных `/history` и `/results` маршрутов в текущем API нет.

## 8. Тесты

Тесты могут создавать и удалять записи. **Никогда не запускайте их против рабочей базы `pcb_ai`.** Используйте отдельную `pcb_ai_test` с установленными миграциями.

```bash
DATABASE_URL="postgresql+psycopg:///pcb_ai_test" \
TEST_DATABASE_URL="postgresql+psycopg:///pcb_ai_test" \
python -m alembic upgrade head

DATABASE_URL="postgresql+psycopg:///pcb_ai_test" \
TEST_DATABASE_URL="postgresql+psycopg:///pcb_ai_test" \
python -m pytest -q
```

Последний подтверждённый результат в проверенном окружении: **55 passed, 1 warning** (`StarletteDeprecationWarning`). Часть HTTP-тестов использует подмену вызова ML, поэтому это не эквивалент полного реального Qt/YOLO E2E.

## 9. Диагностика

- `Address already in use`: порт 8000 занят; проверьте `lsof -nP -iTCP:8000 -sTCP:LISTEN`, прежде чем останавливать чужой/рабочий сервер.
- Если `/health` отвечает, это подтверждает лишь доступность FastAPI, **не готовность** PostgreSQL и YOLO.
- Логи `Analysis request <id>: starting/processing/completed/failed` выводятся через логгер Uvicorn; для успешного локального реального запроса подтверждены `5 detections` и время `1.06s`.
- Если запуск модели не работает, проверьте `ML_MODEL_PATH`, установленный PyTorch/Ultralytics и доступность файла изображения через `STORAGE_PATH`.

## 10. Ограничения и передача команде

- Демо-режим: используется один `demo account`, полноценной авторизации нет.
- ML запускается в `FastAPI BackgroundTasks`, а не в устойчивой внешней очереди; при перезапуске сервера задача может быть прервана.
- Открытые вопросы: единый формат HTTP-ошибок, отдельная сквозная проверка `failed`/нулевого результата в Qt, финальная сборка обеих веток, полноценный production deployment. HTTP-тест состояния `failed` добавлен в `integration-test`; проверка Qt остаётся отдельной задачей.
- Backend-ветка для интеграции: `integration-test`. На момент подготовки этой инструкции последний полученный коммит — **`f177916`** (тест `failed`); новый `GET /images/{image_id}` подготовлен локально и требует отдельного коммита и отправки. Qt frontend разрабатывается отдельно; не считать ветки слитыми без проверки Git.
- История реализована на backend, но её UI ещё должен быть подтверждён отдельно.

При передаче другой участник должен проверить свои `.env`, локальный PostgreSQL, модель, применить миграции, поднять `/health`, выполнить тесты на **отдельной БД** и только затем подключать Qt.

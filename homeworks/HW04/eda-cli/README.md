# S04 – eda_cli: HTTP-сервис качества датасетов (FastAPI)

Расширенная версия проекта `eda-cli` из HW03.

К существующему CLI-приложению для EDA добавлен **HTTP-сервис на FastAPI** с эндпоинтами `/health`, `/quality` и `/quality-from-csv`.  
Используется в рамках Семинара 04 курса «Инженерия ИИ».

---

## Связь с HW03

Проект в HW04 основан на том же пакете `eda_cli`, что и в HW03:

- сохраняется структура `src/eda_cli/` и CLI-команда `eda-cli`;
- добавлен модуль `api.py` с FastAPI-приложением;
- в зависимости добавлены `fastapi` и `uvicorn[standard]`.

Цель HW04 – показать, как поверх уже написанного EDA-ядра поднять простой HTTP-сервис.

---

## Требования

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) установлен в систему
- Браузер (для Swagger UI `/docs`) или любой HTTP-клиент:
  - `curl` / HTTP-клиент в IDE / Postman / Hoppscotch и т.п.

## Инициализация проекта

В корне проекта (HW04/eda-cli):

```bash
uv sync
```

Эта команда:

- создаст виртуальное окружение `.venv`;
- установит зависимости из `pyproject.toml` (включая FastAPI и Uvicorn);
- установит сам проект `eda-cli` в окружение.

### Полный EDA-отчёт

```bash
uv run eda-cli report data/example.csv --out-dir reports
```

В результате в каталоге `reports/` появятся:

- `report.md` - основной отчёт в Markdown;
- `summary.csv` - таблица по колонкам;
- `missing.csv` - пропуски по колонкам;
- `correlation.csv` - корреляционная матрица (если есть числовые признаки);
- `top_categories/*.csv` - top-k категорий по строковым признакам;
- `hist_*.png` - гистограммы числовых колонок;
- `missing_matrix.png` - визуализация пропусков;
- `correlation_heatmap.png` - тепловая карта корреляций.

## Команды

- `eda-cli overview PATH [--sep "," --encoding "utf-8"]` — краткий обзор датасета (размеры, типы, сводка по колонкам).
- `eda-cli report PATH [--out-dir reports --sep "," --encoding "utf-8" --max-hist-columns 6 --top-k-categories 5 --title "EDA-отчёт" --min-missing-share 0.2]` — полный отчёт с таблицами и графиками.
- `uv run eda-cli head data/example.csv` - вывод первых 5-ти строк датасета и краткой сводки

## Новые параметры `report`

- `--max-hist-columns` — сколько числовых колонок включать в гистограммы.
- `--top-k-categories` — сколько top-значений сохранять для категориальных признаков.
- `--title` — заголовок отчёта (`report.md`).
- `--min-missing-share` — порог доли пропусков; колонки выше порога выводятся отдельным списком.

## Пример вызова `report` с новыми опциями

```bash
uv run eda-cli report data/example.csv --out-dir reports --max-hist-columns 8 --top-k-categories 7 --title "EDA Example" --min-missing-share 0.15
```

## Параметры `head` 
- `--n` - колличество выводимых строк (по умолчанию 5)
- `--sep` - разделитель в CSV (по умолчанию ,)
- `--encodig` - кодировка файла (по умолчанию utf-8)

## Тесты

```bash
uv run pytest -q
```

---

## Запуск HTTP-сервиса

HTTP-сервис реализован в модуле `eda_cli.api` на FastAPI.

### Запуск Uvicorn

```bash
uv run uvicorn eda_cli.api:app --reload --port 8000
```

Пояснения:

- `eda_cli.api:app` - путь до объекта FastAPI `app` в модуле `eda_cli.api`;
- `--reload` - автоматический перезапуск сервера при изменении кода (удобно для разработки);
- `--port 8000` - порт сервиса (можно поменять при необходимости).

После запуска сервис будет доступен по адресу:

```text
http://127.0.0.1:8000
```

---

## Эндпоинты сервиса

### 1. `GET /health`

Простейший health-check.

**Запрос:**

```http
GET /health
```

**Ожидаемый ответ `200 OK` (JSON):**

```json
{
  "status": "ok",
  "service": "dataset-quality",
  "version": "0.2.0"
}
```

Пример проверки через `curl`:

```bash
curl http://127.0.0.1:8000/health
```

---

### 2. Swagger UI: `GET /docs`

Интерфейс документации и тестирования API:

```text
http://127.0.0.1:8000/docs
```

Через `/docs` можно:

- вызывать `GET /health`;
- вызывать `POST /quality` (форма для JSON);
- вызывать `POST /quality-from-csv` (форма для загрузки файла).

---

### 3. `POST /quality` – запрос по агрегированным признакам

Эндпоинт принимает **агрегированные признаки датасета** (размеры, доля пропусков и т.п.) и возвращает эвристическую оценку качества.

**Пример запроса:**

```http
POST /quality
Content-Type: application/json
```

Тело:

```json
{
  "n_rows": 10000,
  "n_cols": 12,
  "max_missing_share": 0.15,
  "numeric_cols": 8,
  "categorical_cols": 4
}
```

**Пример ответа `200 OK`:**

```json
{
  "ok_for_model": true,
  "quality_score": 0.8,
  "message": "Данных достаточно, модель можно обучать (по текущим эвристикам).",
  "latency_ms": 3.2,
  "flags": {
    "too_few_rows": false,
    "too_many_columns": false,
    "too_many_missing": false,
    "no_numeric_columns": false,
    "no_categorical_columns": false
  },
  "dataset_shape": {
    "n_rows": 10000,
    "n_cols": 12
  }
}
```

**Пример вызова через `curl`:**

```bash
curl -X POST "http://127.0.0.1:8000/quality" \
  -H "Content-Type: application/json" \
  -d '{"n_rows": 10000, "n_cols": 12, "max_missing_share": 0.15, "numeric_cols": 8, "categorical_cols": 4}'
```

---

### 4. `POST /quality-from-csv` – оценка качества по CSV-файлу

Эндпоинт принимает CSV-файл, внутри:

- читает его в `pandas.DataFrame`;
- вызывает функции из `eda_cli.core`:

  - `summarize_dataset`,
  - `missing_table`,
  - `compute_quality_flags`;
- возвращает оценку качества датасета в том же формате, что `/quality`.

**Запрос:**

```http
POST /quality-from-csv
Content-Type: multipart/form-data
file: <CSV-файл>
```

Через Swagger:

- в `/docs` открыть `POST /quality-from-csv`,
- нажать `Try it out`,
- выбрать файл (например, `data/example.csv`),
- нажать `Execute`.

**Пример вызова через `curl` (Linux/macOS/WSL):**

```bash
curl -X POST "http://127.0.0.1:8000/quality-from-csv" \
  -F "file=@data/example.csv"
```

Ответ будет содержать:

- `ok_for_model` - результат по эвристикам;
- `quality_score` - интегральный скор качества;
- `flags` - булевы флаги из `compute_quality_flags`;
- `dataset_shape` - реальные размеры датасета (`n_rows`, `n_cols`);
- `latency_ms` - время обработки запроса.

---

### 5. `POST /quality-flags-from-csv ` - возвращает расширенные флаги качества

Аналогично `/quality-from-csv`, но возвращает **расширенные флаги** (не только булевы, но и числовые, списки и т.п.).

**Запрос:**

```http
POST /quality-flags-from-csv
Content-Type: multipart/form-data
file: <CSV-файл>
```

**Параметры:**

- `file` (required) — CSV-файл для загрузки.

**Ожидаемый ответ `200 OK`:**

```json
{
  "ok_for_model": true,
  "quality_score": 0.65,
  "message": "CSV выглядит достаточно качественным для обучения модели (по текущим эвристикам).",
  "latency_ms": 14.2,
  "flags": {
    "quality_score": 0.65,
    "max_missing_share": 0.08,
    "too_few_rows": false,
    "too_many_columns": false,
    "too_many_missing": false,
    "no_numeric_columns": false,
    "no_categorical_columns": false,
    "has_constant_columns": false,
    "has_high_cardinality_categoricals": false,
    "has_suspicious_id_duplicates": false,
    "zero_value_columns": [],
    "has_many_zero_values": false
  },
  "dataset_shape": {
    "n_rows": 36,
    "n_cols": 14
  }
}
```

**Пример вызова через `curl`:**

```bash
curl -X POST "http://127.0.0.1:8000/quality-flags-from-csv" \
  -F "file=@data/example.csv"
```

---

### 6. `POST /head` - получение примера строк из CSV

Возвращает первые `n` строк или случайную выборку из CSV-файла.

**Запрос:**

```http
POST /head?n=6&random=true
Content-Type: multipart/form-data
file: <CSV-файл>
```

**Параметры:**

- `file` (required) — CSV-файл для загрузки;
- `n` (int, default 5) — количество строк для возврата;
- `random` (bool, default false) — если `true`, вернуть случайную выборку; если `false`, вернуть первые n строк.

**Ожидаемый ответ `200 OK`:**

```json
{
  "rows": [
    {
      "user_id": 1035,
      "country": "UA",
      "city": "Odessa",
      "device": "Mobile",
      "sessions_last_30d": 12,
      "avg_session_duration_min": 8,
      "pages_per_session": 4.4,
      "purchases_last_30d": 1,
      "revenue_last_30d": 1300,
      "churned": 0,
      "signup_year": 2021,
      "plan": "Basic",
      "n_support_tickets": 1
    }
  ],
  "n": 6,
  "total_rows": 36,
  "random": true,
  "columns": [
    "user_id",
    "country",
    "city",
    "device",
    "sessions_last_30d",
    "avg_session_duration_min",
    "pages_per_session",
    "purchases_last_30d",
    "revenue_last_30d",
    "churned",
    "signup_year",
    "plan",
    "n_support_tickets"
  ],
  "latency_ms": 2.1
}
```

**Поля ответа:**

- `rows` — список строк датасета в формате dict (JSON-совместимый, NaN/±Inf замещены на null);
- `n` — количество возвращённых строк;
- `total_rows` — общее количество строк в CSV;
- `random` — был ли использован random sampling;
- `columns` — список названий колонок;
- `latency_ms` — время обработки запроса.

**Ошибки:**

- `400 Bad Request` — если файл не в формате CSV или пуст;
- `500 Internal Server Error` — при других ошибках.

**Примеры вызова через `curl`:**

Первые 5 строк:
```bash
curl -X POST "http://127.0.0.1:8000/head?n=5&random=false" \
  -F "file=@data/example.csv"
```

Случайная выборка 10 строк:
```bash
curl -X POST "http://127.0.0.1:8000/head?n=10&random=true" \
  -F "file=@data/example.csv"
```

---

## Логирование

Структурированные JSON-логи всех запросов пишутся в файл `logs/api.log`:

**Поля лога:**

- `timestamp` — ISO 8601 (timezone-aware UTC);
- `endpoint` — путь эндпоинта (например, `/head`, `/quality-from-csv`);
- `status` — `"success"`;
- `latency_ms` — время обработки запроса;
- `filename` — имя загруженного файла (для CSV-эндпоинтов);
- `n_rows`, `n_cols` — размеры датасета (для некоторых эндпоинтов);
- `n_requested`, `n_returned`, `total_rows`, `random` — информация о выборке (для `/head`);
- `score` — quality_score (для `/quality` и `/quality-from-csv`);
- `status_code`, `detail` — информация об ошибке (при `status="error"`).

**Пример успешного лога:**

```json
{"timestamp":"2025-12-17T12:54:08.775162+00:00","endpoint":"/head","status":"success","filename":"example.csv","n_requested":10,"n_returned":10,"total_rows":36,"random":true,"latency_ms":2.2}
```

---

## Структура проекта (упрощённо)

```text
S04/
  eda-cli/
    pyproject.toml
    README.md                # этот файл
    src/
      eda_cli/
        __init__.py
        core.py              # EDA-логика, эвристики качества
        viz.py               # визуализации
        cli.py               # CLI (overview/report)
        api.py               # HTTP-сервис (FastAPI)
    tests/
      test_core.py           # тесты ядра
    data/
      example.csv            # учебный CSV для экспериментов
```

---

## Тесты

Запуск тестов (как и в S03):

```bash
uv run pytest -q
```

Рекомендуется перед любыми изменениями в логике качества данных и API:

1. Запустить тесты `pytest`;
2. Проверить работу CLI (`uv run eda-cli ...`);
3. Проверить работу HTTP-сервиса (`uv run uvicorn ...`, затем `/health` и `/quality`/`/quality-from-csv` через `/docs` или HTTP-клиент).

---

## Коментарий

Работоспособность проекта была проверена также на датасете из HW02
# S03 – eda_cli: мини-EDA для CSV

Небольшое CLI-приложение для базового анализа CSV-файлов.
Используется в рамках Семинара 03 курса «Инженерия ИИ».

## Требования

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) установлен в систему

## Инициализация проекта

В корне проекта (S03):

```bash
uv sync
```

Эта команда:

- создаст виртуальное окружение `.venv`;
- установит зависимости из `pyproject.toml`;
- установит сам проект `eda-cli` в окружение.

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

## Запуск CLI

### Краткий обзор

```bash
uv run eda-cli overview data/example.csv
```

Параметры:

- `--sep` – разделитель (по умолчанию `,`);
- `--encoding` – кодировка (по умолчанию `utf-8`).

### Полный EDA-отчёт

```bash
uv run eda-cli report data/example.csv --out-dir reports
```

В результате в каталоге `reports/` появятся:

- `report.md` – основной отчёт в Markdown;
- `summary.csv` – таблица по колонкам;
- `missing.csv` – пропуски по колонкам;
- `correlation.csv` – корреляционная матрица (если есть числовые признаки);
- `top_categories/*.csv` – top-k категорий по строковым признакам;
- `hist_*.png` – гистограммы числовых колонок;
- `missing_matrix.png` – визуализация пропусков;
- `correlation_heatmap.png` – тепловая карта корреляций.

## Тесты

```bash
uv run pytest -q
```

## Коментарий

Работоспособность проекта была проверена также на датасете из HW02
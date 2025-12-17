from __future__ import annotations

from time import perf_counter

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from .core import compute_quality_flags, missing_table, summarize_dataset

import logging
import json
from datetime import datetime, timezone
import math
from pathlib import Path

# uv run uvicorn eda_cli.app:app --reload --port 8000

app = FastAPI(
    title="AIE Dataset Quality API",
    version="0.2.0",
    description=(
        "HTTP-сервис-заглушка для оценки готовности датасета к обучению модели. "
        "Использует простые эвристики качества данных вместо настоящей ML-модели."
    ),
    docs_url="/docs",
    redoc_url=None,
)

# ---------- Логирование ----------
def setup_logging(log_dir: Path = Path("logs")) -> logging.Logger:
    """Настроить логирование в файл и консоль."""
    log_dir.mkdir(exist_ok=True)
    logger = logging.getLogger("eda_api")
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        handler = logging.FileHandler(log_dir / "api.log", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    
    return logger


logger = setup_logging()

def log_action(endpoint: str, **details) -> None:
    """Логировать действие в JSON-формате."""
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "endpoint": endpoint,
        **details,
    }
    logger.info(json.dumps(log_entry))

# ---------- Модели запросов/ответов ----------


class QualityRequest(BaseModel):
    """Агрегированные признаки датасета – 'фичи' для заглушки модели."""

    n_rows: int = Field(..., ge=0, description="Число строк в датасете")
    n_cols: int = Field(..., ge=0, description="Число колонок")
    max_missing_share: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Максимальная доля пропусков среди всех колонок (0..1)",
    )
    numeric_cols: int = Field(
        ...,
        ge=0,
        description="Количество числовых колонок",
    )
    categorical_cols: int = Field(
        ...,
        ge=0,
        description="Количество категориальных колонок",
    )


class QualityResponse(BaseModel):
    """Ответ заглушки модели качества датасета."""

    ok_for_model: bool = Field(
        ...,
        description="True, если датасет считается достаточно качественным для обучения модели",
    )
    quality_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Интегральная оценка качества данных (0..1)",
    )
    message: str = Field(
        ...,
        description="Человекочитаемое пояснение решения",
    )
    latency_ms: float = Field(
        ...,
        ge=0.0,
        description="Время обработки запроса на сервере, миллисекунды",
    )
    flags: dict[str, bool] | None = Field(
        default=None,
        description="Булевы флаги с подробностями (например, too_few_rows, too_many_missing)",
    )
    dataset_shape: dict[str, int] | None = Field(
        default=None,
        description="Размеры датасета: {'n_rows': ..., 'n_cols': ...}, если известны",
    )

# ---------- класс для ответа с флагами ----------
class ExtendedQualityResponse(BaseModel):
    ok_for_model: bool = Field(
        ...,
        description="True, если датасет считается достаточно качественным для обучения модели",
    )
    quality_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Интегральная оценка качества данных (0..1)",
    )
    message: str = Field(
        ...,
        description="Человекочитаемое пояснение решения",
    )
    latency_ms: float = Field(
        ...,
        ge=0.0,
        description="Время обработки запроса на сервере, миллисекунды",
    )
    flags: dict[str, bool | float | list[str] | None] = Field(
        ...,
        description="Флаги с подробностями (например, too_few_rows, too_many_missing)",
    )
    dataset_shape: dict[str, int] = Field(
        ...,
        description="Размеры датасета: {'n_rows': ..., 'n_cols': ...}, если известны",
    )

# ---------- класс для head ответа ----------
class HeadResponse(BaseModel):
    rows: list[dict[str, int | bool | float | str| list[str] | None]] = Field(
        ...,
        description="Строки датасета в формате records",
    )
    latency_ms: float = Field(
        ...,
        ge=0.0,
        description="Время обработки запроса на сервере, миллисекунды",
    )
    n: int = Field(
        ...,
        ge=0,
        description="Запрошенное число строк",
    )
    total_rows: int = Field(
        ..., 
        ge=0, 
        description="Общее число строк в CSV",
    )
    random: bool = Field(
        ..., 
        description="True, если выбрана случайная выборка",
    )
    columns: list[str] = Field(
        ..., 
        description="Список колонок в исходном CSV",
    )

# ---------- Системный эндпоинт ----------


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Простейший health-check сервиса."""
    return {
        "status": "ok",
        "service": "dataset-quality",
        "version": "0.2.0",
    }


# ---------- Заглушка /quality по агрегированным признакам ----------


@app.post("/quality", response_model=QualityResponse, tags=["quality"])
def quality(req: QualityRequest) -> QualityResponse:
    """
    Эндпоинт-заглушка, который принимает агрегированные признаки датасета
    и возвращает эвристическую оценку качества.
    """

    start = perf_counter()

    # Базовый скор от 0 до 1
    score = 1.0

    # Чем больше пропусков, тем хуже
    score -= req.max_missing_share

    # Штраф за слишком маленький датасет
    if req.n_rows < 1000:
        score -= 0.2

    # Штраф за слишком широкий датасет
    if req.n_cols > 100:
        score -= 0.1

    # Штрафы за перекос по типам признаков (если есть числовые и категориальные)
    if req.numeric_cols == 0 and req.categorical_cols > 0:
        score -= 0.1
    if req.categorical_cols == 0 and req.numeric_cols > 0:
        score -= 0.05

    # Нормируем скор в диапазон [0, 1]
    score = max(0.0, min(1.0, score))

    # Простое решение "ок / не ок"
    ok_for_model = score >= 0.7
    if ok_for_model:
        message = "Данных достаточно, модель можно обучать (по текущим эвристикам)."
    else:
        message = "Качество данных недостаточно, требуется доработка (по текущим эвристикам)."

    latency_ms = (perf_counter() - start) * 1000.0

    # Флаги, которые могут быть полезны для последующего логирования/аналитики
    flags = {
        "too_few_rows": req.n_rows < 1000,
        "too_many_columns": req.n_cols > 100,
        "too_many_missing": req.max_missing_share > 0.5,
        "no_numeric_columns": req.numeric_cols == 0,
        "no_categorical_columns": req.categorical_cols == 0,
    }

    '''# Примитивный лог — на семинаре можно обсудить, как это превратить в нормальный logger
    print(
        f"[quality] n_rows={req.n_rows} n_cols={req.n_cols} "
        f"max_missing_share={req.max_missing_share:.3f} "
        f"score={score:.3f} latency_ms={latency_ms:.1f} ms"
    )'''# логирование действия в файл
    log_action(
        "/quality",
        status="success",
        n_rows=req.n_rows,
        n_cols=req.n_cols,
        score=round(score, 3),
        latency_ms=round(latency_ms, 1),
    )

    return QualityResponse(
        ok_for_model=ok_for_model,
        quality_score=score,
        message=message,
        latency_ms=latency_ms,
        flags=flags,
        dataset_shape={"n_rows": req.n_rows, "n_cols": req.n_cols},
    )


# ---------- /quality-from-csv: реальный CSV через нашу EDA-логику ----------


@app.post(
    "/quality-from-csv",
    response_model=QualityResponse,
    tags=["quality"],
    summary="Оценка качества по CSV-файлу с использованием EDA-ядра",
)
async def quality_from_csv(file: UploadFile = File(...)) -> QualityResponse:
    """
    Эндпоинт, который принимает CSV-файл, запускает EDA-ядро
    (summarize_dataset + missing_table + compute_quality_flags)
    и возвращает оценку качества данных.

    Именно это по сути связывает S03 (CLI EDA) и S04 (HTTP-сервис).
    """

    start = perf_counter()

    if file.content_type not in ("text/csv", "application/vnd.ms-excel", "application/octet-stream"):
        # content_type от браузера может быть разным, поэтому проверка мягкая
        # но для демонстрации оставим простую ветку 400
        raise HTTPException(status_code=400, detail="Ожидается CSV-файл (content-type text/csv).")

    try:
        # FastAPI даёт file.file как file-like объект, который можно читать pandas'ом
        df = pd.read_csv(file.file)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Не удалось прочитать CSV: {exc}")

    if df.empty:
        raise HTTPException(status_code=400, detail="CSV-файл не содержит данных (пустой DataFrame).")

    # Используем EDA-ядро из S03
    summary = summarize_dataset(df)
    missing_df = missing_table(df)
    flags_all = compute_quality_flags(summary, missing_df)

    # Ожидаем, что compute_quality_flags вернёт quality_score в [0,1]
    score = float(flags_all.get("quality_score", 0.0))
    score = max(0.0, min(1.0, score))
    ok_for_model = score >= 0.7

    if ok_for_model:
        message = "CSV выглядит достаточно качественным для обучения модели (по текущим эвристикам)."
    else:
        message = "CSV требует доработки перед обучением модели (по текущим эвристикам)."

    latency_ms = (perf_counter() - start) * 1000.0

    # Оставляем только булевы флаги для компактности
    flags_bool: dict[str, bool] = {
        key: bool(value)
        for key, value in flags_all.items()
        if isinstance(value, bool)
    }

    # Размеры датасета берём из summary (если там есть поля n_rows/n_cols),
    # иначе — напрямую из DataFrame.
    try:
        n_rows = int(getattr(summary, "n_rows"))
        n_cols = int(getattr(summary, "n_cols"))
    except AttributeError:
        n_rows = int(df.shape[0])
        n_cols = int(df.shape[1])
    '''
    print(
        f"[quality-from-csv] filename={file.filename!r} "
        f"n_rows={n_rows} n_cols={n_cols} score={score:.3f} "
        f"latency_ms={latency_ms:.1f} ms"
    )''' # логирование действия в файл
    log_action(
        "/quality-from-csv",
        status="success",
        filename=file.filename,
        n_rows=n_rows,
        n_cols=n_cols,
        score=round(score, 3),
        latency_ms=round(latency_ms, 1),
    )

    return QualityResponse(
        ok_for_model=ok_for_model,
        quality_score=score,
        message=message,
        latency_ms=latency_ms,
        flags=flags_bool,
        dataset_shape={"n_rows": n_rows, "n_cols": n_cols},
    )


# ---------- Новые эндпоинты ----------
# ---------- POST /quality-flags-from-csv : аналогично /quality-from-csv, но возвращает ещё не bool флаги ---------- 
# вообще /quality-from-csv и так возвращает все новые добавленные флаги (за исключением одного), но почему бы и нет

@app.post(
    "/quality-flags-from-csv",
    response_model=ExtendedQualityResponse,
    tags=["quality"],
    summary="Оценка качества по CSV-файлу и вывод флагов с использованием EDA-ядра с подробными флагами",
)
async def quality_flags_from_csv(file: UploadFile = File(...)) -> ExtendedQualityResponse:
    """
    Эндпоинт, который принимает CSV-файл, запускает EDA-ядро
    (summarize_dataset + missing_table + compute_quality_flags)
    и возвращает оценку качества данных с подробными флагами.
    """

    start = perf_counter()

    if file.content_type not in ("text/csv", "application/vnd.ms-excel", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Ожидается CSV-файл (content-type text/csv).")

    try:
        df = pd.read_csv(file.file)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Не удалось прочитать CSV: {exc}")

    if df.empty:
        raise HTTPException(status_code=400, detail="CSV-файл не содержит данных (пустой DataFrame).")
    # также выполняем что и в /quality-from-csv
    summary = summarize_dataset(df)
    missing_df = missing_table(df)
    flags_all = compute_quality_flags(summary, missing_df) # уже все флаги

    score = float(flags_all.get("quality_score", 0.0))
    score = max(0.0, min(1.0, score))
    ok_for_model = score >= 0.7

    if ok_for_model:
        message = "CSV выглядит достаточно качественным для обучения модели (по текущим эвристикам)."
    else:
        message = "CSV требует доработки перед обучением модели (по текущим эвристикам)."

    latency_ms = (perf_counter() - start) * 1000.0

    try:
        n_rows = int(getattr(summary, "n_rows"))
        n_cols = int(getattr(summary, "n_cols"))
    except AttributeError:
        n_rows = int(df.shape[0])
        n_cols = int(df.shape[1])
    '''
    print(
        f"[quality-flags-from-csv] filename={file.filename!r} "
        f"n_rows={n_rows} n_cols={n_cols} score={score:.3f} "
        f"latency_ms={latency_ms:.1f} ms"
    )''' # логирование действия в файл
    log_action(
        "/quality-flags-from-csv",
        status="success",
        filename=file.filename,
        n_rows=n_rows,
        n_cols=n_cols,
        score=round(score, 3),
        latency_ms=round(latency_ms, 1),
    )

    return ExtendedQualityResponse(
        ok_for_model=ok_for_model,
        quality_score=score,
        message=message,
        latency_ms=latency_ms,
        flags=flags_all,  # возвращаем все флаги, не только булевы ( ещё один) ) 
        dataset_shape={"n_rows": n_rows, "n_cols": n_cols},
    )  

# ---------- POST /head : принимает CSV + параметр `n` и возвращает первые `n` строк или случайную выборку строк в JSON-формате ----------
@app.post(
    "/head",
    response_model=HeadResponse,
    tags=["data"],
    summary="Возвращает первые n строк или случайную выборку из CSV-файла",
)
async def head(
    file: UploadFile = File(...),
    n: int = 5,
    random: bool = False,
) -> HeadResponse:
    """
    Эндпоинт, который принимает CSV-файл и параметр `n`,
    и возвращает первые `n` строк или случайную выборку из `n` строк в JSON-формате.
    """
    start = perf_counter()

    if file.content_type not in ("text/csv", "application/vnd.ms-excel", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Ожидается CSV-файл (content-type text/csv).")

    try:
        df = pd.read_csv(file.file)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Не удалось прочитать CSV: {exc}")

    if df.empty:
        raise HTTPException(status_code=400, detail="CSV-файл не содержит данных (пустой DataFrame).")

    n_selected = max(0, min(int(n), len(df)))
    if random:
        result_df = df.sample(n=n_selected, random_state=42) if n_selected > 0 else df.head(0)
    else:
        result_df = df.head(n_selected)
    
    latency_ms = (perf_counter() - start) * 1000.0

    # JSON-безопасная обработка NaN/Inf значений
    records = result_df.replace([float("inf"), float("-inf")], None).to_dict(orient="records")
    rows: list[dict[str, object]] = []
    for rec in records:
        clean = {}
        for key, val in rec.items():
            if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                clean[key] = None
            elif pd.isna(val):
                clean[key] = None
            else:
                clean[key] = val
        rows.append(clean)

    # логируем действие
    log_action(
        "/head",
        status="success",
        filename=file.filename,
        n_requested=n,
        n_returned=n_selected,
        total_rows=len(df),
        random=random,
        latency_ms=round(latency_ms, 1),
    )

    return HeadResponse(
        rows=rows,
        latency_ms=latency_ms,
        n=n_selected,
        total_rows=len(df),
        random=random,
        columns=list(df.columns),
    )
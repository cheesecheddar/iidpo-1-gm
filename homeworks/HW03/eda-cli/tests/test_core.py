from __future__ import annotations

import pandas as pd

from eda_cli.core import (
    compute_quality_flags,
    correlation_matrix,
    flatten_summary_for_print,
    missing_table,
    summarize_dataset,
    top_categories,
)


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "age": [10, 20, 30, None],
            "height": [140, 150, 160, 170],
            "city": ["A", "B", "A", None],
        }
    )


def test_summarize_dataset_basic():
    df = _sample_df()
    summary = summarize_dataset(df)

    assert summary.n_rows == 4
    assert summary.n_cols == 3
    assert any(c.name == "age" for c in summary.columns)
    assert any(c.name == "city" for c in summary.columns)

    summary_df = flatten_summary_for_print(summary)
    assert "name" in summary_df.columns
    assert "missing_share" in summary_df.columns


def test_missing_table_and_quality_flags():
    df = _sample_df()
    missing_df = missing_table(df)

    assert "missing_count" in missing_df.columns
    assert missing_df.loc["age", "missing_count"] == 1

    summary = summarize_dataset(df)
    flags = compute_quality_flags(summary, missing_df)
    assert 0.0 <= flags["quality_score"] <= 1.0


def test_correlation_and_top_categories():
    df = _sample_df()
    corr = correlation_matrix(df)
    # корреляция между age и height существует
    assert "age" in corr.columns or corr.empty is False

    top_cats = top_categories(df, max_columns=5, top_k=2)
    assert "city" in top_cats
    city_table = top_cats["city"]
    assert "value" in city_table.columns
    assert len(city_table) <= 2

# Новые тесты логики эвристик
# проверка флаг уникальности
def test_constant_column_flag():
    df = pd.DataFrame({
        "constant_col": [1, 1, 1, 1],
        "var_col": [1, 2, 3, 4],
        "city": ["A", "B", None, "A"]
    })
    summary = summarize_dataset(df)
    missing_df = missing_table(df)
    flags = compute_quality_flags(summary, missing_df)

    assert flags["has_constant_columns"] is True

# проверка флага подозрительных id
def test_suspicious_id_duplicates_flag():
    df = pd.DataFrame({
        "user_id": [1001, 1001, 1002, 1003], # есть дубликаты
        "prod_id": [101, 102, 103, 104], # уникальные
        "purchase_amount": [100.0, 200.0, 150.5, 300.0]
    })
    summary = summarize_dataset(df)
    missing_df = missing_table(df)
    flags = compute_quality_flags(summary, missing_df)

    assert flags["has_suspicious_id_duplicates"] is True

# проверка флага большого числа нулевых значений
def test_too_many_zero_values_flag():
    df = pd.DataFrame({
        "col1": [0, 0, 0, 0],  # все нули
        "col2": [0, 0, 0, 100], # 75% нулей
        "col3": [1, 2, 3, 4],  # нет нулей
    })
    summary = summarize_dataset(df)
    missing_df = missing_table(df)
    flags = compute_quality_flags(summary, missing_df)

    assert flags["has_many_zero_values"] is True
    assert "col1" in flags["zero_value_columns"]
    assert "col2" in flags["zero_value_columns"]
    assert "col3" not in flags["zero_value_columns"]
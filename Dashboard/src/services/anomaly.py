"""
anomaly.py — Detector de anomalías de gasto por categoría (z-score).

Para cada cuenta de gasto (5x) calcula la media y desviación típica
histórica del importe (`Debe`). Una transacción se marca como anomalía
si su z-score `|Debe − μ| / σ` supera un umbral configurable
(default 2.0 → sensible).

Reglas:
  - Solo se calcula para cuentas con prefijo `5` y `Debe > 0`.
  - Solo se consideran categorías con al menos `min_samples` filas
    (default 5) — con menos historial el estadístico no es fiable.
  - Categorías con `std == 0` (todos los importes iguales) se ignoran.
  - Se ignoran filas pasivas de TR (Saveback / RoundUp / Cashback /
    Interest / Bonificación) — su valor es siempre marginal y
    distorsionaría el µ/σ.
"""

from __future__ import annotations

import pandas as pd

from constants import PREFIX_GASTOS
from data.gsheets import clean_cuenta_col
from services.analytics import _PASIVE_CATEGORIES_RE


def compute_anomalies(
    df_diario: pd.DataFrame,
    *,
    z_threshold: float = 2.0,
    min_samples: int = 5,
) -> pd.DataFrame:
    """
    Calcula z-score por (Cuenta, fila) para gastos y devuelve sus anomalías.

    Args:
        df_diario: Libro Diario completo.
        z_threshold: Umbral de z-score absoluto para marcar como anomalía.
        min_samples: Mínimo de filas en la categoría para considerarla.

    Returns:
        DataFrame con las MISMAS columnas que `df_diario` + estas extras
        (solo presentes en las filas analizadas — gastos válidos):
            cat_mean        — media histórica de la categoría
            cat_std         — desviación típica histórica
            cat_count       — número de filas analizadas en la categoría
            z_score         — (Debe − cat_mean) / cat_std
            is_anomaly      — True si abs(z_score) > z_threshold
        Las filas que no se analizaron (no son gasto, std=0, < min_samples)
        no aparecen en el resultado.
    """
    if df_diario is None or df_diario.empty:
        return pd.DataFrame()

    df = clean_cuenta_col(df_diario.copy())
    df["Debe"] = pd.to_numeric(df["Debe"], errors="coerce").fillna(0.0)

    # Solo gastos con Debe > 0
    mask_gasto = df["Nº Cuenta"].str.startswith(PREFIX_GASTOS, na=False) & (df["Debe"] > 0)
    df_gastos = df[mask_gasto].copy()
    if df_gastos.empty:
        return pd.DataFrame()

    # Excluir filas pasivas (Saveback / RoundUp / Cashback / Interest / Bonificación)
    blob = (
        df_gastos.get("Categoría", "").astype(str)
        + " "
        + df_gastos.get("Descripción", "").astype(str)
    )
    mask_active = ~blob.str.contains(
        _PASIVE_CATEGORIES_RE.pattern, regex=True, case=False, na=False
    )
    df_gastos = df_gastos[mask_active]
    if df_gastos.empty:
        return pd.DataFrame()

    # Estadísticos por Cuenta
    stats = df_gastos.groupby("Cuenta")["Debe"].agg(
        cat_mean="mean", cat_std="std", cat_count="count"
    )
    # Filtrar categorías válidas (suficientes datos y varianza > 0)
    valid_stats = stats[(stats["cat_count"] >= min_samples) & (stats["cat_std"] > 0)]
    if valid_stats.empty:
        return pd.DataFrame()

    # Merge estadísticos con las filas
    df_with_stats = df_gastos.merge(valid_stats, how="inner", left_on="Cuenta", right_index=True)

    # z-score y flag
    df_with_stats["z_score"] = (df_with_stats["Debe"] - df_with_stats["cat_mean"]) / df_with_stats[
        "cat_std"
    ]
    df_with_stats["is_anomaly"] = df_with_stats["z_score"].abs() > z_threshold

    return df_with_stats


def make_anomaly_label(z_score: float) -> str:
    """Devuelve el label corto para una anomalía: '⚠ inusual (+2.3σ)'."""
    sign = "+" if z_score >= 0 else ""
    return f"⚠ inusual ({sign}{z_score:.1f}σ)"

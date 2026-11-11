"""
subscriptions.py — Detector de suscripciones / gastos recurrentes.

Agrupa transacciones por similitud de descripción y verifica que sus
intervalos entre ocurrencias sean regulares (semanal, mensual,
trimestral o anual, dentro de una tolerancia). El objetivo es
descubrir fugas silenciosas tipo Netflix, gimnasio, dominios, IPTV,
seguros, etc.

Algoritmo:
  1. Filtrar a gastos (Debe > 0 en cuentas 5x), excluir filas pasivas
     (Saveback/RoundUp/etc.) y limitar a los últimos `lookback_days`
     (default 365 días).
  2. Normalizar la descripción: lowercase, quitar dígitos, fechas,
     códigos de referencia, espacios extra. Coger los primeros 30 chars
     como "fingerprint léxico" del comercio.
  3. Agrupar por fingerprint y filtrar grupos con ≥ `min_occurrences`
     (default 3) ocurrencias.
  4. Para cada grupo, calcular la **mediana** del intervalo entre
     ocurrencias consecutivas y clasificarlo:
        - Semanal:    6 ≤ mediana ≤ 9 días
        - Mensual:   25 ≤ mediana ≤ 35 días
        - Trimestral: 80 ≤ mediana ≤ 100 días
        - Anual:    350 ≤ mediana ≤ 380 días
     Si no encaja en ninguno → descartar (no es recurrente regular).
  5. Devolver: nombre, intervalo, importe medio, última fecha, próxima
     prevista, gasto anual estimado y nº ocurrencias detectadas.
"""

from __future__ import annotations

import re
from datetime import timedelta
from statistics import median

import pandas as pd

from constants import PREFIX_GASTOS
from data.gsheets import clean_cuenta_col
from services.analytics import _PASIVE_CATEGORIES_RE

# Intervalos canónicos (label, mediana_min_dias, mediana_max_dias,
# multiplicador_a_anual)
_INTERVALS: list[tuple[str, int, int, float]] = [
    ("Semanal", 6, 9, 52.0),
    ("Mensual", 25, 35, 12.0),
    ("Trimestral", 80, 100, 4.0),
    ("Anual", 350, 380, 1.0),
]

# Regex para normalizar descripciones — quitar dígitos, fechas y refs.
_DIGITS_RE = re.compile(r"\d+")
_PUNCT_RE = re.compile(r"[^\w\s]")  # mantiene letras, dígitos y espacios
_MULTI_WS_RE = re.compile(r"\s+")


def _normalize_desc(desc: str) -> str:
    """Reduce descripciones a un fingerprint estable: lowercase, sin
    números, sin puntuación, espacios colapsados, primeros 30 chars."""
    if not desc:
        return ""
    s = str(desc).lower()
    s = _DIGITS_RE.sub(" ", s)
    s = _PUNCT_RE.sub(" ", s)
    s = _MULTI_WS_RE.sub(" ", s).strip()
    return s[:30]


def _classify_interval(median_days: float) -> tuple[str, float] | None:
    """Devuelve `(label, factor_anualización)` o None si no es recurrente regular."""
    for label, lo, hi, factor in _INTERVALS:
        if lo <= median_days <= hi:
            return label, factor
    return None


def detect_subscriptions(
    df_diario: pd.DataFrame,
    *,
    lookback_days: int = 365,
    min_occurrences: int = 3,
) -> pd.DataFrame:
    """
    Detecta gastos recurrentes en el Libro Diario.

    Args:
        df_diario: Libro Diario completo.
        lookback_days: Ventana de análisis hacia atrás (default 1 año).
        min_occurrences: Mínimo de ocurrencias para considerar recurrente.

    Returns:
        DataFrame con columnas:
            Nombre          — descripción más representativa del grupo
            Categoría       — nombre de cuenta más frecuente
            Intervalo       — Semanal / Mensual / Trimestral / Anual
            Importe medio   — media del Debe del grupo (€)
            Ocurrencias     — nº de pagos detectados en la ventana
            Última fecha    — fecha del último pago
            Próximo pago    — fecha esperada del siguiente
            Coste anual est.— importe medio × factor de anualización
            Fingerprint     — id interno (para deduplicado / debug)
        Ordenado por Coste anual descendente.
    """
    cols = [
        "Nombre",
        "Categoría",
        "Intervalo",
        "Importe medio",
        "Ocurrencias",
        "Última fecha",
        "Próximo pago",
        "Coste anual est.",
        "Fingerprint",
    ]
    if df_diario is None or df_diario.empty:
        return pd.DataFrame(columns=cols)

    df = clean_cuenta_col(df_diario.copy())
    df["Debe"] = pd.to_numeric(df["Debe"], errors="coerce").fillna(0.0)
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df = df.dropna(subset=["Fecha"])

    # Solo gastos con Debe > 0 en los últimos `lookback_days`
    if lookback_days > 0:
        cutoff = pd.Timestamp.today().normalize() - pd.Timedelta(days=lookback_days)
        df = df[df["Fecha"] >= cutoff]
    df = df[df["Nº Cuenta"].str.startswith(PREFIX_GASTOS, na=False) & (df["Debe"] > 0)]
    if df.empty:
        return pd.DataFrame(columns=cols)

    # Excluir filas pasivas (Saveback / RoundUp / Cashback / Interest / Bonificación)
    blob = df.get("Categoría", "").astype(str) + " " + df.get("Descripción", "").astype(str)
    mask_active = ~blob.str.contains(
        _PASIVE_CATEGORIES_RE.pattern, regex=True, case=False, na=False
    )
    df = df[mask_active]
    if df.empty:
        return pd.DataFrame(columns=cols)

    # Fingerprint léxico
    df["_fp"] = df["Descripción"].fillna("").map(_normalize_desc)
    df = df[df["_fp"] != ""]

    results: list[dict] = []
    for fp, group in df.groupby("_fp"):
        if len(group) < min_occurrences:
            continue

        fechas = sorted(group["Fecha"].dt.normalize().unique())
        if len(fechas) < min_occurrences:
            continue  # mismas fechas duplicadas no cuentan

        # Mediana del intervalo entre fechas consecutivas (en días)
        deltas = [(fechas[i] - fechas[i - 1]).days for i in range(1, len(fechas))]
        if not deltas:
            continue
        median_delta = float(median(deltas))

        classification = _classify_interval(median_delta)
        if classification is None:
            continue
        label, factor = classification

        # Nombre más representativo: la descripción más larga (suele ser
        # la "completa" sin truncar). En empate, la más reciente.
        descs = group["Descripción"].fillna("").astype(str)
        nombre = max(descs, key=lambda s: (len(s), s))[:80].strip()
        if not nombre:
            nombre = fp.title()

        # Categoría más frecuente del grupo
        categoria = group["Cuenta"].astype(str).mode().iloc[0] if not group["Cuenta"].empty else ""

        importe_medio = float(group["Debe"].mean())
        ultima = pd.Timestamp(fechas[-1])
        proximo = ultima + timedelta(days=round(median_delta))
        coste_anual = importe_medio * factor

        results.append(
            {
                "Nombre": nombre,
                "Categoría": categoria,
                "Intervalo": label,
                "Importe medio": round(importe_medio, 2),
                "Ocurrencias": len(group),
                "Última fecha": ultima,
                "Próximo pago": proximo,
                "Coste anual est.": round(coste_anual, 2),
                "Fingerprint": fp,
            }
        )

    if not results:
        return pd.DataFrame(columns=cols)

    out = pd.DataFrame(results)
    return out.sort_values("Coste anual est.", ascending=False).reset_index(drop=True)

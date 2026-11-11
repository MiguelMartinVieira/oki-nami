"""
roundup.py — Round-up manual hacia Berkshire Hathaway (cuenta 141).

Un "round-up" toma un gasto de X,YZ € (pagado **fuera de TR** —
en efectivo, hucha o cualquier cuenta no-121) y simula lo que TR
habría hecho automáticamente: transfiere `ceil(X,YZ) − X,YZ` desde
TR (121) a Berkshire (141) como partida doble:

    Fila 1: Debe  → 141 (Berkshire Hathaway) = céntimos
    Fila 2: Haber → 121 (Trade Republic)     = céntimos

**Importante** — solo se proponen para round-up los gastos cuya
contrapartida (fila Haber del par de partida doble) NO sea la cuenta
121. Razón: TR ya aplica Round-Up automático a todos los gastos que
pasan por su tarjeta, así que duplicarlo sería contar dos veces. Los
gastos elegibles son típicamente los pagados en efectivo (111 Cartera,
112 Hucha) o desde otras cuentas.

Excluye además filas cuyo Categoría/Descripción matchee Saveback /
RoundUp / Cashback / Interest / Bonificación (paranoia adicional —
estos ya están filtrados por el chequeo anterior, pero lo dejamos
defensivamente).
"""

from __future__ import annotations

import math
from datetime import date as date_cls
from datetime import datetime

import pandas as pd

from constants import CUENTA_BERKSHIRE, CUENTA_TR, HISTORY_START_DATE, PREFIX_GASTOS
from data.gsheets import clean_cuenta_col
from services.analytics import _PASIVE_CATEGORIES_RE


# Hash determinista por (fecha, importe, descripción) — sirve para
# evitar redondear dos veces el mismo gasto entre sesiones.
def _txn_fingerprint(row: pd.Series) -> str:
    fecha = row.get("Fecha")
    if isinstance(fecha, (pd.Timestamp, datetime, date_cls)):
        fecha_str = pd.Timestamp(fecha).strftime("%Y-%m-%d")
    else:
        fecha_str = str(fecha or "")
    debe = float(row.get("Debe") or 0)
    desc = str(row.get("Descripción") or "")[:80]
    return f"{fecha_str}|{debe:.2f}|{desc}"


def round_up_cents(amount: float) -> float:
    """Devuelve los céntimos que faltan para llegar al siguiente euro.

    >>> round_up_cents(15.30)
    0.7
    >>> round_up_cents(15.00)  # ya es entero
    0.0
    >>> round_up_cents(0.01)
    0.99
    """
    if amount <= 0:
        return 0.0
    ceil_eur = math.ceil(amount - 1e-9)
    cents = ceil_eur - amount
    # Redondeo a 2 decimales para evitar 0.6999999...
    return round(cents, 2)


_EMPTY_COLS = ["Fecha", "Cuenta", "Categoría", "Descripción", "Debe", "Céntimos", "Fingerprint"]


def _date_key(value) -> str:
    """Normaliza una fecha a 'YYYY-MM-DD' independiente del tipo (Timestamp, str, date)."""
    try:
        return pd.Timestamp(value).strftime("%Y-%m-%d")
    except Exception:
        return str(value)


def _expenses_not_paid_via_tr(df_clean: pd.DataFrame) -> pd.DataFrame:
    """Devuelve solo las filas de gasto (Debe > 0 en cuenta 5x) cuya
    contrapartida (fila Haber del par de partida doble) NO sea la 121.

    Implementación: para cada par de partida doble, ambas filas comparten
    `(Fecha, Descripción, importe)`. Construimos un set de claves donde la
    121 aparece (en cualquier lado, Debe o Haber) y excluimos los gastos
    cuya clave coincida.
    """
    df_clean = df_clean.copy()
    df_clean["_amount"] = (
        pd.to_numeric(df_clean.get("Debe"), errors="coerce").fillna(0.0)
        + pd.to_numeric(df_clean.get("Haber"), errors="coerce").fillna(0.0)
    ).round(2)
    df_clean["_date_key"] = df_clean["Fecha"].apply(_date_key)
    df_clean["_desc_key"] = df_clean.get("Descripción", "").astype(str)

    # Claves (Fecha, Descripción, importe) donde la 121 está implicada
    df_tr_rows = df_clean[df_clean["Nº Cuenta"] == CUENTA_TR]
    tr_keys: set[tuple[str, str, float]] = set(
        zip(
            df_tr_rows["_date_key"],
            df_tr_rows["_desc_key"],
            df_tr_rows["_amount"].round(2),
            strict=False,
        )
    )

    gastos = df_clean[
        df_clean["Nº Cuenta"].str.startswith(PREFIX_GASTOS, na=False)
        & (pd.to_numeric(df_clean["Debe"], errors="coerce").fillna(0.0) > 0)
    ].copy()

    if gastos.empty:
        return gastos

    def _has_tr_counterpart(row: pd.Series) -> bool:
        return (
            row["_date_key"],
            row["_desc_key"],
            round(float(row["_amount"]), 2),
        ) in tr_keys

    gastos["_from_tr"] = gastos.apply(_has_tr_counterpart, axis=1)
    return gastos[~gastos["_from_tr"]].drop(
        columns=["_amount", "_from_tr", "_date_key", "_desc_key"]
    )


def get_pending_roundups(
    df_diario: pd.DataFrame,
    *,
    days_back: int = 0,
    limit: int | None = None,
    already_done_fingerprints: set[str] | None = None,
) -> pd.DataFrame:
    """
    Devuelve TODOS los gastos elegibles para round-up manual (desde HISTORY_START_DATE).

    Reglas:
    - Solo cuentas del grupo 5 (gastos) con `Debe > 0`.
    - **Solo gastos cuya contrapartida NO sea la 121** (TR ya aplica
      Round-Up automático a sus pagos). Es la regla clave del módulo.
    - Excluye filas cuyo `Categoría + Descripción` matchee Saveback /
      RoundUp / Cashback / Interest / Bonificación.
    - Excluye importes que ya son enteros (céntimos = 0).
    - **Filtro temporal único**: solo gastos a partir de `HISTORY_START_DATE`
      (default global del dashboard). El parámetro `days_back` se mantiene
      por compatibilidad pero por defecto está desactivado (0).
    - Excluye fingerprints ya redondeados (parámetro opcional).

    Args:
        days_back: si > 0, además filtra a los últimos N días (encima del
            cutoff global HISTORY_START_DATE). Default 0 = sin ventana móvil.
        limit: si se pasa, recorta a los N más recientes. Default None = todos.

    Returns DataFrame con columnas:
        Fecha · Cuenta · Categoría · Descripción · Debe · Céntimos · Fingerprint
    """
    if df_diario is None or df_diario.empty:
        return pd.DataFrame(columns=_EMPTY_COLS)

    df = clean_cuenta_col(df_diario.copy())
    df["Debe"] = pd.to_numeric(df["Debe"], errors="coerce").fillna(0.0)
    df["Haber"] = pd.to_numeric(df["Haber"], errors="coerce").fillna(0.0)
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df = df.dropna(subset=["Fecha"])

    # Filtro CLAVE: solo gastos NO pagados desde TR (121)
    df = _expenses_not_paid_via_tr(df)
    if df.empty:
        return pd.DataFrame(columns=_EMPTY_COLS)

    # Cutoff global del dashboard (HISTORY_START_DATE = 2026-03-19)
    history_start = pd.Timestamp(HISTORY_START_DATE)
    df = df[df["Fecha"] >= history_start]

    # Ventana móvil adicional opcional (días desde hoy)
    if days_back > 0:
        cutoff = pd.Timestamp.today().normalize() - pd.Timedelta(days=days_back)
        df = df[df["Fecha"] >= cutoff]

    if df.empty:
        return pd.DataFrame(columns=_EMPTY_COLS)

    # Excluir pasivas (Saveback / Round Up / Cashback / Interest / Bonificación)
    blob = df.get("Categoría", "").astype(str) + " " + df.get("Descripción", "").astype(str)
    mask_no_passive = ~blob.str.contains(
        _PASIVE_CATEGORIES_RE.pattern, regex=True, case=False, na=False
    )
    df = df[mask_no_passive]

    # Calcular céntimos
    df["Céntimos"] = df["Debe"].apply(round_up_cents)
    df = df[df["Céntimos"] > 0]

    # Excluir ya hechos
    df["Fingerprint"] = df.apply(_txn_fingerprint, axis=1)
    if already_done_fingerprints:
        df = df[~df["Fingerprint"].isin(already_done_fingerprints)]

    if df.empty:
        return pd.DataFrame(columns=_EMPTY_COLS)

    cols = ["Fecha", "Cuenta", "Categoría", "Descripción", "Debe", "Céntimos", "Fingerprint"]
    df_sorted = df.sort_values("Fecha", ascending=False)[cols].reset_index(drop=True)
    if limit is not None and limit > 0:
        df_sorted = df_sorted.head(limit)
    return df_sorted


def build_roundup_journal_rows(
    amount_cents: float,
    source_desc: str,
    *,
    brk_price_eur: float | None = None,
) -> list[list]:
    """Construye el par de partida doble para un round-up artificial.

    Movimiento: 141 Berkshire ← 121 Trade Republic.

    Args:
        amount_cents: importe en euros (p.ej. 0.70 para 70 céntimos).
        source_desc: descripción del gasto origen (se prefija "Round-up …").
        brk_price_eur: precio actual de BRK en EUR. Si se pasa y es >0,
            se añade `quantity: X.XXXXXX` a la descripción para que el
            cálculo dinámico de acciones (`calc_brk_shares`) lo reconozca
            como acciones reales adquiridas.
    """
    fecha_str = datetime.now().strftime("%Y-%m-%d")
    desc = f"Round-up artificial: {source_desc[:60]}"
    if brk_price_eur and brk_price_eur > 0:
        qty = round(amount_cents / brk_price_eur, 6)
        if qty > 0:
            desc = f"{desc} quantity: {qty:.6f}"
    # Formato Diario: [Fecha, NºCuenta, Cuenta(None→fórmula), Categoría, Debe, Haber, Descripción]
    row_debe = [fecha_str, CUENTA_BERKSHIRE, None, "Round-up Manual", amount_cents, None, desc]
    row_haber = [fecha_str, CUENTA_TR, None, "Round-up Manual", None, amount_cents, desc]
    return [row_debe, row_haber]

import math
import re
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

from constants import HISTORY_START_DATE, TTL_SHEETS
from services.utils import extract_quantity


def get_drilldown_data(df: pd.DataFrame, category: str, is_expense: bool) -> pd.DataFrame:
    """
    Genera el DataFrame procesado para el gráfico de drill-down por categoría.
    Limita a los 15 conceptos más representativos y maneja vacíos.
    """
    df_drill = df[df["Cuenta"] == category].copy()
    if df_drill.empty:
        return df_drill

    df_drill["Concepto"] = df_drill.apply(
        lambda r: (
            str(r.get("Descripción", "")).strip()
            if str(r.get("Descripción", "")).strip() not in ("", "nan", "None", "N/A")
            else str(r.get("Categoría", "")).strip()
        ),
        axis=1,
    )
    df_drill["Concepto"] = df_drill["Concepto"].replace(
        {"": "Sin Detalle", "nan": "Sin Detalle", "N/A": "Sin Detalle"}
    )

    col_importe = "Debe" if is_expense else "Haber"
    drill = (
        df_drill.groupby("Concepto")[col_importe]
        .sum()
        .reset_index()
        .sort_values(col_importe, ascending=True)
        .tail(15)
    )
    drill["Concepto"] = drill["Concepto"].apply(
        lambda x: str(x)[:35] + "..." if len(str(x)) > 35 else str(x)
    )

    return drill


def enrich_with_concepto(df: pd.DataFrame, rename_to_cuenta: bool = True) -> pd.DataFrame:
    """
    Añade una columna 'Concepto' basada en Descripción (fallback a Categoría).

    Si rename_to_cuenta=True, sobreescribe la columna 'Cuenta' con el concepto,
    de forma que las funciones de charts.py (que agrupan por 'Cuenta') funcionen
    automáticamente a nivel de concepto sin cambios.
    """
    out = df.copy()
    out["Concepto"] = out.apply(
        lambda r: (
            str(r.get("Descripción", "")).strip()
            if str(r.get("Descripción", "")).strip() not in ("", "nan", "None", "N/A")
            else str(r.get("Categoría", "")).strip()
        ),
        axis=1,
    )
    out["Concepto"] = out["Concepto"].replace(
        {"": "Sin Detalle", "nan": "Sin Detalle", "N/A": "Sin Detalle"}
    )
    # Truncar conceptos largos para legibilidad en gráficos
    out["Concepto"] = out["Concepto"].apply(
        lambda x: str(x)[:30] + "…" if len(str(x)) > 30 else str(x)
    )
    if rename_to_cuenta:
        out["Cuenta"] = out["Concepto"]
    return out


def get_sparkline_data(df_mov: pd.DataFrame, col_importe: str) -> dict[str, pd.Series]:
    """
    Agrupa los datos por mes y cuenta, y retorna un diccionario de Series
    listas para renderizar sparklines de tendencia, ordenadas por importe total.
    """
    if df_mov.empty or "Mes" not in df_mov.columns:
        return {}

    _pivot = df_mov.groupby(["Mes", "Cuenta"])[col_importe].sum().unstack(fill_value=0)
    _cat_order = _pivot.sum().sort_values(ascending=False).index.tolist()

    return {cat: _pivot[cat].tail(6) for cat in _cat_order}


def calc_pnl_op(
    row: pd.Series,
    precio_brk_usd: float,
    usd_to_eur: float,
    precio_fondo: float,
    extract_quantity_func,
) -> tuple[float | None, float | None]:
    """
    Calcula el P&L latente de una operación de inversión.
    Retorna PnL en Euros y el porcentaje.
    """
    cuenta = str(row.get("Nº Cuenta", ""))
    invertido = float(row.get("Debe", 0) or 0)
    if invertido <= 0:
        return None, None
    desc = str(row.get("Descripción", "") or "")
    shares = extract_quantity_func(desc)
    if shares <= 0:
        return None, None

    if cuenta.startswith("141"):  # BRK
        valor_actual = shares * precio_brk_usd * usd_to_eur
    elif cuenta.startswith("142"):  # Vanguard
        valor_actual = shares * precio_fondo
    else:
        return None, None

    pnl = valor_actual - invertido
    pnl_pct = pnl / invertido * 100
    return round(pnl, 2), round(pnl_pct, 2)


# ──────────────────────────────────────────────
# Meta de ahorro mensual + catch-up
# ──────────────────────────────────────────────


def calc_empirical_beta(df_stock: pd.DataFrame, df_benchmark: pd.DataFrame) -> float:
    """Beta empírica = cov(stock, bench) / var(bench) sobre retornos diarios.

    Acepta DataFrames de `yfinance.history()` (columna `Close` + índice Date).
    Devuelve 1.0 si los datos no son suficientes (fallback neutro).
    """
    if df_stock is None or df_benchmark is None:
        return 1.0
    if df_stock.empty or df_benchmark.empty:
        return 1.0

    def _close(df):
        if "Close" in df.columns:
            return df["Close"]
        # Algunos providers usan "Adj Close" o nombres alternativos
        for cand in ("Adj Close", "close", "price", "Price"):
            if cand in df.columns:
                return df[cand]
        # Si solo hay una columna numérica, usarla
        num_cols = df.select_dtypes(include="number").columns
        if len(num_cols) == 1:
            return df[num_cols[0]]
        return None

    s_close = _close(df_stock)
    b_close = _close(df_benchmark)
    if s_close is None or b_close is None:
        return 1.0

    # Alinear por índice (fecha) por si difieren días de trading
    aligned = pd.concat([s_close, b_close], axis=1, join="inner").dropna()
    if len(aligned) < 10:
        return 1.0
    aligned.columns = ["s", "b"]
    rs = aligned["s"].pct_change().dropna()
    rb = aligned["b"].pct_change().dropna()
    common = rs.index.intersection(rb.index)
    if len(common) < 5:
        return 1.0
    rs, rb = rs.loc[common], rb.loc[common]

    var_b = float(rb.var())
    if var_b <= 0 or np.isnan(var_b):
        return 1.0
    cov_sb = float(rs.cov(rb))
    if np.isnan(cov_sb):
        return 1.0
    return round(cov_sb / var_b, 4)


@st.cache_data(ttl=TTL_SHEETS, show_spinner=False)
def calc_meta_mensual(df_diario: pd.DataFrame, meta_anual: float) -> dict:
    """
    Calcula la meta del mes en curso con lógica de *catch-up*:
    si vienes por debajo del ritmo necesario para el año, este mes la barra
    pide más; si vas adelantado, pide menos (mínimo = meta_mes_base ÷ 4).

    Returns dict con:
        mes_num, year, meta_mes_base, meta_mes_objetivo, ahorro_mes,
        ahorro_ytd_pre_mes, meta_ytd_eom, pct_mes
    """
    if df_diario.empty:
        return {
            "mes_num": pd.Timestamp.today().month,
            "year": pd.Timestamp.today().year,
            "meta_mes_base": meta_anual / 12,
            "meta_mes_objetivo": meta_anual / 12,
            "ahorro_mes": 0.0,
            "ahorro_ytd_pre_mes": 0.0,
            "meta_ytd_eom": 0.0,
            "pct_mes": 0.0,
        }

    today = pd.Timestamp.today()
    year_start = max(
        pd.to_datetime(f"{today.year}-01-01"),
        pd.to_datetime(HISTORY_START_DATE),
    )
    month_start = pd.to_datetime(f"{today.year}-{today.month:02d}-01")

    df = df_diario.copy()
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df["Nº Cuenta"] = df["Nº Cuenta"].astype(str).str.strip()

    df_pre = df[(df["Fecha"] >= year_start) & (df["Fecha"] < month_start)]
    df_cm = df[df["Fecha"] >= month_start]

    def _ahorro(_df):
        if _df.empty:
            return 0.0
        mask = _df["Nº Cuenta"].astype(str).str.startswith("14")
        debe = pd.to_numeric(_df[mask]["Debe"], errors="coerce").fillna(0).sum()
        haber = pd.to_numeric(_df[mask]["Haber"], errors="coerce").fillna(0).sum()
        return float(debe - haber)

    ahorro_ytd_pre_mes = _ahorro(df_pre)
    ahorro_mes = _ahorro(df_cm)

    meta_mes_base = meta_anual / 12.0
    meta_ytd_eom = meta_anual * today.month / 12.0
    # Para no salirte del año, este mes hace falta:
    meta_mes_objetivo = max(meta_ytd_eom - ahorro_ytd_pre_mes, meta_mes_base / 4.0)

    pct_mes = (ahorro_mes / meta_mes_objetivo * 100.0) if meta_mes_objetivo > 0 else 0.0

    return {
        "mes_num": int(today.month),
        "year": int(today.year),
        "meta_mes_base": float(meta_mes_base),
        "meta_mes_objetivo": float(meta_mes_objetivo),
        "ahorro_mes": float(ahorro_mes),
        "ahorro_ytd_pre_mes": float(ahorro_ytd_pre_mes),
        "meta_ytd_eom": float(meta_ytd_eom),
        "pct_mes": float(pct_mes),
    }


# ──────────────────────────────────────────────
# Alertas para la cabecera
# ──────────────────────────────────────────────


@st.cache_data(ttl=TTL_SHEETS, show_spinner=False)
def detect_header_alerts(
    df_diario: pd.DataFrame,
    df_historico: pd.DataFrame | None,
    tr_cash: float,
    metalico_fisico: float,
    total_patrimonio: float,
    fondo_emergencia_umbral_meses: float = 3.0,
    categoria_sobre_gasto_umbral: float = 1.5,
) -> list[dict]:
    """
    Devuelve una lista de alertas accionables para mostrar en la cabecera.

    Cada alerta es un dict con `{level, icon, title, detail}` donde
    `level ∈ {"critical", "warning", "info"}`.
    """
    alerts: list[dict] = []

    if df_diario is None or df_diario.empty:
        return alerts

    df = df_diario.copy()
    df["Nº Cuenta"] = df["Nº Cuenta"].astype(str).str.strip()

    # ── 1. Fondo de emergencia bajo ──
    df_gastos = df[df["Nº Cuenta"].str.startswith("5")].copy()
    if not df_gastos.empty:
        df_gastos["Mes"] = pd.to_datetime(df_gastos["Fecha"]).dt.to_period("M")
        gasto_medio = df_gastos.groupby("Mes")["Debe"].sum().mean()
        liquidez = float(tr_cash + metalico_fisico)
        meses_cubiertos = (liquidez / gasto_medio) if gasto_medio and gasto_medio > 0 else 0.0
        if meses_cubiertos < fondo_emergencia_umbral_meses:
            alerts.append(
                {
                    "level": "critical",
                    "icon": "🛡️",
                    "title": "Fondo de emergencia bajo",
                    "detail": f"{meses_cubiertos:.1f} meses (obj: {fondo_emergencia_umbral_meses:.0f})",
                }
            )

    # ── 2. Categorías de gasto > umbral × media histórica ──
    if not df_gastos.empty:
        cat_mes = df_gastos.groupby(["Mes", "Cuenta"])["Debe"].sum().unstack(fill_value=0)
        if len(cat_mes) >= 3:  # al menos 2 meses anteriores + el actual
            mes_actual = cat_mes.index.max()
            historico = cat_mes.loc[cat_mes.index < mes_actual]
            if not historico.empty:
                media_hist = historico.mean()
                actual = cat_mes.loc[mes_actual]
                for cat in actual.index:
                    media = float(media_hist.get(cat, 0.0))
                    val = float(actual.get(cat, 0.0))
                    if media > 5.0 and val > media * categoria_sobre_gasto_umbral:
                        pct = (val / media - 1.0) * 100.0
                        alerts.append(
                            {
                                "level": "warning",
                                "icon": "📈",
                                "title": f"{cat}: +{pct:.0f}% vs media",
                                "detail": f"Mes: {val:,.0f}€ | Media: {media:,.0f}€",
                            }
                        )

    # ── 3. Nuevo máximo de patrimonio ──
    if df_historico is not None and not df_historico.empty and "Total" in df_historico.columns:
        try:
            hist_max = float(pd.to_numeric(df_historico["Total"], errors="coerce").dropna().max())
            # Toleramos un 0.5 % de margen para no disparar en cada céntimo
            if total_patrimonio >= hist_max * 1.005 and hist_max > 0:
                alerts.append(
                    {
                        "level": "info",
                        "icon": "🚀",
                        "title": "Máximo patrimonio",
                        "detail": f"Actual: {total_patrimonio:,.0f}€ | Ant: {hist_max:,.0f}€",
                    }
                )
        except (TypeError, ValueError):
            pass

    return alerts


# ──────────────────────────────────────────────
# Coste real de un gasto (oportunidad + bruto equivalente)
# ──────────────────────────────────────────────


def calc_real_cost(
    gasto: float,
    tasa_ahorro_pct: float,
    rent_anual_pct: float,
    years: int = 10,
) -> dict:
    """
    Calcula dos visiones del "coste real" de un gasto.

    - bruto_equivalente: cuánto bruto necesitas ganar para gastar `gasto`
      manteniendo tu tasa de ahorro (gasto ÷ (1 − tasa)). Si tasa ≥ 1
      o ≤ 0, el ratio queda en 1.0.
    - oportunidad: cuánto valdrían esos euros invertidos a la rentabilidad
      anual histórica de tu cartera durante `years` años.
    """
    tasa = max(min(tasa_ahorro_pct / 100.0, 0.99), 0.0)
    rent = rent_anual_pct / 100.0

    bruto_equivalente = gasto / (1.0 - tasa) if (1.0 - tasa) > 0 else gasto
    oportunidad = gasto * ((1.0 + rent) ** years) if rent > -1.0 else gasto

    return {
        "gasto": float(gasto),
        "tasa_ahorro_pct": float(tasa_ahorro_pct),
        "rent_anual_pct": float(rent_anual_pct),
        "years": int(years),
        "bruto_equivalente": float(round(bruto_equivalente, 2)),
        "oportunidad": float(round(oportunidad, 2)),
    }


@st.cache_data(ttl=TTL_SHEETS, show_spinner=False)
def calc_cumulative_opportunity_cost(
    df_diario: pd.DataFrame,
    rent_anual_pct: float = 8.0,
    years_horizon: int = 10,
    months_lookback: int = 6,
    filter_account: str | None = None,
) -> dict:
    """Coste de oportunidad acumulado de los gastos discrecionales recientes.

    Si todos los gastos de los últimos `months_lookback` meses hubieran ido a
    una inversión a `rent_anual_pct` durante `years_horizon` años, este es
    el patrimonio futuro que dejas de tener.

    Args:
        df_diario: Libro Diario completo.
        rent_anual_pct: rentabilidad anual estimada de la cartera (%).
        years_horizon: horizonte de la capitalización (años).
        months_lookback: ventana de gastos a integrar (meses hacia atrás).
        filter_account: si se pasa, filtra a una sola Cuenta (categoría 5x).

    Returns:
        {
          "total_gastado": float,           # suma del Debe en la ventana
          "oportunidad_total": float,       # total_gastado × (1+r)^t
          "ganancia_neta": float,           # oportunidad_total − total_gastado
          "factor": float,                  # (1+r)^t
          "n_meses": int,
          "top_categorias": list[dict]      # ordenadas desc por gasto
        }
    """
    factor = (1.0 + rent_anual_pct / 100.0) ** years_horizon
    empty = {
        "total_gastado": 0.0,
        "oportunidad_total": 0.0,
        "ganancia_neta": 0.0,
        "factor": float(factor),
        "n_meses": int(months_lookback),
        "top_categorias": [],
    }

    if df_diario is None or df_diario.empty:
        return empty

    df = df_diario.copy()
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df = df.dropna(subset=["Fecha"])
    cutoff = pd.Timestamp.today() - pd.DateOffset(months=months_lookback)
    df = df[df["Fecha"] >= cutoff]
    df = df[df["Nº Cuenta"].astype(str).str.startswith("5")]
    if filter_account:
        df = df[df["Cuenta"] == filter_account]
    if df.empty:
        return empty

    df["Debe"] = pd.to_numeric(df["Debe"], errors="coerce").fillna(0.0)
    total = float(df["Debe"].sum())
    if total <= 0:
        return empty

    op_total = total * factor
    por_cat = df.groupby("Cuenta")["Debe"].sum().sort_values(ascending=False).head(6)
    top_categorias = [
        {
            "categoria": str(cat),
            "gastado": float(v),
            "oportunidad": float(v * factor),
            "pct_del_total": float(v / total * 100.0),
        }
        for cat, v in por_cat.items()
    ]

    return {
        "total_gastado": total,
        "oportunidad_total": op_total,
        "ganancia_neta": op_total - total,
        "factor": float(factor),
        "n_meses": int(months_lookback),
        "top_categorias": top_categorias,
    }


# ──────────────────────────────────────────────
# FIFO Cost-basis para inversiones (España)
# ──────────────────────────────────────────────


@st.cache_data(ttl=TTL_SHEETS, show_spinner=False)
def build_fifo_lots(
    df_account: pd.DataFrame,
    precio_actual_eur: float,
    fx_rate: float = 1.0,
    cost_adjustment: float = 0.0,
) -> pd.DataFrame:
    """
    Construye la tabla de lotes FIFO para una cuenta de inversión (141 ó 142).

    Cada fila del Diario con `Debe > 0` y `quantity:` en la descripción
    es un lote. El precio medio del lote se obtiene como `Debe / quantity`.

    Args:
        df_account: filas del Diario filtradas por la cuenta de inversión.
        precio_actual_eur: precio actual unitario del activo (en €). Para
            BRK pasar `precio_usd * fx_rate` ya convertido o `precio_usd`
            con `fx_rate` ≠ 1.
        fx_rate: tipo de cambio si `precio_actual_eur` está en USD.
        cost_adjustment: plusvalía histórica acumulada previa (€) a descontar
            del coste del lote inicial (ej. `VANGUARD_HISTORICAL_GAIN`),
            asegurando que el coste neto, precio medio y P&L de la tabla FIFO
            coincidan con las métricas superiores del dashboard.

    Returns DataFrame con columnas:
        Fecha · Acciones · Coste (€) · Precio Medio (€) · Valor Actual (€) ·
        P&L (€) · P&L (%)
    """
    if df_account.empty:
        return pd.DataFrame(
            columns=[
                "Fecha",
                "Acciones",
                "Coste (€)",
                "Precio Medio (€)",
                "Valor Actual (€)",
                "P&L (€)",
                "P&L (%)",
            ]
        )

    df = df_account.copy()
    df = df[pd.to_numeric(df["Debe"], errors="coerce").fillna(0) > 0].copy()
    df["Acciones"] = df["Descripción"].apply(extract_quantity)
    df = df[df["Acciones"] > 0]
    if df.empty:
        return pd.DataFrame(
            columns=[
                "Fecha",
                "Acciones",
                "Coste (€)",
                "Precio Medio (€)",
                "Valor Actual (€)",
                "P&L (€)",
                "P&L (%)",
            ]
        )

    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df = df.sort_values("Fecha").reset_index(drop=True)
    df["Coste"] = pd.to_numeric(df["Debe"], errors="coerce").fillna(0.0)

    # Ajuste por plusvalías históricas previas (ej. Vanguard antes del checkpoint):
    # Restamos cost_adjustment del coste del primer lote para reflejar el verdadero
    # capital invertido out-of-pocket, alineando el precio medio y P&L con las tarjetas.
    if cost_adjustment > 0 and not df.empty:
        df.loc[df.index[0], "Coste"] = max(
            0.0, float(df.loc[df.index[0], "Coste"]) - cost_adjustment
        )

    df["Precio Medio"] = df["Coste"] / df["Acciones"]
    precio_eur = precio_actual_eur * fx_rate
    df["Valor Actual"] = df["Acciones"] * precio_eur
    df["P&L (€)"] = df["Valor Actual"] - df["Coste"]
    df["P&L (%)"] = df.apply(
        lambda r: (r["P&L (€)"] / r["Coste"] * 100.0) if r["Coste"] > 0 else 0.0,
        axis=1,
    )

    return df[
        [
            "Fecha",
            "Acciones",
            "Coste",
            "Precio Medio",
            "Valor Actual",
            "P&L (€)",
            "P&L (%)",
        ]
    ].rename(
        columns={
            "Coste": "Coste (€)",
            "Precio Medio": "Precio Medio (€)",
            "Valor Actual": "Valor Actual (€)",
        }
    )


def simulate_fifo_sale(df_lots: pd.DataFrame, importe_venta_eur: float) -> dict[str, Any]:
    """
    Simula una venta FIFO consumiendo lotes hasta cubrir `importe_venta_eur`.

    Returns dict con:
        lotes_consumidos: list[dict{fecha, acciones, coste, valor, plusvalia}]
        coste_total · valor_total · plusvalia
        importe_solicitado · importe_ejecutado · acciones_total
    """
    out: dict[str, Any] = {
        "lotes_consumidos": [],
        "coste_total": 0.0,
        "valor_total": 0.0,
        "plusvalia": 0.0,
        "importe_solicitado": float(importe_venta_eur),
        "importe_ejecutado": 0.0,
        "acciones_total": 0.0,
    }
    if df_lots.empty or importe_venta_eur <= 0:
        return out

    pending = float(importe_venta_eur)
    for _, lote in df_lots.iterrows():
        if pending <= 0:
            break
        valor_lote = float(lote["Valor Actual (€)"])
        precio_eur = valor_lote / lote["Acciones"] if lote["Acciones"] > 0 else 0.0
        if precio_eur <= 0:
            continue

        if valor_lote <= pending:
            acciones_vendidas = float(lote["Acciones"])
            valor_vendido = valor_lote
            coste_vendido = float(lote["Coste (€)"])
        else:
            acciones_vendidas = pending / precio_eur
            valor_vendido = pending
            # Coste proporcional al porcentaje del lote consumido
            prop = acciones_vendidas / lote["Acciones"]
            coste_vendido = float(lote["Coste (€)"]) * prop

        plusv = valor_vendido - coste_vendido
        out["lotes_consumidos"].append(
            {
                "fecha": lote["Fecha"],
                "acciones": acciones_vendidas,
                "coste": coste_vendido,
                "valor": valor_vendido,
                "plusvalia": plusv,
            }
        )
        out["acciones_total"] += acciones_vendidas
        out["coste_total"] += coste_vendido
        out["valor_total"] += valor_vendido
        out["plusvalia"] += plusv
        pending -= valor_vendido

    out["importe_ejecutado"] = float(importe_venta_eur - max(pending, 0.0))
    return out


# ──────────────────────────────────────────────
# Métricas "Pay Yourself First" & Correlación de Gasto Oportunista
# ──────────────────────────────────────────────

_PASIVE_CATEGORIES_RE = re.compile(
    r"saveback|round\s*[-_ ]?up|cashback|round\s*ups?|interest\s*payment|bonificaci[oó]n",
    re.IGNORECASE,
)


def _is_active_investment_row(row: pd.Series) -> bool:
    """Determina si una fila del Diario es una **inversión activa** (Savings Plan,
    compra directa) vs **pasiva** (Saveback, Round Up, Cashback).

    Sólo las inversiones activas cuentan para Pay Yourself First: las pasivas
    son automatismos de TR (1 % cashback en gastos, redondeo de pagos a euro)
    que ocurren sin decisión consciente del usuario y distorsionarían la
    medida de "cuánto tardo en invertir lo que cobro".
    """
    cat = str(row.get("Categoría", "") or "")
    desc = str(row.get("Descripción", "") or "")
    blob = f"{cat} {desc}"
    return not bool(_PASIVE_CATEGORIES_RE.search(blob))


@st.cache_data(ttl=TTL_SHEETS, show_spinner=False)
def calc_pay_yourself_first_stats(df_diario: pd.DataFrame) -> tuple[float, list[dict]]:
    """
    Calcula el tiempo de reacción medio (en días) entre que Miguel recibe
    ingresos (4x) y realiza una **inversión activa** (Savings Plan, compra
    directa en 141/142).

    Se excluyen automatismos pasivos: Saveback, Round Up, Cashback,
    Interest Payment, Bonificación. Esas inversiones ocurren sin
    decisión consciente y no reflejan la disciplina Pay Yourself First.

    Returns:
        tuple[float, list[dict]]: (promedio_dias, lista_de_emparejamientos)
    """
    if df_diario.empty:
        return 0.0, []

    df = df_diario.copy()
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df = df.dropna(subset=["Fecha"]).sort_values("Fecha")

    # Filtrar ingresos: Nº Cuenta empieza por '4', Haber > 0 (asientos de entrada)
    df_incomes = df[
        (df["Nº Cuenta"].astype(str).str.startswith("4"))
        & (pd.to_numeric(df["Haber"], errors="coerce").fillna(0.0) > 0)
    ].copy()

    # Inversiones: 141 o 142 con Debe > 0, **excluyendo pasivas** (Saveback, RoundUp...)
    df_investments = df[
        (df["Nº Cuenta"].astype(str).isin(["141", "142"]))
        & (pd.to_numeric(df["Debe"], errors="coerce").fillna(0.0) > 0)
    ].copy()
    if not df_investments.empty:
        df_investments = df_investments[df_investments.apply(_is_active_investment_row, axis=1)]

    if df_incomes.empty or df_investments.empty:
        return 0.0, []

    lags = []
    for _, inc in df_incomes.iterrows():
        inc_date = inc["Fecha"]
        # Buscar la primera inversión que se realice en la fecha de ingreso o posterior
        after_inv = df_investments[df_investments["Fecha"] >= inc_date]
        if not after_inv.empty:
            first_inv = after_inv.iloc[0]
            first_inv_date = first_inv["Fecha"]
            days = (first_inv_date - inc_date).days
            lags.append(
                {
                    "income_date": inc_date.strftime("%Y-%m-%d"),
                    "income_desc": str(inc.get("Descripción", "Ingreso")),
                    "income_amount": float(inc["Haber"]),
                    "investment_date": first_inv_date.strftime("%Y-%m-%d"),
                    "investment_desc": str(first_inv.get("Descripción", "Inversión")),
                    "investment_amount": float(first_inv["Debe"]),
                    "days": days,
                }
            )

    if not lags:
        return 0.0, []

    avg_days = sum(item["days"] for item in lags) / len(lags)
    return round(avg_days, 1), lags


@st.cache_data(ttl=TTL_SHEETS, show_spinner=False)
def calc_balance_spending_correlation(
    df_diario: pd.DataFrame,
) -> tuple[float, pd.DataFrame]:
    """
    Calcula si existe correlación estadística (Pearson) entre el saldo líquido disponible (121 TR)
    y el ritmo de gastos discrecionales del grupo 5x (suavizado con ventana móvil de 7 días).

    Returns:
        tuple[float, pd.DataFrame]: (coeficiente_r, df_diario_correlacionado)
    """
    if df_diario.empty:
        return 0.0, pd.DataFrame()

    df = df_diario.copy()
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df = df.dropna(subset=["Fecha"]).sort_values("Fecha")

    start_date = df["Fecha"].min()
    end_date = df["Fecha"].max()
    all_dates = pd.date_range(start=start_date, end=end_date, freq="D")

    # 1. Calcular el saldo diario acumulado de la 121 (Trade Republic),
    #    descontando el saldo de la 133 (Bokatas ONG) — vive físicamente en
    #    la 121 pero no es liquidez de Miguel.
    df_121 = df[df["Nº Cuenta"].astype(str) == "121"].copy()
    df_121["net_change"] = pd.to_numeric(df_121["Debe"], errors="coerce").fillna(
        0.0
    ) - pd.to_numeric(df_121["Haber"], errors="coerce").fillna(0.0)
    daily_change_121 = (
        df_121.groupby("Fecha")["net_change"].sum().reindex(all_dates, fill_value=0.0)
    )

    df_133 = df[df["Nº Cuenta"].astype(str) == "133"].copy()
    # Pasivo: Haber − Debe = saldo en favor de Bokatas
    df_133["bokatas_change"] = pd.to_numeric(df_133["Haber"], errors="coerce").fillna(
        0.0
    ) - pd.to_numeric(df_133["Debe"], errors="coerce").fillna(0.0)
    daily_change_bokatas = (
        df_133.groupby("Fecha")["bokatas_change"].sum().reindex(all_dates, fill_value=0.0)
    )

    daily_balance = (daily_change_121 - daily_change_bokatas).cumsum()

    # 2. Calcular los gastos discrecionales diarios (Grupo 5x, campo Debe > 0)
    df_5x = df[df["Nº Cuenta"].astype(str).str.startswith("5")].copy()
    df_5x["amount"] = pd.to_numeric(df_5x["Debe"], errors="coerce").fillna(0.0)

    daily_spend = df_5x.groupby("Fecha")["amount"].sum().reindex(all_dates, fill_value=0.0)

    # 3. Suavizar gastos discrecionales usando una ventana móvil de 7 días
    rolling_spend = daily_spend.rolling(window=7, min_periods=1).sum()

    df_corr = pd.DataFrame(
        {
            "balance": daily_balance,
            "spend": rolling_spend,
            "daily_spend_raw": daily_spend,
        },
        index=all_dates,
    )

    # Calcular Pearson
    correlation = 0.0
    if len(df_corr) > 10 and df_corr["balance"].std() > 0 and df_corr["spend"].std() > 0:
        correlation = float(df_corr["balance"].corr(df_corr["spend"]))
        if pd.isna(correlation):
            correlation = 0.0

    df_out = df_corr.reset_index().rename(columns={"index": "Fecha"})
    return round(correlation, 3), df_out


# ──────────────────────────────────────────────
# Simulación Monte Carlo de patrimonio
# ──────────────────────────────────────────────


@st.cache_data(ttl=TTL_SHEETS, show_spinner=False)
def simulate_monte_carlo(
    start_value: float,
    monthly_contribution: float,
    annual_return_pct: float,
    annual_volatility_pct: float,
    years: int,
    n_sims: int = 1000,
    seed: int | None = 42,
) -> dict:
    """Simula la evolución del patrimonio bajo retornos log-normales mensuales.

    Cada mes se aplica:
        valor[t+1] = (valor[t] + aportación) × (1 + ret_mensual)

    donde `ret_mensual ~ N(μ_m, σ_m)` calculado a partir de los inputs anuales
    mediante anualización clásica:
        μ_m = (1 + r_anual)^(1/12) − 1
        σ_m = σ_anual / √12

    Args:
        start_value: patrimonio actual (€).
        monthly_contribution: aportación constante al fin de cada mes (€).
        annual_return_pct: rentabilidad anual esperada (%, p.ej. 8 → 8%).
        annual_volatility_pct: volatilidad anual (σ %, p.ej. 15 → 15%).
        years: horizonte en años (1..60).
        n_sims: nº de simulaciones (típico 1000).
        seed: semilla del PRNG (None para no determinista).

    Returns:
        dict con:
          - "paths": np.ndarray shape (n_sims, n_months+1) en €
          - "months": np.ndarray de meses 0..n_months
          - "percentiles": dict {p10, p25, p50, p75, p90} → np.ndarray (n_months+1,)
          - "final": dict {p10, p25, p50, p75, p90} → float (valor final)
          - "total_aportado": float (start + Σ contribuciones)
          - "params": dict (inputs reflejados)
    """
    n_months = int(years) * 12
    if n_months <= 0:
        n_months = 1

    monthly_ret = (1.0 + annual_return_pct / 100.0) ** (1.0 / 12.0) - 1.0
    monthly_sigma = (annual_volatility_pct / 100.0) / math.sqrt(12.0)

    rng = np.random.default_rng(seed)
    # Retornos normales mensuales
    rets = rng.normal(loc=monthly_ret, scale=monthly_sigma, size=(n_sims, n_months))

    paths = np.zeros((n_sims, n_months + 1), dtype=float)
    paths[:, 0] = float(start_value)
    contrib = float(monthly_contribution)
    for t in range(n_months):
        paths[:, t + 1] = (paths[:, t] + contrib) * (1.0 + rets[:, t])

    # Saneamiento: clamp a 0 si por concatenación de retornos muy negativos
    # cae bajo cero (no es realista pero matemáticamente posible con σ alta).
    np.maximum(paths, 0.0, out=paths)

    pct_arr = np.percentile(paths, [10, 25, 50, 75, 90], axis=0)
    percentiles = {
        "p10": pct_arr[0],
        "p25": pct_arr[1],
        "p50": pct_arr[2],
        "p75": pct_arr[3],
        "p90": pct_arr[4],
    }
    final = {k: float(v[-1]) for k, v in percentiles.items()}
    total_aportado = float(start_value) + contrib * n_months

    return {
        "paths": paths,
        "months": np.arange(n_months + 1),
        "percentiles": percentiles,
        "final": final,
        "total_aportado": total_aportado,
        "params": {
            "start_value": float(start_value),
            "monthly_contribution": contrib,
            "annual_return_pct": float(annual_return_pct),
            "annual_volatility_pct": float(annual_volatility_pct),
            "years": int(years),
            "n_sims": int(n_sims),
        },
    }

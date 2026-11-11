"""
test_improvements.py — Pruebas unitarias para mejoras del Dashboard:
1. Meta de Ahorro YTD (calc_ahorro_ytd)
2. Análisis de Beta empírica en vivo (calc_empirical_beta)
3. Correlación de saldo y gastos discrecionales
"""

import numpy as np
import pandas as pd
import pytest

from services.accounting import calc_ahorro_ytd
from services.analytics import calc_balance_spending_correlation, calc_empirical_beta


def test_calc_ahorro_ytd():
    """Valida el cálculo del ahorro YTD anual neto para el año en curso."""
    current_year = pd.Timestamp.today().year

    # Crear datos simulados
    data = [
        # Transacción del año pasado (no debe computarse)
        {
            "Fecha": f"{current_year - 1}-12-15",
            "Nº Cuenta": "41",
            "Debe": 0.0,
            "Haber": 1000.0,
            "Descripción": "Ingreso viejo",
        },
        {
            "Fecha": f"{current_year - 1}-12-15",
            "Nº Cuenta": "51",
            "Debe": 300.0,
            "Haber": 0.0,
            "Descripción": "Gasto viejo",
        },
        # Transacciones de este año (posteriores a HISTORY_START_DATE)
        {
            "Fecha": f"{current_year}-04-10",
            "Nº Cuenta": "41",
            "Debe": 0.0,
            "Haber": 2500.0,
            "Descripción": "Sueldo YTD",
        },
        {
            "Fecha": f"{current_year}-04-15",
            "Nº Cuenta": "51",
            "Debe": 800.0,
            "Haber": 0.0,
            "Descripción": "Alquiler/Comida YTD",
        },
        {
            "Fecha": f"{current_year}-05-01",
            "Nº Cuenta": "55",
            "Debe": 200.0,
            "Haber": 0.0,
            "Descripción": "Viaje YTD",
        },
        # Traspaso de inversión (no debe computarse en ahorro YTD ya que es Activo)
        {
            "Fecha": f"{current_year}-05-10",
            "Nº Cuenta": "141",
            "Debe": 500.0,
            "Haber": 0.0,
            "Descripción": "Inversión BRK",
        },
        # Venta de inversión (debe restar del ahorro)
        {
            "Fecha": f"{current_year}-05-15",
            "Nº Cuenta": "141",
            "Debe": 0.0,
            "Haber": 150.0,
            "Descripción": "Venta parcial BRK",
        },
    ]
    df = pd.DataFrame(data)
    df["Fecha"] = pd.to_datetime(df["Fecha"])

    # Ahorro esperado basado en Inversiones netas (14x Debe - Haber) = 500.0 - 150.0 = 350.0
    ahorro = calc_ahorro_ytd(df)
    assert ahorro == 350.0


def test_calc_empirical_beta_fallback():
    """Fallback neutro = 1.0 (beta del mercado por definición) si los datos no son suficientes."""
    # Nulos
    assert calc_empirical_beta(None, None) == 1.0

    # Vacíos
    df_empty = pd.DataFrame(columns=["Close"])
    assert calc_empirical_beta(df_empty, df_empty) == 1.0

    # Escasos (menos de 10 puntos)
    df_short = pd.DataFrame({"Close": [100.0, 101.0, 100.5]})
    assert calc_empirical_beta(df_short, df_short) == 1.0


def test_calc_empirical_beta_calculation():
    """Valida la fórmula de Beta (Cov/Var) con datos correlacionados y variabilidad."""
    np.random.seed(42)  # Garantizar reproducibilidad
    n_days = 40

    # Retornos aleatorios del SP500 (media 0.05%, volatilidad 1%)
    ret_sp = np.random.normal(0.0005, 0.01, n_days)
    # Retornos de BRK correlacionados con Beta 0.8 más algo de ruido no correlacionado
    ret_brk = ret_sp * 0.8 + np.random.normal(0, 0.002, n_days)

    # Convertir retornos a precios acumulados
    sp_prices = [100.0]
    brk_prices = [100.0]
    for r_s, r_b in zip(ret_sp, ret_brk, strict=True):
        sp_prices.append(sp_prices[-1] * (1.0 + r_s))
        brk_prices.append(brk_prices[-1] * (1.0 + r_b))

    df_sp = pd.DataFrame({"Close": sp_prices})
    df_brk = pd.DataFrame({"Close": brk_prices})

    beta = calc_empirical_beta(df_brk, df_sp)
    # Comprobar que aproxima a 0.8 con una tolerancia razonable por el ruido
    assert pytest.approx(beta, abs=0.08) == 0.8


def test_calc_empirical_beta_with_price_column():
    """Valida que calc_empirical_beta funciona correctamente con la columna 'Price'."""
    np.random.seed(42)
    n_days = 40
    ret_sp = np.random.normal(0.0005, 0.01, n_days)
    ret_brk = ret_sp * 0.8 + np.random.normal(0, 0.002, n_days)

    sp_prices = [100.0]
    brk_prices = [100.0]
    for r_s, r_b in zip(ret_sp, ret_brk, strict=True):
        sp_prices.append(sp_prices[-1] * (1.0 + r_s))
        brk_prices.append(brk_prices[-1] * (1.0 + r_b))

    df_sp = pd.DataFrame({"Price": sp_prices})
    df_brk = pd.DataFrame({"Price": brk_prices})

    beta = calc_empirical_beta(df_brk, df_sp)
    assert pytest.approx(beta, abs=0.08) == 0.8


def test_rebalancing_and_tax_shield_math():
    """Valida los cálculos matemáticos detrás del rebalanceo por aportaciones y el escudo fiscal."""
    # 1. Escudo fiscal
    cuota = 1000.0
    r_rate = 0.07
    anos = 10
    capitalizacion = ((1.0 + r_rate) ** anos) - 1.0
    escudo_val = cuota * capitalizacion
    assert pytest.approx(escudo_val, abs=0.01) == 967.15  # 1000 * ((1.07)^10 - 1)

    # 2. Rebalanceo por aportación
    valor_cartera_pura = 10000.0
    valor_brk_eur = 3000.0  # Peso BRK actual: 30%
    valor_fondo_eur = 7000.0  # Peso Vanguard actual: 70%
    nueva_aportacion = 1000.0
    target_brk = 40.0  # Queremos llegar al 40% de BRK
    target_sp = 60.0

    # Objetivo tras aportación:
    # BRK Target: 40% de 11000 = 4400 €
    # SP Target: 60% de 11000 = 6600 €
    # Desviación para BRK: 4400 - 3000 = +1400 € (necesitamos comprar)
    # Desviación para SP: 6600 - 7000 = -400 € (ya está por encima)
    # Por lo tanto, como sp_diff <= 0, toda la aportación va a BRK:
    target_brk_val = (target_brk / 100.0) * (valor_cartera_pura + nueva_aportacion)
    target_sp_val = (target_sp / 100.0) * (valor_cartera_pura + nueva_aportacion)

    brk_diff = target_brk_val - valor_brk_eur
    sp_diff = target_sp_val - valor_fondo_eur

    if brk_diff <= 0:
        buy_brk = 0.0
        buy_sp = nueva_aportacion
    elif sp_diff <= 0:
        buy_brk = nueva_aportacion
        buy_sp = 0.0
    else:
        total_needed = brk_diff + sp_diff
        buy_brk = (brk_diff / total_needed) * nueva_aportacion
        buy_sp = (sp_diff / total_needed) * nueva_aportacion

    assert buy_brk == 1000.0
    assert buy_sp == 0.0


def test_calc_balance_spending_correlation_edge_cases():
    """Valida el cálculo de correlación entre saldo de TR (121) y gastos discrecionales (5x)."""
    # 1. Caso vacío
    corr_empty, df_empty = calc_balance_spending_correlation(pd.DataFrame())
    assert corr_empty == 0.0
    assert df_empty.empty

    # 2. Caso corto (menos de 10 días)
    data_short = [
        {
            "Fecha": "2026-05-01",
            "Nº Cuenta": "121",
            "Debe": 100.0,
            "Haber": 0.0,
            "Descripción": "Ingreso",
        },
        {
            "Fecha": "2026-05-02",
            "Nº Cuenta": "51",
            "Debe": 10.0,
            "Haber": 0.0,
            "Descripción": "Café",
        },
    ]
    df_short = pd.DataFrame(data_short)
    corr_short, df_out_short = calc_balance_spending_correlation(df_short)
    assert corr_short == 0.0
    assert len(df_out_short) == 2  # 2026-05-01 y 2026-05-02

    # 3. Caso sin variabilidad en el saldo (std balance == 0)
    data_const_bal = []
    for i in range(1, 13):
        data_const_bal.append(
            {
                "Fecha": f"2026-05-{i:02d}",
                "Nº Cuenta": "51",
                "Debe": float(i),
                "Haber": 0.0,
                "Descripción": "Gasto discrecional",
            }
        )
    df_const_bal = pd.DataFrame(data_const_bal)
    corr_const_bal, df_out_const_bal = calc_balance_spending_correlation(df_const_bal)
    assert corr_const_bal == 0.0

    # 4. Caso sin variabilidad en gastos (std spend == 0)
    data_const_spend = []
    for i in range(1, 13):
        data_const_spend.append(
            {
                "Fecha": f"2026-05-{i:02d}",
                "Nº Cuenta": "121",
                "Debe": 100.0,
                "Haber": 0.0,
                "Descripción": "Depósito",
            }
        )
    df_const_spend = pd.DataFrame(data_const_spend)
    corr_const_spend, df_out_const_spend = calc_balance_spending_correlation(df_const_spend)
    assert corr_const_spend == 0.0

    # 5. Caso normal con correlación positiva
    data_normal = []
    for i in range(1, 15):
        data_normal.append(
            {
                "Fecha": f"2026-05-{i:02d}",
                "Nº Cuenta": "121",
                "Debe": 100.0 * i,
                "Haber": 0.0,
                "Descripción": "Depósito",
            }
        )
        data_normal.append(
            {
                "Fecha": f"2026-05-{i:02d}",
                "Nº Cuenta": "51",
                "Debe": 10.0 * i,
                "Haber": 0.0,
                "Descripción": "Discrecional",
            }
        )
    df_normal = pd.DataFrame(data_normal)
    corr_normal, df_out_normal = calc_balance_spending_correlation(df_normal)
    assert corr_normal > 0.5


def test_app_session_state_manager():
    """Prueba que el boundary centralizado AppSessionState funcione correctamente."""
    import streamlit as st

    from services.session_state import session_state

    # Inicializar defaults
    session_state.init_defaults()

    # Verificar valores por defecto inicializados
    assert session_state.last_sync == "--:--:--"
    assert session_state.tl_playing is False
    assert session_state.tl_slider_w == 0
    assert session_state.tl_advance is False

    # Getters y setters básicos
    session_state.last_sync = "12:34:56"
    assert session_state.last_sync == "12:34:56"
    assert st.session_state["last_sync"] == "12:34:56"

    session_state.tl_playing = True
    assert session_state.tl_playing is True

    session_state.tl_slider_w = 42
    assert session_state.tl_slider_w == 42

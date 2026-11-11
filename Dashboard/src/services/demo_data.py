"""
demo_data.py — Modo DEMO con dataset sintético.

Cuando la variable de entorno `DEMO_MODE` está activa (`true`/`1`/`yes`),
el dashboard sirve un Libro Diario sintético generado deterministamente
con `random.seed(42)` en lugar de los datos reales de Google Sheets.

Patrones del dataset sintético:
  - Capital inicial de 4.000 € en el banco (cuenta 121).
  - Sueldo mensual fijo (2.400 €) el día 1 de cada mes → 44.
  - 1-3 compras diarias en supermercados/cafeterías/bares → 51/52/53.
  - Gym mensual día 5 → 54.
  - Bizum/Reembolso ocasional → 45.
  - Compras semanales en Berkshire (60 €) y mensuales en Vanguard (200 €).
  - Saveback ocasional (1 % de compras) → 44 + 141.
  - Cobertura: 180 días (6 meses) hacia atrás desde hoy.

Writes (append_to_diario, automation) **se inhiben** en modo
demo y devuelven `False`/`None` con un log de advertencia.
"""

from __future__ import annotations

import logging
import os
import random
from datetime import date, timedelta

import pandas as pd

from constants import (
    CUENTA_BERKSHIRE,
    CUENTA_CAPITAL_INICIAL,
    CUENTA_CARTERA,
    CUENTA_SP500,
    CUENTA_TR,
    TICKER_BRK,
    TICKER_EURUSD,
    TICKER_VANGUARD,
    TICKER_VWRL_PROXY,
)

log = logging.getLogger(__name__)

_DEMO_SEED = 42

# Catálogo de comercios → cuenta de gasto + rango plausible
_COMERCIOS: list[tuple[str, str, tuple[float, float]]] = [
    ("Mercadona Sant Cugat", "51", (8.50, 45.00)),
    ("Carrefour Express", "51", (5.00, 30.00)),
    ("Lidl", "51", (12.00, 50.00)),
    ("Starbucks Plaza Cataluña", "52", (2.50, 6.50)),
    ("Nespresso boutique", "52", (3.20, 8.00)),
    ("Café Brunch Co.", "52", (4.00, 9.50)),
    ("Bar La Lola", "53", (8.00, 22.00)),
    ("Cervecería del Born", "53", (12.00, 35.00)),
    ("Restaurante Sushi & Co", "53", (15.00, 40.00)),
    ("Renfe Cercanías", "55", (3.20, 12.00)),
    ("Booking.com — Sevilla", "55", (45.00, 180.00)),
    ("Ryanair", "55", (39.99, 89.99)),
    ("Decathlon", "56", (10.00, 60.00)),
    ("FNAC", "56", (8.00, 50.00)),
]

_CUENTAS_NOMBRES: dict[str, str] = {
    "44": "Ingresos Sueldo",
    "45": "Ingresos Puntuales / Otros",
    "51": "Gastos Comida",
    "52": "Gastos Cafeína",
    "53": "Gastos Alcohol & Friends",
    "54": "Gastos Gym",
    "55": "Gastos Viajes",
    "56": "Gastos Puntuales/Otros...",
    "121": "Trade Republic",
    "111": "Cartera",
    "141": "Berkshire Hathaway",
    "142": "Vanguard SP500",
    "31": "Capital Inicial",
}


_CIPHER_POOL = [
    "%",
    "$",
    ".",
    "F",
    "R",
    "/",
    "X",
    "T",
    "Ø",
    "Ɛ",
    "ϛ",
    "ㄥ",
    "§",
    "Ψ",
    "Ω",
    "⇂",
    "‡",
    "⌘",
    "Ж",
    "¥",
]


def scramble_numbers(val) -> str:
    """Cifra cualquier cadena/número reemplazando dígitos 0-9 por mayúsculas, símbolos (%$.FR/,XT) y caracteres especiales."""
    if val is None:
        return ""
    s = str(val)
    res = []
    digit_idx = 0
    for char in s:
        if char.isdigit():
            d = int(char)
            symbol = _CIPHER_POOL[(d + digit_idx * 3) % len(_CIPHER_POOL)]
            res.append(symbol)
            digit_idx += 1
        else:
            res.append(char)
    return "".join(res)


def _env_flag(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in ("true", "1", "yes", "on")


def is_demo_mode() -> bool:
    """True si `DEMO_MODE` está activo: el dashboard sirve datos sintéticos
    y no toca Google Sheets, Drive ni el CSV local."""
    return _env_flag("DEMO_MODE")


def is_cipher_mode() -> bool:
    """True si el Modo Cifrado está activo: datos reales, cifras ocultas en la UI.

    Se activa con el toggle del sidebar o con `CIPHER_MODE=true`. Es
    independiente de `DEMO_MODE` (sirve para enseñar la app con datos reales
    sin enseñar los importes).
    """
    try:
        import streamlit as st

        if "cipher_mode_active" in st.session_state:
            return bool(st.session_state["cipher_mode_active"])
    except Exception:
        pass
    return _env_flag("CIPHER_MODE")


def _row(
    fecha: date,
    cuenta: str,
    debe: float | None,
    haber: float | None,
    desc: str,
    categoria: str = "",
) -> dict:
    return {
        "Fecha": pd.Timestamp(fecha),
        "Nº Cuenta": cuenta,
        "Cuenta": _CUENTAS_NOMBRES.get(cuenta, cuenta),
        "Categoría": categoria,
        "Debe": debe if debe is not None else 0.0,
        "Haber": haber if haber is not None else 0.0,
        "Descripción": desc,
    }


def _pair(
    fecha: date,
    *,
    debe_cuenta: str,
    haber_cuenta: str,
    amount: float,
    desc: str,
    categoria: str = "",
) -> list[dict]:
    """Partida doble convencional."""
    amt = round(amount, 2)
    return [
        _row(fecha, debe_cuenta, amt, None, desc, categoria),
        _row(fecha, haber_cuenta, None, amt, desc, categoria),
    ]


def generate_demo_diario(days_back: int = 180, seed: int = _DEMO_SEED) -> pd.DataFrame:
    """Genera el Libro Diario sintético determinista.

    Args:
        days_back: Días hacia atrás cubiertos.
        seed: Semilla para `random` (reproducibilidad).

    Returns:
        DataFrame con las mismas columnas que `get_diario`.
    """
    rng = random.Random(seed)
    today = date.today()
    start = today - timedelta(days=days_back)
    rows: list[dict] = []

    # ── Capital inicial (1 vez al principio) ──
    rows += _pair(
        start,
        debe_cuenta=CUENTA_TR,
        haber_cuenta=CUENTA_CAPITAL_INICIAL,
        amount=4000.0,
        desc="Transferencia inicial demo",
        categoria="Capital",
    )

    # ── Recorrido día a día ──
    cur = start
    while cur <= today:
        # Sueldo el día 1 de cada mes
        if cur.day == 1:
            rows += _pair(
                cur,
                debe_cuenta=CUENTA_TR,
                haber_cuenta="44",
                amount=2400.0,
                desc=f"Sueldo {cur.strftime('%B').capitalize()} (demo)",
            )

        # Gym el día 5
        if cur.day == 5:
            rows += _pair(
                cur,
                debe_cuenta="54",
                haber_cuenta=CUENTA_TR,
                amount=29.95,
                desc="Cuota mensual gimnasio Anytime Fitness",
            )

        # 1-3 compras al día (excepto sábados/domingos un poco menos)
        n_compras = rng.randint(0, 3) if cur.weekday() >= 5 else rng.randint(1, 3)
        for _ in range(n_compras):
            comercio, cuenta, (mn, mx) = rng.choice(_COMERCIOS)
            amt = round(rng.uniform(mn, mx), 2)
            rows += _pair(
                cur,
                debe_cuenta=cuenta,
                haber_cuenta=CUENTA_TR,
                amount=amt,
                desc=comercio,
                categoria=comercio.split()[0],
            )

            # Saveback 1 % aleatorio
            if rng.random() < 0.35:
                sb = round(amt * 0.01, 2)
                if sb > 0:
                    rows += _pair(
                        cur,
                        debe_cuenta=CUENTA_TR,
                        haber_cuenta="44",
                        amount=sb,
                        desc=f"Saveback {comercio}",
                        categoria="Saveback",
                    )
                    # Reinvierte en BRK con metadata quantity
                    qty = round(sb / 450.0, 6)
                    rows += _pair(
                        cur,
                        debe_cuenta=CUENTA_BERKSHIRE,
                        haber_cuenta=CUENTA_TR,
                        amount=sb,
                        desc=f"Saveback execution quantity: {qty:.6f}",
                        categoria="Saveback",
                    )

        # Bizum/reembolso semanal
        if cur.weekday() == 2 and rng.random() < 0.4:
            amt = round(rng.uniform(5.0, 25.0), 2)
            rows += _pair(
                cur, debe_cuenta=CUENTA_TR, haber_cuenta="45", amount=amt, desc="Bizum amigo demo"
            )

        # Berkshire (semanal el lunes, 60 €)
        if cur.weekday() == 0 and rng.random() < 0.85:
            qty = round(60.0 / 450.0, 6)
            rows += _pair(
                cur,
                debe_cuenta=CUENTA_BERKSHIRE,
                haber_cuenta=CUENTA_TR,
                amount=60.0,
                desc=f"Savings Plan BRK execution quantity: {qty:.6f}",
                categoria="Savings Plan",
            )

        # Vanguard (mensual día 10, 200 €)
        if cur.day == 10:
            qty = round(200.0 / 110.0, 6)
            rows += _pair(
                cur,
                debe_cuenta=CUENTA_SP500,
                haber_cuenta=CUENTA_TR,
                amount=200.0,
                desc=f"Aporte Vanguard SP500 quantity: {qty:.6f}",
                categoria="Vanguard",
            )

        # Sacar efectivo a Cartera (puntual, 1 vez al mes random)
        if cur.day == 15 and rng.random() < 0.5:
            rows += _pair(
                cur,
                debe_cuenta=CUENTA_CARTERA,
                haber_cuenta=CUENTA_TR,
                amount=50.0,
                desc="Reintegro cajero demo",
            )

        cur += timedelta(days=1)

    return pd.DataFrame(rows)


_TIPO_CUENTA: dict[str, str] = {
    "111": "Activo Bancario",
    "121": "Activo Bancario",
    "141": "Inversión",
    "142": "Inversión",
}


def generate_demo_saldos() -> pd.DataFrame:
    """Saldos por cuenta calculados a partir del Diario demo (siempre cuadran)."""
    df = generate_demo_diario()
    net = df.groupby("Nº Cuenta")[["Debe", "Haber"]].sum()
    rows = []
    for cuenta, nombre in _CUENTAS_NOMBRES.items():
        if cuenta not in net.index or cuenta == CUENTA_CAPITAL_INICIAL:
            continue
        debe, haber = net.loc[cuenta, "Debe"], net.loc[cuenta, "Haber"]
        if cuenta.startswith("4"):
            tipo, saldo = "Ingresos", haber - debe
        elif cuenta.startswith("5"):
            tipo, saldo = "Gastos", debe - haber
        else:
            tipo, saldo = _TIPO_CUENTA.get(cuenta, "Activo Bancario"), debe - haber
        rows.append(
            {
                "CUENTAS": cuenta,
                "Unnamed: 1": nombre,
                "Tipo cuenta para resumen": tipo,
                "Saldo para resumen": round(float(saldo), 2),
            }
        )
    return pd.DataFrame(rows)


# ──────────────────────────────────────────────
# Precios sintéticos (DEMO_MODE no llama a Yahoo Finance)
# ──────────────────────────────────────────────

# ticker → (precio de hoy, volatilidad diaria)
_DEMO_PRICES: dict[str, tuple[float, float]] = {
    TICKER_BRK: (480.0, 0.011),
    TICKER_VANGUARD: (110.0, 0.009),
    TICKER_VWRL_PROXY: (121.0, 0.008),
    TICKER_EURUSD: (0.86, 0.003),
}


def demo_price_history(ticker: str, days: int = 90) -> pd.DataFrame:
    """Serie diaria determinista (paseo aleatorio log-normal) que acaba en el precio de hoy."""
    last, vol = _DEMO_PRICES.get(ticker, (100.0, 0.01))
    rng = random.Random(f"{_DEMO_SEED}-{ticker}")
    n = max(int(days), 1) + 1
    steps = [rng.gauss(0.0003, vol) for _ in range(n - 1)]
    prices = [last]
    for r in reversed(steps):
        prices.append(prices[-1] / (1 + r))
    prices.reverse()
    today = date.today()
    dates = [today - timedelta(days=n - 1 - i) for i in range(n)]
    return pd.DataFrame({"Date": dates, "Price": [round(p, 4) for p in prices]})


def demo_price(ticker: str) -> float:
    return _DEMO_PRICES.get(ticker, (100.0, 0.01))[0]


def generate_demo_historico() -> pd.DataFrame:
    """Histórico diario de patrimonio reconstruido desde el Diario demo.

    Usa las mismas funciones contables que `services/history.update_historico`,
    con precios sintéticos, sin escribir nada en disco.
    """
    from services.accounting import (
        calc_brk_shares,
        calc_metalico_fisico,
        calc_padres_total,
        calc_tr_cash,
        calc_vanguard_shares,
    )

    df = generate_demo_diario()
    start = df["Fecha"].min().date()
    days = (date.today() - start).days
    px = {
        t: demo_price_history(t, days).set_index("Date")["Price"]
        for t in (TICKER_BRK, TICKER_VANGUARD, TICKER_EURUSD)
    }
    rows = []
    for d in pd.date_range(start, date.today() - timedelta(days=1)).date:
        df_d = df[df["Fecha"].dt.date <= d]
        efectivo = calc_metalico_fisico(df_d)
        tr = calc_tr_cash(df_d)
        brk = calc_brk_shares(df_d) * px[TICKER_BRK][d] * px[TICKER_EURUSD][d]
        van = calc_vanguard_shares(df_d) * px[TICKER_VANGUARD][d]
        deben = calc_padres_total(df_d, as_of_date=d)
        rows.append(
            {
                "Fecha": pd.Timestamp(d),
                "Efectivo Fisico": round(efectivo, 2),
                "Efectivo TR": round(tr, 2),
                "BRK Value": round(brk, 2),
                "Vanguard Value": round(van, 2),
                "Te Deben": round(deben, 2),
                "Total": round(efectivo + tr + brk + van + deben, 2),
            }
        )
    return pd.DataFrame(rows)


def block_writes_in_demo(operation: str) -> bool:
    """Helper para los puntos de escritura: si demo, loguea + devuelve False.

    Patrón de uso:
        if block_writes_in_demo("append_to_diario"):
            return False
    """
    if is_demo_mode():
        log.warning("DEMO_MODE: operación de escritura '%s' bloqueada.", operation)
        return True
    return False

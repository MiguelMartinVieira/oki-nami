"""
test_inversiones_package.py — Smoke tests del paquete tabs/inversiones/.

Verifica que el refactor de tab_inversiones en submódulos preserve la
interfaz pública y los imports no estén rotos. No renderiza UI (eso
requeriría un runtime de Streamlit); sólo comprueba que el `render`
del paquete sea importable y que los submódulos expongan sus puntos
de entrada.
"""


def test_package_exports_render():
    from tabs.inversiones import render

    assert callable(render), "tabs.inversiones.render debe ser invocable"


def test_submodule_entrypoints_exist():
    """Cada submódulo expone su función pública esperada."""
    from tabs.inversiones.allocation import render_allocation
    from tabs.inversiones.brk import render_brk_tab
    from tabs.inversiones.header import (
        render_sidebar_controls,
        render_top_cards,
        render_validation_warnings,
    )
    from tabs.inversiones.info import render_info_tab
    from tabs.inversiones.ops import render_ops_and_history
    from tabs.inversiones.summary import render_summary_tab
    from tabs.inversiones.vanguard import render_vanguard_tab

    for fn in (
        render_sidebar_controls,
        render_validation_warnings,
        render_top_cards,
        render_allocation,
        render_summary_tab,
        render_info_tab,
        render_brk_tab,
        render_vanguard_tab,
        render_ops_and_history,
    ):
        assert callable(fn), f"{fn.__name__} debe ser invocable"


def test_build_asset_metrics_shape():
    """El helper interno de derivados por activo devuelve las claves esperadas."""
    import pandas as pd

    from tabs.inversiones import _build_asset_metrics

    df = pd.DataFrame(
        {
            "Fecha": pd.to_datetime(["2026-04-01", "2026-04-15"]),
            "Nº Cuenta": ["141", "142"],
            "Debe": [100.0, 200.0],
            "Haber": [0.0, 0.0],
            "Descripción": ["BRK quantity: 0.001", "Vanguard quantity: 0.5"],
        }
    )
    portfolio = {
        "valor_fondo_eur": 250.0,
        "valor_brk_eur": 120.0,
        "precio_brk_usd": 500.0,
        "usd_to_eur": 0.92,
        "acciones_brk": 0.5,
        "acciones_vanguard": 1.5,
    }
    m = _build_asset_metrics(df, portfolio)

    # Claves esenciales
    for key in (
        "df_brk",
        "df_van",
        "total_invested_brk",
        "total_invested_van",
        "total_invested_portfolio",
        "valor_cartera_pura",
        "precio_brk_eur",
        "precio_medio_brk",
        "precio_medio_van",
        "pnl_brk",
        "pnl_pct_brk",
        "pnl_van",
        "pnl_pct_van",
        "pnl_portfolio",
        "pnl_pct_portfolio",
        "peso_brk",
        "peso_van",
        "n_operaciones_brk",
        "pnl_color_brk",
        "pnl_color_van",
        "pnl_color_portfolio",
    ):
        assert key in m, f"_build_asset_metrics no devuelve la clave esperada: {key}"

    # Sanity checks
    assert m["total_invested_brk"] == 100.0
    # Vanguard descuenta VANGUARD_HISTORICAL_GAIN del coste declarado
    from constants import VANGUARD_HISTORICAL_GAIN

    assert m["total_invested_van"] == 200.0 - VANGUARD_HISTORICAL_GAIN
    assert m["peso_brk"] + m["peso_van"] == 100.0 or m["valor_cartera_pura"] == 0


def test_build_asset_metrics_with_sale():
    """Si hay una venta, el coste invertido vivo y el precio medio se ajustan a las acciones restantes."""
    import pandas as pd
    import pytest

    from tabs.inversiones import _build_asset_metrics

    df = pd.DataFrame(
        {
            "Fecha": pd.to_datetime(["2026-04-01", "2026-10-06"]),
            "Nº Cuenta": ["141", "141"],
            "Categoría": ["Compra Berkshire", "Venta Berkshire"],
            "Debe": [800.0, 0.0],
            "Haber": [0.0, 450.0],
            "Descripción": ["quantity: 2.0", "quantity: 1.0"],
        }
    )
    # Compró 2 acciones a 400 €/acc (800 €). Vendió 1 acción. Queda 1 acción.
    portfolio = {
        "valor_fondo_eur": 0.0,
        "valor_brk_eur": 450.0,
        "precio_brk_usd": 489.13,
        "usd_to_eur": 0.92,
        "acciones_brk": 1.0,
        "acciones_vanguard": 0.0,
    }
    m = _build_asset_metrics(df, portfolio)

    # El precio medio debe seguir siendo 400 €/acc (no 800 €/acc)
    assert m["precio_medio_brk"] == pytest.approx(400.0)
    # El capital invertido activo debe ser 400 € (1 acción * 400 €), no 800 €
    assert m["total_invested_brk"] == pytest.approx(400.0)
    # La plusvalía latente de la acción viva debe ser +50 € (450 € - 400 €), no una pérdida ficticia
    assert m["pnl_brk"] == pytest.approx(50.0)

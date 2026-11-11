"""Unit tests para verificar el rango del eje radial en gráficos de telaraña/radar."""

import pandas as pd

from components.charts.radar import (
    build_expense_radar_absolute,
    build_expense_radar_relative,
    build_income_radar_absolute,
    build_income_radar_relative,
    build_radar_mom,
)


def test_radar_charts_radial_range():
    df_cm = pd.DataFrame(
        {
            "Cuenta": ["Comida", "Ocio", "Transporte"],
            "Debe": [100.0, 0.0, 0.0],
            "Haber": [100.0, 0.0, 0.0],
        }
    )
    df_hist = pd.DataFrame(
        {
            "Fecha": pd.to_datetime(["2026-01-01"] * 3),
            "Cuenta": ["Comida", "Ocio", "Transporte"],
            "Debe": [80.0, 50.0, 30.0],
            "Haber": [80.0, 50.0, 30.0],
        }
    )
    df_hist["Mes"] = df_hist["Fecha"].dt.to_period("M")

    # Relative radars
    fig_exp_rel = build_expense_radar_relative(df_cm, df_hist)
    assert fig_exp_rel is not None
    assert fig_exp_rel.layout.polar.radialaxis.range[0] < 0

    fig_inc_rel = build_income_radar_relative(df_cm, df_hist)
    assert fig_inc_rel is not None
    assert fig_inc_rel.layout.polar.radialaxis.range[0] < 0

    # Absolute radars
    fig_exp_abs = build_expense_radar_absolute(df_cm, df_hist)
    assert fig_exp_abs is not None
    assert fig_exp_abs.layout.polar.radialaxis.range[0] < 0

    fig_inc_abs = build_income_radar_absolute(df_cm, df_hist)
    assert fig_inc_abs is not None
    assert fig_inc_abs.layout.polar.radialaxis.range[0] < 0

    # MoM radar
    df_all = pd.concat(
        [
            df_hist.assign(Mes="2026-06"),
            df_cm.assign(Fecha=pd.to_datetime("2026-07-01"), Mes="2026-07"),
        ]
    )
    fig_mom = build_radar_mom(df_cm, df_all, "Debe", is_expense=True)
    assert fig_mom is not None
    assert fig_mom.layout.polar.radialaxis.range[0] < 0

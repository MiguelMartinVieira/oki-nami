import pandas as pd
import streamlit as st

from components.diagnostic_card import render_diagnostic_card, render_dual_card
from constants import DATE_FORMAT, get_category_color
from services.analytics import calc_cumulative_opportunity_cost, calc_real_cost
from services.cost_per_day import (
    compute_cost_per_day,
    estimate_sueldo_hora_from_ingresos,
)

from .context import DiarioContext


def render_coste_real(ctx: DiarioContext) -> None:
    _render_coste_real_tab(
        df_diario=ctx.df_diario,
        df_gastos=ctx.df_gastos,
        df_ingresos=ctx.df_ingresos,
        tasa_ahorro_mes=ctx.tasa_ahorro_mes,
        is_filtered=ctx.is_filtered,
        filtered_cat=ctx.filtered_cat,
        is_expense_filter=ctx.is_expense_filter,
    )


def _render_coste_real_tab(
    df_diario: pd.DataFrame,
    df_gastos: pd.DataFrame,
    df_ingresos: pd.DataFrame,
    tasa_ahorro_mes: float,
    is_filtered: bool,
    filtered_cat: str | None,
    is_expense_filter: bool,
) -> None:
    """
    Visualiza el "coste oculto" de un gasto bajo dos lentes:

    1. **Bruto equivalente**: gasto ÷ (1 − tasa_ahorro_media). Cuánto bruto
       necesitas ganar para cubrirlo sin tocar tu ratio de ahorro.
    2. **Coste de oportunidad a 10 años**: gasto × (1 + r)^10, con `r` =
       rentabilidad anual histórica de tu cartera (BRK + Vanguard).
    """
    # ── Tasa de ahorro media (mes actual + media histórica) ──
    if not df_gastos.empty and not df_ingresos.empty:
        g_mes = df_gastos.groupby("Mes")["Debe"].sum()
        i_mes = df_ingresos.groupby("Mes")["Haber"].sum()
        combinado = pd.DataFrame({"g": g_mes, "i": i_mes}).dropna()
        combinado["tasa"] = (combinado["i"] - combinado["g"]) / combinado["i"] * 100
        tasa_hist = float(combinado["tasa"].mean()) if not combinado.empty else 0.0
        tasa_6m = float(combinado["tasa"].tail(6).mean()) if not combinado.empty else 0.0
    else:
        tasa_hist = 0.0
        tasa_6m = 0.0

    # Años invertido (aprox.)
    df_inv = df_diario[df_diario["Nº Cuenta"].astype(str).str.startswith(("141", "142"))].copy()
    rent_anual_default = 8.0
    if not df_inv.empty:
        primera_op = df_inv["Fecha"].min()
        years_invested = max((pd.Timestamp.today() - primera_op).days / 365.25, 0.25)
    else:
        years_invested = 1.0

    # ── Valores de Ajustes (Leídos del state para cálculos) ──
    rent_anual_input = float(st.session_state.get("coste_real_rent", rent_anual_default))
    years_input = int(st.session_state.get("coste_real_years", 10))
    tasa_aplicada = tasa_hist if abs(tasa_hist) > 0.01 else tasa_ahorro_mes

    # ── Categoría target ──
    if is_filtered and is_expense_filter:
        source = df_gastos[df_gastos["Cuenta"] == filtered_cat].copy()
        filter_acc_for_cum = filtered_cat
    elif is_filtered and not is_expense_filter:
        st.info(
            "La categoría seleccionada es de ingresos. Cambia a 'Todas las categorías' o a una de gasto para ver el coste real."
        )
        return
    else:
        source = df_gastos.copy()
        filter_acc_for_cum = None

    if source.empty:
        st.info("Sin gastos para mostrar.")
        return

    # ═══════════════════════════════════════════════════════════
    # HERO — Coste de oportunidad acumulado de los últimos 6 meses
    # ═══════════════════════════════════════════════════════════
    cum = calc_cumulative_opportunity_cost(
        df_diario=df_diario,
        rent_anual_pct=float(rent_anual_input),
        years_horizon=int(years_input),
        months_lookback=6,
        filter_account=filter_acc_for_cum,
    )

    # Ribbon de top categorías (debajo del hero, sólo si hay variedad)
    cat_ribbon_html = ""
    if cum["top_categorias"] and not is_filtered:
        chips = []
        for c in cum["top_categorias"][:5]:
            acc = get_category_color(c["categoria"], is_expense=True)
            chips.append(
                f'<div style="display:inline-flex; flex-direction:column; gap:2px; '
                f"padding:8px 14px; background:rgba(255,23,68,0.06); "
                f"border:1px solid {acc}55; border-left:3px solid {acc}; "
                f'border-radius:8px; min-width:130px;">'
                f'<div style="font-size:0.7rem; color:#A1A1AA; text-transform:uppercase; '
                f'letter-spacing:0.04em;">{c["categoria"]}</div>'
                f'<div style="font-size:1rem; color:#FFFFFF; font-weight:600; '
                f"font-family:'Roboto Mono',monospace;\">"
                f"{c['oportunidad']:,.0f} €</div>"
                f'<div style="font-size:0.7rem; color:#71717A;">'
                f"de {c['gastado']:,.0f} € gastados</div>"
                f"</div>"
            )
        cat_ribbon_html = (
            '<div style="display:flex; gap:10px; flex-wrap:wrap;">' + "".join(chips) + "</div>"
        )

    hero_body = (
        f"<div style='display:flex; flex-direction:row; align-items:center; justify-content:space-between; gap:24px; flex-wrap:wrap;'>"
        f"  <div style='font-size:3.5rem; font-weight:600; color:#FF1744; "
        f'  font-family:"Roboto Mono",monospace; letter-spacing:-0.04em; '
        f"  line-height:1; white-space:nowrap;'>"
        f"  {cum['oportunidad_total']:,.0f} €</div>"
        f"  {cat_ribbon_html}"
        f"</div>"
    )
    st.markdown(
        render_diagnostic_card(
            "💀 Coste de oportunidad acumulado (últimos 6 meses)",
            hero_body,
            accent_color="#FF1744",
            elevated=True,
            height_full=False,
        ),
        unsafe_allow_html=True,
    )

    st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════
    # CALCULADORA — sin título, directa
    # ═══════════════════════════════════════════════════════════
    col_g1, col_g2, col_g3 = st.columns(3)
    with col_g1:
        with st.container(border=True):
            gasto_input = st.number_input(
                "GASTO A SIMULAR (€)",
                min_value=0.0,
                value=2.50,
                step=0.50,
                key="coste_real_gasto",
                format="%.2f",
            )

    res = calc_real_cost(
        gasto=float(gasto_input),
        tasa_ahorro_pct=tasa_aplicada,
        rent_anual_pct=float(rent_anual_input),
        years=int(years_input),
    )
    with col_g2:
        st.markdown(
            "<div style='height: 104px;'>"
            + render_dual_card(
                "BRUTO EQUIVALENTE",
                f"{res['bruto_equivalente']:,.2f} €",
                "",
                accent_color="#FF4D6D",
            )
            + "</div>",
            unsafe_allow_html=True,
        )
    with col_g3:
        st.markdown(
            "<div style='height: 104px;'>"
            + render_dual_card(
                f"COSTE DE OPORTUNIDAD A {years_input} AÑOS",
                f"{res['oportunidad']:,.2f} €",
                "",
                accent_color="#FF1744",
            )
            + "</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════
    # TABLA — sin título; orden y filtro arriba
    # ═══════════════════════════════════════════════════════════
    col_t1, col_t2 = st.columns([3, 2])
    with col_t1:
        with st.expander("⚙️ Ajustes y perfil financiero", expanded=False):
            col_r1, col_r2 = st.columns([2, 3])
            with col_r1:
                st.number_input(
                    "Rentabilidad anual estimada de tu cartera (%)",
                    min_value=-10.0,
                    max_value=30.0,
                    value=rent_anual_default,
                    step=0.5,
                    key="coste_real_rent",
                    help="Por defecto 8 % (referencia histórica del S&P 500).",
                )
                st.slider(
                    "Horizonte de proyección (años)",
                    min_value=1,
                    max_value=40,
                    value=10,
                    step=1,
                    key="coste_real_years",
                )
            with col_r2:
                perfil_body = (
                    f"Tasa de ahorro <b>mes actual</b>: "
                    f"<b style='color:#00E676;'>{tasa_ahorro_mes:.1f}%</b><br>"
                    f"Tasa de ahorro <b>media histórica</b>: <b>{tasa_hist:.1f}%</b><br>"
                    f"Tasa de ahorro <b>media 6m</b>: <b>{tasa_6m:.1f}%</b><br>"
                    f"Años invertido (aprox.): <b>{years_invested:.1f}</b>"
                )
                st.markdown(
                    render_diagnostic_card(
                        "TU PERFIL FINANCIERO",
                        perfil_body,
                        accent_color="#A1A1AA",
                        height_full=False,
                    ),
                    unsafe_allow_html=True,
                )

    with col_t2:
        sort_mode = st.radio(
            "Ordenar por",
            options=["🗓️ Más recientes", "💀 Mayor impacto"],
            index=0,
            horizontal=True,
            key="coste_real_sort",
            label_visibility="collapsed",
        )

    cutoff = pd.Timestamp.today() - pd.DateOffset(months=6)
    source_recent = source[pd.to_datetime(source["Fecha"], errors="coerce") >= cutoff].copy()
    if source_recent.empty:
        source_recent = source.copy()

    source_recent["Bruto equiv. (€)"] = source_recent["Debe"].apply(
        lambda g: calc_real_cost(g, tasa_aplicada, float(rent_anual_input), int(years_input))[
            "bruto_equivalente"
        ]
    )
    opp_col = f"Oportunidad {int(years_input)}y (€)"
    source_recent[opp_col] = source_recent["Debe"].apply(
        lambda g: calc_real_cost(g, tasa_aplicada, float(rent_anual_input), int(years_input))[
            "oportunidad"
        ]
    )

    if sort_mode.startswith("💀"):
        source_recent = source_recent.sort_values(opp_col, ascending=False)
    else:
        source_recent = source_recent.sort_values("Fecha", ascending=False)
    source_recent = source_recent.head(20).copy()

    source_recent["Fecha"] = pd.to_datetime(source_recent["Fecha"], errors="coerce").dt.strftime(
        DATE_FORMAT
    )

    show_cols = ["Fecha", "Cuenta", "Descripción", "Debe", "Bruto equiv. (€)", opp_col]
    num_cols = ["Debe", "Bruto equiv. (€)", opp_col]

    def _red_gradient(series: pd.Series) -> list[str]:
        """Mapea valores a un fondo crimson sobre dark (más saturado = más impacto).

        Coherente con el tema Abyssal Monochrome:
        - Piso `#18181B` (mismo que las cards) → tope crimson `#FF1744`.
        - Texto interpola de gris `#A1A1AA` a blanco `#FFFFFF` para legibilidad.
        - Cap en percentil 90 (winsorización) — un outlier no aplasta al resto.
        - Curva sqrt para que valores pequeños tengan color perceptible.
        """
        import math as _math

        vals = series.astype(float)
        positives = vals[vals > 0]
        if positives.empty:
            return ["" for _ in vals]

        cap = float(positives.quantile(0.90))
        if cap <= 0:
            cap = float(positives.max())

        # Endpoints en RGB
        bg_lo = (24, 24, 27)  # #18181B
        bg_hi = (255, 23, 68)  # #FF1744
        fg_lo = (161, 161, 170)  # #A1A1AA
        fg_hi = (255, 255, 255)  # #FFFFFF

        out = []
        for v in vals:
            v = float(v)
            if v <= 0:
                out.append("")
                continue
            t_lin = min(v / cap, 1.0)
            t = _math.sqrt(t_lin)
            r = int(bg_lo[0] + (bg_hi[0] - bg_lo[0]) * t)
            g = int(bg_lo[1] + (bg_hi[1] - bg_lo[1]) * t)
            b = int(bg_lo[2] + (bg_hi[2] - bg_lo[2]) * t)
            tr = int(fg_lo[0] + (fg_hi[0] - fg_lo[0]) * t)
            tg = int(fg_lo[1] + (fg_hi[1] - fg_lo[1]) * t)
            tb = int(fg_lo[2] + (fg_hi[2] - fg_lo[2]) * t)
            out.append(
                f"background-color: rgb({r},{g},{b}); color: rgb({tr},{tg},{tb}); font-weight: 600;"
            )
        return out

    styled = (
        source_recent[show_cols]
        .style.format("{:,.2f}", subset=num_cols)
        .apply(_red_gradient, subset=["Debe"])
        .apply(_red_gradient, subset=["Bruto equiv. (€)"])
        .apply(_red_gradient, subset=[opp_col])
    )
    st.dataframe(styled, width="stretch", hide_index=True)

    # ═══════════════════════════════════════════════════════════
    # COST-PER-DAY POR CATEGORÍA
    # ═══════════════════════════════════════════════════════════
    _render_cost_per_day_section(df_diario, is_filtered, filtered_cat)


def _render_cost_per_day_section(
    df_diario: pd.DataFrame,
    is_filtered: bool,
    filtered_cat: str | None,
) -> None:
    """Tabla "Coste-por-día" por categoría — traduce €/mes a €/día,
    horas trabajadas/mes y jornadas/mes según un sueldo/hora editable.
    """
    st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
    st.markdown(
        "<h3 style='margin:0 0 4px 0;'>⏱️ Coste-por-día por categoría</h3>"
        "<div style='color:#A1A1AA; font-size:0.85rem; margin-bottom:14px;'>"
        "Cada gasto traducido a tu tiempo real. Ajusta tu sueldo/hora "
        "y mide cuánto trabajo te cuesta cada categoría."
        "</div>",
        unsafe_allow_html=True,
    )

    # Sugerencia automática del sueldo/hora desde tus ingresos (no obligatorio)
    suggested = estimate_sueldo_hora_from_ingresos(df_diario, months_lookback=3)

    col_slider, col_hint = st.columns([2, 3])
    with col_slider:
        sueldo_hora = st.slider(
            "Tu sueldo/hora efectivo (€/h)",
            min_value=1.0,
            max_value=80.0,
            value=float(st.session_state.get("cpd_sueldo_hora", 10.0)),
            step=0.5,
            key="cpd_sueldo_hora",
            help=(
                "Importe que ganas por hora trabajada. Sirve para traducir "
                "cada gasto a tiempo. Sugerencia derivada de tus ingresos "
                "(43+44 ÷ 160 h): "
                f"{suggested:.2f} €/h"
                if suggested > 0
                else "Importe que ganas por hora trabajada. Sirve para traducir "
                "cada gasto a tiempo."
            ),
        )
    with col_hint:
        months_lookback = st.slider(
            "Ventana de cálculo (meses)",
            min_value=1,
            max_value=12,
            value=3,
            step=1,
            key="cpd_months_lookback",
            help="Promedio mensual sobre esta cantidad de meses recientes.",
        )

    df_cpd = compute_cost_per_day(
        df_diario,
        sueldo_hora_eur=float(sueldo_hora),
        months_lookback=int(months_lookback),
    )

    if is_filtered and filtered_cat:
        df_cpd = df_cpd[df_cpd["Categoría"] == filtered_cat]

    if df_cpd.empty:
        st.caption("Sin gastos en la ventana seleccionada.")
        return

    # Métricas rápidas
    total_eur_mes = float(df_cpd["€/mes"].sum())
    total_horas_mes = float(df_cpd["Horas/mes"].sum())
    total_jornadas_mes = float(df_cpd["Jornadas/mes"].sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("Total €/mes", f"{total_eur_mes:,.2f} €")
    c2.metric("Total horas/mes trabajadas para pagarlo", f"{total_horas_mes:,.1f} h")
    c3.metric("≈ Jornadas/mes (8 h)", f"{total_jornadas_mes:,.2f}")

    # Tabla con colores: cuanto más rojo, más impacto temporal
    def _hours_gradient(series: pd.Series) -> list[str]:
        vals = series.astype(float)
        if vals.empty or vals.max() <= 0:
            return ["" for _ in vals]
        cap = float(vals.quantile(0.90)) or float(vals.max())
        out = []
        for v in vals:
            v = float(v)
            if v <= 0:
                out.append("")
                continue
            t = min(v / cap, 1.0) ** 0.5
            r = int(24 + (255 - 24) * t)
            g = int(24 + (23 - 24) * t)
            b = int(27 + (68 - 27) * t)
            text_color = "#FFFFFF" if t > 0.5 else "#E4E4E7"
            out.append(
                f"background-color: rgb({r},{g},{b}); color: {text_color}; font-weight: 600;"
            )
        return out

    styled = df_cpd.style.format(
        {
            "€/mes": "{:,.2f} €",
            "€/día": "{:,.2f} €",
            "Horas/día": "{:.2f} h",
            "Horas/mes": "{:.1f} h",
            "Jornadas/mes": "{:.2f}",
        }
    ).apply(_hours_gradient, subset=["Horas/mes"])
    st.dataframe(styled, width="stretch", hide_index=True)

    # Mensaje accionable — categorías "ladrón de tiempo"
    if total_horas_mes > 0:
        top = df_cpd.iloc[0]
        st.caption(
            f"💡 La categoría que más tiempo te cuesta es "
            f"**{top['Categoría']}**: {top['Horas/mes']:.1f} h/mes "
            f"({top['Jornadas/mes']:.2f} jornadas completas). "
            f"Reducirla a la mitad te devolvería "
            f"{top['Horas/mes'] / 2:.1f} h cada mes para ti."
        )

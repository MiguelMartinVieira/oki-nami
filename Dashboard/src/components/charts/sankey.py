import pandas as pd
import plotly.graph_objects as go

from constants import (
    COLOR_BERKSHIRE,
    COLOR_INGRESOS,
    COLOR_SP500,
    get_category_color,
)
from services.utils import clean_cat_name

from .base import _LAYOUT_BASE, _apply_crystal_aesthetic


def _clean_cat_name(name) -> str:
    """Sanitiza nombres de categoría provenientes de GSheets (ej. elimina #N/A, 0, nan...)."""
    return clean_cat_name(name)


def _group_concepts(
    df_sub: pd.DataFrame | None, cat_col: str, amount_col: str, min_amount: float = 15.0
) -> pd.DataFrame:
    """
    Agrupa conceptos con importe < min_amount dentro de cada cuenta/categoría
    en un único nodo especificando la categoría 'Otros <Nombre> (<15€)'.
    """
    if df_sub is None or df_sub.empty:
        return pd.DataFrame(columns=[cat_col, "Categoría", amount_col])

    df_c = df_sub.copy()
    df_c["Categoría"] = df_c["Categoría"].fillna("").astype(str).str.strip()
    df_c.loc[df_c["Categoría"] == "", "Categoría"] = "Otros"

    if cat_col in df_c.columns:
        df_c[cat_col] = df_c[cat_col].apply(_clean_cat_name)

    grp = df_c.groupby([cat_col, "Categoría"])[amount_col].sum().reset_index()
    grp = grp[grp[amount_col] > 0]

    rows = []
    for c_name, sub in grp.groupby(cat_col):
        main_items = sub[sub[amount_col] >= min_amount]
        micro_items = sub[sub[amount_col] < min_amount]

        for _, r in main_items.iterrows():
            rows.append({cat_col: c_name, "Categoría": r["Categoría"], amount_col: r[amount_col]})

        if not micro_items.empty:
            otros_sum = micro_items[amount_col].sum()
            if otros_sum > 0:
                short_cat = str(c_name).replace("Gastos ", "").replace("Ingresos ", "").strip()
                label_otros = f"Otros {short_cat} (<15€)" if short_cat else "Otros (<15€)"
                rows.append({cat_col: c_name, "Categoría": label_otros, amount_col: otros_sum})

    return pd.DataFrame(rows)


def _reconcile_sub_concepts(
    sub_df: pd.DataFrame, amount_col: str, target_total: float
) -> pd.DataFrame:
    """
    Garantiza la ley de conservación de flujo en Sankey (inflow == outflow).
    Si la suma de conceptos difiere del total del nodo padre (por ejemplo, cuando
    hay ventas/desinversiones en una cuenta), absorbe el exceso en los conceptos
    mayores (waterfall) y ajusta diferencias residuales de punto flotante para
    que la suma de conceptos sea exactamente igual a target_total.
    """
    if sub_df is None or sub_df.empty or target_total <= 0:
        cols = (
            sub_df.columns if sub_df is not None and not sub_df.empty else ["Categoría", amount_col]
        )
        return pd.DataFrame(columns=cols)

    res = sub_df.copy().reset_index(drop=True)
    res[amount_col] = pd.to_numeric(res[amount_col], errors="coerce").fillna(0.0)
    current_sum = float(res[amount_col].sum())

    if current_sum <= 0:
        return pd.DataFrame(columns=res.columns)

    if current_sum > target_total:
        excess = current_sum - target_total
        res = res.sort_values(amount_col, ascending=False).reset_index(drop=True)
        for idx in range(len(res)):
            if excess <= 1e-6:
                break
            val = float(res.at[idx, amount_col])
            deduct = min(val, excess)
            res.at[idx, amount_col] = val - deduct
            excess -= deduct
        res = res[res[amount_col] > 1e-4].copy()

    if res.empty:
        return pd.DataFrame(columns=sub_df.columns)

    # Ajuste fino para cuadrar flotantes exactamente al céntimo
    diff = target_total - float(res[amount_col].sum())
    if abs(diff) > 1e-4 and not res.empty:
        max_idx = res[amount_col].idxmax()
        res.at[max_idx, amount_col] = float(res.at[max_idx, amount_col]) + diff

    return res[res[amount_col] > 0].copy()


def build_sankey(
    cat_incomes: pd.Series,
    cat_expenses: pd.Series,
    total_hist_ingresos: float,
    total_hist_gastos: float,
    df_ingresos: pd.DataFrame = None,
    df_gastos: pd.DataFrame = None,
    total_inversiones: float = 0.0,
    df_inversiones: pd.DataFrame = None,
    mode: str = "categories",  # "categories", "detailed", "expenses"
    min_concept_amount: float = 15.0,
) -> go.Figure | None:
    """
    Diagrama Sankey configurable en varios modos:
    - mode="categories": Visión General (3 niveles: Categorías Ingreso -> Total -> Categorías Gasto/Inv/Ahorro).
      Limpio, compacto (~440px) y sin sobrecarga visual.
    - mode="detailed": Desglose completo de 5 niveles con agrupación inteligente de micro-conceptos (<15€).
    - mode="expenses": Vista enfocada exclusivamente en el desglose de gastos (Total Gasto -> Categorías -> Conceptos).
    """
    # Sanitizar series de categorías
    if cat_incomes is not None and not cat_incomes.empty:
        cat_incomes = cat_incomes.copy()
        cat_incomes.index = [_clean_cat_name(str(idx)) for idx in cat_incomes.index]
        cat_incomes = cat_incomes.groupby(level=0).sum()
    else:
        cat_incomes = pd.Series(dtype=float)

    if cat_expenses is not None and not cat_expenses.empty:
        cat_expenses = cat_expenses.copy()
        cat_expenses.index = [_clean_cat_name(str(idx)) for idx in cat_expenses.index]
        cat_expenses = cat_expenses.groupby(level=0).sum()
    else:
        cat_expenses = pd.Series(dtype=float)

    if cat_incomes.empty and cat_expenses.empty and total_hist_gastos <= 0:
        return None

    # Sanitizar DataFrames
    if df_ingresos is not None and not df_ingresos.empty and "Cuenta" in df_ingresos.columns:
        df_ingresos = df_ingresos.copy()
        df_ingresos["Cuenta"] = df_ingresos["Cuenta"].apply(lambda x: _clean_cat_name(str(x)))

    if df_gastos is not None and not df_gastos.empty and "Cuenta" in df_gastos.columns:
        df_gastos = df_gastos.copy()
        df_gastos["Cuenta"] = df_gastos["Cuenta"].apply(lambda x: _clean_cat_name(str(x)))

    if (
        df_inversiones is not None
        and not df_inversiones.empty
        and "Cuenta" in df_inversiones.columns
    ):
        df_inversiones = df_inversiones.copy()
        df_inversiones["Cuenta"] = df_inversiones["Cuenta"].apply(lambda x: _clean_cat_name(str(x)))

    total_outflows = total_hist_gastos + max(total_inversiones, 0.0)
    ahorro_val = max(total_hist_ingresos - total_outflows, 0)
    deficit_val = max(total_outflows - total_hist_ingresos, 0)
    fondo_total = total_hist_ingresos + deficit_val

    labels, node_colors, x_pos, y_pos = [], [], [], []
    _node_values = []
    sources, targets, values, link_colors = [], [], [], []
    _idx = {}
    _col_nodes = {}

    def _lbl(name: str, val: float) -> str:
        res = f"{name} {val:,.2f}€"
        try:
            from services.demo_data import is_cipher_mode, scramble_numbers

            if is_cipher_mode():
                return scramble_numbers(res)
        except Exception:
            pass
        return res

    def _add(key: str, label: str, color: str, x: float, value: float = 0) -> int:
        if key in _idx:
            return _idx[key]
        i = len(labels)
        labels.append(label)
        node_colors.append(color)
        x_pos.append(x)
        y_pos.append(0)
        _node_values.append(value)
        _idx[key] = i
        col = round(x, 2)
        _col_nodes.setdefault(col, []).append((key, value))
        return i

    def _parse_rgba(c: str):
        c = c.strip()
        if c.startswith("#"):
            h = c.lstrip("#")
            if len(h) == 3:
                h = "".join(ch * 2 for ch in h)
            return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0
        if c.startswith("rgba("):
            parts = c[5:-1].split(",")
            return int(parts[0]), int(parts[1]), int(parts[2]), float(parts[3])
        if c.startswith("rgb("):
            parts = c[4:-1].split(",")
            return int(parts[0]), int(parts[1]), int(parts[2]), 1.0
        return 148, 163, 184, 0.3

    def _link(src_key, tgt_key, val, color_hex: str | None = None):
        if val <= 0 or src_key not in _idx or tgt_key not in _idx:
            return
        sources.append(_idx[src_key])
        targets.append(_idx[tgt_key])
        values.append(val)
        base = color_hex if color_hex else node_colors[_idx[src_key]]
        r, g, b, _ = _parse_rgba(base)

        mx = max(r, g, b)
        if mx > 0:
            factor = 255.0 / mx
            r = min(255, int(r * factor))
            g = min(255, int(g * factor))
            b = min(255, int(b * factor))

        link_colors.append(f"rgba({r},{g},{b},0.35)")

    def _lbl(name, amount):
        formatted = f"{name} {amount:,.2f}€"
        try:
            from services.demo_data import is_cipher_mode, scramble_numbers

            if is_cipher_mode():
                return scramble_numbers(formatted)
        except Exception:
            pass
        return formatted

    sorted_cat_incomes = cat_incomes.sort_values(ascending=False)
    sorted_cat_expenses = cat_expenses.sort_values(ascending=False)

    # -------------------------------------------------------------
    # MODO 1: EXPENSES (Solo Gastos)
    # -------------------------------------------------------------
    if mode == "expenses":
        total_g = total_hist_gastos if total_hist_gastos > 0 else sorted_cat_expenses.sum()
        _add("fondo_gasto", _lbl("Total Gastos", total_g), "#DC2626", 0.05, total_g)

        # Categorías de gasto
        for cat_name, cat_total in sorted_cat_expenses.items():
            _cat_color_exp = get_category_color(cat_name, is_expense=True)
            _add(f"ecat_{cat_name}", _lbl(cat_name, cat_total), _cat_color_exp, 0.50, cat_total)
            _link("fondo_gasto", f"ecat_{cat_name}", cat_total, color_hex=_cat_color_exp)

        grp_exp = _group_concepts(df_gastos, "Cuenta", "Debe", min_concept_amount)
        if not grp_exp.empty:
            for cat_name, cat_total in sorted_cat_expenses.items():
                _cat_color_exp = get_category_color(cat_name, is_expense=True)
                sub_grp = grp_exp[grp_exp["Cuenta"] == cat_name].sort_values(
                    "Debe", ascending=False
                )
                sub_grp = _reconcile_sub_concepts(sub_grp, "Debe", cat_total)
                if not sub_grp.empty:
                    for concept, amount in zip(
                        sub_grp["Categoría"].to_numpy(), sub_grp["Debe"].to_numpy(), strict=False
                    ):
                        key = f"ec_{cat_name}_{concept}"
                        _add(key, _lbl(concept, amount), _cat_color_exp, 0.95, amount)
                        _link(f"ecat_{cat_name}", key, amount)
                else:
                    _add(
                        f"ec_{cat_name}_dir",
                        _lbl(cat_name, cat_total),
                        _cat_color_exp,
                        0.95,
                        cat_total,
                    )
                    _link(f"ecat_{cat_name}", f"ec_{cat_name}_dir", cat_total)
        else:
            for cat_name, cat_total in sorted_cat_expenses.items():
                _cat_color_exp = get_category_color(cat_name, is_expense=True)
                _add(
                    f"ec_{cat_name}_dir", _lbl(cat_name, cat_total), _cat_color_exp, 0.95, cat_total
                )
                _link(f"ecat_{cat_name}", f"ec_{cat_name}_dir", cat_total)

        height = max(
            420, 200 + max(len(sorted_cat_expenses), len(grp_exp) if not grp_exp.empty else 5) * 35
        )

    # -------------------------------------------------------------
    # MODO 2: CATEGORIES (Visión General - 3 Niveles)
    # -------------------------------------------------------------
    elif mode == "categories":
        _add("fondo", _lbl("Total", fondo_total), "rgba(0,0,0,0)", 0.50, fondo_total)

        # Categorías de ingreso (x=0.05)
        for cat_name, cat_total in sorted_cat_incomes.items():
            _cat_color_inc = get_category_color(cat_name, is_expense=False)
            _add(f"icat_{cat_name}", _lbl(cat_name, cat_total), _cat_color_inc, 0.05, cat_total)
            _link(f"icat_{cat_name}", "fondo", cat_total)

        if deficit_val > 0:
            _add("deficit", _lbl("Déficit", deficit_val), "#DC2626", 0.05, deficit_val)
            _link("deficit", "fondo", deficit_val)

        # Categorías de gasto (x=0.95)
        for cat_name, cat_total in sorted_cat_expenses.items():
            _cat_color_exp = get_category_color(cat_name, is_expense=True)
            _add(f"ecat_{cat_name}", _lbl(cat_name, cat_total), _cat_color_exp, 0.95, cat_total)
            _link("fondo", f"ecat_{cat_name}", cat_total, color_hex=_cat_color_exp)

        if ahorro_val > 0:
            _add("ahorro", _lbl("Ahorro", ahorro_val), COLOR_INGRESOS, 0.95, ahorro_val)
            _link("fondo", "ahorro", ahorro_val, color_hex=COLOR_INGRESOS)

        if total_inversiones > 0:
            if (
                df_inversiones is not None
                and not df_inversiones.empty
                and "Cuenta" in df_inversiones.columns
            ):
                df_inv_calc = df_inversiones.copy()
                debe_s = (
                    pd.to_numeric(df_inv_calc["Debe"], errors="coerce").fillna(0)
                    if "Debe" in df_inv_calc.columns
                    else 0.0
                )
                haber_s = (
                    pd.to_numeric(df_inv_calc["Haber"], errors="coerce").fillna(0)
                    if "Haber" in df_inv_calc.columns
                    else 0.0
                )
                df_inv_calc["Importe"] = debe_s - haber_s
                grp_cuenta = df_inv_calc.groupby("Cuenta")["Importe"].sum().reset_index()
                for c_name, c_amount in zip(
                    grp_cuenta["Cuenta"].to_numpy(), grp_cuenta["Importe"].to_numpy(), strict=False
                ):
                    if c_amount > 0:
                        c_color = (
                            COLOR_BERKSHIRE
                            if "berkshire" in c_name.lower()
                            else (
                                COLOR_SP500
                                if "vanguard" in c_name.lower() or "sp500" in c_name.lower()
                                else COLOR_BERKSHIRE
                            )
                        )
                        _add(f"inv_cat_{c_name}", _lbl(c_name, c_amount), c_color, 0.95, c_amount)
                        _link("fondo", f"inv_cat_{c_name}", c_amount, color_hex=c_color)
            else:
                _add(
                    "inv_cat",
                    _lbl("Inversiones", total_inversiones),
                    COLOR_BERKSHIRE,
                    0.95,
                    total_inversiones,
                )
                _link("fondo", "inv_cat", total_inversiones, color_hex=COLOR_BERKSHIRE)

        max_nodes = max(
            len(sorted_cat_incomes) + (1 if deficit_val > 0 else 0), len(sorted_cat_expenses) + 2
        )
        height = max(440, 220 + max_nodes * 35)

    # -------------------------------------------------------------
    # MODO 3: DETAILED (Desglose Completo 5 Niveles con Agrupación)
    # -------------------------------------------------------------
    else:
        _add("fondo", _lbl("Total", fondo_total), "rgba(0,0,0,0)", 0.50, fondo_total)

        # Level 2: Categorías de Ingreso (x=0.25)
        for cat_name, cat_total in sorted_cat_incomes.items():
            _cat_color_inc = get_category_color(cat_name, is_expense=False)
            _add(f"icat_{cat_name}", _lbl(cat_name, cat_total), _cat_color_inc, 0.25, cat_total)
            _link(f"icat_{cat_name}", "fondo", cat_total)

        grp_inc = _group_concepts(df_ingresos, "Cuenta", "Haber", min_concept_amount)
        if not grp_inc.empty:
            for cat_name, cat_total in sorted_cat_incomes.items():
                _cat_color_inc = get_category_color(cat_name, is_expense=False)
                sub_grp = grp_inc[grp_inc["Cuenta"] == cat_name].sort_values(
                    "Haber", ascending=False
                )
                sub_grp = _reconcile_sub_concepts(sub_grp, "Haber", cat_total)
                if not sub_grp.empty:
                    for concept, amount in zip(
                        sub_grp["Categoría"].to_numpy(), sub_grp["Haber"].to_numpy(), strict=False
                    ):
                        key = f"ic_{cat_name}_{concept}"
                        _add(key, _lbl(concept, amount), _cat_color_inc, 0.01, amount)
                        _link(key, f"icat_{cat_name}", amount)
                else:
                    _add(
                        f"ic_{cat_name}_dir",
                        _lbl(cat_name, cat_total),
                        _cat_color_inc,
                        0.01,
                        cat_total,
                    )
                    _link(f"ic_{cat_name}_dir", f"icat_{cat_name}", cat_total)
        else:
            for cat_name, cat_total in sorted_cat_incomes.items():
                _cat_color_inc = get_category_color(cat_name, is_expense=False)
                _add(
                    f"ic_{cat_name}_dir", _lbl(cat_name, cat_total), _cat_color_inc, 0.01, cat_total
                )
                _link(f"ic_{cat_name}_dir", f"icat_{cat_name}", cat_total)

        if deficit_val > 0:
            _add("deficit", _lbl("Déficit", deficit_val), "#DC2626", 0.25, deficit_val)
            _link("deficit", "fondo", deficit_val)

        # Level 4: Categorías de Gasto (x=0.75)
        for cat_name, cat_total in sorted_cat_expenses.items():
            _cat_color_exp = get_category_color(cat_name, is_expense=True)
            _add(f"ecat_{cat_name}", _lbl(cat_name, cat_total), _cat_color_exp, 0.75, cat_total)
            _link("fondo", f"ecat_{cat_name}", cat_total, color_hex=_cat_color_exp)

        grp_exp = _group_concepts(df_gastos, "Cuenta", "Debe", min_concept_amount)
        if not grp_exp.empty:
            for cat_name, cat_total in sorted_cat_expenses.items():
                _cat_color_exp = get_category_color(cat_name, is_expense=True)
                sub_grp = grp_exp[grp_exp["Cuenta"] == cat_name].sort_values(
                    "Debe", ascending=False
                )
                sub_grp = _reconcile_sub_concepts(sub_grp, "Debe", cat_total)
                if not sub_grp.empty:
                    for concept, amount in zip(
                        sub_grp["Categoría"].to_numpy(), sub_grp["Debe"].to_numpy(), strict=False
                    ):
                        key = f"ec_{cat_name}_{concept}"
                        _add(key, _lbl(concept, amount), _cat_color_exp, 0.99, amount)
                        _link(f"ecat_{cat_name}", key, amount)
                else:
                    _add(
                        f"ec_{cat_name}_dir",
                        _lbl(cat_name, cat_total),
                        _cat_color_exp,
                        0.99,
                        cat_total,
                    )
                    _link(f"ecat_{cat_name}", f"ec_{cat_name}_dir", cat_total)
        else:
            for cat_name, cat_total in sorted_cat_expenses.items():
                _cat_color_exp = get_category_color(cat_name, is_expense=True)
                _add(
                    f"ec_{cat_name}_dir", _lbl(cat_name, cat_total), _cat_color_exp, 0.99, cat_total
                )
                _link(f"ecat_{cat_name}", f"ec_{cat_name}_dir", cat_total)

        # Inversiones (Level 4: x=0.75, Level 5: x=0.99)
        if total_inversiones > 0:
            if (
                df_inversiones is not None
                and not df_inversiones.empty
                and "Cuenta" in df_inversiones.columns
            ):
                df_inv_calc = df_inversiones.copy()
                debe_s = (
                    pd.to_numeric(df_inv_calc["Debe"], errors="coerce").fillna(0)
                    if "Debe" in df_inv_calc.columns
                    else 0.0
                )
                haber_s = (
                    pd.to_numeric(df_inv_calc["Haber"], errors="coerce").fillna(0)
                    if "Haber" in df_inv_calc.columns
                    else 0.0
                )
                df_inv_calc["Importe"] = debe_s - haber_s
                grp_inv = _group_concepts(df_inv_calc, "Cuenta", "Importe", min_concept_amount)
                grp_cuenta = df_inv_calc.groupby("Cuenta")["Importe"].sum().reset_index()
                for c_name, c_amount in zip(
                    grp_cuenta["Cuenta"].to_numpy(), grp_cuenta["Importe"].to_numpy(), strict=False
                ):
                    if c_amount > 0:
                        c_color = (
                            COLOR_BERKSHIRE
                            if "berkshire" in c_name.lower()
                            else (
                                COLOR_SP500
                                if "vanguard" in c_name.lower() or "sp500" in c_name.lower()
                                else COLOR_BERKSHIRE
                            )
                        )
                        key_cuenta = f"inv_cat_{c_name}"
                        _add(key_cuenta, _lbl(c_name, c_amount), c_color, 0.75, c_amount)
                        _link("fondo", key_cuenta, c_amount, color_hex=c_color)

                        sub_inv = (
                            grp_inv[grp_inv["Cuenta"] == c_name]
                            if not grp_inv.empty
                            else pd.DataFrame()
                        )
                        sub_inv = _reconcile_sub_concepts(sub_inv, "Importe", c_amount)
                        if not sub_inv.empty:
                            for concept, amount in zip(
                                sub_inv["Categoría"].to_numpy(),
                                sub_inv["Importe"].to_numpy(),
                                strict=False,
                            ):
                                if amount > 0:
                                    key_concepto = f"inv_c_{c_name}_{concept}"
                                    _add(key_concepto, _lbl(concept, amount), c_color, 0.99, amount)
                                    _link(key_cuenta, key_concepto, amount)
                        else:
                            key_concepto = f"inv_c_{c_name}_dir"
                            _add(key_concepto, _lbl(c_name, c_amount), c_color, 0.99, c_amount)
                            _link(key_cuenta, key_concepto, c_amount)
            else:
                _add(
                    "inv_cat",
                    _lbl("Inversiones", total_inversiones),
                    COLOR_BERKSHIRE,
                    0.75,
                    total_inversiones,
                )
                _link("fondo", "inv_cat", total_inversiones, color_hex=COLOR_BERKSHIRE)
                _add(
                    "inv_dir",
                    _lbl("Inversiones", total_inversiones),
                    COLOR_BERKSHIRE,
                    0.99,
                    total_inversiones,
                )
                _link("inv_cat", "inv_dir", total_inversiones)

        # Ahorro (Level 4: x=0.75, Level 5: x=0.99)
        if ahorro_val > 0:
            _add("ahorro_mid", "", COLOR_INGRESOS, 0.75, ahorro_val)
            _add("ahorro", _lbl("Ahorro", ahorro_val), COLOR_INGRESOS, 0.99, ahorro_val)
            _link("fondo", "ahorro_mid", ahorro_val, color_hex=COLOR_INGRESOS)
            _link("ahorro_mid", "ahorro", ahorro_val)

        max_nodes_col = max(len(nodes) for nodes in _col_nodes.values()) if _col_nodes else 5
        height = max(520, 240 + max_nodes_col * 38)

    # ── Posiciones Y explícitas por columna ──
    NODE_PAD_PX = 14
    for _col, nodes in _col_nodes.items():
        n_count = len(nodes)
        if n_count == 1:
            y_pos[_idx[nodes[0][0]]] = 0.5
            continue

        total_val = sum(v for _, v in nodes)
        if total_val <= 0:
            for j, (k, _) in enumerate(nodes):
                y_pos[_idx[k]] = (j + 0.5) / n_count
            continue

        pad_norm = NODE_PAD_PX / float(height)
        total_pad_norm = pad_norm * (n_count - 1)
        usable_norm = max(0.1, 1.0 - total_pad_norm - 0.02)
        cursor = 0.01

        for k, v in nodes:
            h_k = (v / total_val) * usable_norm
            y_pos[_idx[k]] = cursor + h_k / 2.0
            cursor += h_k + pad_norm

    try:
        from services.demo_data import is_cipher_mode, scramble_numbers

        if is_cipher_mode():
            labels = [scramble_numbers(lbl) for lbl in labels]
    except Exception:
        pass

    # ── Construir figura Plotly ──
    fig = go.Figure(
        data=[
            go.Sankey(
                arrangement="perpendicular",
                node=dict(
                    pad=NODE_PAD_PX,
                    thickness=4,
                    label=labels,
                    color=node_colors,
                    line=dict(color="#FFFFFF", width=0.5),
                    x=x_pos,
                    y=y_pos,
                ),
                link=dict(source=sources, target=targets, value=values, color=link_colors),
            )
        ]
    )

    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=10, b=10),
        title_text="",
        font_size=11,
        **_LAYOUT_BASE,
    )
    fig.update_layout(font=dict(color="#FFFFFF"))
    return _apply_crystal_aesthetic(fig)

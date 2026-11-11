import pandas as pd
import plotly.graph_objects as go
import pytest

from components.charts.sankey import _clean_cat_name, _group_concepts, build_sankey


def test_clean_cat_name():
    assert _clean_cat_name("Gastos Comida") == "Gastos Comida"
    assert _clean_cat_name("#N/A (Did not find value '45' in VLOOKUP evaluation.)") == "Cuenta 45"
    assert _clean_cat_name("#N/A") == "Sin Categorizar"
    assert _clean_cat_name("") == "Sin Categorizar"
    assert _clean_cat_name(None) == "Sin Categorizar"


def test_group_concepts():
    df_sample = pd.DataFrame(
        [
            {"Cuenta": "Gastos Comida", "Categoría": "Supermercado", "Debe": 55.0},
            {"Cuenta": "Gastos Comida", "Categoría": "Café", "Debe": 2.50},
            {"Cuenta": "Gastos Comida", "Categoría": "Snack", "Debe": 1.20},
            {"Cuenta": "Gastos Comida", "Categoría": "Chuchería", "Debe": 0.80},
        ]
    )
    res = _group_concepts(df_sample, "Cuenta", "Debe", min_amount=15.0)
    assert not res.empty
    # Supermercado >= 15€ debe mantenerse
    assert "Supermercado" in res["Categoría"].values
    # Café, Snack, Chuchería < 15€ deben agruparse en "Otros Comida (<15€)"
    assert "Otros Comida (<15€)" in res["Categoría"].values
    otros_val = res[res["Categoría"] == "Otros Comida (<15€)"]["Debe"].values[0]
    assert otros_val == 4.50


def test_build_sankey_empty():
    fig = build_sankey(pd.Series(dtype=float), pd.Series(dtype=float), 0.0, 0.0)
    assert fig is None


def test_build_sankey_categories_mode():
    cat_inc = pd.Series(
        {"Ingresos Ítaca": 1000.0, "#N/A (Did not find value '41' in VLOOKUP)": 500.0}
    )
    cat_exp = pd.Series({"Gastos Comida": 400.0, "Gastos Gym": 100.0})

    fig = build_sankey(
        cat_incomes=cat_inc,
        cat_expenses=cat_exp,
        total_hist_ingresos=1500.0,
        total_hist_gastos=500.0,
        total_inversiones=200.0,
        mode="categories",
    )
    assert isinstance(fig, go.Figure)
    sankey_data = fig.data[0]
    labels = sankey_data.node.label
    x_positions = set(sankey_data.node.x)

    # Debe contener etiquetas de categoría sanitizadas
    assert any("Ingresos Ítaca" in lbl for lbl in labels)
    assert any("Cuenta 41" in lbl for lbl in labels)
    assert any("Gastos Comida" in lbl for lbl in labels)

    # Las posiciones X en modo categorías solo son 0.05, 0.50 y 0.95
    assert x_positions.issubset({0.05, 0.50, 0.95})


def test_build_sankey_detailed_mode():
    cat_inc = pd.Series({"Ingresos Ítaca": 1000.0})
    cat_exp = pd.Series({"Gastos Comida": 500.0})

    df_gastos = pd.DataFrame(
        [
            {"Cuenta": "Gastos Comida", "Categoría": "Mercadona", "Debe": 450.0},
            {"Cuenta": "Gastos Comida", "Categoría": "Pan", "Debe": 2.0},
            {"Cuenta": "Gastos Comida", "Categoría": "Chicle", "Debe": 1.0},
        ]
    )

    fig = build_sankey(
        cat_incomes=cat_inc,
        cat_expenses=cat_exp,
        total_hist_ingresos=1000.0,
        total_hist_gastos=500.0,
        df_gastos=df_gastos,
        mode="detailed",
        min_concept_amount=15.0,
    )
    assert isinstance(fig, go.Figure)
    labels = fig.data[0].node.label

    # En modo detallado, debe mostrar Mercadona y agrupado Otros Comida (<15€)
    assert any("Mercadona" in lbl for lbl in labels)
    assert any("Otros Comida (<15€)" in lbl for lbl in labels)


def test_build_sankey_expenses_mode():
    cat_exp = pd.Series({"Gastos Comida": 300.0, "Gastos Gym": 80.0})
    fig = build_sankey(
        cat_incomes=pd.Series(dtype=float),
        cat_expenses=cat_exp,
        total_hist_ingresos=0.0,
        total_hist_gastos=380.0,
        mode="expenses",
    )
    assert isinstance(fig, go.Figure)
    labels = fig.data[0].node.label
    assert any("Total Gastos" in lbl for lbl in labels)
    assert any("Gastos Comida" in lbl for lbl in labels)


def test_sankey_no_y_overlaps():
    cat_inc = pd.Series({"Ingresos Sueldo": 3000.0, "Ingresos Extra": 500.0})
    cat_exp = pd.Series(
        {
            "Gastos Comida": 200.0,
            "Gastos Ropa": 100.0,
            "Gastos Cafe": 10.0,
        }
    )
    df_gastos = pd.DataFrame(
        [
            {"Cuenta": "Gastos Comida", "Categoría": "Super", "Debe": 200.0},
            {"Cuenta": "Gastos Ropa", "Categoría": "Tienda", "Debe": 100.0},
            {"Cuenta": "Gastos Cafe", "Categoría": "Café", "Debe": 10.0},
        ]
    )
    df_inv = pd.DataFrame(
        [
            {"Cuenta": "Berkshire Hathaway", "Categoría": "Fondo", "Debe": 300.0},
        ]
    )

    fig = build_sankey(
        cat_incomes=cat_inc,
        cat_expenses=cat_exp,
        total_hist_ingresos=3500.0,
        total_hist_gastos=310.0,
        df_gastos=df_gastos,
        total_inversiones=300.0,
        df_inversiones=df_inv,
        mode="detailed",
    )
    assert isinstance(fig, go.Figure)

    nodes_by_x = {}
    for label, x, y in zip(
        fig.data[0].node.label, fig.data[0].node.x, fig.data[0].node.y, strict=False
    ):
        col = round(x, 2)
        nodes_by_x.setdefault(col, []).append((label, y))

    for col, nodes in nodes_by_x.items():
        if len(nodes) > 1:
            ys = [y for _, y in nodes]
            assert ys == sorted(ys), f"Los nodos en x={col} no están ordenados monótonamente en Y"


def test_sankey_inversiones_subtract_sales():
    cat_inc = pd.Series({"Sueldo": 2000.0})
    cat_exp = pd.Series({"Comida": 500.0})
    # Compra 600, Venta 200 -> Neto 400
    df_inv = pd.DataFrame(
        [
            {"Cuenta": "Berkshire Hathaway", "Categoría": "Fondo", "Debe": 600.0, "Haber": 0.0},
            {"Cuenta": "Berkshire Hathaway", "Categoría": "Fondo", "Debe": 0.0, "Haber": 200.0},
        ]
    )
    # Mode categories
    fig_cat = build_sankey(
        cat_incomes=cat_inc,
        cat_expenses=cat_exp,
        total_hist_ingresos=2000.0,
        total_hist_gastos=500.0,
        total_inversiones=400.0,
        df_inversiones=df_inv,
        mode="categories",
    )
    assert isinstance(fig_cat, go.Figure)
    labels_cat = fig_cat.data[0].node.label
    assert any("Berkshire Hathaway 400.00€" in lbl for lbl in labels_cat)

    # Mode detailed
    fig_det = build_sankey(
        cat_incomes=cat_inc,
        cat_expenses=cat_exp,
        total_hist_ingresos=2000.0,
        total_hist_gastos=500.0,
        total_inversiones=400.0,
        df_inversiones=df_inv,
        mode="detailed",
    )
    assert isinstance(fig_det, go.Figure)
    labels_det = fig_det.data[0].node.label
    assert any("Berkshire Hathaway 400.00€" in lbl for lbl in labels_det)


def test_reconcile_sub_concepts():
    from components.charts.sankey import _reconcile_sub_concepts

    # Escenario: Bote 3643.90, Round Up 158.32, Saveback 33.93 con objetivo 2436.15 (1400 venta)
    df_sub = pd.DataFrame(
        [
            {"Categoría": "Bote", "Importe": 3643.90},
            {"Categoría": "Round Up", "Importe": 158.32},
            {"Categoría": "Saveback", "Importe": 33.93},
        ]
    )
    res = _reconcile_sub_concepts(df_sub, "Importe", 2436.15)
    assert res["Importe"].sum() == pytest.approx(2436.15)
    # Bote absorbe los 1400 de venta
    assert res[res["Categoría"] == "Bote"]["Importe"].iloc[0] == pytest.approx(2243.90)
    assert res[res["Categoría"] == "Round Up"]["Importe"].iloc[0] == pytest.approx(158.32)
    assert res[res["Categoría"] == "Saveback"]["Importe"].iloc[0] == pytest.approx(33.93)


def test_sankey_detailed_mode_inflow_equals_outflow_with_sales():
    cat_inc = pd.Series({"Sueldo": 5000.0})
    cat_exp = pd.Series({"Gastos Comida": 500.0})
    df_gastos = pd.DataFrame(
        [{"Cuenta": "Gastos Comida", "Categoría": "Super", "Debe": 500.0, "Haber": 0.0}]
    )
    df_inv = pd.DataFrame(
        [
            {"Cuenta": "Berkshire Hathaway", "Categoría": "Bote", "Debe": 3643.90, "Haber": 0.0},
            {"Cuenta": "Berkshire Hathaway", "Categoría": "Round Up", "Debe": 158.32, "Haber": 0.0},
            {"Cuenta": "Berkshire Hathaway", "Categoría": "Saveback", "Debe": 33.93, "Haber": 0.0},
            {
                "Cuenta": "Berkshire Hathaway",
                "Categoría": "Venta Berkshire",
                "Debe": 0.0,
                "Haber": 1399.00,
            },
            {
                "Cuenta": "Berkshire Hathaway",
                "Categoría": "Comisiones Venta",
                "Debe": 0.0,
                "Haber": 1.00,
            },
        ]
    )
    net_inv = (3643.90 + 158.32 + 33.93) - 1400.00  # 2436.15
    fig = build_sankey(
        cat_incomes=cat_inc,
        cat_expenses=cat_exp,
        total_hist_ingresos=5000.0,
        total_hist_gastos=500.0,
        df_gastos=df_gastos,
        total_inversiones=net_inv,
        df_inversiones=df_inv,
        mode="detailed",
    )
    assert isinstance(fig, go.Figure)
    labels = fig.data[0].node.label
    brk_idx = [i for i, lbl in enumerate(labels) if "Berkshire Hathaway 2,436.15€" in lbl][0]

    # Calcular inflow y outflow del nodo Berkshire Hathaway
    inflow = sum(
        val
        for src, tgt, val in zip(
            fig.data[0].link.source, fig.data[0].link.target, fig.data[0].link.value, strict=False
        )
        if tgt == brk_idx
    )
    outflow = sum(
        val
        for src, tgt, val in zip(
            fig.data[0].link.source, fig.data[0].link.target, fig.data[0].link.value, strict=False
        )
        if src == brk_idx
    )

    assert inflow == pytest.approx(2436.15)
    assert outflow == pytest.approx(2436.15)
    assert inflow == pytest.approx(outflow)

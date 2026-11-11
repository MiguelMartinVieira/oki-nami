# ──────────────────────────────────────────────
# 1. Fiscalidad (España)
# ──────────────────────────────────────────────

# Tramos de la base del ahorro (España, IRPF 2024). Cada tupla es
# `(tamaño_del_tramo, tipo_marginal)`. Fuente única de verdad — se usa
# tanto aquí como en `components/fiscal_sim.py` para el desglose visual.
TRAMOS_IRPF: list[tuple[float, float]] = [
    (6_000.0, 0.19),  # Hasta 6.000€: 19%
    (44_000.0, 0.21),  # De 6.000€ a 50.000€ (tramo de 44k): 21%
    (150_000.0, 0.23),  # De 50.000€ a 200.000€ (tramo de 150k): 23%
    (float("inf"), 0.26),  # Más de 200.000€: 26%
]


def calc_tax_spain(plusvalia: float) -> float:
    """Cuota fiscal estimada sobre plusvalías en España (base del ahorro 2024)."""
    if plusvalia <= 0:
        return 0.0
    tax = 0.0
    remaining = plusvalia
    for tramo_size, rate in TRAMOS_IRPF:
        taxable = min(remaining, tramo_size)
        tax += taxable * rate
        remaining -= taxable
        if remaining <= 0:
            break
    return round(tax, 2)

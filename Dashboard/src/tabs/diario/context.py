from dataclasses import dataclass

import pandas as pd


@dataclass
class DiarioContext:
    df_diario: pd.DataFrame
    gi: dict
    total_patrimonio: float
    delta_patrimonio: float | None
    ahorro_mes: float
    tasa_ahorro_mes: float
    color_ahorro: str

    # Filter state
    is_filtered: bool
    filtered_cat: str | None
    is_expense_filter: bool
    filt_all: pd.DataFrame
    filt_cm: pd.DataFrame
    filt_cat_totals: pd.Series

    # Date Period Filter state
    date_mode: str = "🌐 Histórico Completo"
    date_label: str = "Histórico Completo"
    start_date: pd.Timestamp | None = None
    end_date: pd.Timestamp | None = None

    # Common extracted from gi
    @property
    def df_gastos(self) -> pd.DataFrame:
        return self.gi["df_gastos"]

    @property
    def df_ingresos(self) -> pd.DataFrame:
        return self.gi["df_ingresos"]

    @property
    def df_gastos_cm(self) -> pd.DataFrame:
        return self.gi["df_gastos_cm"]

    @property
    def df_ingresos_cm(self) -> pd.DataFrame:
        return self.gi["df_ingresos_cm"]

    @property
    def cat_expenses(self) -> pd.Series:
        return self.gi["cat_expenses"]

    @property
    def cat_incomes(self) -> pd.Series:
        return self.gi["cat_incomes"]

"""
pdf_generator.py — Generación de informes en PDF usando fpdf2.
"""

from datetime import datetime

import pandas as pd
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from constants import DATE_FORMAT


class OkiNamiPDF(FPDF):
    def header(self):
        # Logo o Título
        self.set_font("helvetica", "B", 15)
        self.set_text_color(15, 23, 42)  # #0F172A
        self.cell(
            0,
            10,
            "Oki-Nami - Dashboard de Finanzas",
            border=0,
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="L",
        )
        self.set_font("helvetica", "I", 8)
        self.cell(
            0,
            5,
            f"Generado el {datetime.now().strftime(DATE_FORMAT + ' %H:%M')}",
            border=0,
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="L",
        )
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(100)
        self.cell(0, 10, f"Página {self.page_no()}/{{nb}}", align="C")


from constants import MESES_ES


def generate_padres_pdf(
    df_131: pd.DataFrame,
    year: int | None = None,
    month: int | None = None,
    df_subset: pd.DataFrame | None = None,
    title_suffix: str | None = None,
) -> bytes:
    """Genera el informe de Padres en PDF."""
    if df_subset is not None and not df_subset.empty:
        df_mes = df_subset.copy()
        if "Fecha" in df_mes.columns:
            df_mes["Fecha"] = pd.to_datetime(df_mes["Fecha"], dayfirst=True, errors="coerce")
    else:
        df = df_131.copy()
        df["Fecha"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")
        if year is not None and month is not None:
            df_mes = df[(df["Fecha"].dt.year == year) & (df["Fecha"].dt.month == month)].copy()
        else:
            df_mes = df.copy()

    if "Fecha" in df_mes.columns:
        df_mes = df_mes.sort_values("Fecha", na_position="last")

    total_debe = df_mes["Debe"].fillna(0).sum() if "Debe" in df_mes.columns else 0.0
    total_haber = df_mes["Haber"].fillna(0).sum() if "Haber" in df_mes.columns else 0.0
    saldo = total_debe - total_haber

    pdf = OkiNamiPDF()
    pdf.add_page()

    # Título de sección
    pdf.set_font("helvetica", "B", 16)
    if title_suffix:
        pdf_title = f"Informe de Gastos - {title_suffix}"
    elif month is not None and year is not None:
        pdf_title = f"Informe de Gastos - {MESES_ES.get(month, month)} {year}"
    else:
        pdf_title = "Informe de Gastos - Liquidación"

    pdf.cell(
        0,
        10,
        pdf_title,
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(5)

    # Resumen
    pdf.set_font("helvetica", "B", 12)
    pdf.set_fill_color(248, 249, 250)
    pdf.cell(100, 10, "Concepto", border=1, fill=True)
    pdf.cell(40, 10, "Importe", border=1, fill=True, align="R")
    pdf.ln()

    pdf.set_font("helvetica", "", 11)
    pdf.cell(100, 10, "Total Gastado (Debe)", border=1)
    pdf.cell(40, 10, f"{total_debe:,.2f} EUR", border=1, align="R")
    pdf.ln()
    pdf.cell(100, 10, "Total Devuelto (Haber)", border=1)
    pdf.cell(40, 10, f"{total_haber:,.2f} EUR", border=1, align="R")
    pdf.ln()
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(100, 10, "SALDO PENDIENTE", border=1, fill=True)
    pdf.cell(40, 10, f"{saldo:,.2f} EUR", border=1, fill=True, align="R")
    pdf.ln(15)

    # Tabla de Movimientos
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "Detalle de Movimientos", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    # Cabecera tabla
    pdf.set_font("helvetica", "B", 10)
    pdf.set_fill_color(59, 130, 246)  # Primary Blue
    pdf.set_text_color(255)
    pdf.cell(25, 8, "Fecha", border=1, fill=True)
    pdf.cell(40, 8, "Categoría", border=1, fill=True)
    pdf.cell(85, 8, "Descripción", border=1, fill=True)
    pdf.cell(20, 8, "Debe", border=1, fill=True, align="R")
    pdf.cell(20, 8, "Haber", border=1, fill=True, align="R")
    pdf.ln()

    pdf.set_text_color(0)
    pdf.set_font("helvetica", "", 9)
    for _, row in df_mes.iterrows():
        val_f = row.get("Fecha")
        if pd.isna(val_f):
            fecha = ""
        elif hasattr(val_f, "strftime"):
            try:
                fecha = val_f.strftime(DATE_FORMAT)
            except (ValueError, AttributeError):
                fecha = str(val_f)
        else:
            fecha = str(val_f)

        cat = str(row.get("Categoría", ""))[:20]
        desc = str(row.get("Descripción", ""))[:45]
        debe = f"{row['Debe']:,.2f}" if pd.notna(row.get("Debe")) and row.get("Debe") != 0 else ""
        haber = (
            f"{row['Haber']:,.2f}" if pd.notna(row.get("Haber")) and row.get("Haber") != 0 else ""
        )

        pdf.cell(25, 7, fecha, border=1)
        pdf.cell(40, 7, cat, border=1)
        pdf.cell(85, 7, desc, border=1)
        pdf.cell(20, 7, debe, border=1, align="R")
        pdf.cell(20, 7, haber, border=1, align="R")
        pdf.ln()

    return bytes(pdf.output())


def generate_fiscal_pdf(
    asset_name, total_invested, valor_actual, plusvalia, cuota, neto, tipo_efectivo
) -> bytes:
    """Genera el informe fiscal de un activo en PDF."""
    pdf = OkiNamiPDF()
    pdf.add_page()

    pdf.set_font("helvetica", "B", 16)
    pdf.cell(
        0, 10, f"Análisis de Impacto Fiscal - {asset_name}", new_x=XPos.LMARGIN, new_y=YPos.NEXT
    )
    pdf.ln(10)

    # Grid de métricas
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(90, 10, "Métrica", border=1, fill=True)
    pdf.cell(60, 10, "Valor", border=1, fill=True, align="R")
    pdf.ln()

    pdf.set_font("helvetica", "", 11)
    metrics = [
        ("Inversión Total", f"{total_invested:,.2f} EUR"),
        ("Valor de Mercado Actual", f"{valor_actual:,.2f} EUR"),
        ("Plusvalía Latente", f"{plusvalia:,.2f} EUR"),
        ("Cuota Estimada IRPF (España 2024)", f"-{cuota:,.2f} EUR"),
        ("Neto tras Impuestos", f"{neto:,.2f} EUR"),
        ("Tipo Efectivo de Gravamen", f"{tipo_efectivo:.2f} %"),
    ]

    for label, val in metrics:
        pdf.cell(90, 10, label, border=1)
        pdf.cell(60, 10, val, border=1, align="R")
        pdf.ln()

    pdf.ln(10)
    pdf.set_font("helvetica", "I", 9)
    pdf.multi_cell(
        0,
        5,
        "Nota: Esta estimación es orientativa y se basa en los tramos del ahorro vigentes en España (19%, 21%, 23%, 26%). Consulta con un asesor fiscal antes de realizar operaciones.",
    )

    return bytes(pdf.output())

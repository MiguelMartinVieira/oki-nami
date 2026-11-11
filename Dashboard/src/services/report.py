"""
report.py — Generación de informes en Excel y CSV de Padres (Cuenta 131).
"""

import io

import pandas as pd

from constants import DATE_FORMAT, PADRES_DRIVE_FOLDER_ID, drive_folder_url

DRIVE_FOLDER_URL = drive_folder_url(PADRES_DRIVE_FOLDER_ID)


def _mes_anterior() -> tuple[int, int]:
    """Devuelve (año, mes) del mes anterior al actual."""
    today = pd.Timestamp.today()
    if today.month == 1:
        return today.year - 1, 12
    return today.year, today.month - 1


def _format_fecha_export(series: pd.Series) -> pd.Series:
    """Formatea la columna Fecha garantizando no alterar fechas ni perder valores NaT."""
    dt = pd.to_datetime(series, errors="coerce")
    mask_nat = dt.isna() & series.notna()
    if mask_nat.any():
        dt.loc[mask_nat] = pd.to_datetime(series.loc[mask_nat], dayfirst=True, errors="coerce")

    formatted = dt.dt.strftime(DATE_FORMAT)
    return formatted.fillna(
        series.astype(str).replace("nan", "").replace("None", "").replace("<NaT>", "")
    )


def generate_padres_export_df(
    df_matched: pd.DataFrame,
    year: int | None = None,
    month: int | None = None,
    df_subset: pd.DataFrame | None = None,
    only_expenses: bool = False,
) -> pd.DataFrame:
    """
    Prepara el DataFrame de exportación para la cuenta 131 (Padres).
    Si se proporciona df_subset, usa esas filas directamente.
    De lo contrario, filtra por año y mes.
    Mantiene la estructura completa de la tabla vista en el Dashboard:
    [Fecha, Categoría, Descripción, Debe, Haber, Justificante, Estado, Enlace archivo Drive]
    """
    if df_subset is not None and not df_subset.empty:
        df_mes = df_subset.copy()
    else:
        df = df_matched.copy()
        dt_temp = pd.to_datetime(df["Fecha"], errors="coerce")
        mask_nat = dt_temp.isna() & df["Fecha"].notna()
        if mask_nat.any():
            dt_temp.loc[mask_nat] = pd.to_datetime(
                df["Fecha"].loc[mask_nat], dayfirst=True, errors="coerce"
            )

        if year is not None and month is not None:
            df_mes = df[(dt_temp.dt.year == year) & (dt_temp.dt.month == month)].copy()
        else:
            df_mes = df.copy()

    if only_expenses and "Debe" in df_mes.columns:
        df_mes = df_mes[df_mes["Debe"].fillna(0) > 0].copy()

    # Garantizar presencia y limpieza de columnas
    for c in ["Categoría", "Descripción", "Justificante", "Estado"]:
        if c not in df_mes.columns:
            df_mes[c] = ""
        else:
            df_mes[c] = df_mes[c].fillna("").astype(str).replace("None", "").str.strip()

    for num_col in ["Debe", "Haber"]:
        if num_col not in df_mes.columns:
            df_mes[num_col] = 0.0
        else:
            df_mes[num_col] = pd.to_numeric(df_mes[num_col], errors="coerce").fillna(0.0)

    # Integración con Google Drive para obtener enlaces
    try:
        import os

        from services.drive_doc import list_drive_files

        drive_files = list_drive_files(PADRES_DRIVE_FOLDER_ID) if PADRES_DRIVE_FOLDER_ID else []
        drive_map = {os.path.splitext(f["name"])[0]: f["id"] for f in drive_files}

        def get_drive_link(filename):
            if not filename or pd.isna(filename):
                return ""
            clean_name = str(filename).split(" —")[0].strip()
            clean_name = os.path.splitext(clean_name)[0]

            file_id = drive_map.get(clean_name)
            if file_id:
                return f"https://drive.google.com/file/d/{file_id}/view"
            return ""

        df_mes["Enlace archivo Drive"] = df_mes["Justificante"].apply(get_drive_link)
    except Exception as e:
        df_mes["Enlace archivo Drive"] = f"Error cargando Drive: {e}"

    # Formato seguro de fecha
    df_mes["Fecha"] = _format_fecha_export(df_mes["Fecha"])

    cols = [
        "Fecha",
        "Categoría",
        "Descripción",
        "Debe",
        "Haber",
        "Justificante",
        "Estado",
        "Enlace archivo Drive",
    ]

    return (
        df_mes[cols].sort_values("Fecha", ascending=False)
        if not df_mes.empty
        else pd.DataFrame(columns=cols)
    )


def generate_padres_excel(
    df_matched: pd.DataFrame,
    year: int | None = None,
    month: int | None = None,
    df_subset: pd.DataFrame | None = None,
) -> bytes:
    """
    Genera un Excel en memoria con las transacciones de la cuenta 131.
    """
    df_sorted = generate_padres_export_df(df_matched, year=year, month=month, df_subset=df_subset)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_sorted.to_excel(writer, sheet_name="Gastos", index=False)

        ws = writer.sheets["Gastos"]
        cols = list(df_sorted.columns)

        # Convertir la columna de enlaces en hipervínculos clickables
        if "Enlace archivo Drive" in cols:
            col_idx = cols.index("Enlace archivo Drive") + 1
            for row in range(2, ws.max_row + 1):
                cell = ws.cell(row=row, column=col_idx)
                if cell.value and str(cell.value).startswith("http"):
                    cell.hyperlink = str(cell.value)
                    cell.style = "Hyperlink"

        # Ajustar anchos de columna
        for col in ws.columns:
            max_len = max((len(str(cell.value)) for cell in col if cell.value), default=10)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 60)

    return output.getvalue()


def generate_padres_csv(
    df_matched: pd.DataFrame,
    year: int | None = None,
    month: int | None = None,
    df_subset: pd.DataFrame | None = None,
) -> bytes:
    """
    Genera un CSV en memoria (UTF-8 con BOM '\ufeff' para compatibilidad con Excel)
    con las transacciones de la cuenta 131.
    """
    df_sorted = generate_padres_export_df(df_matched, year=year, month=month, df_subset=df_subset)
    csv_string = df_sorted.to_csv(index=False, encoding="utf-8-sig")
    return csv_string.encode("utf-8-sig")

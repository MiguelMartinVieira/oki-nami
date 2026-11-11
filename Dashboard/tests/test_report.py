import os
import sys

import pandas as pd
import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from services.report import generate_padres_csv, generate_padres_excel, generate_padres_export_df


def test_generate_padres_export_df():
    df_matched = pd.DataFrame(
        [
            {
                "Fecha": "2026-08-01",
                "Categoría": "Supermercado",
                "Debe": 15.50,
                "Justificante": "20260801 Supermercado 15,50 €.jpg",
                "Estado": "Match Imagen",
            },
            {
                "Fecha": "2026-08-02",
                "Categoría": "Farmacia",
                "Debe": 8.20,
                "Justificante": "20260802 Farmacia 8,20 €.jpg",
                "Estado": "Match Imagen",
            },
        ]
    )

    export_df = generate_padres_export_df(df_matched)
    assert not export_df.empty
    assert list(export_df.columns) == [
        "Fecha",
        "Categoría",
        "Descripción",
        "Debe",
        "Haber",
        "Justificante",
        "Estado",
        "Enlace archivo Drive",
    ]
    assert len(export_df) == 2


def test_generate_padres_csv_and_excel_bytes():
    df_matched = pd.DataFrame(
        [
            {
                "Fecha": "2026-08-01",
                "Categoría": "Supermercado",
                "Debe": 25.00,
                "Justificante": "20260801 SPAR 25,00 €.jpg",
                "Estado": "Match Imagen",
            }
        ]
    )

    csv_bytes = generate_padres_csv(df_matched)
    excel_bytes = generate_padres_excel(df_matched)

    assert isinstance(csv_bytes, bytes)
    assert len(csv_bytes) > 0
    # UTF-8 BOM check: \xef\xbb\xbf
    assert csv_bytes.startswith(b"\xef\xbb\xbf")

    csv_text = csv_bytes.decode("utf-8-sig")
    assert "Supermercado" in csv_text
    assert "25.0" in csv_text

    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 0


def test_generate_padres_export_df_dates_preservation():
    df_matched = pd.DataFrame(
        [
            {
                "Fecha": "2026/08/06",
                "Categoría": "Telefonía",
                "Debe": 0,
                "Haber": 2.63,
                "Estado": "➖ N/A (Ingreso)",
            },
            {
                "Fecha": "2026/07/31",
                "Categoría": "Peluquería",
                "Debe": 16,
                "Haber": 0,
                "Estado": "Match Imagen",
            },
            {
                "Fecha": "2026/06/10",
                "Categoría": "Primaprix",
                "Debe": 2.35,
                "Haber": 0,
                "Estado": "Match Imagen",
            },
        ]
    )

    export_df = generate_padres_export_df(df_matched)
    fechas = export_df["Fecha"].tolist()
    assert "2026/08/06" in fechas
    assert "2026/07/31" in fechas
    assert "2026/06/10" in fechas
    assert "" not in fechas

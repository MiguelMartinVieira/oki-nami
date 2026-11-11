"""
test_csv_gsheets_pipeline.py — Suite de pruebas para sincronización GSheets, CSV y caché Parquet.

Cubre:
  1. Invalidación completa de cachés (memoria + disco parquet) al detectar cambios remotos.
  2. Fallback robusto a CSV cuando GSheets no está disponible.
  3. Parsing correcto de fechas (ISO, formateadas, números serie GSheets, años string).
  4. Sincronización del espejo CSV al añadir filas con append_to_diario.
"""

import os
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from constants import (
    BACKUP_DIR,
    CSV_DIARIO,
)
from data.gsheets import (
    _PARQUET_DENOM,
    _PARQUET_DIARIO,
    _PARQUET_HISTORICO,
    _PARQUET_SALDOS,
    _can_use_gsheets,
    append_to_diario,
    check_and_refresh_if_remote_changed,
    get_diario,
    invalidate_data_caches,
)


class _StubSessionState:
    def __init__(self, initial: str | None = None):
        self.sheet_modified_time = initial


# ──────────────────────────────────────────────
# 1. Invalidación de Parquets en Disco
# ──────────────────────────────────────────────


def test_invalidate_data_caches_purges_parquet_files(tmp_path):
    """Verifica que invalidate_data_caches borre físicamente los parquets de disco."""
    test_parquet = tmp_path / "_cache_diario.parquet"
    df_dummy = pd.DataFrame({"A": [1, 2]})
    df_dummy.to_parquet(test_parquet)

    assert test_parquet.exists()

    with patch("data.gsheets._PARQUET_DIARIO", str(test_parquet)):
        invalidate_data_caches()
        assert not test_parquet.exists()


@patch("data.gsheets.get_sheet_modified_time", return_value="2026-07-29T10:00:00Z")
def test_remote_edit_detection_purges_parquet_disk_cache(mock_mt, tmp_path):
    """Verifica que al detectar un cambio remoto en GSheets, se borre el parquet en disco."""
    test_parquet = tmp_path / "_cache_diario.parquet"
    pd.DataFrame({"col": [10, 20]}).to_parquet(test_parquet)

    assert test_parquet.exists()

    sst = _StubSessionState(initial="2026-07-29T09:00:00Z")

    with patch("data.gsheets._PARQUET_DIARIO", str(test_parquet)):
        changed = check_and_refresh_if_remote_changed(sst)
        assert changed is True
        assert sst.sheet_modified_time == "2026-07-29T10:00:00Z"
        assert not test_parquet.exists()


# ──────────────────────────────────────────────
# 2. Parsing de Fechas Robusto
# ──────────────────────────────────────────────


def test_date_parsing_robustness(tmp_path):
    """Prueba que parse_fecha maneje ISO, seriales GSheets y no desplace años string."""
    csv_file = tmp_path / "test_diario.csv"
    csv_content = """Fecha,Nº Cuenta,Cuenta,Categoría,Debe,Haber,Descripción
2026-03-20,410,Ingresos,Nómima,0,2500,Sueldo
46123,510,Gastos,Supermercado,50,0,Compra
2026/05/10,111,Cartera,Efectivo,10,0,Retiro
"""
    csv_file.write_text(csv_content, encoding="utf-8")

    with (
        patch("data.gsheets._can_use_gsheets", return_value=False),
        patch("data.gsheets.CSV_DIARIO", str(csv_file)),
        patch("data.gsheets._PARQUET_DIARIO", str(tmp_path / "dummy.parquet")),
    ):
        get_diario.clear()
        df = get_diario()

        assert not df.empty
        assert len(df) == 3

        fechas = df["Fecha"].tolist()
        # Fila 1: 2026-03-20 ISO
        assert fechas[0].year == 2026
        assert fechas[0].month == 3
        assert fechas[0].day == 20

        # Fila 2: 46123 (Serial GSheets ~ 2026-04-11)
        assert fechas[1].year == 2026
        assert fechas[1].month == 4

        # Fila 3: 2026/05/10
        assert fechas[2].year == 2026
        assert fechas[2].month == 5
        assert fechas[2].day == 10


# ──────────────────────────────────────────────
# 3. Actualización de Espejo CSV al Insertar
# ──────────────────────────────────────────────


@patch("data.gsheets._can_use_gsheets", return_value=True)
@patch("data.gsheets._get_gspread_client")
def test_append_to_diario_updates_csv_mirror(mock_client, mock_can_use, tmp_path):
    """Verifica que append_to_diario escriba en GSheets Y actualice el espejo CSV local."""
    mock_sheet = MagicMock()
    mock_sheet.col_values.return_value = ["Fecha", "2026-03-01"]
    fake_client = MagicMock()
    fake_client.open_by_url.return_value.worksheet.return_value = mock_sheet
    mock_client.return_value = fake_client

    csv_file = tmp_path / "mirror_diario.csv"
    csv_file.write_text(
        "Fecha,Nº Cuenta,Cuenta,Categoría,Debe,Haber,Descripción\n", encoding="utf-8"
    )

    new_rows = [
        ["2026-07-29", "410", "Ingresos", "Freelance", 0, 500, "Cobro proyecto"],
        ["2026-07-29", "111", "Cartera", "Efectivo", 500, 0, "Ingreso cuenta"],
    ]

    with (
        patch("data.gsheets.CSV_DIARIO", str(csv_file)),
        patch("data.gsheets._PARQUET_DIARIO", str(tmp_path / "dummy.parquet")),
    ):
        success = append_to_diario(new_rows)
        assert success is True

        content = csv_file.read_text(encoding="utf-8")
        assert "Cobro proyecto" in content
        assert "Ingreso cuenta" in content
        assert "410" in content

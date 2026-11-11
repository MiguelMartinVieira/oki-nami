"""
test_paths_and_routes.py — Tests exhaustivos para verificar rutas del proyecto,
rutas de carpetas, importaciones de módulos y generación de reportes (CSV/Excel).
"""

import os
import sys
from pathlib import Path

import pandas as pd
import pytest

# Añadir src/ al path de Python
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from config.paths import (
    BACKUP_DIR,
    BASE_DIR,
    FINANZAS_ROOT,
    PADRES_FOLDER,
    POSSIBLE_PADRES_FOLDERS,
    PROJECT_ROOT,
)
from services.report import (
    _format_fecha_export,
    _mes_anterior,
    generate_padres_csv,
    generate_padres_excel,
    generate_padres_export_df,
)


class TestProjectPaths:
    """Verifica que las rutas clave del proyecto existan y sean accesibles."""

    def test_base_and_project_root_exist(self):
        assert BASE_DIR.exists(), f"BASE_DIR no existe: {BASE_DIR}"
        assert PROJECT_ROOT.exists(), f"PROJECT_ROOT no existe: {PROJECT_ROOT}"

    def test_backup_dir_exists(self):
        assert BACKUP_DIR.exists(), f"BACKUP_DIR no existe: {BACKUP_DIR}"

    def test_padres_folder_resolution(self):
        # La carpeta es local y opcional (no existe en CI ni en un clon limpio):
        # se comprueba que la resolución elige un candidato válido.
        assert PADRES_FOLDER is not None
        assert len(POSSIBLE_PADRES_FOLDERS) > 0
        assert PADRES_FOLDER in POSSIBLE_PADRES_FOLDERS


class TestModuleImportsAndRoutes:
    """Verifica que los módulos principales y rutas de servicios se importen sin errores."""

    def test_import_services_report(self):
        import services.report as rep

        assert hasattr(rep, "generate_padres_export_df")
        assert hasattr(rep, "generate_padres_excel")
        assert hasattr(rep, "generate_padres_csv")

    def test_import_padres_tab(self):
        import tabs.padres.main as padres_main

        assert hasattr(padres_main, "render")

    def test_import_guitarra_tab(self):
        import tabs.guitarra.main as guitarra_main

        assert hasattr(guitarra_main, "render")

    def test_no_legacy_email_imports(self):
        """Asegura que ningún módulo intente importar el antiguo email_report."""
        with pytest.raises(ModuleNotFoundError):
            import services.email_report  # noqa: F401


class TestReportExportFormats:
    """Pruebas exhaustivas para la generación de CSV y Excel de Padres."""

    @pytest.fixture
    def sample_matched_df(self):
        return pd.DataFrame(
            [
                {
                    "Fecha": "2026/08/06",
                    "Categoría": "Telefonía",
                    "Descripción": "",
                    "Debe": 0.0,
                    "Haber": 2.63,
                    "Justificante": "",
                    "Estado": "➖ N/A (Ingreso)",
                },
                {
                    "Fecha": "2026/08/01",
                    "Categoría": "EMT Valencia",
                    "Descripción": "",
                    "Debe": 2.0,
                    "Haber": 0.0,
                    "Justificante": "EMT Valencia — Doc Sin Ticket",
                    "Estado": "Match Docs",
                },
                {
                    "Fecha": "2026/07/31",
                    "Categoría": "Peluquería",
                    "Descripción": "",
                    "Debe": 16.0,
                    "Haber": 0.0,
                    "Justificante": "20260731 Marco Aldany 16,00 €.jpg",
                    "Estado": "Match Imagen",
                },
                {
                    "Fecha": "2026/07/29",
                    "Categoría": "Iryo",
                    "Descripción": "Script",
                    "Debe": 19.0,
                    "Haber": 0.0,
                    "Justificante": "20260729 iryo 19,00 €.pdf",
                    "Estado": "Match PDF",
                },
            ]
        )

    def test_export_df_structure(self, sample_matched_df):
        export_df = generate_padres_export_df(sample_matched_df)
        expected_cols = [
            "Fecha",
            "Categoría",
            "Descripción",
            "Debe",
            "Haber",
            "Justificante",
            "Estado",
            "Enlace archivo Drive",
        ]
        assert list(export_df.columns) == expected_cols
        assert len(export_df) == 4

    def test_date_formatting_preservation(self, sample_matched_df):
        export_df = generate_padres_export_df(sample_matched_df)
        fechas = export_df["Fecha"].tolist()

        # Verificar que no hay celdas de fecha vacías o alteradas
        assert "2026/08/06" in fechas
        assert "2026/08/01" in fechas
        assert "2026/07/31" in fechas
        assert "2026/07/29" in fechas
        assert "" not in fechas
        assert None not in fechas

    def test_income_and_expense_preservation(self, sample_matched_df):
        export_df = generate_padres_export_df(sample_matched_df)
        categories = export_df["Categoría"].tolist()
        assert "Telefonía" in categories  # Debería incluir ingresos (Haber > 0)
        assert "Peluquería" in categories  # Debería incluir gastos (Debe > 0)

    def test_csv_generation(self, sample_matched_df):
        csv_bytes = generate_padres_csv(sample_matched_df)
        assert isinstance(csv_bytes, bytes)
        assert csv_bytes.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM

        text = csv_bytes.decode("utf-8-sig")
        assert "Telefonía" in text
        assert "Peluquería" in text
        assert "2026/08/06" in text
        assert "2026/07/31" in text

    def test_excel_generation(self, sample_matched_df):
        excel_bytes = generate_padres_excel(sample_matched_df)
        assert isinstance(excel_bytes, bytes)
        assert len(excel_bytes) > 0
        # Cabecera mágica de archivo zip / xlsx (PK\x03\x04)
        assert excel_bytes.startswith(b"PK\x03\x04")

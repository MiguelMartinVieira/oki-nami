# 🤖 AGENTS.md — Manual Arquitectónico y Guía Maestra para Agentes IA

> **Última actualización**: 2026-10-09 — **Auditoría de Arquitectura, Limpieza de Código Muerto y Orquestación**.

Este documento es la **fuente de verdad técnica definitiva** para cualquier agente de IA (Antigravity, Gemini, etc.) que navegue, audite o modifique la base de código de **Oki-Nami**.

---

## 1. Visión General del Sistema

**Oki-Nami** es una plataforma personal de finanzas, control contable de partida doble, analítica patrimonial, auditoría de cuentas compartidas y seguimiento de hábitos en macOS/Linux.

| Parámetro | Valor / Tecnología |
|---|---|
| **Arquitectura** | Monolito modular en Python con interfaz **Streamlit** (7 pestañas) |
| **Diseño / Estilo** | **Abyssal Monochrome / Dark Bento** (fuerza `base="dark"`, `#09090B`, glassmorphism CSS, tipografía Plus Jakarta Sans / Roboto Mono) |
| **Persistencia Primaria** | **Google Sheets API** (vía `gspread` + `google-auth`) con fallback local Parquet/CSV |
| **APIs Externas** | **Yahoo Finance** (`yfinance` + caché Parquet/CSV), **Google Drive API** (tickets Padres/Bokatas), **Google Docs API** ("Pagos Sin Ticket"), **INE API** (IPC España) |
| **Pestañas (7)** | 1. `Resumen` (Bento Grid), 2. `Libro Diario`, 3. `Inversiones`, 4. `Padres`, 5. `Bokatas`, 6. `Hábitos`, 7. `Guitarra` |
| **Entorno & Tooling** | `uv` (Fast Python Package Manager), Python 3.12+, macOS native app bundle |
| **Suite de Tests** | `pytest` modular en `Dashboard/tests/` (100% passing) |

---

## 2. Delimitación de Alcance para Agentes de IA

Cualquier agente de IA que opere en la base de código debe limitar sus acciones estrictamente al ámbito de su rol asignado:

### 2.1. Agente Orquestador y Arquitectura (`orchestrator-agent`)
* **Directorios bajo su alcance**: `pyproject.toml`, `.env.example`, `.gitignore`, `Dashboard/src/app.py`, `Dashboard/src/config/`.
* **Herramientas permitidas**: `view_file`, `replace_file_content`, `write_to_file`, `run_command`.
* **Comando obligatorio de verificación**:
  ```bash
  uv run pytest Dashboard/tests/test_paths.py Dashboard/tests/test_paths_and_routes.py
  ```

### 2.2. Agente UI / Frontend (`ui-agent`)
* **Directorios bajo su alcance**: `Dashboard/src/tabs/`, `Dashboard/src/components/`, `Dashboard/src/static/`, `Dashboard/src/theme.py`, `Dashboard/src/constants.py`.
* **Herramientas permitidas**: `view_file`, `replace_file_content`, `write_to_file`, `run_command`.
* **Comando obligatorio de verificación**:
  ```bash
  uv run pytest Dashboard/tests/test_aesthetic_contract.py Dashboard/tests/test_tab_resumen.py Dashboard/tests/test_guitarra_tab.py
  ```

### 2.3. Agente de Lógica de Negocio y Contabilidad (`services-agent`)
* **Directorios bajo su alcance**: `Dashboard/src/services/`.
* **Herramientas permitidas**: `view_file`, `replace_file_content`, `write_to_file`, `run_command`.
* **Comando obligatorio de verificación**:
  ```bash
  uv run pytest Dashboard/tests/test_accounting.py Dashboard/tests/test_auditor_logic.py Dashboard/tests/test_improvements.py Dashboard/tests/test_session_state.py
  ```

### 2.4. Agente de Datos e Integraciones (`data-agent`)
* **Directorios bajo su alcance**: `Dashboard/src/data/`.
* **Herramientas permitidas**: `view_file`, `replace_file_content`, `run_command`.
* **Comando obligatorio de verificación**:
  ```bash
  uv run pytest Dashboard/tests/test_sheets_sync.py Dashboard/tests/test_yahoo_service.py Dashboard/tests/test_csv_gsheets_pipeline.py
  ```

### 2.5. Agente QA y Blindaje de Pruebas (`qa-agent`)
* **Directorios bajo su alcance**: `Dashboard/tests/`.
* **Herramientas permitidas**: `view_file`, `replace_file_content`, `write_to_file`, `run_command`.
* **Comando obligatorio de verificación**:
  ```bash
  uv run pytest
  ```

---

## 3. Comandos Principales para Desarrollo y Testing

```bash
# 1. Ejecutar el Dashboard en local (Streamlit)
uv run python Dashboard/run_dashboard.py

# 2. Ejecutar la suite completa de pruebas
uv run pytest

# 3. Formateo y linting de código
uv run ruff check Dashboard/src Dashboard/tests
```

"""
tab_habitos.py — Tab "Hábitos y Ahorros".

Módulo gamificado para controlar hábitos diarios, micro-ahorros
activos y castigos por fallos con persistencia local en caché.
"""

import json
import uuid
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

# Ruta del archivo de caché y constants
from components.tab_markers import render_accent_notice
from config.paths import BASE_DIR
from constants import COLOR_HABITOS_BURDEOS

CACHE_FILE = BASE_DIR.parent / ".cache" / "habitos_ahorros.json"

# ──────────────────────────────────────────────
# Configuración de los Elementos
# ──────────────────────────────────────────────

CASTIGOS_SUAVES = [
    {"icon": "", "label": "Snack", "value": 2.00, "cuenta": "MULTA_SUAVE"},
    {"icon": "", "label": "Poca Agua", "value": 1.00, "cuenta": "MULTA_SUAVE"},
    {"icon": "", "label": "Romper 1º Impulso", "value": 1.00, "cuenta": "MULTA_SUAVE"},
    {"icon": "", "label": "No Journaling", "value": 1.00, "cuenta": "MULTA_SUAVE"},
    {"icon": "", "label": "Discord / Reddit", "value": 5.00, "cuenta": "MULTA_SUAVE"},
    {"icon": "", "label": "YouTube", "value": 3.00, "cuenta": "MULTA_SUAVE"},
    {"icon": "", "label": "No MacroFactor", "value": 2.00, "cuenta": "MULTA_SUAVE"},
    {"icon": "", "label": "Free2Move", "value": 4.00, "cuenta": "MULTA_SUAVE"},
    {"icon": "", "label": "Habitación Desordenada", "value": 1.50, "cuenta": "MULTA_SUAVE"},
    {"icon": "", "label": "Móvil al Despertar", "value": 1.50, "cuenta": "MULTA_SUAVE"},
    {"icon": "", "label": "Postura Encorvada", "value": 1.00, "cuenta": "MULTA_SUAVE"},
    {"icon": "", "label": "Suplementación", "value": 1.50, "cuenta": "MULTA_SUAVE"},
]

CASTIGOS_GRAVES = [
    {"icon": "", "label": "Faltar A Clase", "value": 15.00, "cuenta": "MULTA_GRAVE"},
    {"icon": "", "label": "Capricho", "value": 20.00, "cuenta": "MULTA_GRAVE"},
    {"icon": "", "label": "Uber/Cabify", "value": 8.50, "cuenta": "MULTA_GRAVE"},
    {"icon": "", "label": "Tabaco", "value": 7.00, "cuenta": "MULTA_GRAVE"},
    {"icon": "", "label": "Última Ronda", "value": 5.00, "cuenta": "MULTA_GRAVE"},
    {"icon": "", "label": "Pereza Entreno", "value": 5.00, "cuenta": "MULTA_GRAVE"},
    {"icon": "", "label": "Procastinar", "value": 5.00, "cuenta": "MULTA_GRAVE"},
    {"icon": "", "label": "Mañana Perdida", "value": 4.00, "cuenta": "MULTA_GRAVE"},
    {"icon": "", "label": "Acostarse Tarde", "value": 4.00, "cuenta": "MULTA_GRAVE"},
    {"icon": "", "label": "Doomscroll", "value": 4.00, "cuenta": "MULTA_GRAVE"},
    {"icon": "", "label": "Comida Basura", "value": 4.00, "cuenta": "MULTA_GRAVE"},
    {"icon": "", "label": "Monster", "value": 4.00, "cuenta": "MULTA_GRAVE"},
]

# Alias de retrocompatibilidad
AHORROS = CASTIGOS_SUAVES
CASTIGOS = CASTIGOS_GRAVES


# ──────────────────────────────────────────────
# Funciones de Persistencia (I/O)
# ──────────────────────────────────────────────


def load_data() -> dict:
    """Carga los datos de hábitos desde el archivo JSON de caché."""
    if not CACHE_FILE.exists():
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        default_data = {"current_month_total": 0.0, "current_events": [], "history_archive": []}
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(default_data, f, indent=2, ensure_ascii=False)
        return default_data
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error cargando caché de hábitos: {e}")
        return {"current_month_total": 0.0, "current_events": [], "history_archive": []}


def save_data(data: dict) -> None:
    """Recalcula el total del mes corriente y guarda en el archivo JSON."""
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        current_total = sum(event["value"] for event in data.get("current_events", []))
        data["current_month_total"] = round(current_total, 2)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        st.error(f"Error guardando caché de hábitos: {e}")


def add_event(label: str, value: float, event_type: str) -> None:
    """Añade un nuevo clic/evento a la bitácora actual."""
    data = load_data()
    new_event = {
        "id": f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{uuid.uuid4().hex[:6]}",  # ID único con microsegundos + sufijo UUID para evitar colisiones rápidos
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": event_type,  # "ahorro" o "castigo"
        "label": label,
        "value": value,
    }
    data["current_events"].append(new_event)
    save_data(data)


def delete_event(event_id: str) -> None:
    """Borra un evento específico (Undo/Deshacer)."""
    data = load_data()
    data["current_events"] = [e for e in data.get("current_events", []) if e.get("id") != event_id]
    save_data(data)


def archive_and_reset() -> None:
    """Archiva el mes actual en el histórico y limpia el bote a cero."""
    data = load_data()
    current_events = data.get("current_events", [])
    if not current_events:
        st.warning("No hay eventos en el mes actual para archivar.")
        return

    month_str = datetime.now().strftime("%Y-%m")
    total_suaves = sum(
        e["value"] for e in current_events if e.get("type") in ("castigo_suave", "ahorro", "suave")
    )
    total_graves = sum(
        e["value"] for e in current_events if e.get("type") in ("castigo_grave", "castigo", "grave")
    )
    total_mes = sum(e["value"] for e in current_events)

    archive_entry = {
        "month": month_str,
        "total_suaves": round(total_suaves, 2),
        "total_graves": round(total_graves, 2),
        "total_ahorros": round(total_suaves, 2),
        "total_castigos": round(total_graves, 2),
        "total_mes": round(total_mes, 2),
        "events": current_events,
    }

    data["history_archive"].append(archive_entry)
    data["current_events"] = []
    data["current_month_total"] = 0.0
    save_data(data)


# ──────────────────────────────────────────────
# Renderización del Tab
# ──────────────────────────────────────────────


def render(df_diario: pd.DataFrame | None = None) -> None:
    """Renderiza el tab completo de Hábitos y Ahorros.

    Args:
        df_diario: Libro Diario (necesario para el sub-tab "Retos" — se usa
            para calcular baselines y ahorros reales). Si es None, los Retos
            se deshabilitan con un caption explicativo.
    """

    # ── Estilos (Botones cuadrados + 2 acentos: blanco Ahorros · burdeos Castigos) ──
    # Estrategia: aplicamos los estilos GLOBALMENTE a `button[kind="primary"]`
    # (que es lo que sí funcionaba históricamente). Para evitar la contaminación
    # del botón "Enviar Ahora" de Padres, ese tab lleva su propio override de
    st.markdown(
        """
    <div id="habitos-tab-marker" style="display:none;"></div>
    <style>
        /* === Base común (forma, tamaño, tipografía) === */
        div.element-container:has(#habitos-tab-marker) ~ div button[kind="primary"] {
            width: 100% !important;
            aspect-ratio: 1 / 1 !important;
            max-width: 150px !important;
            margin: 0 auto !important;
            border-radius: 14px !important;
            padding: 10px !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-weight: 600 !important;
            font-size: 0.82rem !important;
            line-height: 1.25 !important;
            transition: all 0.2s ease !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            text-align: center !important;
            background-color: #18181B !important;
            color: #E4E4E7 !important;
            white-space: pre-wrap !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.35) !important;
        }

        button[kind="primary"] div,
        button[kind="primary"] p {
            white-space: pre-wrap !important;
            margin: 0 !important;
            display: block !important;
            text-align: center !important;
        }

        /* === Acento BLANCO — Castigos Suaves (vía wrapper class st-key-btn_suave_* / st-key-btn_ahorro_*) === */
        [class*="st-key-btn_suave_"] button[kind="primary"],
        [class*="st-key-btn_ahorro_"] button[kind="primary"] {
            border: 1px solid rgba(255, 255, 255, 0.18) !important;
            border-top: 2px solid rgba(255, 255, 255, 0.55) !important;
        }
        [class*="st-key-btn_suave_"] button[kind="primary"]:hover,
        [class*="st-key-btn_suave_"] button[kind="primary"]:active,
        [class*="st-key-btn_suave_"] button[kind="primary"]:focus,
        [class*="st-key-btn_ahorro_"] button[kind="primary"]:hover,
        [class*="st-key-btn_ahorro_"] button[kind="primary"]:active,
        [class*="st-key-btn_ahorro_"] button[kind="primary"]:focus {
            color: #FFFFFF !important;
            border-color: rgba(255, 255, 255, 0.45) !important;
            border-top-color: #FFFFFF !important;
            background-color: #1F1F23 !important;
            transform: scale(0.96) !important;
            box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.22), 0 2px 10px rgba(0,0,0,0.4) !important;
        }


        /* === Acento BURDEOS/MAGENTA — Castigos Graves (vía wrapper class st-key-btn_grave_* / st-key-btn_castigo_*) === */
        [class*="st-key-btn_grave_"] button[kind="primary"],
        [class*="st-key-btn_castigo_"] button[kind="primary"] {
            border: 1px solid rgba(179, 0, 89, 0.25) !important;
            border-top: 2px solid rgba(179, 0, 89, 0.65) !important;
            color: #B30059 !important;
        }
        [class*="st-key-btn_grave_"] button[kind="primary"] p,
        [class*="st-key-btn_castigo_"] button[kind="primary"] p {
            color: #B30059 !important;
        }
        [class*="st-key-btn_grave_"] button[kind="primary"]:hover,
        [class*="st-key-btn_grave_"] button[kind="primary"]:active,
        [class*="st-key-btn_grave_"] button[kind="primary"]:focus,
        [class*="st-key-btn_castigo_"] button[kind="primary"]:hover,
        [class*="st-key-btn_castigo_"] button[kind="primary"]:active,
        [class*="st-key-btn_castigo_"] button[kind="primary"]:focus {
            color: #B30059 !important;
            border-color: rgba(179, 0, 89, 0.55) !important;
            border-top-color: #B30059 !important;
            background-color: #1F1F23 !important;
            transform: scale(0.96) !important;
            box-shadow: 0 0 0 1px rgba(179, 0, 89, 0.30), 0 2px 10px rgba(0,0,0,0.4) !important;
        }

        /* ========================================================================== */
        /* LOGOS PERSONALIZADOS POR BOTÓN (Ajuste por índice de lista) */
        /* ========================================================================== */

        /* ── CASTIGOS SUAVES (Índices 00 a 08) ── */

        /* Snack (Suave 00) */
        [class*="st-key-btn_suave_00"] button[kind="primary"] p,
        [class*="st-key-btn_ahorro_00"] button[kind="primary"] p {
            background-image: url("app/static/logo_snack_cropped.png?v=500") !important;
            background-size: 57px auto !important;
            background-repeat: no-repeat !important;
            background-position: center top 5px !important;
            padding-top: 82px !important;
            width: 100% !important;
            min-width: 100px !important;
            display: block !important;
        }

        /* Poca Agua (Suave 01) */
        [class*="st-key-btn_suave_01"] button[kind="primary"] p,
        [class*="st-key-btn_ahorro_01"] button[kind="primary"] p {
            background-image: url("app/static/logo_poca_agua_cropped.png?v=500") !important;
            background-size: 50px auto !important;
            background-repeat: no-repeat !important;
            background-position: center top 5px !important;
            padding-top: 82px !important;
            width: 100% !important;
            min-width: 100px !important;
            display: block !important;
        }

        /* Romper 1º Impulso (Suave 02) */
        [class*="st-key-btn_suave_02"] button[kind="primary"] p,
        [class*="st-key-btn_ahorro_02"] button[kind="primary"] p {
            background-image: url("app/static/logo_romper_impulso_cropped.png?v=500") !important;
            background-size: 57px auto !important;
            background-repeat: no-repeat !important;
            background-position: center top 5px !important;
            padding-top: 82px !important;
            width: 100% !important;
            min-width: 100px !important;
            display: block !important;
        }

        /* No Journaling (Suave 03) */
        [class*="st-key-btn_suave_03"] button[kind="primary"] p,
        [class*="st-key-btn_ahorro_03"] button[kind="primary"] p {
            background-image: url("app/static/logo_no_journaling_cropped.png?v=500") !important;
            background-size: 65px auto !important;
            background-repeat: no-repeat !important;
            background-position: center top 5px !important;
            padding-top: 82px !important;
            width: 100% !important;
            min-width: 100px !important;
            display: block !important;
        }

        /* Discord / Reddit (Suave 04) */
        [class*="st-key-btn_suave_04"] button[kind="primary"] p,
        [class*="st-key-btn_ahorro_04"] button[kind="primary"] p {
            background-image: url("app/static/logo_discord_cropped.png?v=500") !important;
            background-size: 85px auto !important;
            background-repeat: no-repeat !important;
            background-position: center top 5px !important;
            padding-top: 82px !important;
            width: 100% !important;
            min-width: 100px !important;
            display: block !important;
        }

        /* YouTube (Suave 05) */
        [class*="st-key-btn_suave_05"] button[kind="primary"] p,
        [class*="st-key-btn_ahorro_05"] button[kind="primary"] p {
            background-image: url("app/static/logo_youtube_cropped.png?v=500") !important;
            background-size: 90px auto !important;
            background-repeat: no-repeat !important;
            background-position: center top 5px !important;
            padding-top: 82px !important;
            width: 100% !important;
            min-width: 100px !important;
            display: block !important;
        }

        /* No MacroFactor (Suave 06) */
        [class*="st-key-btn_suave_06"] button[kind="primary"] p,
        [class*="st-key-btn_ahorro_06"] button[kind="primary"] p {
            background-image: url("app/static/logo_no_macrofactor_cropped.png?v=500") !important;
            background-size: 70px auto !important;
            background-repeat: no-repeat !important;
            background-position: center top 5px !important;
            padding-top: 82px !important;
            width: 100% !important;
            min-width: 100px !important;
            display: block !important;
        }

        /* Free2Move (Suave 07) */
        [class*="st-key-btn_suave_07"] button[kind="primary"] p,
        [class*="st-key-btn_ahorro_07"] button[kind="primary"] p {
            background-image: url("app/static/logo_free2move_cropped.png?v=500") !important;
            background-size: 57px auto !important;
            background-repeat: no-repeat !important;
            background-position: center top 5px !important;
            padding-top: 82px !important;
            width: 100% !important;
            min-width: 100px !important;
            display: block !important;
        }

        /* Habitación Desordenada (Suave 08) */
        [class*="st-key-btn_suave_08"] button[kind="primary"] p,
        [class*="st-key-btn_ahorro_08"] button[kind="primary"] p {
            background-image: url("app/static/logo_habitacion_desordenada_cropped.png?v=900") !important;
            background-size: 68px auto !important;
            background-repeat: no-repeat !important;
            background-position: center top 12px !important;
            padding-top: 82px !important;
            width: 100% !important;
            min-width: 100px !important;
            display: block !important;
        }

        /* Móvil al Despertar (Suave 09) */
        [class*="st-key-btn_suave_09"] button[kind="primary"] p,
        [class*="st-key-btn_ahorro_09"] button[kind="primary"] p {
            background-image: url("app/static/logo_movil_despertar_cropped.png?v=1200") !important;
            background-size: auto 48px !important;
            background-repeat: no-repeat !important;
            background-position: center top 10px !important;
            padding-top: 82px !important;
            width: 100% !important;
            min-width: 100px !important;
            display: block !important;
        }

        /* Postura Encorvada (Suave 10) */
        [class*="st-key-btn_suave_10"] button[kind="primary"] p,
        [class*="st-key-btn_ahorro_10"] button[kind="primary"] p {
            background-image: url("app/static/logo_postura_encorvada_cropped.png?v=1100") !important;
            background-size: 58px auto !important;
            background-repeat: no-repeat !important;
            background-position: center top 10px !important;
            padding-top: 82px !important;
            width: 100% !important;
            min-width: 100px !important;
            display: block !important;
        }

        /* Suplementación (Suave 11) */
        [class*="st-key-btn_suave_11"] button[kind="primary"] p,
        [class*="st-key-btn_ahorro_11"] button[kind="primary"] p {
            background-image: url("app/static/logo_suplementacion_cropped.png?v=1600") !important;
            background-size: 55px auto !important;
            background-repeat: no-repeat !important;
            background-position: center top 10px !important;
            padding-top: 82px !important;
            width: 100% !important;
            min-width: 100px !important;
            display: block !important;
        }


        /* ── CASTIGOS GRAVES (Índices 00 a 11) ── */

        /* Faltar A Clase (Grave 00) */
        [class*="st-key-btn_grave_00"] button[kind="primary"] p,
        [class*="st-key-btn_castigo_00"] button[kind="primary"] p {
            background-image: url("app/static/logo_clase_cropped.png?v=500") !important;
            background-size: 62px auto !important;
            background-repeat: no-repeat !important;
            background-position: center top 5px !important;
            padding-top: 82px !important;
            width: 100% !important;
            min-width: 100px !important;
            display: block !important;
        }

        /* Capricho (Grave 01) */
        [class*="st-key-btn_grave_01"] button[kind="primary"] p,
        [class*="st-key-btn_castigo_01"] button[kind="primary"] p {
            background-image: url("app/static/logo_capricho_cropped.png?v=500") !important;
            background-size: 55px auto !important;
            background-repeat: no-repeat !important;
            background-position: center top 5px !important;
            padding-top: 82px !important;
            width: 100% !important;
            min-width: 100px !important;
            display: block !important;
        }

        /* Uber/Cabify (Grave 02) */
        [class*="st-key-btn_grave_02"] button[kind="primary"] p,
        [class*="st-key-btn_castigo_02"] button[kind="primary"] p {
            background-image: url("app/static/logo_uber_cabify_cropped.png?v=500") !important;
            background-size: 57px auto !important;
            background-repeat: no-repeat !important;
            background-position: center top 5px !important;
            padding-top: 82px !important;
            width: 100% !important;
            min-width: 100px !important;
            display: block !important;
        }

        /* Tabaco (Grave 03) */
        [class*="st-key-btn_grave_03"] button[kind="primary"] p,
        [class*="st-key-btn_castigo_03"] button[kind="primary"] p {
            background-image: url("app/static/logo_tabaco_cropped.png?v=500") !important;
            background-size: 57px auto !important;
            background-repeat: no-repeat !important;
            background-position: center top 5px !important;
            padding-top: 82px !important;
            width: 100% !important;
            min-width: 100px !important;
            display: block !important;
        }

        /* Última Ronda (Grave 04) */
        [class*="st-key-btn_grave_04"] button[kind="primary"] p,
        [class*="st-key-btn_castigo_04"] button[kind="primary"] p {
            background-image: url("app/static/logo_ultima_ronda_cropped.png?v=500") !important;
            background-size: 57px auto !important;
            background-repeat: no-repeat !important;
            background-position: center top 5px !important;
            padding-top: 82px !important;
            width: 100% !important;
            min-width: 100px !important;
            display: block !important;
        }

        /* Pereza Entreno (Grave 05) */
        [class*="st-key-btn_grave_05"] button[kind="primary"] p,
        [class*="st-key-btn_castigo_05"] button[kind="primary"] p {
            background-image: url("app/static/logo_pereza_entreno_cropped.png?v=500") !important;
            background-size: 70px auto !important;
            background-repeat: no-repeat !important;
            background-position: center top 5px !important;
            padding-top: 82px !important;
            width: 100% !important;
            min-width: 100px !important;
            display: block !important;
        }

        /* Procastinar (Grave 06) */
        [class*="st-key-btn_grave_06"] button[kind="primary"] p,
        [class*="st-key-btn_castigo_06"] button[kind="primary"] p {
            background-image: url("app/static/logo_procastinar_cropped.png?v=1300") !important;
            background-size: auto 48px !important;
            background-repeat: no-repeat !important;
            background-position: center top 10px !important;
            padding-top: 82px !important;
            width: 100% !important;
            min-width: 100px !important;
            display: block !important;
        }

        /* Mañana Perdida (Grave 07) */
        [class*="st-key-btn_grave_07"] button[kind="primary"] p,
        [class*="st-key-btn_castigo_07"] button[kind="primary"] p {
            background-image: url("app/static/logo_manana_perdida_cropped.png?v=500") !important;
            background-size: 55px auto !important;
            background-repeat: no-repeat !important;
            background-position: center top 5px !important;
            padding-top: 82px !important;
            width: 100% !important;
            min-width: 100px !important;
            display: block !important;
        }

        /* Acostarse Tarde (Grave 08) */
        [class*="st-key-btn_grave_08"] button[kind="primary"] p,
        [class*="st-key-btn_castigo_08"] button[kind="primary"] p {
            background-image: url("app/static/logo_acostarse_tarde_cropped.png?v=500") !important;
            background-size: 50px auto !important;
            background-repeat: no-repeat !important;
            background-position: center top 5px !important;
            padding-top: 82px !important;
            width: 100% !important;
            min-width: 100px !important;
            display: block !important;
        }

        /* Doomscroll (Grave 09) */
        [class*="st-key-btn_grave_09"] button[kind="primary"] p,
        [class*="st-key-btn_castigo_09"] button[kind="primary"] p {
            background-image: url("app/static/logo_doomscroll_cropped.png?v=500") !important;
            background-size: 65px auto !important;
            background-repeat: no-repeat !important;
            background-position: center top 5px !important;
            padding-top: 82px !important;
            width: 100% !important;
            min-width: 100px !important;
            display: block !important;
        }

        /* Comida Basura (Grave 10) */
        [class*="st-key-btn_grave_10"] button[kind="primary"] p,
        [class*="st-key-btn_castigo_10"] button[kind="primary"] p {
            background-image: url("app/static/logo_comida_basura_cropped.png?v=400") !important;
            background-size: 70px auto !important;
            background-repeat: no-repeat !important;
            background-position: center top 5px !important;
            padding-top: 82px !important;
            width: 100% !important;
            min-width: 100px !important;
            display: block !important;
        }

        /* Monster (Grave 11) */
        [class*="st-key-btn_grave_11"] button[kind="primary"] p,
        [class*="st-key-btn_castigo_11"] button[kind="primary"] p {
            background-image: url("app/static/logo_monster_cropped.png?v=2026") !important;
            background-size: auto 65px !important;
            background-repeat: no-repeat !important;
            background-position: center top 8px !important;
            padding-top: 82px !important;
            width: 100% !important;
            min-width: 100px !important;
            display: block !important;
        }

        /* Logo personalizado para Romper 1º Impulso (índice 02) */
        [class*="st-key-btn_ahorro_02"] button[kind="primary"] p,
        [class*="st-key-btn_suave_02"] button[kind="primary"] p {
            background-image: url("app/static/logo_romper_impulso_cropped.png?v=99") !important;
            background-size: 57px auto !important;
            background-repeat: no-repeat !important;
            background-position: center top 5px !important;
            padding-top: 82px !important;
            width: 100% !important;
            min-width: 100px !important;
            display: block !important;
        }
        [class*="st-key-btn_ahorro_02"] button[kind="primary"] p::first-line,
        [class*="st-key-btn_suave_02"] button[kind="primary"] p::first-line {
            font-size: 0.82rem !important;
            line-height: 1.25 !important;
        }


        /* Pills (Bitácora) — neutros, acento sólo en castigo */
        .burdeos-pill {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
            font-family: 'Plus Jakarta Sans', sans-serif;
            background: rgba(255, 255, 255, 0.04);
            color: #E4E4E7;
            border: 1px solid rgba(255, 255, 255, 0.10);
            letter-spacing: 0.02em;
        }
        .burdeos-pill.muted {
            background: rgba(179, 0, 89, 0.10);
            color: #B30059;
            border-color: rgba(179, 0, 89, 0.35);
        }        /* ── Adaptación de logos para Monitor Vertical (Portrait) ── */
        @media (orientation: portrait) {
            /* 1. Emojis / Logos primer línea text size en formato 8 columnas */
            [class*="st-key-btn_ahorro_"] button[kind="primary"] p::first-line,
            [class*="st-key-btn_castigo_"] button[kind="primary"] p::first-line {
                font-size: 0.62rem !important;
                line-height: 1.1 !important;
            }

            /* 2. Logos personalizados miniatura para formato 8 columnas */
            [class*="st-key-btn_ahorro_"] button[kind="primary"] p,
            [class*="st-key-btn_castigo_"] button[kind="primary"] p {
                background-size: 30px auto !important;
                padding-top: 34px !important;
                min-width: 0 !important;
                background-position: center top 2px !important;
            }

            /* 3. Optimización del botón: letra pequeña, padding mínimo, cuadrados puros */
            div.element-container:has(#habitos-tab-marker) ~ div button[kind="primary"] {
                font-size: 0.62rem !important;
                padding: 4px 2px !important;
                border-radius: 8px !important;
                max-width: none !important;
            }

            div.element-container:has(#habitos-tab-marker) ~ div button[kind="primary"] p {
                word-wrap: break-word !important;
                white-space: pre-wrap !important;
                line-height: 1.1 !important;
                font-size: 0.62rem !important;
            }
        }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # ── Cargar datos actuales ──
    data = load_data()
    current_events = data.get("current_events", [])
    total_suaves = sum(
        e["value"] for e in current_events if e.get("type") in ("castigo_suave", "ahorro", "suave")
    )
    total_graves = sum(
        e["value"] for e in current_events if e.get("type") in ("castigo_grave", "castigo", "grave")
    )
    total_bote = sum(e["value"] for e in current_events)

    try:
        from services.demo_data import is_cipher_mode, scramble_numbers

        if is_cipher_mode():
            str_bote = scramble_numbers(f"{total_bote:,.2f}")
            str_suaves = scramble_numbers(f"{total_suaves:,.2f}")
            str_graves = scramble_numbers(f"{total_graves:,.2f}")
        else:
            str_bote = f"{total_bote:,.2f}"
            str_suaves = f"{total_suaves:,.2f}"
            str_graves = f"{total_graves:,.2f}"
    except Exception:
        str_bote = f"{total_bote:,.2f}"
        str_suaves = f"{total_suaves:,.2f}"
        str_graves = f"{total_graves:,.2f}"

    # ── Tarjeta Superior (Bote Mensual · Impuestos a la Disciplina) ──
    bote_html = f"""
    <div style="background: linear-gradient(145deg, #18181B 0%, #09090B 100%);
                border: 1px solid rgba(255,255,255,0.06);
                border-top: 2px solid rgba(179, 0, 89, 0.7);
                padding: 24px 28px; border-radius: 16px;
                box-shadow: 0 4px 18px rgba(0,0,0,0.4);
                margin-bottom: 24px;
                font-family: 'Plus Jakarta Sans', sans-serif;">
            <div style="font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.12em;
                                    color: #A1A1AA; font-weight: 600;">
                    Bote de Impuestos a la Disciplina
            </div>
            <div style="font-size: 3rem; font-weight: 600; color: #E4E4E7; letter-spacing: -0.05em;
                                    margin: 6px 0 14px; font-family: 'Roboto Mono', monospace; line-height: 1.05;">
                    {str_bote} €
            </div>
            <hr style="border: none; border-top: 1px solid rgba(255,255,255,0.06); margin: 12px 0;">
            <div style="display: flex; gap: 36px; font-size: 0.88rem; flex-wrap: wrap;">
                    <div>
                            <span style="color: #A1A1AA; font-weight: 500;">Castigos Suaves:</span>
                            <span style="color: #FFFFFF; font-weight: 600; font-family: 'Roboto Mono', monospace;">
                                    {str_suaves} €
                            </span>
                    </div>
                    <div>
                            <span style="color: #A1A1AA; font-weight: 500;">Castigos Graves:</span>
                            <span style="color: #B30059; font-weight: 600; font-family: 'Roboto Mono', monospace;">
                                    {str_graves} €
                            </span>
                    </div>
            </div>
    </div>
    """

    st.markdown(bote_html, unsafe_allow_html=True)

    # ── Callback Factories (Evitan problemas de estado en Streamlit) ──
    def make_click_callback(label, value, event_type):
        return lambda: add_event(label, value, event_type)

    def make_delete_callback(event_id):
        return lambda: delete_event(event_id)

    # ── Renderizado de Botones (Filas de 8 combinando Suaves y Graves) ──
    all_items = []
    for i, item in enumerate(CASTIGOS_SUAVES):
        all_items.append(
            {"index_type": "suave", "real_index": i, "item": item, "event_type": "castigo_suave"}
        )
    for i, item in enumerate(CASTIGOS_GRAVES):
        all_items.append(
            {"index_type": "grave", "real_index": i, "item": item, "event_type": "castigo_grave"}
        )

    for row in range(0, len(all_items), 8):
        cols = st.columns(8)
        chunk = all_items[row : row + 8]
        for i, info in enumerate(chunk):
            real_i = info["real_index"]
            index_type = info["index_type"]
            event_type = info["event_type"]
            item = info["item"]
            with cols[i]:
                btn_label = item["label"]
                st.button(
                    btn_label,
                    key=f"btn_{index_type}_{real_i:02d}",
                    on_click=make_click_callback(item["label"], item["value"], event_type),
                    type="primary",
                    use_container_width=True,
                )

    st.markdown(
        "<br><hr style='border-color: rgba(255,255,255,0.06);'><br>",
        unsafe_allow_html=True,
    )

    # ── Tabs de Gestión e Histórico ──
    tab_bitacora, tab_stats = st.tabs(["Bitácora del Mes", "Estadísticas y Análisis"])

    with tab_bitacora:
        if not current_events:
            st.markdown(
                render_accent_notice(
                    "Aún no has registrado ningún hábito o ahorro en este periodo. "
                    "¡Toma tu primera decisión!",
                    COLOR_HABITOS_BURDEOS,
                    icon="🎯",
                ),
                unsafe_allow_html=True,
            )
        else:
            # Mostrar Timeline en sentido inverso (recientes arriba)
            for e in reversed(current_events):
                try:
                    dt = datetime.strptime(e["timestamp"], "%Y-%m-%d %H:%M:%S")
                    time_str = dt.strftime("%d %b, %H:%M")
                except Exception:
                    time_str = e["timestamp"]

                c_time, c_type, c_desc, c_val, c_act = st.columns([1.2, 1.2, 3, 1, 0.6])

                with c_time:
                    st.markdown(
                        f"<div style='color: #71717A; font-size: 0.88rem; "
                        f'padding-top: 6px; font-family: "Roboto Mono", monospace;\'>'
                        f"{time_str}</div>",
                        unsafe_allow_html=True,
                    )

                with c_type:
                    is_suave = e.get("type") in ("castigo_suave", "ahorro", "suave")
                    pill_class = "burdeos-pill" if is_suave else "burdeos-pill muted"
                    pill_text = "Suave" if is_suave else "Grave"
                    st.markdown(
                        f"<div style='padding-top: 4px;'>"
                        f"<span class='{pill_class}'>{pill_text}</span></div>",
                        unsafe_allow_html=True,
                    )

                with c_desc:
                    st.markdown(
                        f"<div style='font-weight: 500; font-size: 0.95rem; "
                        f"padding-top: 4px; color: #E4E4E7;'>{e['label']}</div>",
                        unsafe_allow_html=True,
                    )

                with c_val:
                    is_suave = e.get("type") in ("castigo_suave", "ahorro", "suave")
                    color = "#E4E4E7" if is_suave else "#B30059"
                    st.markdown(
                        f"<div style='color: {color}; font-weight: 600; "
                        f"font-size: 0.95rem; padding-top: 4px; "
                        f'font-family: "Roboto Mono", monospace;\'>'
                        f"{e['value']:.2f} €</div>",
                        unsafe_allow_html=True,
                    )

                with c_act:
                    st.button(
                        "×",
                        key=f"del_{e['id']}",
                        on_click=make_delete_callback(e["id"]),
                        help="Deshacer este registro por error",
                        width="stretch",
                    )

                st.markdown(
                    "<hr style='margin: 8px 0; border: none; "
                    "border-top: 1px dashed rgba(255,255,255,0.06);'>",
                    unsafe_allow_html=True,
                )

        # ── Cierre de Bote y Reset ──
        st.markdown("<br><br>", unsafe_allow_html=True)

        c_chk, c_btn = st.columns([2, 1])
        with c_chk:
            confirm = st.checkbox(
                "Confirmo que he modificado mi plan de inversión en Trade Republic e invertido esta cantidad.",
                key="confirm_reset_habits",
            )
        with c_btn:
            if st.button(
                "Archivar y Reiniciar Bote", disabled=not confirm, key="btn_reset_habits_action"
            ):
                archive_and_reset()
                st.success("¡Bote reiniciado con éxito! Comenzando un nuevo mes.")
                st.balloons()
                st.rerun()

    with tab_stats:
        history_archive = data.get("history_archive", [])

        # Unificar histórico + mes actual
        all_events = list(current_events)
        for arch in history_archive:
            all_events.extend(arch.get("events", []))

        if not all_events:
            st.markdown(
                render_accent_notice(
                    "Aún no hay suficientes datos registrados para generar estadísticas. "
                    "¡Sigue pulsando botones!",
                    COLOR_HABITOS_BURDEOS,
                    icon="📊",
                ),
                unsafe_allow_html=True,
            )
        else:
            df_events = pd.DataFrame(all_events)
            if "type" not in df_events.columns:
                df_events["type"] = ""
            if "label" not in df_events.columns:
                df_events["label"] = ""

            df_suaves = df_events[df_events["type"].isin(["castigo_suave", "ahorro", "suave"])]
            df_graves = df_events[df_events["type"].isin(["castigo_grave", "castigo", "grave"])]

            # Visualización Gráfica
            c_g1, c_g2 = st.columns(2)

            with c_g1:
                if not df_suaves.empty:
                    counts_a = df_suaves.groupby("label").size().reset_index(name="Frecuencia")
                    counts_a = counts_a.sort_values(by="Frecuencia", ascending=True)
                    fig_a = px.bar(
                        counts_a,
                        x="Frecuencia",
                        y="label",
                        orientation="h",
                        title="Castigos Suaves (Frecuencia)",
                        color_discrete_sequence=["#A1A1AA"],
                        text="Frecuencia",
                    )
                    fig_a.update_layout(
                        margin=dict(l=10, r=20, t=50, b=10),
                        height=280,
                        font_family="'Plus Jakarta Sans', sans-serif",
                        font_color="#E4E4E7",
                        title_font_color="#FFFFFF",
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        xaxis=dict(
                            showgrid=True, gridcolor="rgba(255,255,255,0.06)", color="#A1A1AA"
                        ),
                        yaxis=dict(title="", color="#E4E4E7"),
                    )
                    fig_a.update_traces(
                        textposition="outside",
                        cliponaxis=False,
                        textfont=dict(color="#FFFFFF"),
                    )
                    st.plotly_chart(fig_a, width="stretch", key="chart_victorias")
                else:
                    st.info("No hay datos de castigos suaves registrados.")

            with c_g2:
                if not df_graves.empty:
                    counts_c = df_graves.groupby("label").size().reset_index(name="Frecuencia")
                    counts_c = counts_c.sort_values(by="Frecuencia", ascending=True)
                    fig_c = px.bar(
                        counts_c,
                        x="Frecuencia",
                        y="label",
                        orientation="h",
                        title="Castigos Graves (Frecuencia)",
                        color_discrete_sequence=["#B30059"],
                        text="Frecuencia",
                    )
                    fig_c.update_layout(
                        margin=dict(l=10, r=20, t=50, b=10),
                        height=280,
                        font_family="'Plus Jakarta Sans', sans-serif",
                        font_color="#E4E4E7",
                        title_font_color="#FFFFFF",
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        xaxis=dict(
                            showgrid=True, gridcolor="rgba(255,255,255,0.06)", color="#A1A1AA"
                        ),
                        yaxis=dict(title="", color="#E4E4E7"),
                    )
                    fig_c.update_traces(
                        textposition="outside",
                        cliponaxis=False,
                        textfont=dict(color="#FFFFFF"),
                    )
                    st.plotly_chart(fig_c, width="stretch", key="chart_fallos")
                else:
                    st.info("No hay datos de castigos graves registrados.")

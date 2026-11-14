# -*- coding: utf-8 -*-
"""
PREDWEEM Lolium — Olavarría.

La página muestra la alerta de grandes flujos de Lolium del paquete ``lolium-comun`` (probabilidad de gran flujo en
los próximos 7 días, qué hacer esta semana, ventana del graminicida de barbecho, residual a la siembra y flujos tardíos)
con el clima diario del repositorio (``meteo_daily.csv``).

El motor PREDWEEM anterior (red neuronal y balance hídrico, ``app_emergenciacombinado_core.py`` y sus modelos) ya no se
ejecuta: su inicio estimado de la emergencia erró 12–14 días en promedio y no mejoraba la alerta. Sus archivos quedan
en el repositorio solo como referencia.
"""
import importlib
from pathlib import Path

import pandas as pd
import streamlit as st

# Control de acceso (ingreso con Google y usuarios aprobados). Inactivo hasta configurar los secretos [acceso] y [auth].
from acceso_predweem import mostrar_sesion, requerir_acceso
from lolium_comun import pagina

BASE = Path(__file__).resolve().parent

requerir_acceso("Olavarría")
pagina.encabezado("🌾 PREDWEEM LOLIUM — OLAVARRÍA (BA) lat=-36.8799 lon=-60.2160", "PREDWEEM OLAVARRÍA")
parametros = pagina.barra_lateral(BASE, "Olavarría")
meteo = pagina.cargar_meteo(BASE, None)

NOTA_OLAVARRIA = (
    "**Validación en Olavarría.** El modelo se probó, sin reajustarlo, con los conteos de "
    "Olavarría 2026 (`data/campanias/2026/`; 7 fechas entre el 20/03 y el 20/06, cada 12 a 20 días; 6 intervalos, 4 con "
    "emergencia ≥ 5 % de la campaña por semana) y el clima de esta app. Emitida al comienzo de cada intervalo, la alerta "
    "ordenó perfectamente los intervalos con y sin gran flujo (AUC 1,00): con la fecha de primeras plántulas, los 4 quedaron en "
    "*Alerta* y ninguno de los 2 sin gran flujo. No hay gemelo digital de Olavarría con el que comparar.\n\n"
    "**Límites en Olavarría.** Una sola campaña y apenas 6 intervalos largos, sin un conteo inicial en cero (el primero, el "
    "20/03, ya tenía plántulas): es una comprobación mínima, no una validación. El clima es reanálisis ERA5 en la grilla de "
    "Olavarría, no observaciones de estación. La alerta con conteos está calibrada con conteos semanales; con recorridas "
    "espaciadas conviene usar sobre todo la fecha de primeras plántulas. La curva acumulada es el calendario de referencia regional; con "
    "una segunda campaña de Olavarría se podrá usar un calendario propio, como en Tres Arroyos."
)


_resultados_alerta = None
if meteo is not None and not meteo.empty:
    try:
        import alerta_lolmu as _alerta_lolmu
        import visualizacion_alerta_lolmu as _vis_alerta

        # Streamlit conserva en memoria los módulos ya importados entre ejecuciones: tras una actualización del
        # repositorio, recargarlos evita usar una versión vieja
        importlib.reload(_alerta_lolmu)
        importlib.reload(_vis_alerta)
        _resultados_alerta = _vis_alerta.mostrar_alerta_lolmu(
            meteo,
            **parametros,
    tope_hasta_ultimo_cero=True,  # semanas ya cerradas por un conteo posterior en cero: probabilidad 0
    curva_desde_ultimo_cero=True,  # la curva acumulada arranca a mitad de camino entre el último cero y el primer conteo con plántulas
    curva_tiempo_termico=True,  # con primeras plántulas, curva acumulada en tiempo térmico desde esa fecha
    localidad="Olavarría",
    nota_sitio=NOTA_OLAVARRIA,
        )
    except Exception as _error_alerta:  # noqa: BLE001
        st.warning(f"No se pudo calcular la alerta: {_error_alerta}")

pagina.descarga_excel(_resultados_alerta, "Olavarria", "descarga_excel_resultados_final_olavarria")
mostrar_sesion()

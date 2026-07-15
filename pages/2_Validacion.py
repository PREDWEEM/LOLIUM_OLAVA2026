# -*- coding: utf-8 -*-
"""Página Streamlit de validación automática para PREDWEEM Olavarría."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

import calcular_metricas_validacion as motor

st.set_page_config(
    page_title=f"Validación — {motor.SITIO}",
    page_icon="📊",
    layout="wide",
)

ARCHIVOS_REQUERIDOS = (
    motor.APP,
    motor.METEO,
    motor.CAMPO,
    *motor.ARCHIVOS_MODELO,
)


def formato_fecha(valor: Any) -> str:
    if valor is None or pd.isna(valor):
        return "N/D"
    return pd.Timestamp(valor).strftime("%d-%m-%Y")


def formato_numero(
    valor: Any,
    decimales: int = 2,
    sufijo: str = "",
) -> str:
    if valor is None or pd.isna(valor):
        return "N/D"
    return f"{float(valor):.{decimales}f}{sufijo}"


def formato_delta(valor: Any) -> str:
    if valor is None or pd.isna(valor):
        return "N/D"
    return f"{int(valor):+d} d"


def huella_archivos(
    base: Path,
) -> tuple[tuple[str, int, int], ...]:
    huella: list[tuple[str, int, int]] = []
    for nombre in ARCHIVOS_REQUERIDOS:
        ruta = base / nombre
        if ruta.exists():
            estado = ruta.stat()
            huella.append(
                (
                    nombre,
                    int(estado.st_mtime_ns),
                    int(estado.st_size),
                )
            )
        else:
            huella.append((nombre, -1, -1))
    return tuple(huella)


def ejecutar_sin_interferir_streamlit(
    base: Path,
    campo_acumulado: bool,
) -> dict[str, Any]:
    streamlit_real = sys.modules.get("streamlit")
    try:
        return motor.ejecutar_app(
            base,
            campo_acumulado=campo_acumulado,
        )
    finally:
        if streamlit_real is None:
            sys.modules.pop("streamlit", None)
        else:
            sys.modules["streamlit"] = streamlit_real


@st.cache_data(show_spinner=False)
def calcular_resultados(
    base_str: str,
    campo_acumulado: bool,
    umbral_evento: float,
    prominencia_pico: float,
    _huella: tuple[tuple[str, int, int], ...],
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    motor.UMBRAL_EVENTO = float(umbral_evento)
    motor.PROMINENCIA_PICO = float(prominencia_pico)

    globales = ejecutar_sin_interferir_streamlit(
        Path(base_str),
        campo_acumulado,
    )
    sync = motor.sincronizar_eventos(
        globales["df"],
        globales["df_campo"],
        globales["col_fecha"],
        globales["col_plm2"],
    )
    indicadores = motor.metricas(globales, sync)

    columnas = [
        columna
        for columna in (
            "Fecha",
            "EMERREL",
            "DG",
            "Primer_Pico_Habilitado",
            "EMERREL_ANTES_FILTRO_PRIMER_PICO",
        )
        if columna in globales["df"].columns
    ]
    return (
        indicadores,
        sync,
        globales["df"][columnas].copy(),
    )


def agregar_linea(
    figura: go.Figure,
    fecha: Any,
    texto: str,
    color: str,
    estilo: str,
    y: float,
) -> None:
    if fecha is None or pd.isna(fecha):
        return

    figura.add_vline(
        x=fecha,
        line_color=color,
        line_dash=estilo,
        line_width=1.5,
    )
    figura.add_annotation(
        x=fecha,
        xref="x",
        y=y,
        yref="paper",
        text=texto,
        showarrow=False,
        xanchor="center",
        yanchor="bottom",
        bgcolor="rgba(255,255,255,0.94)",
        bordercolor="rgba(148,163,184,0.45)",
        borderwidth=1,
        borderpad=3,
        font=dict(size=11, color=color),
    )


def grafico_flujos(
    sync: pd.DataFrame,
    indicadores: dict[str, Any],
) -> go.Figure:
    figura = go.Figure()
    figura.add_trace(
        go.Bar(
            x=sync["Fecha"],
            y=sync["Campo_Relativo"],
            name="Observado",
            marker_color="#60A5FA",
        )
    )
    figura.add_trace(
        go.Bar(
            x=sync["Fecha"],
            y=sync["Sim_Relativo"],
            name="Simulado por intervalo",
            marker_color="#166534",
        )
    )

    agregar_linea(
        figura,
        indicadores.get(
            "Fecha_primer_pico_observado"
        ),
        "Primer pico observado",
        "#2563EB",
        "dash",
        1.04,
    )
    agregar_linea(
        figura,
        indicadores.get(
            "Fecha_primer_pico_simulado_intervalo"
        ),
        "Pico simulado por intervalo",
        "#166534",
        "dot",
        1.12,
    )

    figura.update_layout(
        title="Flujos relativos por intervalo real",
        barmode="group",
        xaxis_title="Fecha final del intervalo",
        yaxis_title="Flujo relativo",
        height=540,
        hovermode="x unified",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.18,
            xanchor="right",
            x=1,
        ),
        margin=dict(l=70, r=25, t=130, b=65),
    )
    figura.update_yaxes(
        gridcolor="rgba(148,163,184,0.25)"
    )
    figura.update_xaxes(showgrid=False)
    return figura


def grafico_acumulado(
    sync: pd.DataFrame,
) -> go.Figure:
    figura = go.Figure()
    figura.add_trace(
        go.Scatter(
            x=sync["Fecha"],
            y=sync["Campo_Acumulado"] * 100,
            mode="markers+lines",
            name="Observado",
            marker=dict(size=9),
        )
    )
    figura.add_trace(
        go.Scatter(
            x=sync["Fecha"],
            y=sync["Sim_Acumulado"] * 100,
            mode="lines",
            name="Simulado",
            line=dict(width=2.8, dash="dash"),
        )
    )
    figura.update_layout(
        title="Trayectoria acumulada",
        xaxis_title="Fecha",
        yaxis_title="Emergencia acumulada (%)",
        height=500,
        hovermode="x unified",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    )
    figura.update_yaxes(
        range=[0, 105],
        gridcolor="rgba(148,163,184,0.25)",
    )
    figura.update_xaxes(showgrid=False)
    return figura


def grafico_decision(
    diario: pd.DataFrame,
    indicadores: dict[str, Any],
) -> go.Figure:
    figura = go.Figure()
    figura.add_trace(
        go.Scatter(
            x=diario["Fecha"],
            y=diario["EMERREL"],
            mode="lines",
            name="EMERREL diaria",
            line=dict(width=2.3),
        )
    )

    control = indicadores.get("Fecha_control")
    limite = indicadores.get("Fecha_limite")
    if pd.notna(control) and pd.notna(limite):
        figura.add_vrect(
            x0=control,
            x1=limite,
            fillcolor="rgba(34,197,94,0.12)",
            layer="below",
            line_width=0,
            annotation_text="Ventana eficiente",
            annotation_position="top left",
        )

    referencias = (
        (
            indicadores.get(
                "Fecha_primer_pico_simulado"
            ),
            "Pico diario simulado",
            "#111827",
            "dot",
            1.02,
        ),
        (
            indicadores.get(
                "Fecha_primer_pico_observado"
            ),
            "Pico observado",
            "#2563EB",
            "dash",
            1.10,
        ),
        (
            indicadores.get("Fecha_alerta"),
            "Primera alerta",
            "#6B7280",
            "dash",
            1.18,
        ),
        (
            control,
            "Control",
            "#111827",
            "dot",
            1.26,
        ),
        (
            limite,
            "Límite",
            "#166534",
            "dot",
            1.34,
        ),
    )
    for referencia in referencias:
        agregar_linea(figura, *referencia)

    figura.update_layout(
        title="Serie diaria y fechas de decisión",
        xaxis_title="Fecha",
        yaxis_title="EMERREL",
        height=570,
        hovermode="x unified",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        margin=dict(l=70, r=25, t=165, b=65),
    )
    figura.update_yaxes(
        range=[0, 1.05],
        gridcolor="rgba(148,163,184,0.25)",
    )
    figura.update_xaxes(showgrid=False)
    return figura


def crear_excel(
    indicadores: dict[str, Any],
    sync: pd.DataFrame,
    diario: pd.DataFrame,
) -> bytes:
    salida = io.BytesIO()
    limpio = {
        clave: motor.serializar(valor)
        for clave, valor in indicadores.items()
    }
    with pd.ExcelWriter(
        salida,
        engine="xlsxwriter",
        datetime_format="dd-mm-yyyy",
    ) as writer:
        pd.DataFrame([limpio]).to_excel(
            writer,
            sheet_name="Metricas",
            index=False,
        )
        sync.to_excel(
            writer,
            sheet_name="Event_to_Event",
            index=False,
        )
        diario.to_excel(
            writer,
            sheet_name="Serie_Diaria",
            index=False,
        )
    return salida.getvalue()


st.title(
    f"📊 Validación automática — {motor.SITIO}"
)
st.caption(
    "El F1 y la frecuencia de picos se calculan por intervalos "
    "Event-to-Event. El Δ principal conserva la resolución diaria."
)

faltantes = [
    nombre
    for nombre in ARCHIVOS_REQUERIDOS
    if not (BASE / nombre).exists()
]

with st.sidebar:
    st.header("Configuración")
    campo_acumulado = st.checkbox(
        "Los datos de campo son acumulados",
        value=bool(motor.CAMPO_ES_ACUMULADO),
    )
    umbral_evento = st.number_input(
        "Umbral de flujo significativo",
        min_value=0.00,
        max_value=1.00,
        value=float(motor.UMBRAL_EVENTO),
        step=0.01,
        format="%.2f",
    )
    prominencia_pico = st.number_input(
        "Prominencia mínima del pico",
        min_value=0.00,
        max_value=1.00,
        value=float(motor.PROMINENCIA_PICO),
        step=0.01,
        format="%.2f",
    )
    recalcular = st.button(
        "🔄 Recalcular métricas",
        type="primary",
        width="stretch",
        disabled=bool(faltantes),
    )
    st.divider()
    st.code(
        f"Modelo: {motor.APP}\n"
        f"Meteorología: {motor.METEO}\n"
        f"Campo: {motor.CAMPO}",
        language=None,
    )

if faltantes:
    st.error(
        "Faltan archivos:\n\n- "
        + "\n- ".join(faltantes)
    )
    st.stop()

if recalcular:
    calcular_resultados.clear()

with st.spinner(
    "Ejecutando PREDWEEM Olavarría..."
):
    try:
        indicadores, sincronizado, diario = (
            calcular_resultados(
                str(BASE),
                campo_acumulado,
                float(umbral_evento),
                float(prominencia_pico),
                huella_archivos(BASE),
            )
        )
    except Exception as exc:
        st.exception(exc)
        st.stop()

delta_diario = indicadores.get(
    "Delta_primer_pico_dias"
)
delta_intervalo = indicadores.get(
    "Delta_primer_pico_intervalo_dias"
)

fecha_sim = indicadores.get(
    "Fecha_primer_pico_simulado"
)
fecha_obs = indicadores.get(
    "Fecha_primer_pico_observado"
)

if pd.notna(fecha_sim) and pd.notna(fecha_obs):
    comprobado = (
        pd.Timestamp(fecha_sim)
        - pd.Timestamp(fecha_obs)
    ).days
    if int(delta_diario) == comprobado:
        st.success(
            "✅ Δ diario verificado: "
            f"{formato_delta(delta_diario)}."
        )
    else:
        st.error(
            "El Δ mostrado no coincide con las fechas."
        )

st.subheader("Resumen de desempeño")
resumen = st.columns(6)
resumen[0].metric(
    "F1 de picos",
    formato_numero(
        indicadores.get("F1_picos"),
        2,
    ),
)
resumen[1].metric(
    "NSE de flujos",
    formato_numero(
        indicadores.get("NSE_flujos"),
        2,
    ),
)
resumen[2].metric(
    "Δ primer pico diario",
    formato_delta(delta_diario),
    help=(
        "Pico diario simulado menos pico observado. "
        "Negativo = anticipación."
    ),
)
resumen[3].metric(
    "Δ por intervalo",
    formato_delta(delta_intervalo),
    help=(
        "Auditoría basada en la fecha final "
        "del intervalo Event-to-Event."
    ),
)
resumen[4].metric(
    "PEC al control",
    formato_numero(
        indicadores.get("PEC_control_pct"),
        1,
        " %",
    ),
)
resumen[5].metric(
    "Ventana 600–800",
    formato_numero(
        indicadores.get(
            "Ventana_600_800_dias"
        ),
        0,
        " d",
    ),
)

picos = st.columns(5)
for columna, etiqueta, clave in (
    (picos[0], "Picos observados", "Picos_observados"),
    (picos[1], "Picos simulados", "Picos_simulados"),
    (picos[2], "Picos coincidentes", "Hits_picos"),
    (picos[3], "Picos omitidos", "Omisiones_picos"),
    (picos[4], "Falsos picos", "Falsos_picos"),
):
    columna.metric(
        etiqueta,
        formato_numero(
            indicadores.get(clave),
            0,
        ),
    )

st.subheader("Fechas del primer pico y decisión")
fechas = st.columns(6)
for columna, etiqueta, clave in (
    (
        fechas[0],
        "Pico diario simulado",
        "Fecha_primer_pico_simulado",
    ),
    (
        fechas[1],
        "Pico observado",
        "Fecha_primer_pico_observado",
    ),
    (
        fechas[2],
        "Pico simulado por intervalo",
        "Fecha_primer_pico_simulado_intervalo",
    ),
    (
        fechas[3],
        "Inicio térmico",
        "Fecha_inicio_termico",
    ),
    (
        fechas[4],
        "Control recomendado",
        "Fecha_control",
    ),
    (
        fechas[5],
        "Límite de control",
        "Fecha_limite",
    ),
):
    columna.metric(
        etiqueta,
        formato_fecha(
            indicadores.get(clave)
        ),
    )

tab_flujos, tab_acum, tab_control, tab_descarga = (
    st.tabs(
        [
            "Picos y flujos",
            "Trayectoria acumulada",
            "Decisión de control",
            "Datos y descargas",
        ]
    )
)

config_png = {
    "displaylogo": False,
    "toImageButtonOptions": {
        "format": "png",
        "width": 1800,
        "height": 1000,
        "scale": 2,
    },
}

with tab_flujos:
    st.plotly_chart(
        grafico_flujos(
            sincronizado,
            indicadores,
        ),
        width="stretch",
        config=config_png,
    )
    st.dataframe(
        sincronizado,
        width="stretch",
        hide_index=True,
    )

with tab_acum:
    st.plotly_chart(
        grafico_acumulado(sincronizado),
        width="stretch",
        config=config_png,
    )

with tab_control:
    st.plotly_chart(
        grafico_decision(
            diario,
            indicadores,
        ),
        width="stretch",
        config=config_png,
    )
    st.info(
        "La franja verde representa la ventana "
        "comprendida entre 600 y 800 °Cd."
    )

with tab_descarga:
    limpio = {
        clave: motor.serializar(valor)
        for clave, valor in indicadores.items()
    }
    st.dataframe(
        pd.DataFrame([limpio]),
        width="stretch",
        hide_index=True,
    )

    excel = crear_excel(
        indicadores,
        sincronizado,
        diario,
    )
    csv_metricas = (
        pd.DataFrame([limpio])
        .to_csv(index=False)
        .encode("utf-8-sig")
    )
    csv_eventos = (
        sincronizado.to_csv(
            index=False,
            date_format="%Y-%m-%d",
        ).encode("utf-8-sig")
    )
    json_metricas = json.dumps(
        limpio,
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")

    d1, d2, d3 = st.columns(3)
    d1.download_button(
        "📥 Descargar Excel",
        data=excel,
        file_name=(
            "PREDWEEM_validacion_olavarria.xlsx"
        ),
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        width="stretch",
    )
    d2.download_button(
        "📥 Métricas CSV",
        data=csv_metricas,
        file_name="metricas_olavarria.csv",
        mime="text/csv",
        width="stretch",
    )
    d3.download_button(
        "📥 Métricas JSON",
        data=json_metricas,
        file_name="metricas_olavarria.json",
        mime="application/json",
        width="stretch",
    )
    st.download_button(
        "📥 Event-to-Event CSV",
        data=csv_eventos,
        file_name="event_to_event_olavarria.csv",
        mime="text/csv",
        width="stretch",
    )

with st.expander("Definición de indicadores"):
    st.markdown(
        """
- **F1 de picos:** coincidencia calculada sobre flujos Event-to-Event.
- **Δ primer pico diario:** fecha diaria del pico validado del modelo menos fecha del pico observado.
- **Δ por intervalo:** fecha final del intervalo simulado menos fecha del pico observado; se conserva para auditoría.
- **PEC al control:** emergencia observada acumulada hasta la fecha recomendada.
- **Ventana 600–800 °Cd:** días calendario disponibles para realizar el control.
        """
    )

# -*- coding: utf-8 -*-
"""
Página Streamlit para la validación automática de PREDWEEM.

Ubicación recomendada:
    pages/2_Validacion.py

Debe coexistir en el repositorio con:
    app_emergenciacombinado.py
    calcular_metricas_validacion.py
    meteo_daily.csv
    VALIDA (1).xlsx
    IW.npy
    bias_IW.npy
    LW.npy
    bias_out.npy
    modelo_clusters_k3.pkl
"""

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


def huella_archivos(base: Path) -> tuple[tuple[str, int, int], ...]:
    """
    Huella utilizada para invalidar la caché cuando cambia algún archivo
    del modelo, la meteorología o los datos observados.
    """
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


def ejecutar_motor_sin_interferir_streamlit(
    base: Path,
    campo_acumulado: bool,
) -> dict[str, Any]:
    """
    El script de cálculo reemplaza temporalmente el módulo `streamlit`
    por un stub silencioso para ejecutar el modelo original.

    Esta función restaura siempre el módulo Streamlit real después de
    obtener la simulación, evitando interferencias con esta página.
    """
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
    """
    Ejecuta el modelo local y devuelve:
    - indicadores;
    - tabla Event-to-Event;
    - serie diaria simulada.
    """
    base = Path(base_str)

    motor.UMBRAL_EVENTO = float(umbral_evento)
    motor.PROMINENCIA_PICO = float(prominencia_pico)

    globales = ejecutar_motor_sin_interferir_streamlit(
        base,
        campo_acumulado=campo_acumulado,
    )

    sincronizado = motor.sincronizar_eventos(
        globales["df"],
        globales["df_campo"],
        globales["col_fecha"],
        globales["col_plm2"],
    )
    indicadores = motor.metricas(globales, sincronizado)

    columnas_diarias = [
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
    diario = globales["df"][columnas_diarias].copy()

    return indicadores, sincronizado, diario


def dataframe_indicadores(
    indicadores: dict[str, Any],
) -> pd.DataFrame:
    nombres = {
        "Sitio": "Sitio",
        "N_intervalos": "Número de intervalos",
        "Intervalo_mediano_dias": "Intervalo mediano (días)",
        "Picos_observados": "Picos observados",
        "Picos_simulados": "Picos simulados",
        "Razon_picos_sim_obs": "Razón picos sim./obs.",
        "Hits_picos": "Picos coincidentes",
        "Omisiones_picos": "Picos omitidos",
        "Falsos_picos": "Falsos picos",
        "F1_picos": "F1 de picos",
        "F1_intervalos": "F1 de intervalos",
        "Pearson_flujos": "Pearson de flujos",
        "NSE_flujos": "NSE de flujos",
        "Fecha_primer_flujo_observado": "Primer flujo observado",
        "Fecha_primer_flujo_simulado": "Primer flujo simulado",
        "Delta_primer_flujo_dias": "Δ primer flujo (días)",
        "Fecha_primer_pico_observado": "Primer pico observado",
        "Fecha_primer_pico_simulado": "Primer pico simulado",
        "Delta_primer_pico_dias": "Δ primer pico (días)",
        "Fecha_inicio_termico": "Inicio térmico",
        "Fecha_alerta": "Primera alerta",
        "Fecha_control": "Control recomendado",
        "Fecha_limite": "Límite de control",
        "PEC_control_pct": "PEC al control (%)",
        "Lead_time_dias": "Lead time (días)",
        "Ventana_600_800_dias": "Ventana 600–800 °Cd (días)",
    }

    filas: list[dict[str, Any]] = []
    for clave, etiqueta in nombres.items():
        if clave not in indicadores:
            continue

        valor = indicadores[clave]
        if clave.startswith("Fecha_"):
            valor = formato_fecha(valor)
        filas.append(
            {
                "Indicador": etiqueta,
                "Valor": valor,
            }
        )

    return pd.DataFrame(filas)


def crear_excel(
    indicadores: dict[str, Any],
    sincronizado: pd.DataFrame,
    diario: pd.DataFrame,
) -> bytes:
    salida = io.BytesIO()
    serializados = {
        clave: motor.serializar(valor)
        for clave, valor in indicadores.items()
    }

    with pd.ExcelWriter(
        salida,
        engine="xlsxwriter",
        datetime_format="dd-mm-yyyy",
    ) as writer:
        pd.DataFrame([serializados]).to_excel(
            writer,
            sheet_name="Metricas",
            index=False,
        )
        sincronizado.to_excel(
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


def grafico_event_to_event(
    sincronizado: pd.DataFrame,
) -> go.Figure:
    figura = go.Figure()

    figura.add_trace(
        go.Bar(
            x=sincronizado["Fecha"],
            y=sincronizado["Campo_Relativo"],
            name="Observado",
            marker_color="#60A5FA",
            hovertemplate=(
                "<b>%{x|%d-%m-%Y}</b><br>"
                "Observado: %{y:.3f}<extra></extra>"
            ),
        )
    )
    figura.add_trace(
        go.Bar(
            x=sincronizado["Fecha"],
            y=sincronizado["Sim_Relativo"],
            name="Simulado",
            marker_color="#166534",
            hovertemplate=(
                "<b>%{x|%d-%m-%Y}</b><br>"
                "Simulado: %{y:.3f}<extra></extra>"
            ),
        )
    )

    figura.update_layout(
        title="Flujos relativos por intervalo real de monitoreo",
        barmode="group",
        xaxis_title="Fecha final del intervalo",
        yaxis_title="Flujo relativo",
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
        margin=dict(l=70, r=25, t=80, b=65),
    )
    figura.update_yaxes(
        range=[0, max(
            1.0,
            float(
                sincronizado[
                    ["Campo_Relativo", "Sim_Relativo"]
                ].max().max()
            ) * 1.10,
        )],
        gridcolor="rgba(148,163,184,0.25)",
    )
    figura.update_xaxes(showgrid=False)

    return figura


def grafico_acumulado(
    sincronizado: pd.DataFrame,
) -> go.Figure:
    figura = go.Figure()

    figura.add_trace(
        go.Scatter(
            x=sincronizado["Fecha"],
            y=sincronizado["Campo_Acumulado"] * 100,
            mode="markers+lines",
            name="Observado",
            marker=dict(
                size=9,
                color="#60A5FA",
                line=dict(color="#FFFFFF", width=1),
            ),
            line=dict(color="#60A5FA", width=2.2),
        )
    )
    figura.add_trace(
        go.Scatter(
            x=sincronizado["Fecha"],
            y=sincronizado["Sim_Acumulado"] * 100,
            mode="lines",
            name="Simulado",
            line=dict(
                color="#166534",
                width=2.8,
                dash="dash",
            ),
        )
    )

    figura.update_layout(
        title="Trayectoria acumulada observada y simulada",
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
        margin=dict(l=70, r=25, t=80, b=65),
    )
    figura.update_yaxes(
        range=[0, 105],
        gridcolor="rgba(148,163,184,0.25)",
    )
    figura.update_xaxes(showgrid=False)

    return figura


def grafico_serie_diaria(
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
            line=dict(
                color="#075FCF",
                width=2.3,
            ),
            hovertemplate=(
                "<b>%{x|%d-%m-%Y}</b><br>"
                "EMERREL: %{y:.3f}<extra></extra>"
            ),
        )
    )

    fecha_control = indicadores.get("Fecha_control")
    fecha_limite = indicadores.get("Fecha_limite")
    fecha_inicio = indicadores.get("Fecha_inicio_termico")
    fecha_alerta = indicadores.get("Fecha_alerta")

    if pd.notna(fecha_control) and pd.notna(fecha_limite):
        figura.add_vrect(
            x0=fecha_control,
            x1=fecha_limite,
            fillcolor="rgba(34,197,94,0.12)",
            layer="below",
            line_width=0,
            annotation_text="Ventana eficiente",
            annotation_position="top left",
        )

    referencias = (
        (
            fecha_alerta,
            "Primera alerta",
            "#6B7280",
            "dash",
        ),
        (
            fecha_inicio,
            "Inicio térmico",
            "#111827",
            "dot",
        ),
        (
            fecha_control,
            "Control",
            "#111827",
            "dot",
        ),
        (
            fecha_limite,
            "Límite",
            "#166534",
            "dot",
        ),
    )

    for fecha, texto, color, estilo in referencias:
        if pd.isna(fecha):
            continue
        figura.add_vline(
            x=fecha,
            line_color=color,
            line_dash=estilo,
            line_width=1.5,
        )
        figura.add_annotation(
            x=fecha,
            xref="x",
            y=1.02,
            yref="paper",
            text=texto,
            showarrow=False,
            xanchor="center",
            yanchor="bottom",
            bgcolor="rgba(255,255,255,0.93)",
            bordercolor="rgba(148,163,184,0.45)",
            borderwidth=1,
            borderpad=3,
            font=dict(size=11, color=color),
        )

    figura.update_layout(
        title="Serie diaria y fechas de decisión agronómica",
        xaxis_title="Fecha",
        yaxis_title="EMERREL",
        height=520,
        hovermode="x unified",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        margin=dict(l=70, r=25, t=105, b=65),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.12,
            xanchor="right",
            x=1,
        ),
    )
    figura.update_yaxes(
        range=[0, 1.05],
        gridcolor="rgba(148,163,184,0.25)",
    )
    figura.update_xaxes(showgrid=False)

    return figura


st.title(f"📊 Validación automática — {motor.SITIO}")
st.caption(
    "Comparación Event-to-Event entre la emergencia diaria simulada "
    "y los conteos reales almacenados en el repositorio."
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
        help=(
            "Active esta opción únicamente cuando cada valor de campo "
            "sea el total acumulado desde el inicio de la campaña."
        ),
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
    st.markdown("**Archivos utilizados**")
    st.code(
        "\n".join(
            [
                f"Modelo: {motor.APP}",
                f"Meteorología: {motor.METEO}",
                f"Campo: {motor.CAMPO}",
            ]
        ),
        language=None,
    )


if faltantes:
    st.error(
        "No es posible ejecutar la validación. Faltan los siguientes "
        "archivos en el repositorio:\n\n- "
        + "\n- ".join(faltantes)
    )
    st.stop()


huella = huella_archivos(BASE)

if recalcular:
    calcular_resultados.clear()

with st.spinner(
    "Ejecutando el modelo y calculando las métricas de validación..."
):
    try:
        indicadores, sincronizado, diario = calcular_resultados(
            str(BASE),
            campo_acumulado,
            float(umbral_evento),
            float(prominencia_pico),
            huella,
        )
    except Exception as exc:
        st.exception(exc)
        st.stop()


st.subheader("Resumen de desempeño")

fila_1 = st.columns(6)
fila_1[0].metric(
    "F1 de picos",
    formato_numero(indicadores.get("F1_picos"), 2),
)
fila_1[1].metric(
    "NSE de flujos",
    formato_numero(indicadores.get("NSE_flujos"), 2),
)
fila_1[2].metric(
    "Δ primer pico",
    formato_numero(
        indicadores.get("Delta_primer_pico_dias"),
        0,
        " d",
    ),
    help="Negativo: el modelo anticipa. Positivo: el modelo se retrasa.",
)
fila_1[3].metric(
    "PEC al control",
    formato_numero(
        indicadores.get("PEC_control_pct"),
        1,
        " %",
    ),
)
fila_1[4].metric(
    "Lead time",
    formato_numero(
        indicadores.get("Lead_time_dias"),
        0,
        " d",
    ),
)
fila_1[5].metric(
    "Ventana 600–800",
    formato_numero(
        indicadores.get("Ventana_600_800_dias"),
        0,
        " d",
    ),
)

fila_2 = st.columns(4)
fila_2[0].metric(
    "Picos observados",
    formato_numero(indicadores.get("Picos_observados"), 0),
)
fila_2[1].metric(
    "Picos simulados",
    formato_numero(indicadores.get("Picos_simulados"), 0),
)
fila_2[2].metric(
    "Picos coincidentes",
    formato_numero(indicadores.get("Hits_picos"), 0),
)
fila_2[3].metric(
    "Falsos picos",
    formato_numero(indicadores.get("Falsos_picos"), 0),
)


st.subheader("Fechas de decisión agronómica")

c1, c2, c3, c4 = st.columns(4)
c1.metric(
    "Primer pico observado",
    formato_fecha(
        indicadores.get("Fecha_primer_pico_observado")
    ),
)
c2.metric(
    "Inicio térmico",
    formato_fecha(indicadores.get("Fecha_inicio_termico")),
)
c3.metric(
    "Control recomendado",
    formato_fecha(indicadores.get("Fecha_control")),
)
c4.metric(
    "Límite de control",
    formato_fecha(indicadores.get("Fecha_limite")),
)


tab_flujos, tab_acumulado, tab_decision, tab_datos = st.tabs(
    [
        "Picos y flujos",
        "Trayectoria acumulada",
        "Decisión de control",
        "Datos y descargas",
    ]
)

with tab_flujos:
    st.plotly_chart(
        grafico_event_to_event(sincronizado),
        width="stretch",
        config={
            "displaylogo": False,
            "toImageButtonOptions": {
                "format": "png",
                "filename": f"PREDWEEM_{motor.ID_SITIO}_event_to_event",
                "width": 1800,
                "height": 1000,
                "scale": 2,
            },
        },
    )

    st.dataframe(
        sincronizado,
        width="stretch",
        hide_index=True,
        column_config={
            "Fecha": st.column_config.DateColumn(
                "Fecha",
                format="DD-MM-YYYY",
            ),
            "Inicio_Intervalo": st.column_config.DateColumn(
                "Inicio",
                format="DD-MM-YYYY",
            ),
            "Campo_Relativo": st.column_config.NumberColumn(
                "Observado relativo",
                format="%.3f",
            ),
            "Sim_Relativo": st.column_config.NumberColumn(
                "Simulado relativo",
                format="%.3f",
            ),
        },
    )

with tab_acumulado:
    st.plotly_chart(
        grafico_acumulado(sincronizado),
        width="stretch",
        config={
            "displaylogo": False,
            "toImageButtonOptions": {
                "format": "png",
                "filename": f"PREDWEEM_{motor.ID_SITIO}_acumulado",
                "width": 1800,
                "height": 1000,
                "scale": 2,
            },
        },
    )

with tab_decision:
    st.plotly_chart(
        grafico_serie_diaria(diario, indicadores),
        width="stretch",
        config={
            "displaylogo": False,
            "toImageButtonOptions": {
                "format": "png",
                "filename": f"PREDWEEM_{motor.ID_SITIO}_ventana_control",
                "width": 1800,
                "height": 1000,
                "scale": 2,
            },
        },
    )

    st.info(
        "La franja verde representa la ventana térmica comprendida "
        "entre el objetivo de control y el límite operativo."
    )

with tab_datos:
    st.markdown("#### Tabla completa de indicadores")
    tabla_indicadores = dataframe_indicadores(indicadores)
    st.dataframe(
        tabla_indicadores,
        width="stretch",
        hide_index=True,
    )

    indicadores_serializados = {
        clave: motor.serializar(valor)
        for clave, valor in indicadores.items()
    }

    csv_metricas = pd.DataFrame(
        [indicadores_serializados]
    ).to_csv(index=False).encode("utf-8-sig")

    csv_eventos = sincronizado.to_csv(
        index=False,
        date_format="%Y-%m-%d",
    ).encode("utf-8-sig")

    csv_diario = diario.to_csv(
        index=False,
        date_format="%Y-%m-%d",
    ).encode("utf-8-sig")

    json_metricas = json.dumps(
        indicadores_serializados,
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")

    excel = crear_excel(
        indicadores,
        sincronizado,
        diario,
    )

    d1, d2, d3 = st.columns(3)
    d1.download_button(
        "📥 Descargar Excel",
        data=excel,
        file_name=(
            f"PREDWEEM_validacion_{motor.ID_SITIO}.xlsx"
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
        file_name=f"metricas_{motor.ID_SITIO}.csv",
        mime="text/csv",
        width="stretch",
    )
    d3.download_button(
        "📥 Métricas JSON",
        data=json_metricas,
        file_name=f"metricas_{motor.ID_SITIO}.json",
        mime="application/json",
        width="stretch",
    )

    d4, d5 = st.columns(2)
    d4.download_button(
        "📥 Event-to-Event CSV",
        data=csv_eventos,
        file_name=f"event_to_event_{motor.ID_SITIO}.csv",
        mime="text/csv",
        width="stretch",
    )
    d5.download_button(
        "📥 Serie diaria CSV",
        data=csv_diario,
        file_name=f"serie_diaria_{motor.ID_SITIO}.csv",
        mime="text/csv",
        width="stretch",
    )


with st.expander("Definición de los indicadores"):
    st.markdown(
        """
- **F1 de picos:** coincidencia entre máximos locales observados y simulados.
- **NSE de flujos:** ajuste de las magnitudes relativas Event-to-Event.
- **Δ primer pico:** fecha simulada menos fecha observada.
- **PEC al control:** porcentaje de la emergencia observada acumulada hasta la fecha recomendada.
- **Lead time:** días entre la primera alerta y la fecha de control.
- **Ventana 600–800 °Cd:** días calendario disponibles entre el control recomendado y su límite.
        """
    )

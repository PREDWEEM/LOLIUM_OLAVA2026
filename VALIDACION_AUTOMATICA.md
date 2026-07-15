# Validación automática PREDWEEM — Olavarría

El archivo `calcular_metricas_validacion.py` ejecuta el motor real de
`app_emergenciacombinado.py` en modo silencioso, usando los mismos parámetros
predeterminados y los archivos del repositorio. Luego compara la tasa diaria
simulada con `VALIDA (1).xlsx` mediante integración **Event-to-Event**.

## Indicadores producidos

- número de picos observados y simulados;
- razón entre picos simulados y observados;
- hits, omisiones, falsos picos y F1 de picos;
- F1 de intervalos con emergencia;
- Pearson y NSE de los flujos relativos;
- desfase del primer flujo significativo;
- desfase del primer pico;
- fecha de inicio del tiempo térmico;
- fecha recomendada de control a 600 °Cd;
- fecha límite a 800 °Cd;
- porcentaje de emergencia observada acumulada al control (PEC);
- lead time;
- duración calendario de la ventana 600–800 °Cd.

## Ejecución local

```bash
pip install -r requirements.txt
python calcular_metricas_validacion.py
```

## Archivos generados

```text
resultados_validacion/
├── metricas_olavarria.json
├── metricas_olavarria.csv
├── event_to_event_olavarria.csv
└── serie_diaria_olavarria.csv
```

El cálculo incluye el primer muestreo observado. La tolerancia para asociar
picos simulados y observados corresponde al intervalo mediano de monitoreo del
sitio.

Por defecto, `VALIDA (1).xlsx` se interpreta como una serie de **flujos por
intervalo**. Cuando el archivo contenga conteos acumulados, ejecutar:

```bash
python calcular_metricas_validacion.py --campo-acumulado
```

## Automatización

El workflow `.github/workflows/calcular_metricas_validacion.yml` valida el
cálculo en los pull requests y lo vuelve a ejecutar cuando cambian en `main`:

- `app_emergenciacombinado.py`;
- `meteo_daily.csv`;
- `VALIDA (1).xlsx`;
- los pesos y archivos del modelo;
- el propio script de métricas.

Después de una actualización en `main`, los resultados modificados se guardan
automáticamente en `resultados_validacion/`.

## Estandarización multisitio

En los demás repositorios debe conservarse la misma estructura de columnas del
archivo `metricas_<sitio>.csv`. Solo deben adaptarse al comienzo del script:

- nombre e identificador del sitio;
- nombre del archivo de campo y alias usado por la app;
- correcciones locales del modelo, que ya se mantienen dentro del
  `app_emergenciacombinado.py` correspondiente.

Como el script ejecuta la app real, se preservan automáticamente las
particularidades de cada sitio, por ejemplo el lag de Pergamino o el agotamiento
Weibull de Balcarce, sin duplicar el motor ecofisiológico.

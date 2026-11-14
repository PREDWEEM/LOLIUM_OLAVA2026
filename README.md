# PREDWEEM — Lolium Olavarría 2026

Repositorio correspondiente a la implementación de **PREDWEEM** para la predicción de la emergencia y la dinámica fenológica de *Lolium multiflorum* en Olavarría, provincia de Buenos Aires, Argentina.

> **Propiedad intelectual**  
> Copyright © 2026 Guillermo R. Chantre / PREDWEEM.  
> Todos los derechos reservados.
>
> Este repositorio constituye software propietario. Su disponibilidad pública no concede autorización para utilizar, copiar, modificar, redistribuir, sublicenciar, realizar ingeniería inversa ni explotar comercialmente el código, los modelos, los parámetros, los pesos neuronales, la documentación o los datos incluidos.
>
> Consulte el aviso completo en [COPYRIGHT.md](COPYRIGHT.md).

## Finalidad

PREDWEEM es una herramienta de apoyo a la toma de decisiones agronómicas basada en la integración de datos meteorológicos, modelos predictivos y filtros ecofisiológicos para anticipar los flujos de emergencia de raigrás anual.

La implementación de este repositorio está orientada a la localidad de **Olavarría** y debe utilizarse dentro del dominio geográfico, climático y agronómico para el cual fue configurada y validada.

## Estrategia meteorológica

La serie operativa `meteo_daily.csv` utiliza las coordenadas de Olavarría `-36.8799, -60.2160` y separa explícitamente los datos según su origen y función:

- **ERA5-Land:** reanálisis histórico consolidado, utilizado hasta el último día que la API entrega completo.
- **ERA5:** respaldo explícito si ERA5-Land no presenta una ventana reciente válida.
- **ECMWF IFS histórico:** completa automáticamente los días posteriores al último reanálisis completo.
- **ECMWF IFS HRES:** pronóstico operativo desde el día actual hasta siete días posteriores.

Antes de descargar el histórico completo, el actualizador sondea una ventana reciente y detecta el último día con Tmax, Tmin y precipitación válidas. De esta manera, una demora transitoria de ERA5-Land no interrumpe el workflow: los días todavía incompletos pasan al bloque ECMWF IFS sin ser rellenados artificialmente.

El archivo conserva las columnas requeridas por el modelo (`Fecha`, `TMAX`, `TMIN`, `Prec`) y añade:

- `FUENTE`: producto meteorológico utilizado.
- `TIPO`: `REANALISIS`, `REANALISIS_FALLBACK`, `HISTORICO_MODELO` o `PRONOSTICO`.
- `FECHA_EMISION`: fecha y hora local de generación del bloque meteorológico.

La precipitación faltante **no se reemplaza por cero ni se arrastra desde el día anterior**. Si la API devuelve fechas discontinuas, duplicados, precipitación negativa o una temperatura máxima inferior a la mínima dentro de un bloque que debería estar completo, la actualización falla y conserva intacto el archivo operativo anterior.

La actualización automática se ejecuta diariamente a las **07:30** y **15:30**, hora de Argentina, y también puede iniciarse manualmente mediante GitHub Actions.

## Alerta de flushes

La página muestra la **alerta de flushes** de *Lolium multiflorum*: la probabilidad de que en los próximos 7 días emerja
≥ 5 % de la campaña, con dos niveles (*Atención* desde 15 %, *Alerta* desde 25 %), la emergencia acumulada esperada y la
ventana de control post-emergente (600–800 °Cd desde el inicio). El modelo (`alerta_lolmu.py`, `alerta_lolmu_params.json`,
`visualizacion_alerta_lolmu.py`) es el calibrado con 17 campañas de Bordenave y combina, con la información disponible a la
fecha de emisión: el calendario medio de emergencia de LOLMU; la respuesta a las lluvias ya registradas; opcionalmente, la
fecha en que se vieron las primeras plántulas del lote (que además ancla el reloj térmico; sin ese dato la ventana de
control no se calcula); y, opcionalmente, conteos de plántulas (tabla o planilla Excel/CSV).

**Comprobación en Olavarría.** Sin reajustar el modelo, con los conteos de 2026 (`data/campanias/2026/`; 7 fechas entre el
20/03 y el 20/06, 6 intervalos de 12 a 20 días, 4 con flush) y el clima de este repositorio: AUC 1,00; con la fecha de
primeras plántulas, los 4 intervalos con flush quedaron en *Alerta* y ninguno de los 2 sin flush. Es una comprobación mínima
(una campaña, 6 intervalos largos y sin conteo inicial en cero), no una validación; no hay gemelo digital de Olavarría con el
que comparar. El clima es reanálisis ERA5, no de estación. La curva acumulada es el calendario de Bordenave.

La barra lateral conserva solo los parámetros que usa la alerta (temperaturas base, óptima y crítica, y objetivos 600 y
800 °Cd); los del motor PREDWEEM quedan en sus valores por defecto (cobertura de rastrojo 10 %).

## Campaña vigente y actualización automática

La campaña meteorológica va del **1 de enero al 1 de octubre** de cada año (`_campania_vigente()` en `actualizar_clima.py`;
las variables `CAMPANIA_INICIO` y `CAMPANIA_FIN` la fijan a mano). Después del 1 de octubre la serie queda cerrada; el
**1 de enero siguiente** la carga se reinicia sola. En los primeros 21 días se admite no tener todavía reanálisis del año: ECMWF
IFS histórico cubre desde el 1 de enero. `test_actualizar_clima.py` prueba el reinicio.

## Despliegue privado

La aplicación está preparada para ejecutarse desde un checkout privado. Los datos, el logo y los activos científicos deben cargarse desde archivos locales del repositorio. Consulte [PRIVATE_REPOSITORY.md](PRIVATE_REPOSITORY.md).

La actualización meteorológica programada puede continuar funcionando en un repositorio privado mediante GitHub Actions, siempre que Actions permanezca habilitado y el workflow conserve permisos de escritura sobre el contenido del repositorio.

## Curva acumulada en tiempo térmico desde las primeras plántulas

Cuando se informa la fecha de las primeras plántulas (o hay un primer conteo con plántulas), la curva de emergencia
acumulada deja de seguir el calendario y sigue el **tiempo térmico acumulado desde esa fecha** (media y rango 10–90 % de
17 campañas de Bordenave, `curva_tt` en `alerta_lolmu_params.json`); más allá del clima disponible se suman temperaturas
medias históricas. Error medio de la emergencia acumulada en las fechas de conteo desde las primeras plántulas (puntos %):

| Localidad | Calendario por fecha | Tiempo térmico desde el inicio |
|---|---|---|
| Bordenave (17 campañas, dejando cada una afuera) | 12,9 | 11,3 |
| Lartigau 2026 | 9,9 | 5,8 |
| Olavarría 2026 | 13,7 | 10,7 |
| Pergamino 2024 y 2026 | 17,5 | 7,2 |
| San Pedro 2023, 2024 y 2026 | 19,5 | 14,4 |

Mejora sobre todo donde la fecha de inicio varía mucho entre años. En Tres Arroyos y Balcarce sigue el calendario propio
del sitio (error 6,1 y 6,9 puntos) y en Azul el calendario de Bordenave (5,3 contra 15,8 en su única campaña).

## Señal de lluvia (actualización de noviembre de 2026)

La señal de lluvia usa ahora el **modelo de pulsos ajustado con las 17 campañas de *Lolium multiflorum* de Bordenave**.
El tamaño de cada pulso depende del agua que entró al suelo, de cuán seco estaba y de la época del año (máximo para
lluvias de fines de mayo); la mitad de la respuesta emerge dentro de 114 °Cd de tiempo térmico de suelo y el 90 %
dentro de 252 °Cd. Con el nuevo núcleo se reajustaron los modelos logísticos, los percentiles de referencia y la
recalibración de flujos tardíos (`alerta_lolmu_params.json`). El balance de agua y la temperatura de suelo no cambian.

Validación con cada campaña de Bordenave predicha con el ajuste sin ella (incluido el núcleo de lluvia): AUC 0,77 solo
con clima, 0,83 con primeras plántulas y 0,87 con conteos. En las ocho localidades de validación, sin reajustar: 0,89,
0,92 y 0,93 (calendario solo, 0,89). En Olavarría: 1,00, 1,00 y 1,00 (antes 1,00, 1,00 y 1,00); las tablas de
validación de este sitio que figuran más arriba corresponden a la versión anterior.

## Aviso de flujos tardíos

Del 1 de mayo al 30 de junio la app muestra además la **probabilidad de flujos tardíos**: que en los próximos 7 días
emerja al menos 2 % de la campaña. El aviso se da desde 20 %; sin datos del lote, desde 25 % (`tardia.umbral_tramos`).
En esa época los grandes flujos (≥ 5 %) son raros, pero pocas plantas por semana importan para decidir la fecha de siembra.
Es la misma alerta recalibrada por nivel de información (`tardia` en `alerta_lolmu_params.json`). Aparece en un recuadro
debajo de la alerta, en el **semáforo semanal** del gráfico (fila «Flujos tardíos»: violeta fuerte = flujo tardío probable;
la fila «Grandes flujos» repite el nivel de cada semana) y en la descarga en Excel.

| Información | AUC Bordenave (17 campañas, 130 semanas de mayo–junio, 42 con ≥ 2 %) | Detectadas con el aviso | Semanas marcadas |
|---|---|---|---|
| Solo clima (aviso desde 25 %) | 0,57 | 67 % | 68 % |
| + primeras plántulas | 0,79 | 90 % | 62 % |
| + conteos semanales | 0,87 | 86 % | 51 % |

Cada campaña se predijo con el ajuste sin ella. Sin datos del lote el aviso casi no distingue semanas: conviene cargar la
fecha de primeras plántulas. En otras seis localidades (58 intervalos de mayo–junio, 10 con ≥ 2 % por semana) la AUC fue
0,85 con primeras plántulas y 0,89 con conteos, con 90 % de detección; allí la probabilidad tiende a ser alta (30 % contra
17 % observado).

**Del 1 de julio al 1 de octubre no se muestra probabilidad** (`tardia.recorrida`): en Bordenave (80 semanas, 11 con
flujo tardío) no distinguió las semanas con emergencia (AUC 0,41–0,50), y bajar el umbral solo marcaba más semanas al
azar. En su lugar, la app recomienda **recorrer los lotes cada 2 semanas**, sobre todo donde suele haber emergencia
invernal (sudoeste bonaerense), antes de definir la fecha de siembra o un control. En el semáforo esas semanas aparecen
en gris.

En las apps con dos o más campañas propias (Bordenave, Tres Arroyos, Balcarce, San Pedro y Pergamino), el recuadro de
flujos tardíos muestra además cuánto emergió **después de la fecha de emisión en cada campaña del sitio**. Si en esas
campañas, en mediana, emergió menos de 3 % de la campaña desde esa fecha, el aviso se presenta como «Flujo tardío posible
según el modelo; en <sitio> la emergencia suele cortarse antes»: la recalibración de tardíos se ajustó con Bordenave, donde
la emergencia se extiende hasta el invierno, y en sitios donde se corta antes avisa de más (en Balcarce, en mayo de 2014,
2025 y 2026, avisó 8 semanas y hubo 2 flujos tardíos). La probabilidad se sigue mostrando.

## Residual a la siembra (guía de riesgo)

Debajo de la alerta, un recuadro siempre visible muestra, para la **fecha de siembra prevista** (1/05–31/07; si no se
carga, el 1/06 como referencia), el riesgo de nacimientos en la **ventana de acción del residual: de 10 días antes a 45 días
después de la siembra**, el período de acción promedio de un herbicida residual. Tiene tres tarjetas: riesgo, nacimientos en
la ventana (mediana de las campañas, en plantas/m² y en % de la campaña) y recomendación. Se calcula con las 34 campañas de la región, como referencia, porque Olavarría tiene una sola campaña; se muestra también el valor de esa campaña (`residual` en `alerta_lolmu_params.json`). Las plantas/m² usan la densidad de cada campaña con conteos; las campañas que solo
tienen la curva relativa usan la densidad de referencia del sitio (5826 pl/m² por campaña, mediana de las
campañas con conteos, aplicada a la distribución regional):

| Siembra | Nacimientos de −10 a +45 días (mediana) | Riesgo para el residual | Campañas del sitio |
|---|---|---|---|
| 1/05 | 916 pl/m² (15,7 %) | Muy alto | 2026: 2213 pl/m² |
| 15/05 | 453 pl/m² (7,8 %) | Muy alto | 2026: 1303 pl/m² |
| 1/06 | 193 pl/m² (3,3 %) | Muy alto | 2026: 450 pl/m² |
| 15/06 | 151 pl/m² (2,6 %) | Muy alto | 2026: 64 pl/m² |
| 1/07 | 98 pl/m² (1,7 %) | Muy alto | 2026: 0 pl/m² |

El nivel de riesgo surge de las plantas/m² que nacieron en la ventana en una campaña típica (mediana). Se usan plantas
y no el % de la campaña porque en sitios con mucha densidad una fracción chica son muchas plantas (en San Pedro, 0,8 % de
la campaña fueron 29–42 pl/m²):

| Riesgo | Nacimientos en la ventana | Recomendación |
|---|---|---|
| 🔴 Muy alto | ≥ 50 pl/m² | Usar residual |
| 🟠 Alto | 20–50 pl/m² | Residual recomendado |
| 🟡 Medio | 5–20 pl/m² | Según infestación: residual si el lote tiene alta infestación o antecedentes de raigrás |
| 🟢 Bajo | < 5 pl/m² | Residual solo en lotes muy infestados |

Sin otro dato, las densidades son las registradas en los ensayos del sitio. El usuario puede indicar la **infestación de raigrás de su lote** (opcional): baja (unas 200 pl/m² en toda la campaña), media (unas 1.000) o alta (unas 4.000). Con ese dato las plantas/m² se calculan con la densidad del lote y, como la infestación ya está considerada, las recomendaciones de los niveles medio y bajo pasan a «residual opcional» y «no hace falta residual».

Debajo de las tarjetas se indica el valor de cada campaña del sitio y qué proporción de las campañas cayó en cada nivel. Es
un **riesgo histórico, no una predicción de la campaña**: ni la fecha de primeras plántulas ni el clima anticiparon cuánta
emergencia queda después de la siembra.

## Condiciones de uso

No se concede licencia de uso por el solo hecho de acceder al repositorio. Cualquier utilización académica, técnica, institucional o comercial que exceda la visualización del contenido requiere autorización previa y escrita del titular de los derechos correspondientes.

Las solicitudes de autorización deben canalizarse mediante los medios de contacto del titular del repositorio PREDWEEM.

## Limitación de responsabilidad

PREDWEEM es una herramienta de soporte para decisiones y no sustituye el diagnóstico profesional, el monitoreo a campo ni la evaluación agronómica específica de cada lote. Las decisiones de manejo deben ser adoptadas por profesionales responsables considerando las condiciones locales y la normativa aplicable.

## Autoría

**PREDWEEM by Guillermo R. Chantre**

## Fin de carga de cada campaña

La última fecha meteorológica de cada campaña es el **1 de octubre, inclusive** (en 2026, el 1/10/2026). El pronóstico se
recorta al alcanzar ese límite y desde el 2 de octubre no se consulta el pronóstico futuro. Las consultas históricas ERA5-Land,
ERA5 y ECMWF IFS quedan limitadas al 1 de octubre, permitiendo actualizar el reanálisis de los días pendientes sin ampliar la
campaña. La serie cerrada debe ser continua y no admite fechas posteriores al límite. El 1 de enero siguiente comienza la
campaña nueva.

## Módulo común (LOLIUM-COMUN)

La alerta, su visualización y el control de acceso son comunes a las 8 apps de Lolium y están en el paquete
[PREDWEEM/LOLIUM-COMUN](https://github.com/PREDWEEM/LOLIUM-COMUN), fijado por versión en `requirements.txt`
(`lolium-comun @ git+https://github.com/PREDWEEM/LOLIUM-COMUN@<commit>  # v1.2.0`). En esta app, `alerta_lolmu.py`,
`visualizacion_alerta_lolmu.py` y `acceso_predweem.py` son archivos puente que cargan ese paquete con los parámetros de este
sitio (`alerta_lolmu_params.json`), que siguen acá. Los cambios a la alerta se hacen en LOLIUM-COMUN y llegan a la app al
actualizar la versión en `requirements.txt`.

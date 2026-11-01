# Campañas de Olavarría: emergencia y clima

Son los datos de *Lolium multiflorum* de Olavarría con que se probó la alerta. La actualización automática no modifica estas
carpetas (`meteo_daily.csv`, en cambio, se reemplaza con la campaña nueva el 1 de enero de cada año).

## 2026

| Archivo | Contenido |
|---|---|
| `emergencia_olavarria_2026_original.xlsx` | Planilla de conteos (FECHA, PLM2), sin cambios: copia de `VALIDA (1).xlsx` de la raíz del repositorio. |
| `emergencia_olavarria_2026.csv` | Los mismos datos con días desde el conteo anterior, fracción de cada intervalo y emergencia acumulada (%). |
| `clima_olavarria_2026.csv` | Copia de `meteo_daily.csv` al cierre de la campaña: 274 días (2026-01-01 – 2026-10-01), 492 mm. |

Conteos: 7 fechas del 20/03/2026 al 20/06/2026, cada 12 a 20 días;
5826 plántulas/m² en total. `PLM2` son las plántulas nuevas por m² en el intervalo que termina en esa fecha. **No hay conteo
inicial en cero**: el primero (20/03) ya tenía plántulas, así que se desconoce cuándo empezó la emergencia; los porcentajes son
sobre lo registrado. La planilla no identifica la localidad; se asume Olavarría por estar en este repositorio.

Clima: reanálisis **ERA5** (respaldo de ERA5-Land) en la grilla de Olavarría (−36,88; −60,22), no observaciones de estación
(columnas `FUENTE` y `TIPO`).

**Para sumar una campaña**, cree la carpeta `<año>/` con `emergencia_olavarria_<año>.csv` (al menos `Fecha` y `PLM2`) y su clima.
Con dos o más campañas se podrá usar un calendario propio de Olavarría para la curva acumulada, como en Tres Arroyos.

## Huellas SHA-256

| Archivo | SHA-256 |
|---|---|
| `2026/clima_olavarria_2026.csv` | `e3993b4733e731fd41ee045a7a3b5d6d038077994fd76ac1501ea77bb5107cbd` |
| `2026/emergencia_olavarria_2026.csv` | `46fb9c533e39721f8d4df4bfc99fa644bf1daa047b370472250c35159a47acd3` |
| `2026/emergencia_olavarria_2026_original.xlsx` | `287762dd0c1c71740c5df53f423446f4c2c268c7fd29051b7029d3860ded4ff5` |

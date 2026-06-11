import requests
import pandas as pd
import sys
import os

# Coordenadas de OLAVARRIA, Provincia de Buenos Aires
LAT = -36.8799
LON = -60.2160
ARCHIVO_CSV = 'meteo_daily.csv'

def actualizar_pronostico():
    url = "https://api.open-meteo.com/v1/forecast"
    
    # MODIFICACIÓN CRÍTICA: Traemos los últimos 7 días (ya observados/consolidados) 
    # y los próximos 7 días de pronóstico técnico.
    params = {
        "latitude": LAT,
        "longitude": LON,
        "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum"],
        "timezone": "America/Argentina/Buenos_Aires",
        "past_days": 7,
        "forecast_days": 7
    }
    
    print("Consultando a Open-Meteo (Ventana Híbrida: -7d a +7d) ...")
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            print(f"Error en la API: {response.text}")
            sys.exit(1)
    except Exception as e:
        print(f"Error de conexión con la API: {e}")
        sys.exit(1)
        
    data = response.json()
    
    # DataFrame con los 14 días totales (7 pasados + hoy + 6 futuros)
    df_nuevo = pd.DataFrame({
        'Fecha': data['daily']['time'],
        'TMAX': data['daily']['temperature_2m_max'],
        'TMIN': data['daily']['temperature_2m_min'],
        'Prec': data['daily']['precipitation_sum']
    })
    
    # Forzar el parseo a datetime para evitar fallos de comparación de strings
    df_nuevo['Fecha'] = pd.to_datetime(df_nuevo['Fecha'])
    
    if df_nuevo.isnull().values.any():
        print("ADVERTENCIA: Datos incompletos detectados. Aplicando interpolación temporal (ffill).")
        df_nuevo = df_nuevo.ffill()

    # Integración inteligente con el archivo histórico
    if os.path.exists(ARCHIVO_CSV):
        print(f"Leyendo historial desde {ARCHIVO_CSV}...")
        df_historico = pd.read_csv(ARCHIVO_CSV)
        df_historico['Fecha'] = pd.to_datetime(df_historico['Fecha'])
        
        # Combinamos el historial con la ventana nueva
        df_final = pd.concat([df_historico, df_nuevo], ignore_index=True)
        
        # EXPLICACIÓN DEL PROCESO:
        # Al usar keep='last', los registros de los 7 días pasados que trae la API 
        # (que ya pasaron por el filtro de reanálisis/observación real) eliminan y 
        # reemplazan a los registros de "pronóstico" que guardaste hace unos días.
        df_final = df_final.drop_duplicates(subset=['Fecha'], keep='last')
        df_final = df_final.sort_values(by='Fecha').reset_index(drop=True)
    else:
        print(f"No se encontró {ARCHIVO_CSV}, creando un archivo nuevo...")
        df_final = df_nuevo

    # Guardar manteniendo el estándar de formato ISO estricto (YYYY-MM-DD)
    df_final['Fecha'] = df_final['Fecha'].dt.strftime('%Y-%m-%d')
    df_final.to_csv(ARCHIVO_CSV, index=False)
    
    print("Archivo meteorológico sincronizado y corregido con éxito. Últimos 10 registros:")
    print(df_final.tail(10))

if __name__ == "__main__":
    actualizar_pronostico()

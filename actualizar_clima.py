
import requests
import pandas as pd
import sys
import os

# Coordenadas estrictas OLAVARRÍA (PREDWEEM Integral)
LAT = -36.8799
LON = -60.2160
ARCHIVO_CSV = 'meteo_daily.csv'

def actualizar_pronostico():
    url = "https://api.open-meteo.com/v1/forecast"
    
    # ESTRATEGIA: Pedimos 14 días para ATRÁS (datos consolidados) y 7 para ADELANTE (pronóstico)
    params = {
        "latitude": LAT,
        "longitude": LON,
        "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum"],
        "timezone": "America/Argentina/Buenos_Aires",
        "past_days": 14,
        "forecast_days": 10
    }
    
    print("Consultando a Open-Meteo (Ventana Híbrida: -14d a +7d) ...")
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            print(f"Error en la API: {response.text}")
            sys.exit(1)
    except Exception as e:
        print(f"Fallo de conexión: {e}")
        sys.exit(1)
        
    data = response.json()
    
    # DataFrame con la ventana móvil corregida y proyectada
    df_nuevo = pd.DataFrame({
        'Fecha': data['daily']['time'],
        'TMAX': data['daily']['temperature_2m_max'],
        'TMIN': data['daily']['temperature_2m_min'],
        'Prec': data['daily']['precipitation_sum']
    })
    
    # Asegurar el tipado de fecha para evitar fallos de merge de strings
    df_nuevo['Fecha'] = pd.to_datetime(df_nuevo['Fecha'])
    
    if df_nuevo.isnull().values.any():
        print("ADVERTENCIA: La API devolvió algunos nulos. Aplicando ffill básico.")
        df_nuevo = df_nuevo.ffill()

    if os.path.exists(ARCHIVO_CSV):
        print(f"Leyendo historial desde {ARCHIVO_CSV}...")
        df_historico = pd.read_csv(ARCHIVO_CSV)
        df_historico['Fecha'] = pd.to_datetime(df_historico['Fecha'])
        
        # Combinamos las series
        df_final = pd.concat([df_historico, df_nuevo], ignore_index=True)
        
        # Al conservar el 'last', los 14 días pasados que trajo la API (ya corregidos)
        # pisan los pronósticos viejos que habías guardado en ejecuciones anteriores.
        df_final = df_final.drop_duplicates(subset=['Fecha'], keep='last')
        df_final = df_final.sort_values(by='Fecha').reset_index(drop=True)
    else:
        print(f"No se encontró {ARCHIVO_CSV}, creando uno nuevo...")
        df_final = df_nuevo

    # Formatear la fecha antes de guardar para mantener limpio el CSV limpio
    df_final['Fecha'] = df_final['Fecha'].dt.strftime('%Y-%m-%Y' if '%Y-%m-%d' else '%Y-%m-%d')
    
    df_final.to_csv(ARCHIVO_CSV, index=False)
    print("¡Base de datos meteorológica actualizada con éxito!")
    print(df_final.tail(12))

if __name__ == "__main__":
    actualizar_pronostico()

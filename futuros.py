import requests
import time
from datetime import datetime, timedelta
import pandas as pd

# Configuración
API_KEY = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"
BASE_URL = f"https://api.coinalyze.net/v1/"
SYMBOLS = ["BTCUSDT_PERP.A"]  # Puedes añadir más símbolos aquí
TEMPORALIDADES = ["1hour", "4hour", "daily"]  # Temporalidades a procesar
RANGO_DIAS = 30  # Rango de días hacia atrás

def log_mensaje(mensaje, nivel="INFO"):
    """Imprime un mensaje en consola con formato."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{nivel}] {mensaje}")

def fetch_data(endpoint, symbol, interval, from_timestamp, to_timestamp, max_retries=3):
    """Solicita datos de Coinalyze y maneja errores."""
    url = f"{BASE_URL}{endpoint}?api_key={API_KEY}&symbols={symbol}&interval={interval}&from={from_timestamp}&to={to_timestamp}"
    
    for intento in range(max_retries):
        try:
            log_mensaje(f"Realizando solicitud a la API: {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # Lanza un error si el código HTTP no es 200
            data = response.json()
            if not data or len(data) == 0:
                log_mensaje(f"No se encontraron datos para {symbol} en {interval}.", nivel="WARNING")
                return None
            log_mensaje(f"Datos recibidos correctamente para {symbol} ({interval}).")
            return data
        except requests.exceptions.RequestException as e:
            log_mensaje(f"Error en la solicitud: {e}. Reintentando... ({intento + 1}/{max_retries})", nivel="ERROR")
            time.sleep(5)  # Esperar antes de reintentar
        except Exception as e:
            log_mensaje(f"Error inesperado: {e}", nivel="CRITICAL")
            break
    log_mensaje(f"Fallo después de {max_retries} intentos para {symbol} ({interval}).", nivel="ERROR")
    return None

def procesar_datos(temporalidad):
    """Procesa los datos para una temporalidad específica."""
    log_mensaje(f"Procesando temporalidad: {temporalidad}...")

    ahora = datetime.utcnow()
    desde = int((ahora - timedelta(days=RANGO_DIAS)).timestamp())
    hasta = int(ahora.timestamp())

    datos_totales = []

    for symbol in SYMBOLS:
        log_mensaje(f"Obteniendo datos para {symbol} en temporalidad {temporalidad}...")

        # Solicitar datos desde diferentes endpoints
        ohlcv = fetch_data("ohlcv-history", symbol, temporalidad, desde, hasta)
        open_interest = fetch_data("open-interest-history", symbol, temporalidad, desde, hasta)
        long_short_ratio = fetch_data("long-short-ratio-history", symbol, temporalidad, desde, hasta)
        liquidation = fetch_data("liquidation-history", symbol, temporalidad, desde, hasta)
        funding_rate = fetch_data("funding-rate-history", symbol, temporalidad, desde, hasta)

        # Validar que se hayan obtenido todos los datos
        if not ohlcv or not open_interest or not long_short_ratio or not liquidation or not funding_rate:
            log_mensaje(f"Faltan datos para {symbol} ({temporalidad}). Omitiendo.", nivel="WARNING")
            continue

        # Procesar datos y convertirlos a DataFrame
        log_mensaje(f"Procesando datos recibidos para {symbol} ({temporalidad})...")
        try:
            df_ohlcv = pd.DataFrame(ohlcv)
            df_open_interest = pd.DataFrame(open_interest)
            df_long_short = pd.DataFrame(long_short_ratio)
            df_liquidation = pd.DataFrame(liquidation)
            df_funding = pd.DataFrame(funding_rate)

            # Unir los datos en un único DataFrame
            final_df = (
                df_ohlcv
                .merge(df_open_interest, on="timestamp", how="left")
                .merge(df_long_short, on="timestamp", how="left")
                .merge(df_liquidation, on="timestamp", how="left")
                .merge(df_funding, on="timestamp", how="left")
            )
            final_df["fecha_hora"] = pd.to_datetime(final_df["timestamp"], unit="s")
            final_df = final_df.sort_values(by="fecha_hora")
            datos_totales.append(final_df)
            log_mensaje(f"Datos procesados correctamente para {symbol} ({temporalidad}).")
        except Exception as e:
            log_mensaje(f"Error al procesar datos para {symbol} ({temporalidad}): {e}", nivel="ERROR")
    
    if datos_totales:
        # Concatenar todos los datos procesados
        todos_datos_df = pd.concat(datos_totales, ignore_index=True)
        log_mensaje(f"Datos finalizados para temporalidad {temporalidad}.")
        return todos_datos_df
    else:
        log_mensaje(f"No se encontraron datos útiles para la temporalidad {temporalidad}.", nivel="WARNING")
        return None

if __name__ == "__main__":
    for temporalidad in TEMPORALIDADES:
        try:
            datos = procesar_datos(temporalidad)
            if datos is not None:
                archivo = f"datos_{temporalidad}.csv"
                datos.to_csv(archivo, index=False)
                log_mensaje(f"Datos guardados en el archivo: {archivo}")
        except Exception as e:
            log_mensaje(f"Error general en el procesamiento de {temporalidad}: {e}", nivel="CRITICAL")

import threading
import requests
import pandas as pd
import time
import datetime
import os
import talib
import logging
import json

# Configuración del logging
logging.basicConfig(filename='btc_analisis.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Frecuencia de actualización (en segundos)
frecuencia_actualizacion = 60 * 5  # Actualiza cada 5 minutos

# Función para obtener datos de Kraken
def obtener_ohlc_kraken(pair, interval, since=None):
    url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval={interval}"
    if since:
        url += f"&since={since}"
    retries = 3
    for i in range(retries):
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if data['error']:
                print(f"Error de Kraken: {data['error']}")
                return None
            if not data['result']:
                print("No hay datos disponibles para este intervalo.")
                return None
            df = pd.DataFrame(data['result'][pair], columns=['time', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'])
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df = df.set_index('time')
            df = df.astype(float)
            return df
        except requests.exceptions.RequestException as e:
            print(f"Error al obtener datos de Kraken: {e}")
            time.sleep(5)
    print("Número máximo de reintentos alcanzado.")
    return None

# Función para guardar el DataFrame
def guardar_dataframe(df, filename):
    if df is not None:
        try:
            df.to_csv(filename)
            print(f"Datos guardados en {filename}")
        except Exception as e:
            print(f"Error al guardar el archivo: {e}")
    else:
        print("No hay datos para guardar.")

# Función para agregar indicadores técnicos

        

def actualizar_archivos(pair, carpeta="datos_BTC"):
    temporalidades = {
        15: "15m",
        60: "1h",
        240: "4h",
        1440: "1d"
    }
    for interval, filename_suffix in temporalidades.items():
        filename = os.path.join(carpeta, f"{pair}_{filename_suffix}.csv")
        try:
            df = pd.read_csv(filename, index_col='time', parse_dates=True)
        except FileNotFoundError:
            print(f"Archivo {filename} no encontrado. Creando archivo nuevo.")
            df = pd.DataFrame()
        df = actualizar_dataframe(df, pair, interval)
        # ELIMINA ESTA LÍNEA: df = agregar_indicadores(df)
        guardar_dataframe(df, filename)
      
def calcular_rsi(df):
    try:
        df['RSI'] = talib.RSI(df['close'], timeperiod=14)
        return df
    except Exception as e:
        logging.error(f"Error al calcular RSI: {e}")
        return df

def calcular_bandas_bollinger(df):
    try:
        upperband, middleband, lowerband = talib.BBANDS(df['close'], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
        df['BB_upper'] = upperband
        df['BB_middle'] = middleband
        df['BB_lower'] = lowerband
        return df
    except Exception as e:
        logging.error(f"Error al calcular Bandas de Bollinger: {e}")
        return df

def calcular_macd(df):
    try:
        macd, macdsignal, macdhist = talib.MACD(df['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        df['MACD'] = macd
        df['MACD_signal'] = macdsignal
        df['MACD_hist'] = macdhist
        return df
    except Exception as e:
        logging.error(f"Error al calcular MACD: {e}")
        return df

def calcular_hulma(df):
    try:
        def hull_moving_average(series, period):
            half_length = period // 2
            sqrt_length = int(period**0.5)
            wma_half = talib.WMA(series, timeperiod=half_length)
            wma_full = talib.WMA(series, timeperiod=period)
            hull_ma = talib.WMA(2 * wma_half - wma_full, timeperiod=sqrt_length)
            return hull_ma
        df['HMA'] = hull_moving_average(df['close'], period=14)
        return df
    except Exception as e:
        logging.error(f"Error al calcular HMA: {e}")
        return df
        
# Función para actualizar un DataFrame con nuevos datos

def actualizar_dataframe(df, pair, interval):
    if df.empty:
        since = None
    else:
        last_timestamp = int(df.index[-1].timestamp()) + 1
        since = last_timestamp

    nuevos_datos = obtener_ohlc_kraken(pair, interval, since)

    if nuevos_datos is not None:
        if not nuevos_datos.empty:
            df_actualizado = pd.concat([df, nuevos_datos])
            df_actualizado = df_actualizado[~df_actualizado.index.duplicated(keep='last')]
            return df_actualizado
        else:
            print(f"No hay nuevos datos para el intervalo {interval}")
            return df
    else:
        print(f"Error al obtener nuevos datos para el intervalo {interval}")
        return df

# Función para procesar archivos CSV
def encontrar_minimos_maximos(precios, ventana=3):
    """Encuentra mínimos y máximos locales en una serie de precios."""
    minimos = []
    maximos = []
    for i in range(ventana, len(precios) - ventana):
        # Verificar mínimo local
        if all(precios[i] < precios[i - j] for j in range(1, ventana + 1)) and \
           all(precios[i] < precios[i + j] for j in range(1, ventana + 1)):
            minimos.append((i, precios[i]))
        # Verificar máximo local
        if all(precios[i] > precios[i - j] for j in range(1, ventana + 1)) and \
           all(precios[i] > precios[i + j] for j in range(1, ventana + 1)):
            maximos.append((i, precios[i]))
    return minimos, maximos

def detectar_tendencia(minimos, maximos):
    """Detecta la tendencia del precio basándose en mínimos y máximos."""
    if len(minimos) < 2 or len(maximos) < 2:
        return "Indefinido"

    # Convertir las listas de tuplas a listas de precios para facilitar la comparación
    precios_minimos = [minimo[1] for minimo in minimos]
    precios_maximos = [maximo[1] for maximo in maximos]

    minimos_crecientes = all(precios_minimos[i] < precios_minimos[i + 1] for i in range(len(precios_minimos) - 1))
    maximos_crecientes = all(precios_maximos[i] < precios_maximos[i + 1] for i in range(len(precios_maximos) - 1))

    minimos_decrecientes = all(precios_minimos[i] > precios_minimos[i + 1] for i in range(len(precios_minimos) - 1))
    maximos_decrecientes = all(precios_maximos[i] > precios_maximos[i + 1] for i in range(len(precios_maximos) - 1))

    if minimos_crecientes and maximos_crecientes:
        return "Alcista"
    elif minimos_decrecientes and maximos_decrecientes:
        return "Bajista"
    elif minimos_crecientes and maximos_decrecientes:
        return "Triángulo Ascendente" #Esta condición es improbable, pero se deja por consistencia
    elif minimos_decrecientes and maximos_crecientes:
        return "Triángulo Descendente" #Esta condición es improbable, pero se deja por consistencia
    else:
        return "Lateralidad"

def analizar_precio(df):
    """Analiza el precio y la tendencia."""
    try:
        precios = df['close'].values.tolist()
        minimos, maximos = encontrar_minimos_maximos(precios)
        tendencia = detectar_tendencia(minimos, maximos)
        logging.info(f"Análisis de precio: Tendencia detectada: {tendencia}")
        return tendencia
    except Exception as e:
        logging.exception(f"Error al analizar el precio: {e}")
        return "Error en el análisis"

def analizar_indicadores(df):
    """Analiza los indicadores técnicos y el VWAP."""
    try:
        ultimo_rsi = df['RSI'].iloc[-1] if not df['RSI'].empty else "Sin datos"
        logging.info(f"Análisis de indicadores: Último RSI: {ultimo_rsi}")

        if not df['BB_UPPER'].empty and not df['BB_LOWER'].empty and not df['close'].empty:
            if df['close'].iloc[-1] > df['BB_UPPER'].iloc[-1]:
                logging.info("Precio cerca de la banda superior de Bollinger.")
            elif df['close'].iloc[-1] < df['BB_LOWER'].iloc[-1]:
                logging.info("Precio cerca de la banda inferior de Bollinger.")

        ultimo_macd = df['MACD'].iloc[-1] if not df['MACD'].empty else "Sin datos"
        ultimo_macd_signal = df['MACD_signal'].iloc[-1] if not df['MACD_signal'].empty else "Sin datos"
        logging.info(f"Último MACD: {ultimo_macd}, Señal: {ultimo_macd_signal}")

        ultimo_hulma = df['HULMA'].iloc[-1] if not df['HULMA'].empty else "Sin datos"
        logging.info(f"Último HULMA: {ultimo_hulma}")

        ultimo_vwap = df['vwap'].iloc[-1] if not df['vwap'].empty else "Sin datos"
        logging.info(f"Último VWAP: {ultimo_vwap}")
    except Exception as e:
        logging.exception(f"Error al analizar los indicadores: {e}")

def procesar_csv(pair, filename_suffix, carpeta="datos_BTC"):
    """Procesa un archivo CSV, calculando indicadores y realizando análisis."""
    nombre_archivo = f"{pair}_{filename_suffix}.csv"
    ruta_completa = os.path.join(carpeta, nombre_archivo)
    try:
        df = pd.read_csv(ruta_completa, index_col='time', parse_dates=True)
        df['close'] = df['close'].astype(float)
        df['vwap'] = df['vwap'].astype(float)

        # Calcular indicadores (USANDO LAS NUEVAS FUNCIONES)
        df = calcular_rsi(df)
        df = calcular_bandas_bollinger(df)
        df = calcular_macd(df)
        df = calcular_hulma(df)

        # Realizar análisis
        analizar_precio(df)
        analizar_indicadores(df)

        guardar_dataframe(df, ruta_completa)
        logging.info(f"Archivo {nombre_archivo} procesado y guardado correctamente.")

    except FileNotFoundError:
        logging.error(f"Archivo no encontrado: {ruta_completa}")
    except Exception as e:
        logging.exception(f"Error al procesar {ruta_completa}: {e}")

def detectar_divergencias_rsi(df):
    """Detecta divergencias alcistas y bajistas en el RSI."""
    divergencias_alcistas = []
    divergencias_bajistas = []
    for i in range(2, len(df)):
        if df['close'][i] < df['close'][i-1] and df['RSI'][i] > df['RSI'][i-1]:
            divergencias_alcistas.append((df.index[i], df['close'][i], df['RSI'][i]))
        if df['close'][i] > df['close'][i-1] and df['RSI'][i] < df['RSI'][i-1]:
            divergencias_bajistas.append((df.index[i], df['close'][i], df['RSI'][i]))
    return divergencias_alcistas, divergencias_bajistas

def detectar_divergencias_macd(df):
    """Detecta divergencias alcistas y bajistas en el MACD."""
    divergencias_alcistas = []
    divergencias_bajistas = []
    for i in range(2, len(df)):
        if df['close'][i] < df['close'][i-1] and df['MACD'][i] > df['MACD'][i-1]:
            divergencias_alcistas.append((df.index[i], df['close'][i], df['MACD'][i]))
        if df['close'][i] > df['close'][i-1] and df['MACD'][i] < df['MACD'][i-1]:
            divergencias_bajistas.append((df.index[i], df['close'][i], df['MACD'][i]))
    return divergencias_alcistas, divergencias_bajistas

def analizar_rsi(df):
    try:
        df = calcular_rsi(df)
        divergencias_alcistas, divergencias_bajistas = detectar_divergencias_rsi(df) # Usa tu función existente para RSI
        if divergencias_alcistas:
            ultima_divergencia = divergencias_alcistas[-1] # Obtiene la última divergencia alcista
            fecha, precio, rsi = ultima_divergencia
            print(f"Última divergencia alcista en RSI detectada en: {fecha} (Precio: {precio}, RSI: {rsi}).")
            logging.info(f"Última divergencia alcista en RSI detectada en: {fecha} (Precio: {precio}, RSI: {rsi}).")
        else:
            print("No se encontraron divergencias alcistas en RSI.")
            logging.info("No se encontraron divergencias alcistas en RSI.")

        if divergencias_bajistas:
            ultima_divergencia = divergencias_bajistas[-1] # Obtiene la última divergencia bajista
            fecha, precio, rsi = ultima_divergencia
            print(f"Última divergencia bajista en RSI detectada en: {fecha} (Precio: {precio}, RSI: {rsi}).")
            logging.info(f"Última divergencia bajista en RSI detectada en: {fecha} (Precio: {precio}, RSI: {rsi}).")
        else:
            print("No se encontraron divergencias bajistas en RSI.")
            logging.info("No se encontraron divergencias bajistas en RSI.")
        return df
    except Exception as e:
        logging.error(f"Error al analizar RSI: {e}")
        print(f"Error al analizar RSI: {e}")
        return df

def analizar_macd(df):
    try:
        df = calcular_macd(df)
        divergencias_alcistas, divergencias_bajistas = detectar_divergencias_macd(df)  # Usa tu función existente para MACD
        if divergencias_alcistas:
            ultima_divergencia = divergencias_alcistas[-1]  # Obtiene la última divergencia alcista
            fecha, precio, macd = ultima_divergencia
            print(f"Última divergencia alcista en MACD detectada en: {fecha} (Precio: {precio}, MACD: {macd}).")
            logging.info(f"Última divergencia alcista en MACD detectada en: {fecha} (Precio: {precio}, MACD: {macd}).")
        else:
            print("No se encontraron divergencias alcistas en MACD.")
            logging.info("No se encontraron divergencias alcistas en MACD.")

        if divergencias_bajistas:
            ultima_divergencia = divergencias_bajistas[-1]  # Obtiene la última divergencia bajista
            fecha, precio, macd = ultima_divergencia
            print(f"Última divergencia bajista en MACD detectada en: {fecha} (Precio: {precio}, MACD: {macd}).")
            logging.info(f"Última divergencia bajista en MACD detectada en: {fecha} (Precio: {precio}, MACD: {macd}).")
        else:
            print("No se encontraron divergencias bajistas en MACD.")
            logging.info("No se encontraron divergencias bajistas en MACD.")
        return df
    except Exception as e:
        logging.error(f"Error al analizar MACD: {e}")
        print(f"Error al analizar MACD: {e}")
        return df

def analizar_bandas_bollinger(df):
    """Analiza las Bandas de Bollinger."""
    if df['BB_upper'].empty or df['BB_lower'].empty or df['close'].empty:
        return "Sin datos de Bandas de Bollinger"

    precio_cerca_superior = df['close'].iloc[-1] > df['BB_upper'].iloc[-1]
    precio_cerca_inferior = df['close'].iloc[-1] < df['BB_lower'].iloc[-1]
    
    analisis = ""
    if precio_cerca_superior:
        analisis = "Precio cerca de la banda superior de Bollinger."
    elif precio_cerca_inferior:
        analisis = "Precio cerca de la banda inferior de Bollinger."
    else:
        analisis = "Precio dentro de las Bandas de Bollinger."
    return analisis

def analizar_volumen(df):
    """Analiza el volumen en relación al precio."""
    if df['volume'].empty or df['close'].empty:
        return "Sin datos de Volumen"

    volumen_actual = df['volume'].iloc[-1]
    variacion_precio = (df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2] if len(df) > 1 else 0
    analisis = f"Volumen: {volumen_actual:.2f}. "
    if abs(variacion_precio) > 0.02 and volumen_actual > df['volume'].mean(): #Movimiento significativo del 2% con volumen por encima de la media
      analisis += "Movimiento de precio significativo con volumen alto."
    return analisis

def generar_resumen(df, filename_suffix):
    """Genera un resumen del análisis técnico."""
    tendencia = analizar_precio(df)
    analisis_rsi = analizar_rsi(df)
    analisis_macd = analizar_macd(df)
    analisis_bb = analizar_bandas_bollinger(df)
    analisis_volumen = analizar_volumen(df)
    ultimo_vwap = df['vwap'].iloc[-1] if not df['vwap'].empty else "Sin datos"

    resumen = f"Resumen Técnico ({filename_suffix}):\n"
    resumen += f"Tendencia: {tendencia}\n"
    resumen += f"VWAP: {ultimo_vwap}\n"
    resumen += f"{analisis_rsi}\n"
    resumen += f"{analisis_macd}\n"
    resumen += f"{analisis_bb}\n"
    resumen += f"{analisis_volumen}\n"
    return resumen



def analizar_temporalidad(pair, carpeta, interval, filename_suffix):
    """Función principal que analiza una temporalidad específica."""
    logging.info(f"Analizando {filename_suffix}...")
    actualizar_archivos(pair, carpeta)
    nombre_archivo = f"{pair}_{filename_suffix}.csv"
    ruta_completa = os.path.join(carpeta, nombre_archivo)
    try:
        df = pd.read_csv(ruta_completa, index_col='time', parse_dates=True)
        df['close'] = df['close'].astype(float)
        df['vwap'] = df['vwap'].astype(float)

        # Calcular indicadores
        df = calcular_rsi(df)
        df = calcular_bandas_bollinger(df)
        df = calcular_macd(df)
        df = calcular_hulma(df)

        resumen = generar_resumen(df, filename_suffix)
        # Imprimir el resumen COMPLETO en la consola:
        print(resumen)  # <--- Esta línea es la clave
        logging.info(f"Resumen generado para {filename_suffix}: {resumen}")  # Loggea el resumen completo

    except FileNotFoundError:
        logging.error(f"Archivo no encontrado: {ruta_completa}")
    except Exception as e:
        logging.exception(f"Error al procesar {ruta_completa}: {e}")
      
def calcular_tiempo_hasta_proximo_cierre(intervalo_segundos):
    """Calculates the time in seconds until the next candle close."""
    ahora = datetime.datetime.now(datetime.UTC)  # Fix for deprecation warning
    minutos_actuales = ahora.minute
    segundos_actuales = ahora.second
    segundos_hasta_cierre = (intervalo_segundos - (minutos_actuales * 60 + segundos_actuales) % intervalo_segundos)
    return segundos_hasta_cierre

def bucle_principal(pair, carpeta, intervalos):
    while True:
        for intervalo_segundos, filename_suffix in intervalos.items():
            tiempo_espera = calcular_tiempo_hasta_proximo_cierre(intervalo_segundos)
            print(f"Esperando {tiempo_espera} segundos para {filename_suffix}...") # Mensaje en la consola
            logging.info(f"Esperando {tiempo_espera} segundos hasta el próximo cierre de vela de {filename_suffix}...")
            time.sleep(tiempo_espera)

            print(f"Analizando {filename_suffix}...") # Mensaje en la consola
            logging.info(f"Cierre de vela de {filename_suffix}. Iniciando análisis...")
            analizar_temporalidad(pair, carpeta, intervalo_segundos, filename_suffix)

        print("Ciclo completo. Esperando el próximo ciclo...") # Mensaje en la consola
        logging.info("Ciclo completo. Esperando el próximo ciclo...")

def main():
    pair = "XBTUSDT"
    carpeta_datos = "datos_BTC"
    os.makedirs(carpeta_datos, exist_ok=True)
    intervalos = {
        15 * 60: "15m",
        60 * 60: "1h",
        4 * 60 * 60: "4h",
        24 * 60 * 60: "1d"
    }

    hilo_bucle = threading.Thread(target=bucle_principal, args=(pair, carpeta_datos, intervalos))
    hilo_bucle.daemon = True
    hilo_bucle.start()

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()

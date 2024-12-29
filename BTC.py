import threading
import requests
import pandas as pd
import time
import datetime
import os
import talib
import logging
import json
from scipy.signal import argrelextrema

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
    print(f"URL de la solicitud a Kraken: {url}") #Imprime la url
    logging.info(f"URL de la solicitud a Kraken: {url}") #Imprime la url en el log

    retries = 3
    for i in range(retries):
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if data['error']:
                print(f"Error de Kraken: {data['error']}")
                logging.error(f"Error de Kraken: {data['error']}")
                return None
            if not data['result']:
                print("No hay datos disponibles para este intervalo.")
                logging.info("No hay datos disponibles para este intervalo.")
                return None
            df = pd.DataFrame(data['result'][pair], columns=['time', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'])
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df = df.set_index('time')
            df = df.astype(float)
            return df
        except requests.exceptions.RequestException as e:
            print(f"Error al obtener datos de Kraken: {e}")
            logging.error(f"Error al obtener datos de Kraken: {e}")
            time.sleep(5)
    print("Número máximo de reintentos alcanzado.")
    logging.error("Número máximo de reintentos alcanzado.")
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
        df['HMA'] = hull_moving_average(df['close'], period=12)
        return df
    except Exception as e:
        logging.error(f"Error al calcular HMA: {e}")
        return df
        
# Función para actualizar un DataFrame con nuevos datos
def actualizar_dataframe(df, pair, interval_seconds): # Recibe el intervalo en segundos
    if df.empty:
        since = None
    else:
        last_timestamp = int(df.index[-1].timestamp()) + 1
        since = last_timestamp

    nuevos_datos = obtener_ohlc_kraken(pair, interval_seconds, since) # Usa interval_seconds

    if nuevos_datos is not None:
        if not nuevos_datos.empty:
            df_actualizado = pd.concat([df, nuevos_datos])
            df_actualizado = df_actualizado.sort_index() # Ordenar el DataFrame por índice (timestamp)
            df_actualizado = df_actualizado[~df_actualizado.index.duplicated(keep='last')]
            return df_actualizado
        else:
            print(f"No hay nuevos datos para el intervalo {interval_seconds}") # Imprime el intervalo en segundos
            return df
    else:
        print(f"Error al obtener nuevos datos para el intervalo {interval_seconds}") # Imprime el intervalo en segundos
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

def analizar_tendencia(minimos, maximos, min_puntos=3): # Añadido min_puntos
    """Analiza la tendencia con más detalle, incluyendo triángulos y fuerza."""
    if len(minimos) < min_puntos or len(maximos) < min_puntos:
        return {"tipo": "Indefinido", "fuerza": "N/A"}

    precios_minimos = [minimo[1] for minimo in minimos]
    tiempos_minimos = [minimo[0] for minimo in minimos]
    precios_maximos = [maximo[1] for maximo in maximos]
    tiempos_maximos = [maximo[0] for maximo in maximos]
    
    # Calcular pendientes usando regresión lineal
    pendiente_minimos, _ = np.polyfit(tiempos_minimos, precios_minimos, 1)
    pendiente_maximos, _ = np.polyfit(tiempos_maximos, precios_maximos, 1)

    minimos_crecientes = pendiente_minimos > 0
    maximos_crecientes = pendiente_maximos > 0
    minimos_decrecientes = pendiente_minimos < 0
    maximos_decrecientes = pendiente_maximos < 0
    
    #Umbrales para la fuerza de la tendencia
    umbral_fuerte = 0.5
    umbral_moderada = 0.1

    fuerza_minimos = "N/A"
    fuerza_maximos = "N/A"

    if abs(pendiente_minimos) > umbral_fuerte: fuerza_minimos = "Fuerte"
    elif abs(pendiente_minimos) > umbral_moderada: fuerza_minimos = "Moderada"
    elif abs(pendiente_minimos) > 0 : fuerza_minimos = "Debil"

    if abs(pendiente_maximos) > umbral_fuerte: fuerza_maximos = "Fuerte"
    elif abs(pendiente_maximos) > umbral_moderada: fuerza_maximos = "Moderada"
    elif abs(pendiente_maximos) > 0 : fuerza_maximos = "Debil"

    if minimos_crecientes and maximos_crecientes:
        return {"tipo": "Alcista", "fuerza": f"Minimos: {fuerza_minimos}, Maximos: {fuerza_maximos}"}
    elif minimos_decrecientes and maximos_decrecientes:
        return {"tipo": "Bajista", "fuerza": f"Minimos: {fuerza_minimos}, Maximos: {fuerza_maximos}"}
    #Verificacion de triangulos
    elif minimos_crecientes and maximos_decrecientes:
        return {"tipo": "Triángulo Ascendente", "fuerza": "N/A"}
    elif minimos_decrecientes and maximos_crecientes:
        return {"tipo": "Triángulo Descendente", "fuerza": "N/A"}
    else:
        return {"tipo": "Lateralidad", "fuerza": "N/A"}



def procesar_csv(pair, filename_suffix, carpeta="datos_BTC"):
    """Procesa un archivo CSV, calculando indicadores, análisis y generando informe."""
    nombre_archivo = f"{pair}_{filename_suffix}.csv"
    ruta_completa = os.path.join(carpeta, nombre_archivo)

    try:
        # LECTURA DEL CSV CON MANEJO DE TIPOS DE DATOS Y ERRORES
        df = pd.read_csv(ruta_completa, index_col='time', parse_dates=True,
                           dtype={'open': np.float64, 'high': np.float64, 'low': np.float64,
                                  'close': np.float64, 'vwap': np.float64, 'volume': np.float64})

        # LIMPIEZA DE DATOS (CRUCIAL PARA EVITAR ERRORES)
        df.dropna(inplace=True)
        cols_a_limpiar = ['open', 'high', 'low', 'close', 'vwap', 'volume']
        for col in cols_a_limpiar:
            if df[col].dtype == object:
                df[col] = df[col].str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(inplace=True)
        df = df[df['volume'] != 0]
        df = df[~df.index.duplicated(keep='last')]

        # CALCULAR INDICADORES (DESPUÉS DE LA LIMPIEZA)
        df = calcular_rsi(df)
        df = calcular_bandas_bollinger(df)
        df = calcular_macd(df)
        df = calcular_hulma(df)

        # Obtener datos para el informe
        ultimo_precio = df['close'].iloc[-1]
        precios = df['close'].values.tolist()
        minimos, maximos = encontrar_minimos_maximos(precios)
        tendencia = analizar_tendencia(minimos, maximos)
        rsi_data = analizar_rsi(df)
        macd_data = analizar_macd(df)
        bandas_bollinger_analisis = analizar_bandas_bollinger(df)
        ultimo_hma = df['HMA'].iloc[-1] if not df['HMA'].empty else 0
        ultimo_vwap = df['vwap'].iloc[-1] if not df['vwap'].empty else 0
        analisis_volumen = analizar_volumen(df)

        # Calcular rangos de compra
        maximo_reciente = df['high'].rolling(window=14).max().iloc[-1] if len(df) >= 14 else df['high'].max()
        minimo_reciente = df['low'].rolling(window=14).min().iloc[-1] if len(df) >= 14 else df['low'].min()
        rangos_compra = calcular_rangos_compra(tendencia, maximo_reciente, minimo_reciente)

        # Generar consejos de trading
        consejos = generar_consejos_trading(ultimo_precio, tendencia, rsi_data, macd_data, bandas_bollinger_analisis, ultimo_hma, analisis_volumen)

        # VWAP mensaje
        if pd.isna(ultimo_vwap) or ultimo_vwap == 0:
            vwap_mensaje = "VWAP no disponible."
        else:
            vwap_mensaje = f"VWAP: {ultimo_vwap:.2f}"

        # Generar el informe personalizado
        resumen_telegram = generar_informe_personalizado(ultimo_precio, tendencia, rsi_data, macd_data, bandas_bollinger_analisis, ultimo_hma, vwap_mensaje, analisis_volumen, consejos, rangos_compra, filename_suffix)
        print(resumen_telegram)
        logging.info(f"Resumen para Telegram generado para {filename_suffix}: {resumen_telegram}")

        guardar_dataframe(df, ruta_completa)
        logging.info(f"Archivo {nombre_archivo} procesado y guardado correctamente.")

    except FileNotFoundError:
        logging.error(f"Archivo no encontrado: {ruta_completa}")
    except pd.errors.ParserError as e:
        logging.error(f"Error al analizar el CSV: {e}. Revisa el formato del archivo.")
        print(f"Error al analizar el CSV: {e}. Revisa el formato del archivo.")
    except Exception as e:
        logging.exception(f"Error al procesar {ruta_completa}: {e}")
import pandas as pd
import logging

def detectar_divergencias_rsi(df, periodo=10, min_diff=2): # Añadido min_diff
    """Detecta divergencias alcistas y bajistas en el RSI, enfocándose en la última."""
    try:
        if 'RSI' not in df.columns or df['RSI'].isnull().all() or len(df) < periodo:
            return {"tipo": None, "fecha": None, "precio": None, "rsi": None, "mensaje": "Datos insuficientes para detectar divergencias."}

        df_periodo = df.iloc[-periodo:].copy() # Importante usar .copy()

        # Encontrar picos y valles locales
        maximos_precio_indices = argrelextrema(df_periodo['close'].values, np.greater)[0]
        minimos_precio_indices = argrelextrema(df_periodo['close'].values, np.less)[0]
        maximos_rsi_indices = argrelextrema(df_periodo['RSI'].values, np.greater)[0]
        minimos_rsi_indices = argrelextrema(df_periodo['RSI'].values, np.less)[0]

        divergencia = {"tipo": None, "fecha": None, "precio": None, "rsi": None, "mensaje": "No se detectaron divergencias en el periodo analizado."}

        # Buscar divergencias alcistas
        for i_precio in minimos_precio_indices:
          for i_rsi in minimos_rsi_indices:
            if i_precio < i_rsi:
              if df_periodo['close'].iloc[i_precio] > df_periodo['close'].iloc[i_rsi] and df_periodo['RSI'].iloc[i_precio] < df_periodo['RSI'].iloc[i_rsi] and abs(df_periodo['close'].iloc[i_precio]-df_periodo['close'].iloc[i_rsi]) >= min_diff:
                divergencia["tipo"] = "alcista"
                divergencia["fecha"] = df_periodo.index[i_rsi]
                divergencia["precio"] = df_periodo['close'].iloc[i_rsi]
                divergencia["rsi"] = df_periodo['RSI'].iloc[i_rsi]
                divergencia["mensaje"] = f"Posible divergencia alcista detectada el {divergencia['fecha'].strftime('%Y-%m-%d')}. Precio: {divergencia['precio']:.2f}, RSI: {divergencia['rsi']:.2f}. Esto podría indicar una posible reversión alcista."
                break
          else:
            continue
          break
        
        # Buscar divergencias bajistas
        for i_precio in maximos_precio_indices:
          for i_rsi in maximos_rsi_indices:
            if i_precio < i_rsi:
              if df_periodo['close'].iloc[i_precio] < df_periodo['close'].iloc[i_rsi] and df_periodo['RSI'].iloc[i_precio] > df_periodo['RSI'].iloc[i_rsi] and abs(df_periodo['close'].iloc[i_precio]-df_periodo['close'].iloc[i_rsi]) >= min_diff:
                divergencia["tipo"] = "bajista"
                divergencia["fecha"] = df_periodo.index[i_rsi]
                divergencia["precio"] = df_periodo['close'].iloc[i_rsi]
                divergencia["rsi"] = df_periodo['RSI'].iloc[i_rsi]
                divergencia["mensaje"] = f"Posible divergencia bajista detectada el {divergencia['fecha'].strftime('%Y-%m-%d')}. Precio: {divergencia['precio']:.2f}, RSI: {divergencia['rsi']:.2f}. Esto podría indicar una posible reversión bajista."
                break
          else:
            continue
          break
        
        return divergencia

    except Exception as e:
        logging.exception(f"Error al detectar divergencias en el RSI: {e}")


def detectar_divergencias_macd(df, periodo=10, min_diff=0.1):
    """Detecta divergencias alcistas y bajistas en el MACD."""
    try:
        if 'MACD' not in df.columns or 'MACD_signal' not in df.columns or df['MACD'].isnull().all() or len(df) < periodo:
            return {"tipo": None, "fecha": None, "macd": None, "signal": None, "mensaje": "Datos insuficientes para detectar divergencias."}

        df_periodo = df.iloc[-periodo:].copy()

        maximos_precio_indices = argrelextrema(df_periodo['close'].values, np.greater)[0]
        minimos_precio_indices = argrelextrema(df_periodo['close'].values, np.less)[0]
        maximos_macd_indices = argrelextrema(df_periodo['MACD'].values, np.greater)[0]
        minimos_macd_indices = argrelextrema(df_periodo['MACD'].values, np.less)[0]
        
        divergencia = {"tipo": None, "fecha": None, "macd": None, "signal": None, "mensaje": "No se detectaron divergencias en el periodo analizado."}

        for i_precio in minimos_precio_indices:
          for i_macd in minimos_macd_indices:
            if i_precio < i_macd:
              if df_periodo['close'].iloc[i_precio] > df_periodo['close'].iloc[i_macd] and df_periodo['MACD'].iloc[i_precio] < df_periodo['MACD'].iloc[i_macd] and abs(df_periodo['MACD'].iloc[i_precio]-df_periodo['MACD'].iloc[i_macd]) >= min_diff:
                divergencia["tipo"] = "alcista"
                divergencia["fecha"] = df_periodo.index[i_macd]
                divergencia["macd"] = df_periodo['MACD'].iloc[i_macd]
                divergencia["signal"] = df_periodo['MACD_signal'].iloc[i_macd]
                divergencia["mensaje"] = f"Posible divergencia alcista detectada el {divergencia['fecha'].strftime('%Y-%m-%d')}. MACD: {divergencia['macd']:.4f}, Señal: {divergencia['signal']:.4f}. Esto podría indicar una posible reversión alcista."
                break
          else:
            continue
          break
        
        for i_precio in maximos_precio_indices:
          for i_macd in maximos_macd_indices:
            if i_precio < i_macd:
              if df_periodo['close'].iloc[i_precio] < df_periodo['close'].iloc[i_macd] and df_periodo['MACD'].iloc[i_precio] > df_periodo['MACD'].iloc[i_macd] and abs(df_periodo['MACD'].iloc[i_precio]-df_periodo['MACD'].iloc[i_macd]) >= min_diff:
                divergencia["tipo"] = "bajista"
                divergencia["fecha"] = df_periodo.index[i_macd]
                divergencia["macd"] = df_periodo['MACD'].iloc[i_macd]
                divergencia["signal"] = df_periodo['MACD_signal'].iloc[i_macd]
                divergencia["mensaje"] = f"Posible divergencia bajista detectada el {divergencia['fecha'].strftime('%Y-%m-%d')}. MACD: {divergencia['macd']:.4f}, Señal: {divergencia['signal']:.4f}. Esto podría indicar una posible reversión bajista."
                break
          else:
            continue
          break

        return divergencia

    except Exception as e:
        logging.exception(f"Error al detectar divergencias en el MACD: {e}")
        return {"tipo": None, "fecha": None, "macd": None, "signal": None, "mensaje": "Error al detectar divergencias."}


def analizar_rsi(df, periodo=14):
    """Analiza el RSI y proporciona información sobre sobrecompra, sobreventa, cruces de la línea central, fallos de oscilación y divergencias."""
    if 'RSI' not in df.columns or len(df) < periodo:
        return {"sobrecompra": False, "sobreventa": False, "cruce_50": None, "fallo_oscilacion": None, "divergencias": {"alcistas": [], "bajistas": []}, "mensaje": "Datos insuficientes para el análisis del RSI."}

    ultimo_rsi = df['RSI'].iloc[-1]
    penultimo_rsi = df['RSI'].iloc[-2]

    analisis = {
        "sobrecompra": ultimo_rsi > 70,
        "sobreventa": ultimo_rsi < 30,
        "cruce_50": None,
        "fallo_oscilacion": None,  # Pendiente de implementar
        "divergencias": {"alcistas": [], "bajistas": []},
        "mensaje": ""
    }

    if penultimo_rsi < 50 and ultimo_rsi > 50:
        analisis["cruce_50"] = "alcista"
        analisis["mensaje"] += "El RSI cruzó la línea central (50) al alza. "
    elif penultimo_rsi > 50 and ultimo_rsi < 50:
        analisis["cruce_50"] = "bajista"
        analisis["mensaje"] += "El RSI cruzó la línea central (50) a la baja. "

    # Integrar la detección de divergencias
    divergencias_alcistas, divergencias_bajistas = detectar_divergencias_rsi(df)
    analisis["divergencias"]["alcistas"] = divergencias_alcistas
    analisis["divergencias"]["bajistas"] = divergencias_bajistas

    if divergencias_alcistas:
        analisis["mensaje"] += f"Se detectaron {len(divergencias_alcistas)} divergencias alcistas. "
        for fecha, precio, rsi in divergencias_alcistas: #añadido para mostrar la informacion de cada divergencia
             analisis["mensaje"] += f"Divergencia alcista en: {fecha} (Precio: {precio:.2f}, RSI: {rsi:.2f}). "
    if divergencias_bajistas:
        analisis["mensaje"] += f"Se detectaron {len(divergencias_bajistas)} divergencias bajistas. "
        for fecha, precio, rsi in divergencias_bajistas: #añadido para mostrar la informacion de cada divergencia
             analisis["mensaje"] += f"Divergencia bajista en: {fecha} (Precio: {precio:.2f}, RSI: {rsi:.2f}). "

    analisis["mensaje"] += f"RSI actual: {ultimo_rsi:.2f}. "
    if analisis["sobrecompra"]:
        analisis["mensaje"] += "El RSI está en zona de sobrecompra. "
    if analisis["sobreventa"]:
        analisis["mensaje"] += "El RSI está en zona de sobreventa. "

    if not analisis["mensaje"]:  # Simplificado: si el mensaje está vacío
        analisis["mensaje"] = "No se detectaron señales relevantes en el RSI."

    return analisis

def analizar_macd(df, periodo_corto=12, periodo_largo=26, periodo_signal=9):
    """Analiza el MACD y proporciona información sobre cruces, divergencias y el histograma."""
    if 'MACD' not in df.columns or 'MACD_signal' not in df.columns or 'close' not in df.columns or len(df) < periodo_largo:
        return {"cruces": {"senal": None, "cero": None}, "divergencias": {"alcistas": [], "bajistas": []}, "histograma": None, "mensaje": "Datos insuficientes para el análisis del MACD."}

    ultimo_macd = df['MACD'].iloc[-1]
    penultimo_macd = df['MACD'].iloc[-2]
    ultima_senal = df['MACD_signal'].iloc[-1]
    penultima_senal = df['MACD_signal'].iloc[-2]
    ultimo_cierre = df['close'].iloc[-1]
    penultimo_cierre = df['close'].iloc[-2]

    analisis = {
        "cruces": {"senal": None, "cero": None},
        "divergencias": {"alcistas": [], "bajistas": []},
        "histograma": None,
        "mensaje": ""
    }

    # Cruces de la línea MACD con la señal
    if penultimo_macd < penultima_senal and ultimo_macd > ultima_senal:
        analisis["cruces"]["senal"] = "alcista"
        analisis["mensaje"] += "Cruce alcista del MACD con la señal. "
    elif penultimo_macd > penultima_senal and ultimo_macd < ultima_senal:
        analisis["cruces"]["senal"] = "bajista"
        analisis["mensaje"] += "Cruce bajista del MACD con la señal. "

    # Cruces de la línea MACD con cero
    if penultimo_macd < 0 and ultimo_macd > 0:
        analisis["cruces"]["cero"] = "alcista"
        analisis["mensaje"] += "El MACD cruzó el cero al alza. "
    elif penultimo_macd > 0 and ultimo_macd < 0:
        analisis["cruces"]["cero"] = "bajista"
        analisis["mensaje"] += "El MACD cruzó el cero a la baja. "

    # Histograma
    histograma_actual = ultimo_macd - ultima_senal
    analisis["histograma"] = histograma_actual
    analisis["mensaje"] += f"Valor del histograma del MACD: {histograma_actual:.4f}. "

    # Integrar la detección de divergencias (usando la funcion mejorada)
    divergencia_macd = detectar_divergencias_macd(df, min_diff=0.01) #ponemos un min_diff mas pequeño para el ejemplo
    analisis["divergencias"]["alcistas"] = [divergencia_macd] if divergencia_macd["tipo"] == "alcista" else []
    analisis["divergencias"]["bajistas"] = [divergencia_macd] if divergencia_macd["tipo"] == "bajista" else []

    if analisis["divergencias"]["alcistas"]:
        analisis["mensaje"] += f"Se detectó una divergencia alcista. "
        for divergencia in analisis["divergencias"]["alcistas"]:
            analisis["mensaje"] += divergencia["mensaje"]

    if analisis["divergencias"]["bajistas"]:
        analisis["mensaje"] += f"Se detectó una divergencia bajista. "
        for divergencia in analisis["divergencias"]["bajistas"]:
            analisis["mensaje"] += divergencia["mensaje"]

    if not analisis["mensaje"]:
        analisis["mensaje"] = "No se detectaron señales relevantes en el MACD."

    return analisis

def calcular_rangos_compra(tendencia, maximo_reciente, minimo_reciente, tipo_rango="corto"):
    """Calcula los rangos de compra utilizando retrocesos de Fibonacci.

    Args:
        tendencia: Diccionario con información de la tendencia.
        maximo_reciente: Máximo reciente.
        minimo_reciente: Mínimo reciente.
        tipo_rango: "corto" o "largo" (opcional, por defecto "corto").

    Returns:
        Diccionario con los rangos de compra o None si la tendencia no es válida.
    """
    # ... (resto del código)
    # Aquí podrías agregar lógica adicional si necesitas diferenciar el cálculo
    # según el tipo de rango, aunque en la fórmula actual no es necesario.
    # El parámetro tipo_rango podría servir para documentar mejor el uso de la funcion
    # en caso de que en un futuro se quiera añadir logica diferente
    # para rangos cortos y largos.

    if tendencia["tipo"] == "Alcista":
        rango_618 = maximo_reciente - (maximo_reciente - minimo_reciente) * 0.618
        rango_50 = maximo_reciente - (maximo_reciente - minimo_reciente) * 0.5
        rango_382 = maximo_reciente - (maximo_reciente - minimo_reciente) * 0.382
        return {"61.8%": rango_618, "50%": rango_50, "38.2%": rango_382}
    elif tendencia["tipo"] == "Bajista":
        rango_618 = minimo_reciente + (maximo_reciente - minimo_reciente) * 0.618
        rango_50 = minimo_reciente + (maximo_reciente - minimo_reciente) * 0.5
        rango_382 = minimo_reciente + (maximo_reciente - minimo_reciente) * 0.382
        return {"61.8%": rango_618, "50%": rango_50, "38.2%": rango_382}
    else:
        return None


def generar_consejos_trading(precio, tendencia, rsi, macd, bandas_bollinger, hma, volumen):
    """Genera consejos de trading basados en el análisis técnico."""

    consejos = []

    # --- Entradas basadas en Tendencia, RSI, MACD y HMA ---
    if tendencia["tipo"] == "Alcista" and tendencia["fuerza"] in ("Moderada", "Fuerte"):
        if rsi["valor"] is not None and rsi["valor"] < 70:  # Evitar sobrecompra
            if macd["cruce"] and macd["tipo_cruce"] == "alcista":
                if precio > hma:
                    if "alto" in volumen.lower() or volumen > 1.5 * volumen_promedio: #Considera un valor numerico o string
                        consejos.append("Posible entrada alcista: Tendencia alcista moderada/fuerte, RSI por debajo de 70, cruce alcista en MACD, precio por encima del HMA y volumen alto.")
                    else:
                        consejos.append("Posible entrada alcista a confirmar: Tendencia alcista moderada/fuerte, RSI por debajo de 70, cruce alcista en MACD y precio por encima del HMA, pero volumen no confirma la entrada, esperar confirmación.")

                else:
                    consejos.append("Esperar: Tendencia alcista moderada/fuerte, RSI por debajo de 70 y cruce alcista en MACD, pero precio por debajo del HMA, esperar a que el precio supere el HMA.")
            elif precio > hma:
                consejos.append("Posible entrada alcista a confirmar: Tendencia alcista moderada/fuerte, RSI por debajo de 70 y precio por encima del HMA, pero sin cruce en MACD, esperar confirmación.")

    elif tendencia["tipo"] == "Bajista" and tendencia["fuerza"] in ("Moderada", "Fuerte"):
        if rsi["valor"] is not None and rsi["valor"] > 30:  # Evitar sobreventa
            if macd["cruce"] and macd["tipo_cruce"] == "bajista":
                if precio < hma:
                     if "alto" in volumen.lower() or volumen > 1.5 * volumen_promedio: #Considera un valor numerico o string
                        consejos.append("Posible entrada bajista: Tendencia bajista moderada/fuerte, RSI por encima de 30, cruce bajista en MACD, precio por debajo del HMA y volumen alto.")
                     else:
                        consejos.append("Posible entrada bajista a confirmar: Tendencia bajista moderada/fuerte, RSI por encima de 30, cruce bajista en MACD y precio por debajo del HMA, pero volumen no confirma la entrada, esperar confirmación.")
                else:
                    consejos.append("Esperar: Tendencia bajista moderada/fuerte, RSI por encima de 30 y cruce bajista en MACD, pero precio por encima del HMA, esperar a que el precio se sitúe por debajo del HMA.")
            elif precio < hma:
                consejos.append("Posible entrada bajista a confirmar: Tendencia bajista moderada/fuerte, RSI por encima de 30 y precio por debajo del HMA, pero sin cruce en MACD, esperar confirmación.")

    # --- Divergencias en RSI ---
    if rsi.get("divergencia"): #Manejo de KeyErrors
        consejos.append(f"Precaución: Divergencia {rsi.get('tipo_divergencia')} en RSI. Posible cambio de tendencia.")

    # --- Bandas de Bollinger ---
    if bandas_bollinger: #Manejo de NoneType
        if "cerca de la banda superior" in bandas_bollinger.lower():
            consejos.append("Precaución: Precio cerca de la banda superior de Bollinger. Posible sobrecompra o reversión bajista, especialmente en tendencias débiles.")
            if tendencia["fuerza"] == "Débil":
                consejos.append("Confirmación adicional: Tendencia alcista débil, precio cerca de la banda superior, posible venta.")
        elif "cerca de la banda inferior" in bandas_bollinger.lower():
            consejos.append("Precaución: Precio cerca de la banda inferior de Bollinger. Posible sobreventa o reversión alcista, especialmente en tendencias débiles.")
            if tendencia["fuerza"] == "Débil":
                consejos.append("Confirmación adicional: Tendencia bajista débil, precio cerca de la banda inferior, posible compra.")

    # --- Patrones de Triángulo ---
    if tendencia.get("tipo") in ("Triángulo Ascendente", "Triángulo Descendente"): #Manejo de KeyErrors
        consejos.append(f"Patrón de {tendencia.get('tipo')} detectado. Estar atento a la ruptura del triángulo para confirmar la dirección del movimiento.")
        if tendencia["tipo"] == "Triángulo Ascendente":
             consejos.append(f"Un triángulo ascendente generalmente se resuelve al alza.")
        else:
             consejos.append(f"Un triángulo descendente generalmente se resuelve a la baja.")

    return consejos


import pandas as pd

def analizar_bandas_bollinger(df, periodo=20, desviaciones=2):
    """Analiza las Bandas de Bollinger y proporciona información sobre apretones, rupturas y otros patrones."""

    if 'BB_upper' not in df.columns or 'BB_lower' not in df.columns or 'close' not in df.columns or len(df) < periodo:
        return {"apretón": False, "ruptura": None, "caminando": None, "rebote": None, "mensaje": "Datos insuficientes para el análisis de Bandas de Bollinger."}

    ultimo_cierre = df['close'].iloc[-1]
    penultimo_cierre = df['close'].iloc[-2]
    ultima_superior = df['BB_upper'].iloc[-1]
    penultima_superior = df['BB_upper'].iloc[-2]
    ultima_inferior = df['BB_lower'].iloc[-1]
    penultima_inferior = df['BB_lower'].iloc[-2]

    analisis = {
        "apretón": False,
        "ruptura": None,
        "caminando": None,
        "rebote": None,
        "mensaje": ""
    }

    # Apretón (Squeeze) - Simplificado: comparando el rango actual con el promedio de rangos anteriores
    rango_actual = ultima_superior - ultima_inferior
    rangos_anteriores = df['BB_upper'].iloc[-periodo:-1] - df['BB_lower'].iloc[-periodo:-1]
    rango_promedio = rangos_anteriores.mean()
    if rango_actual < rango_promedio * 0.8: #si el rango actual es menor al 80% del promedio se considera apreton
        analisis["apretón"] = True
        analisis["mensaje"] += "Se observa un apretón de las Bandas de Bollinger (baja volatilidad). "

    # Rupturas
    if penultimo_cierre <= penultima_superior and ultimo_cierre > ultima_superior:
        analisis["ruptura"] = "superior"
        analisis["mensaje"] += "Ruptura de la Banda de Bollinger superior. "
    elif penultimo_cierre >= penultima_inferior and ultimo_cierre < ultima_inferior:
        analisis["ruptura"] = "inferior"
        analisis["mensaje"] += "Ruptura de la Banda de Bollinger inferior. "

    # Caminando por las bandas (simplificado)
    if ultimo_cierre > ultima_superior and penultimo_cierre > penultima_superior:
        analisis["caminando"] = "superior"
        analisis["mensaje"] += "El precio está caminando por la Banda de Bollinger superior. "
    elif ultimo_cierre < ultima_inferior and penultimo_cierre < penultima_inferior:
        analisis["caminando"] = "inferior"
        analisis["mensaje"] += "El precio está caminando por la Banda de Bollinger inferior. "

    #Rebote en las bandas
    if penultimo_cierre < penultima_inferior and ultimo_cierre > ultima_inferior: #precio toco la banda inferior y volvio a subir
        analisis["rebote"] = "inferior"
        analisis["mensaje"] += "Rebote en la Banda de Bollinger inferior. "
    elif penultimo_cierre > penultima_superior and ultimo_cierre < ultima_superior: #precio toco la banda superior y volvio a bajar
        analisis["rebote"] = "superior"
        analisis["mensaje"] += "Rebote en la Banda de Bollinger superior. "

    if not analisis["mensaje"]:
        analisis["mensaje"] = "Precio dentro de las Bandas de Bollinger, sin señales relevantes."

    return analisis


def analizar_hma(df, periodo=12):
    """Analiza la Hull Moving Average (HMA) y proporciona información sobre la tendencia."""
    if 'HMA' not in df.columns or len(df) < periodo:
        return {"tendencia": None, "mensaje": "Datos insuficientes para el análisis de la HMA."}

    ultima_hma = df['HMA'].iloc[-1]
    penultima_hma = df['HMA'].iloc[-2]
    ultimo_cierre = df['close'].iloc[-1]

    analisis = {
        "tendencia": None,
        "mensaje": ""
    }

    if ultima_hma > penultima_hma:
        analisis["tendencia"] = "alcista"
        analisis["mensaje"] += "La HMA muestra una tendencia alcista. "
        if ultimo_cierre > ultima_hma:
            analisis["mensaje"] += "El precio está por encima de la HMA, reforzando la tendencia alcista. "
    elif ultima_hma < penultima_hma:
        analisis["tendencia"] = "bajista"
        analisis["mensaje"] += "La HMA muestra una tendencia bajista. "
        if ultimo_cierre < ultima_hma:
            analisis["mensaje"] += "El precio está por debajo de la HMA, reforzando la tendencia bajista. "
    else:
        analisis["mensaje"] += "La HMA se encuentra plana o sin tendencia clara."

    return analisis  
  
def analizar_volumen(df, periodo_correlacion=14, periodo_volumen_relativo=20):
    """Analiza el volumen en relación al precio, incluyendo divergencias y correlación."""
    if df['volume'].empty or df['close'].empty or len(df) < periodo_correlacion:
        return {"analisis": "Sin datos suficientes para el análisis de volumen.", "correlacion": None, "divergencia": None, "volumen_relativo": None}

    volumen = df['volume'].replace(0, np.nan) # Reemplazar ceros por NaN para evitar errores en los cálculos
    if volumen.isnull().all():
        return {"analisis": "Datos de volumen no disponibles.", "correlacion": None, "divergencia": None, "volumen_relativo": None}

    volumen_actual = volumen.iloc[-1]
    variacion_precio = (df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2] if len(df) > 1 else 0

    analisis_vol = f"Volumen: {volumen_actual:.2f}. "

    if abs(variacion_precio) > 0.02 and volumen_actual > volumen.mean():
        analisis_vol += "Movimiento de precio significativo con volumen alto. "
    elif abs(variacion_precio) > 0.02 and volumen_actual < volumen.mean():
        analisis_vol += "Movimiento de precio significativo con volumen bajo. "
    elif abs(variacion_precio) < 0.01 and volumen_actual > volumen.mean():
        analisis_vol += "Poca variación de precio con volumen alto. "

    # Correlación volumen-precio
    variaciones_precio = df['close'].pct_change().dropna()
    variaciones_volumen = volumen.pct_change().dropna()

    if len(variaciones_precio) >= periodo_correlacion and len(variaciones_volumen) >= periodo_correlacion:
        correlacion = np.corrcoef(variaciones_precio[-periodo_correlacion:], variaciones_volumen[-periodo_correlacion:])[0, 1]
    else:
        correlacion = None

    # Divergencias (ejemplo simple)
    divergencia = None
    if df['close'].iloc[-1] > df['close'].iloc[-2] and volumen.iloc[-1] < volumen.iloc[-2]:
        divergencia = "bajista"
        analisis_vol += "Posible divergencia bajista (precio sube, volumen baja). "
    elif df['close'].iloc[-1] < df['close'].iloc[-2] and volumen.iloc[-1] > volumen.iloc[-2]:
        divergencia = "alcista"
        analisis_vol += "Posible divergencia alcista (precio baja, volumen sube). "

    # Volumen relativo
    volumen_relativo = volumen_actual / volumen.rolling(window=periodo_volumen_relativo).mean().iloc[-1] if len(volumen) >= periodo_volumen_relativo else None
    if volumen_relativo is not None:
        analisis_vol += f"Volumen relativo (vs. media {periodo_volumen_relativo} periodos): {volumen_relativo:.2f}. "

    return {"analisis": analisis_vol, "correlacion": correlacion, "divergencia": divergencia, "volumen_relativo": volumen_relativo}



def analizar_temporalidad(pair, carpeta, interval, filename_suffix, periodos_rsi=14, periodos_bb=20, desviaciones_bb=2, periodos_macd_rapido=12, periodos_macd_lento=26, periodos_macd_senal=9, periodos_hma=9):
    """Analiza una temporalidad específica."""

    logging.info(f"Analizando {filename_suffix}...")
    actualizar_archivos(pair, carpeta)

    nombre_archivo = f"{pair}_{filename_suffix}.csv"
    ruta_completa = os.path.join(carpeta, nombre_archivo)

    try:
        df = pd.read_csv(ruta_completa, index_col='time', parse_dates=True)

        # Comprobación de columnas y conversión a numérico
        columnas_requeridas = ['open', 'high', 'low', 'close', 'volume', 'vwap']
        if not all(col in df.columns for col in columnas_requeridas):
            logging.error(f"El archivo {nombre_archivo} no contiene las columnas requeridas: {columnas_requeridas}")
            return None

        for col in columnas_requeridas:  # Iterar solo sobre las columnas requeridas
            df[col] = pd.to_numeric(df[col], errors='coerce')

        if df.empty or df['close'].isnull().all():
            logging.warning(f"No hay datos válidos para {filename_suffix}. Imposible generar informe.")
            return None

        df.fillna(method='ffill', inplace=True)

        # Cálculo de indicadores
        df = calcular_rsi(df, periodos=periodos_rsi)
        df = calcular_bandas_bollinger(df, periodos=periodos_bb, desviaciones=desviaciones_bb)
        df = calcular_macd(df, rapido=periodos_macd_rapido, lento=periodos_macd_lento, senal=periodos_macd_senal)
        df = calcular_hulma(df, periodos=periodos_hma)

        # Obtener datos para el informe
        ultimo_precio = df['close'].iloc[-1] if not df['close'].empty else None
        precios = df['close'].dropna().values.tolist()
        minimos, maximos = encontrar_minimos_maximos(precios)
        tendencia = analizar_tendencia(minimos, maximos)

        rsi_data = analizar_rsi(df)
        macd_data = analizar_macd(df)
        bandas_bollinger_analisis = analizar_bandas_bollinger(df)
        ultimo_hma = df['HMA'].iloc[-1] if 'HMA' in df.columns and not df['HMA'].empty else None
        ultimo_vwap = df['vwap'].iloc[-1] if 'vwap' in df.columns and not df['vwap'].empty else None
        analisis_volumen_completo = analizar_volumen(df)

        # Calcular rangos de compra
        maximo_reciente = df['high'].rolling(window=14).max().iloc[-1] if len(df) >= 14 and 'high' in df.columns else df['high'].max() if 'high' in df.columns and not df['high'].empty else None
        minimo_reciente = df['low'].rolling(window=14).min().iloc[-1] if len(df) >= 14 and 'low' in df.columns else df['low'].min() if 'low' in df.columns and not df['low'].empty else None
        rangos_compra = calcular_rangos_compra(tendencia, maximo_reciente, minimo_reciente) if maximo_reciente is not None and minimo_reciente is not None else None

        # *** ANÁLISIS DEL VWAP ***
        if ultimo_vwap is not None and ultimo_precio is not None and not np.isnan(ultimo_vwap) and not np.isnan(ultimo_precio):
            if ultimo_precio > ultimo_vwap:
                vwap_mensaje = f"VWAP: {ultimo_vwap:.2f}. Precio por encima del VWAP (Presión compradora intradía)."
            elif ultimo_precio < ultimo_vwap:
                vwap_mensaje = f"VWAP: {ultimo_vwap:.2f}. Precio por debajo del VWAP (Presión vendedora intradía)."
            else:
                vwap_mensaje = f"VWAP: {ultimo_vwap:.2f}. Precio en el VWAP."
        else:
            vwap_mensaje = "VWAP no disponible."

        # Generar el informe
        resumen_telegram = generar_informe_completo(ultimo_precio, tendencia, rsi_data, macd_data, bandas_bollinger_analisis, ultimo_hma, vwap_mensaje, analisis_volumen_completo, rangos_compra, filename_suffix)

        print(resumen_telegram)
        logging.info(f"Resumen generado para {filename_suffix}: {resumen_telegram}")

        guardar_dataframe(df, ruta_completa)
        logging.info(f"Archivo {nombre_archivo} procesado y guardado.")
        return resumen_telegram

    except FileNotFoundError:
        logging.error(f"Archivo no encontrado: {ruta_completa}")
        return None
    except pd.errors.EmptyDataError:
        logging.error(f"El archivo {ruta_completa} está vacío.")
        return None
    except Exception as e:
        logging.exception(f"Error al procesar {ruta_completa}: {e}")
        return None
      
def generar_informe_completo(ultimo_precio, tendencia, rsi_data, macd_data, bandas_bollinger_analisis, ultimo_hma, vwap_mensaje, analisis_volumen_completo, rangos_compra, filename_suffix, mensaje_tiempo_restante, consejos_trading):
    """Genera el informe completo con mensajes detallados y fuerza de señal."""

    informe = f"""
==========================
Análisis Técnico: {filename_suffix.split('_')[0]} ({filename_suffix})
Fecha: {datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S UTC")}
==========================
Precio actual: {ultimo_precio:.2f if ultimo_precio is not None else "N/A"}
Tendencia: {tendencia if tendencia is not None else "N/A"}
{mensaje_tiempo_restante}

--- RSI ---
RSI: {rsi_data.get('valor', "N/A"):.2f} ({rsi_data.get('condicion', "N/A")})
"""
    if rsi_data and 'condicion' in rsi_data:
        fuerza_senal = "fuerte" if (tendencia == "Alcista" and rsi_data['condicion'] == "Sobreventa") or (tendencia == "Bajista" and rsi_data['condicion'] == "Sobrecompra") else "débil"
        informe += f"- El RSI está en {rsi_data['condicion'].lower()}, señal {fuerza_senal}.\n"

    informe += f"""
--- MACD ---
MACD: {macd_data.get('macd', "N/A"):.2f}, Señal: {macd_data.get('senal', "N/A"):.2f} ({macd_data.get('cruce', "N/A")})
"""
    if macd_data and 'cruce' in macd_data:
        informe += f"- Se detectó un {macd_data['cruce'].lower()}.\n"

    informe += f"""
--- Bandas de Bollinger ---
"""
    if bandas_bollinger_analisis:
        informe += f"""
    - Cierre sobre banda superior: {bandas_bollinger_analisis.get('cierre_sobre_banda_superior', "N/A")}
    - Cierre bajo banda inferior: {bandas_bollinger_analisis.get('cierre_bajo_banda_inferior', "N/A")}
"""
        if bandas_bollinger_analisis.get('cierre_sobre_banda_superior'):
            informe += "- El precio cerró por encima de la banda superior, lo que sugiere sobrecompra o una tendencia alcista fuerte.\n"
        elif bandas_bollinger_analisis.get('cierre_bajo_banda_inferior'):
            informe += "- El precio cerró por debajo de la banda inferior, lo que sugiere sobreventa o una tendencia bajista fuerte.\n"
        else:
            informe += "- El precio se mantiene dentro de las Bandas de Bollinger.\n"
    else:
        informe += "N/A\n"

    informe += f"""
--- Análisis de Volumen ---
"""
    if analisis_volumen_completo:
        informe += f"""
    - Volumen actual: {analisis_volumen_completo.get('volumen_actual', "N/A")}
    - Volumen promedio: {analisis_volumen_completo.get('volumen_promedio', "N/A")}
    - {analisis_volumen_completo.get('mensaje', "N/A")}\n"""
    else:
        informe += "N/A\n"

    informe += f"""
--- HMA (Hull Moving Average) ---
HMA: {ultimo_hma:.2f if ultimo_hma is not None else "N/A"}
{vwap_mensaje}

--- Rangos de Compra ---
"""
    if rangos_compra:
        informe += f"""
    - Soporte: {rangos_compra.get('soporte', "N/A"):.2f}
    - Resistencia: {rangos_compra.get('resistencia', "N/A"):.2f}
    - {rangos_compra.get('mensaje', "N/A")}\n"""
    else:
        informe += "N/A\n"

    puntos_senal_alcista = 0
    puntos_senal_bajista = 0

    if rsi_data and rsi_data.get('condicion') == "Sobreventa":
        puntos_senal_alcista += 1
    if rsi_data and rsi_data.get('condicion') == "Sobrecompra":
        puntos_senal_bajista += 1
    if macd_data and macd_data.get('cruce') == "Cruce alcista":
        puntos_senal_alcista += 2
    if macd_data and macd_data.get('cruce') == "Cruce bajista":
        puntos_senal_bajista += 2
    if bandas_bollinger_analisis and bandas_bollinger_analisis.get('cierre_sobre_banda_superior'):
        puntos_senal_bajista += 1
    if bandas_bollinger_analisis and bandas_bollinger_analisis.get('cierre_bajo_banda_inferior'):
        puntos_senal_alcista += 1
    if analisis_volumen_completo:
        if "por encima del promedio" in analisis_volumen_completo.get('mensaje', ""):
            puntos_senal_alcista += 0.5 if tendencia == "Alcista" else 0
            puntos_senal_bajista += 0.5 if tendencia == "Bajista" else 0
            if tendencia == "Lateral":
                puntos_senal_alcista += 0.25
                puntos_senal_bajista += 0.25

    informe += f"""
--- Resumen de Señales ---
Puntos señal alcista: {puntos_senal_alcista}
Puntos señal bajista: {puntos_senal_bajista}
Señal general: {"Alcista" if puntos_senal_alcista > puntos_senal_bajista else "Bajista" if puntos_senal_bajista > puntos_senal_alcista else "Neutra"}
"""

    # **AQUÍ ESTÁ EL CAMBIO CRUCIAL: SEPARACIÓN DE LA SECCIÓN DE CONSEJOS**
    informe += """
--- Consejos de Trading ---
""" # Se abre la sección con un string normal
    if consejos_trading:
        for consejo in consejos_trading:
            informe += f"- {consejo}\n" # Se añaden los consejos con f-strings *dentro* del bucle
    else:
        informe += "No hay consejos disponibles en este momento.\n"

    return informe

def calcular_tiempo_restante(minutes):
    """Calcula el tiempo restante en segundos hasta el próximo cierre de vela según el intervalo."""
    now = datetime.datetime.now()

    # Si el intervalo es en minutos
    if minutes <= 60:
        # Calcular el siguiente múltiplo de minutos
        next_interval = (now.minute // minutes + 1) * minutes
        next_candle_time = now.replace(minute=next_interval % 60, second=0, microsecond=0)
        if next_candle_time < now:
            next_candle_time += datetime.timedelta(hours=1)
    else:
        # Si es un intervalo mayor (1h, 4h, 1d), ajustamos según la hora
        next_candle_time = now.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=(now.hour // (minutes // 60) + 1) * (minutes // 60))

    # Calcular el tiempo restante hasta el próximo cierre
    remaining_seconds = (next_candle_time - now).total_seconds()

    return remaining_seconds
  
def procesar_temporalidad(pair, carpeta, intervalo_segundos, filename_suffix):
    """Procesa una temporalidad específica."""
    print(f"Iniciando procesamiento de {filename_suffix}...")
    logging.info(f"Iniciando procesamiento de {filename_suffix}...")

    # Aquí realizarías las operaciones específicas para esta temporalidad
    procesar_csv(pair, filename_suffix, carpeta)

    print(f"Finalizado procesamiento de {filename_suffix}.")
    logging.info(f"Finalizado procesamiento de {filename_suffix}.")

def procesar_csv(pair, filename_suffix, carpeta, intervalos):
    """Procesa una temporalidad específica y actualiza el CSV."""
    ruta_csv = os.path.join(carpeta, f"{pair}_{filename_suffix}.csv")
    try:
        df = pd.read_csv(ruta_csv, index_col='time', parse_dates=True)
    except FileNotFoundError:
        print(f"Archivo {ruta_csv} no encontrado. Creando archivo nuevo.")
        df = pd.DataFrame()

    # Obtener el intervalo en segundos del diccionario
    minutes = int(filename_suffix[:-1]) if filename_suffix[:-1].isdigit() else None  # Manejar el caso "1d"
    if minutes is None:
        if filename_suffix == "1d":
            intervalo_segundos = 24 * 60 * 60
        else:
            print(f"Error: Sufijo de archivo no válido: {filename_suffix}")
            logging.error(f"Error: Sufijo de archivo no válido: {filename_suffix}")
            return
    else:
        intervalo_segundos = intervalos.get(minutes, None)
        if intervalo_segundos is None:
            print(f"Error: Intervalo no definido para {minutes} minutos")
            logging.error(f"Error: Intervalo no definido para {minutes} minutos")
            return

    df = actualizar_dataframe(df, pair, intervalo_segundos)

    if not df.empty and 'close' in df.columns:
        df['sma_20'] = df['close'].rolling(window=20).mean()

    df['ultima_actualizacion'] = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

    guardar_dataframe(df, ruta_csv)
    print(f"Archivo {filename_suffix} actualizado.")
    logging.info(f"Archivo {filename_suffix} actualizado.")

def bucle_principal(pair, carpeta, intervalos):
    """Bucle principal que sincroniza el análisis de las temporalidades."""
    ultimos_tiempos = {filename_suffix: 0 for filename_suffix in intervalos.values()}
    while True:
        tiempo_actual = time.time()

        for minutes, filename_suffix in intervalos.items():
            intervalo_segundos = minutes * 60  # Calcular intervalo_segundos UNA SOLA VEZ
            tiempo_transcurrido = tiempo_actual - ultimos_tiempos.get(filename_suffix, 0)

            if tiempo_transcurrido >= intervalo_segundos:
                print(f"Iniciando procesamiento de {filename_suffix}...")
                logging.info(f"Iniciando procesamiento de {filename_suffix}...")

                procesar_csv(pair, filename_suffix, carpeta, intervalos)

                print(f"Finalizado procesamiento de {filename_suffix}.")
                logging.info(f"Finalizado procesamiento de {filename_suffix}.")

                ultimos_tiempos[filename_suffix] = tiempo_actual

        print("--------------------------------------------------")
        logging.info("--------------------------------------------------")
        time.sleep(1)
def main():
    pair = "XBTUSDT"
    carpeta_datos = "datos_BTC"
    os.makedirs(carpeta_datos, exist_ok=True)
    intervalos = {
        15: "15m",
        60: "1h",
        240: "4h",
        1440: "1d"
    }

    bucle_principal(pair, carpeta_datos, intervalos)

if __name__ == "__main__":
    main()

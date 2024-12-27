import requests
import pandas as pd
import time
import datetime
import os
import talib

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
            time.sleep(5)  # Esperar antes de reintentar
    print("Número máximo de reintentos alcanzado.")
    return None

def guardar_dataframe(df, filename):
    if df is not None:
        try:
            df.to_csv(filename)
            print(f"Datos guardados en {filename}")
        except Exception as e:
            print(f"Error al guardar el archivo: {e}")
    else:
        print("No hay datos para guardar.")

def obtener_y_guardar_multiples_temporalidades(pair, desde, carpeta="data"):
    # Crear la carpeta si no existe
    os.makedirs(carpeta, exist_ok=True)
    temporalidades = {
        15: "15m",
        60: "1h",
        240: "4h",
        1440: "1d"
    }
    for interval, filename_suffix in temporalidades.items():
        print(f"Obteniendo datos para el intervalo de {filename_suffix}...")
        df = obtener_ohlc_kraken(pair, interval, since=desde)
        filename = os.path.join(carpeta, f"{pair}_{filename_suffix}.csv")
        guardar_dataframe(df, filename)

# Ejemplo de uso:
pair = "XBTUSDT"  # Par BTC/USDT en Kraken
desde = datetime.datetime(2023, 1, 1).timestamp()
carpeta_datos = "datos_BTC" #Nombre de la carpeta donde se guardaran los archivos

obtener_y_guardar_multiples_temporalidades(pair, desde, carpeta_datos)

print("Proceso completado.")

# (Las funciones obtener_ohlc_kraken y guardar_dataframe del código anterior se mantienen igual)

def actualizar_dataframe(df, pair, interval):
    if df.empty:  # Si el DataFrame está vacío, obtener datos desde el inicio
        since = None
    else:
        last_timestamp = int(df.index[-1].timestamp()) + 1 #Obtener el ultimo timestamp y sumarle 1 segundo para evitar duplicados
        since = last_timestamp

    nuevos_datos = obtener_ohlc_kraken(pair, interval, since)

    if nuevos_datos is not None:
        if not nuevos_datos.empty: #Verificar si se obtuvieron nuevos datos
            df_actualizado = pd.concat([df, nuevos_datos])
            df_actualizado = df_actualizado[~df_actualizado.index.duplicated(keep='last')] #Eliminar duplicados en el indice
            return df_actualizado
        else:
            print(f"No hay nuevos datos para el intervalo {interval}")
            return df
    else:
        print(f"Error al obtener nuevos datos para el intervalo {interval}")
        return df

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
        guardar_dataframe(df, filename)

# Ejemplo de uso (bucle principal):
pair = "XBTUSDT"
carpeta_datos = "datos_BTC"
frecuencia_actualizacion = 60  # Actualizar cada 60 segundos (1 minuto)

while True:
    print("Actualizando datos...")
    actualizar_archivos(pair, carpeta_datos)
    print(f"Datos actualizados. Esperando {frecuencia_actualizacion} segundos...")
    time.sleep(frecuencia_actualizacion)
def calcular_rsi(df, periodo=14):
    if len(df) < periodo:
        print(f"Se necesitan al menos {periodo} datos para calcular el RSI.")
        return df  # Devuelve el DataFrame original SIN MODIFICAR si no hay suficientes datos
    df['RSI'] = talib.RSI(df['close'], timeperiod=periodo)
    return df

def calcular_bandas_bollinger(df, periodo=20, desviaciones=2):
    if len(df) < periodo:
        print(f"Se necesitan al menos {periodo} datos para calcular las Bandas de Bollinger.")
        return df  # Devuelve el DataFrame original SIN MODIFICAR
    df['BB_MIDDLE'], df['BB_UPPER'], df['BB_LOWER'] = talib.BBANDS(df['close'], timeperiod=periodo, nbdevup=desviaciones, nbdevdn=desviaciones, matype=0)
    return df

def calcular_macd(df, rapido=12, lento=26, senal=9):
    if len(df) < lento:
        print(f"Se necesitan al menos {lento} datos para calcular el MACD.")
        return df  # Devuelve el DataFrame original SIN MODIFICAR
    df['MACD'], df['MACD_signal'], df['MACD_hist'] = talib.MACD(df['close'], fastperiod=rapido, slowperiod=lento, signalperiod=senal)
    return df

def calcular_hulma(df, periodo_base=9):
    if len(df) < periodo_base:
        print(f"Se necesitan al menos {periodo_base} datos para calcular la HULMA.")
        return df  # Devuelve el DataFrame original SIN MODIFICAR
    if len(df) < periodo_base*2: #Corrección para evitar error en el calculo de la HULMA
        return df
    sqrt_periodo = int(periodo_base**0.5) #Se usa el periodo base para calcular la raiz cuadrada y no len(df)
    df['HULMA'] = talib.MA(df['close'], timeperiod=periodo_base).rolling(window=sqrt_periodo).mean()
    df['HULMA'] = talib.MA(df['HULMA'], timeperiod=sqrt_periodo).rolling(window=sqrt_periodo).mean()
    return df

# --- Función Principal para Calcular y Guardar Indicadores (CORRECCIONES FUNDAMENTALES) ---
def calcular_y_guardar_indicadores(pair, carpeta="datos_BTC"):
    temporalidades = {
        15: "15m",
        60: "1h",
        240: "4h",
        1440: "1d"
    }

    for interval, filename_suffix in temporalidades.items():
        filename = os.path.join(carpeta, f"{pair}_{filename_suffix}.csv")
        df_original = cargar_dataframe(filename)

        if df_original is not None and not df_original.empty:
            print(f"Procesando {filename}")

            # Asegurar que el índice esté configurado correctamente
            if not isinstance(df_original.index, pd.DatetimeIndex):
                df_original.index = pd.to_datetime(df_original.index)

            # Crear copia para cálculos
            df_indicadores = df_original.copy()

            # Calcular indicadores
            df_indicadores = calcular_rsi(df_indicadores)
            df_indicadores = calcular_bandas_bollinger(df_indicadores)
            df_indicadores = calcular_macd(df_indicadores)
            df_indicadores = calcular_hulma(df_indicadores)

            # Combinar DataFrames, manteniendo índices alineados
            indicadores_unidos = df_original.join(
                df_indicadores.drop(columns=df_original.columns, errors='ignore'),
                how='left'
            )

            # Guardar los datos actualizados
            guardar_dataframe(indicadores_unidos, filename)
            print(f"Indicadores agregados y guardados en {filename}")
        else:
            print(f"No se pudo cargar o procesar el archivo {filename}.")

def cargar_dataframe(filename):
    try:
        df = pd.read_csv(filename, index_col='time', parse_dates=True)
        return df
    except FileNotFoundError:
        print(f"Archivo {filename} no encontrado.")
        return None

def guardar_dataframe(df, filename):
    if df is not None:
        try:
            df.to_csv(filename)
            print(f"Datos guardados en {filename}")
        except Exception as e:
            print(f"Error al guardar el archivo: {e}")
    else:
        print("No hay datos para guardar.")


def analizar_y_generar_alertas(df, temporalidad):
    alertas = []

    # Análisis del RSI
    if df['RSI'].iloc[-1] >= 70:
        alertas.append(f"RSI en sobrecompra en {temporalidad}. Posible señal de venta.")
    elif df['RSI'].iloc[-1] <= 30:
        alertas.append(f"RSI en sobreventa en {temporalidad}. Posible señal de compra.")

    #Divergencias RSI (ejemplo básico, necesita mejora para detección robusta)
    if len(df) >= 3:
      if df['close'].iloc[-1] < df['close'].iloc[-2] and df['RSI'].iloc[-1] > df['RSI'].iloc[-2]:
          alertas.append(f"Posible divergencia alcista en RSI en {temporalidad}.")
      elif df['close'].iloc[-1] > df['close'].iloc[-2] and df['RSI'].iloc[-1] < df['RSI'].iloc[-2]:
          alertas.append(f"Posible divergencia bajista en RSI en {temporalidad}.")


    # Análisis de Bandas de Bollinger
    if df['close'].iloc[-1] >= df['BB_UPPER'].iloc[-1]:
        alertas.append(f"Precio tocando/sobrepasando la Banda de Bollinger superior en {temporalidad}.")
    elif df['close'].iloc[-1] <= df['BB_LOWER'].iloc[-1]:
        alertas.append(f"Precio tocando/sobrepasando la Banda de Bollinger inferior en {temporalidad}.")

    # Analisis MACD
    if df['MACD'].iloc[-1] > df['MACD_signal'].iloc[-1] and df['MACD'].iloc[-2] <= df['MACD_signal'].iloc[-2]:
        alertas.append(f"Cruce alcista del MACD en {temporalidad}. Posible señal de compra.")
    elif df['MACD'].iloc[-1] < df['MACD_signal'].iloc[-1] and df['MACD'].iloc[-2] >= df['MACD_signal'].iloc[-2]:
        alertas.append(f"Cruce bajista del MACD en {temporalidad}. Posible señal de venta.")

    if df['MACD'].iloc[-1] > 0 and df['MACD'].iloc[-2] <= 0:
        alertas.append(f"MACD cruza por encima de cero en {temporalidad}. Refuerza señal alcista.")
    elif df['MACD'].iloc[-1] < 0 and df['MACD'].iloc[-2] >= 0:
        alertas.append(f"MACD cruza por debajo de cero en {temporalidad}. Refuerza señal bajista.")

    # Analisis HULMA
    if df['close'].iloc[-1] > df['HULMA'].iloc[-1]:
        alertas.append(f"Precio por encima de la HULMA en {temporalidad}. Tendencia alcista según HULMA.")
    elif df['close'].iloc[-1] < df['HULMA'].iloc[-1]:
        alertas.append(f"Precio por debajo de la HULMA en {temporalidad}. Tendencia bajista según HULMA.")
    #Retorna las alertas
    return alertas

def calcular_y_analizar(pair, carpeta="datos_BTC"):
    temporalidades = {
        15: "15m",
        60: "1h",
        240: "4h",
        1440: "1d"
    }
    resultados = {} #diccionario para almacenar los resultados por temporalidad

    for interval, filename_suffix in temporalidades.items():
        filename = os.path.join(carpeta, f"{pair}_{filename_suffix}.csv")
        df = cargar_dataframe(filename)

        if df is not None:

            alertas = analizar_y_generar_alertas(df, filename_suffix)
            resultados[filename_suffix] = alertas #almacena las alertas en el diccionario
            guardar_dataframe(df,filename)
        else:
            print(f"No se pudo cargar el archivo {filename}")
    return resultados

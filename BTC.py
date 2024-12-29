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
    print("Entrando en calcular_rsi")
    if len(df) < periodo:
        print(f"No hay suficientes datos para calcular el RSI ({len(df)} datos). Se necesitan al menos {periodo}.")
        return df
    df['RSI'] = talib.RSI(df['close'], timeperiod=periodo)
    print(f"RSI calculado: {df['RSI'].iloc[-1]}")
    print("Saliendo de calcular_rsi")
    return df

def calcular_bandas_bollinger(df, periodo=20, desviaciones=2):
    print("Entrando en calcular_bandas_bollinger")
    if len(df) < periodo:
        print(f"No hay suficientes datos para calcular las Bandas de Bollinger ({len(df)} datos). Se necesitan al menos {periodo}.")
        return df
    bbands = talib.BBANDS(df['close'], timeperiod=periodo, nbdevup=desviaciones, nbdevdn=desviaciones, matype=0)
    df['BB_UPPER'] = bbands[0]
    df['BB_MIDDLE'] = bbands[1]
    df['BB_LOWER'] = bbands[2]
    print("Saliendo de calcular_bandas_bollinger")
    return df

def calcular_macd(df, rapido=12, lento=26, senal=9):
    print("Entrando en calcular_macd")
    if len(df) < lento:
        print(f"No hay suficientes datos para calcular el MACD ({len(df)} datos). Se necesitan al menos {lento}.")
        return df
    macd = talib.MACD(df['close'], fastperiod=rapido, slowperiod=lento, signalperiod=senal)
    df['MACD'] = macd[0]
    df['MACD_signal'] = macd[1]
    df['MACD_hist'] = macd[2]
    print("Saliendo de calcular_macd")
    return df

def calcular_hulma(df, periodo_base=9):
    print("Entrando en calcular_hulma")
    if len(df) < periodo_base * 2: # Se necesitan al menos el doble del periodo base
        print(f"No hay suficientes datos para calcular la HULMA ({len(df)} datos). Se necesitan al menos {periodo_base * 2}.")
        return df
    sqrt_periodo = int(periodo_base**0.5)
    df['HULMA'] = talib.MA(df['close'], timeperiod=periodo_base).rolling(window=sqrt_periodo).mean()
    df['HULMA'] = talib.MA(df['HULMA'], timeperiod=sqrt_periodo).rolling(window=sqrt_periodo).mean()
    print("Saliendo de calcular_hulma")
    return df


def calcular_indicadores(df): #Función para calcular todos los indicadores de una vez
    if len(df) >= 26: #Comprueba que haya datos suficientes para el MACD
        df['RSI'] = talib.RSI(df['close'], timeperiod=14)
        bbands = talib.BBANDS(df['close'], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
        df['BB_UPPER'] = bbands[0]
        df['BB_MIDDLE'] = bbands[1]
        df['BB_LOWER'] = bbands[2]
        macd = talib.MACD(df['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        df['MACD'] = macd[0]
        df['MACD_signal'] = macd[1]
        df['MACD_hist'] = macd[2]
        periodo_base = 9
        if len(df) >= periodo_base * 2:
            sqrt_periodo = int(periodo_base**0.5)
            df['HULMA'] = talib.MA(df['close'], timeperiod=periodo_base).rolling(window=sqrt_periodo).mean()
            df['HULMA'] = talib.MA(df['HULMA'], timeperiod=sqrt_periodo).rolling(window=sqrt_periodo).mean()
        else:
            print("No hay datos suficientes para calcular la HULMA.")
    else:
        print("No hay datos suficientes para calcular los indicadores.")
    return df


def calcular_y_guardar_indicadores(pair, carpeta="datos_BTC"):
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
            print(f"Procesando {filename}, longitud del dataframe: {len(df)}")

            # --- Cálculo de indicadores ---
            df = calcular_indicadores(df)

            df.to_csv(filename)
            print(f"DataFrame guardado en {filename}")

        except FileNotFoundError:
            print(f"Archivo {filename} no encontrado. Se creará al actualizar los datos.")
        except Exception as e:
            print(f"Error procesando {filename}: {e}")
            import traceback
            traceback.print_exc()

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




------------------------------------------------
import threading
import requests
import pandas as pd
import time
import datetime
import os
import talib

def obtener_ohlc_kraken(pair, interval, since=None):
    # Lógica para obtener datos desde Kraken
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

def leer_y_procesar_csv(ruta_archivo):
    """Lee un archivo CSV, lo imprime (opcional) y lo procesa."""
    try:
        print(f"[leer_y_procesar_csv] Intentando leer el archivo: {ruta_archivo}")
        if not os.path.exists(ruta_archivo): #Verifica si el archivo existe ANTES de intentar leerlo
            print(f"[leer_y_procesar_csv] ERROR: El archivo NO existe en la ruta: {ruta_archivo}")
            return None

        print(f"[leer_y_procesar_csv] Archivo EXISTE. Procediendo con la lectura...")
        df = pd.read_csv(ruta_archivo, index_col='time', parse_dates=True)

        #Ejemplo de uso de talib
        df['RSI'] = talib.RSI(df['close'], timeperiod=14)
        print(f"[leer_y_procesar_csv] RSI calculado (primeras 5 filas):\n{df['RSI'].head().to_string()}")
        return df

    except FileNotFoundError: 
        print(f"[leer_y_procesar_csv] ERROR: Archivo no encontrado en la ruta: {ruta_archivo}")
        return None
    except Exception as e:
        print(f"[leer_y_procesar_csv] Ocurrió un error general: {e}")
        return None

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

def actualizar_dataframe(df, pair, interval):
    if df.empty:  # Si el DataFrame está vacío, obtener datos desde el inicio
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

# Función que se ejecutará en un hilo separado para procesar el CSV
def procesar_csv(pair, interval, carpeta="datos_BTC"):
    nombre_archivo = f"{pair}_{interval}.csv"
    ruta_completa = os.path.join(carpeta, nombre_archivo)
    dataframe_procesado = leer_y_procesar_csv(ruta_completa)
    if dataframe_procesado is not None:
        print(f"Archivo {nombre_archivo} procesado correctamente.")
    else:
        print(f"No se pudo procesar el archivo {nombre_archivo}.")

def main():
    pair = "XBTUSDT"
    carpeta_datos = "datos_BTC"
    temporalidades = {
        15: "15m",
        60: "1h",
        240: "4h",
        1440: "1d"
    }
    
    while True:
        for interval, filename_suffix in temporalidades.items():
            print(f"Obteniendo datos para el intervalo de {filename_suffix}...")
            df = obtener_ohlc_kraken(pair, interval)
            if df is not None:
                filename = os.path.join(carpeta_datos, f"{pair}_{filename_suffix}.csv")
                guardar_dataframe(df, filename)
                
                # Crear un hilo para procesar el CSV
                threading.Thread(target=procesar_csv, args=(pair, filename_suffix)).start()

        print("Datos actualizados. Esperando 60 segundos...")
        time.sleep(60)

if __name__ == "__main__":
    main()

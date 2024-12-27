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
        print(f"No hay suficientes datos para calcular el RSI ({len(df)} datos). Se necesitan al menos {periodo}.")
        return df
    df['RSI'] = talib.RSI(df['close'], timeperiod=periodo)
    return df

def calcular_bandas_bollinger(df, periodo=20, desviaciones=2):
    if len(df) < periodo:
        print(f"No hay suficientes datos para calcular las Bandas de Bollinger ({len(df)} datos). Se necesitan al menos {periodo}.")
        return df
    bbands = talib.BBANDS(df['close'], timeperiod=periodo, nbdevup=desviaciones, nbdevdn=desviaciones, matype=0)
    df['BB_UPPER'] = bbands[0]
    df['BB_MIDDLE'] = bbands[1]
    df['BB_LOWER'] = bbands[2]
    return df

def calcular_macd(df, rapido=12, lento=26, senal=9):
    if len(df) < lento:
        print(f"No hay suficientes datos para calcular el MACD ({len(df)} datos). Se necesitan al menos {lento}.")
        return df
    macd = talib.MACD(df['close'], fastperiod=rapido, slowperiod=lento, signalperiod=senal)
    df['MACD'] = macd[0]
    df['MACD_signal'] = macd[1]
    df['MACD_hist'] = macd[2]
    return df

def calcular_hulma(df, periodo_base=9):
    if len(df) < periodo_base * 2:
        print(f"No hay suficientes datos para calcular la HULMA ({len(df)} datos). Se necesitan al menos {periodo_base * 2}.")
        return df
    sqrt_periodo = int(periodo_base**0.5)
    df['HULMA'] = talib.MA(df['close'], timeperiod=periodo_base).rolling(window=sqrt_periodo).mean()
    df['HULMA'] = talib.MA(df['HULMA'], timeperiod=sqrt_periodo).rolling(window=sqrt_periodo).mean()
    return df

# Ejemplo de prueba (datos simulados):
data = {'close': np.random.rand(50) * 100} #Genera 50 numeros aleatorios entre 0 y 100
df_test = pd.DataFrame(data)

print("DataFrame original:")
print(df_test.head())
print(len(df_test))

df_test = calcular_rsi(df_test)
print("\nDataFrame con RSI:")
print(df_test.head(20)) #Imprime las primeras 20 filas para ver los NaN
print(len(df_test))


df_test = calcular_bandas_bollinger(df_test)
print("\nDataFrame con Bandas de Bollinger:")
print(df_test.head(25)) #Imprime las primeras 25 filas para ver los NaN
print(len(df_test))

df_test = calcular_macd(df_test)
print("\nDataFrame con MACD:")
print(df_test.head(30)) #Imprime las primeras 30 filas para ver los NaN
print(len(df_test))

df_test = calcular_hulma(df_test)
print("\nDataFrame con HULMA:")
print(df_test.head(20)) #Imprime las primeras 20 filas para ver los NaN
print(len(df_test))

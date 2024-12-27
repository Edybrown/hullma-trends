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

def calcular_rsi(df, periodo=14):
    """Calcula el RSI (Relative Strength Index)."""
    if len(df) < periodo: # Verifica si hay suficientes datos
        return pd.Series(index=df.index) # Devuelve una Serie vacía si no hay datos suficientes
    delta = df['close'].diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ma_up = up.rolling(window=periodo).mean()
    ma_down = down.rolling(window=periodo).mean()
    rsi = 100 - (100 / (1 + ma_up / ma_down))
    return rsi

def calcular_bandas_bollinger(df, periodo=20, desviaciones=2):
    """Calcula las Bandas de Bollinger."""
    if len(df) < periodo:
        return pd.Series(index=df.index), pd.Series(index=df.index), pd.Series(index=df.index)
    media = df['close'].rolling(window=periodo).mean()
    desviacion_estandar = df['close'].rolling(window=periodo).std()
    banda_superior = media + desviaciones * desviacion_estandar
    banda_inferior = media - desviaciones * desviacion_estandar
    return banda_superior, media, banda_inferior

def calcular_hulma(df, periodo=9):
    """Calcula el Hull Moving Average (HMA)."""
    if len(df) < periodo:
        return pd.Series(index=df.index)
    n = periodo
    sqrt_n = int(np.sqrt(n))
    wma1 = df['close'].rolling(window=int(n / 2)).apply(lambda x: np.average(x, weights=np.arange(1, len(x) + 1)))
    wma2 = df['close'].rolling(window=n).apply(lambda x: np.average(x, weights=np.arange(1, len(x) + 1)))
    hma = (2 * wma1 - wma2).rolling(window=sqrt_n).apply(lambda x: np.average(x, weights=np.arange(1, len(x) + 1)))
    return hma

def calcular_macd(df, periodo_corto=12, periodo_largo=26, periodo_senal=9):
    """Calcula el MACD (Moving Average Convergence Divergence)."""
    if len(df) < periodo_largo:
        return pd.Series(index=df.index), pd.Series(index=df.index)
    ema_corto = df['close'].ewm(span=periodo_corto, adjust=False).mean()
    ema_largo = df['close'].ewm(span=periodo_largo, adjust=False).mean()
    macd = ema_corto - ema_largo
    senal = macd.ewm(span=periodo_senal, adjust=False).mean()
    return macd, senal

def calcular_y_guardar_indicadores(pair, carpeta="datos_BTC"):
    """Calcula y guarda los indicadores para *cada* archivo CSV."""
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
            if not df.empty:
                # ***Aquí está la clave: se asegura de que 'close' exista y se manejan los valores NaN***
                if 'close' in df.columns: #Verifica que la columna close exista
                    df['RSI'] = calcular_rsi(df).fillna(method='bfill') #Calcula el RSI y rellena los valores NaN
                    banda_superior, media, banda_inferior = calcular_bandas_bollinger(df)
                    df['Banda Superior'] = banda_superior.fillna(method='bfill')
                    df['Banda Media'] = media.fillna(method='bfill')
                    df['Banda Inferior'] = banda_inferior.fillna(method='bfill')
                    df['HMA'] = calcular_hulma(df).fillna(method='bfill')
                    macd, senal = calcular_macd(df)
                    df['MACD'] = macd.fillna(method='bfill')
                    df['Señal MACD'] = senal.fillna(method='bfill')
                    guardar_dataframe(df, filename)
                    print(f"Indicadores calculados y guardados en {filename}")
                else:
                    print(f"La columna 'close' no existe en {filename}. No se calcularon indicadores.")

            else:
                print(f"DataFrame vacío para {filename}. No se calcularon indicadores.")
        except FileNotFoundError:
            print(f"Archivo {filename} no encontrado. No se calcularon indicadores.")




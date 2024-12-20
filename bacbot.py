import requests
import pandas as pd
import time
import talib
import numpy as np
import csv
import os

def obtener_datos_coinex(simbolo, intervalo, limit=1000):
    url = f"https://api.coinex.com/v1/market/kline?market={simbolo}&type={intervalo}&limit={limit}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Lanza una excepción para errores HTTP
        data = response.json()['data']
        df = pd.DataFrame(data)

        # Convertir timestamps a datetime y establecer como índice
        df['date'] = pd.to_datetime(df['date'], unit='s')
        df.set_index('date', inplace=True)
        # Convertir columnas a numérico (importante para cálculos)
        df = df.apply(pd.to_numeric, errors='coerce')
        df.rename(columns={'open':'Open', 'close':'Close', 'high':'High', 'low':'Low', 'vol':'Volume'}, inplace=True)
        return df
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener datos de Coinex: {e}")
        return None
    except KeyError as e:
        print(f"Error al procesar datos de Coinex, posible cambio en formato de API: {e}")
        return None

# Ejemplos de uso
simbolo = "BTC/USDT"
intervalo = "5m"
df_5m = obtener_datos_coinex(simbolo, intervalo)

def calcular_indicadores(df):
    try:
        close = df['Close'].values
        if len(close) < 14:
            print("No hay suficientes datos para calcular los indicadores")
            return None
        df['RSI_Lento'] = talib.RSI(close, timeperiod=14)
        df['RSI_Rapido'] = talib.RSI(close, timeperiod=8)
        df['HMA'] = talib.HMA(close, timeperiod=14)
        return df
    except Exception as e:
        print(f"Error al calcular indicadores: {e}")
        return None
def aplicar_estrategia(df, stop_loss=0.01):
    operaciones = []
    en_posicion = False
    precio_entrada = 0

    for i in range(1, len(df)):
        if pd.isna(df['RSI_Lento'][i]) or pd.isna(df['RSI_Rapido'][i]) or pd.isna(df['HMA'][i]):
            continue

        if df['RSI_Rapido'][i] > df['RSI_Lento'][i] and not en_posicion:
            operacion = {'fecha': df.index[i], 'tipo': 'compra', 'precio_entrada': df['Close'][i]}
            en_posicion = True
            precio_entrada = df['Close'][i]
        elif df['RSI_Rapido'][i] < df['RSI_Lento'][i] and en_posicion:
            operacion = {'fecha': df.index[i], 'tipo': 'venta', 'precio_entrada': precio_entrada, 'precio_salida': df['Close'][i], 'profit':(df['Close'][i]-precio_entrada)/precio_entrada}
            operaciones.append(operacion)
            en_posicion = False

        if en_posicion:  # Check stop-loss
            if df['Close'][i] < precio_entrada * (1 - stop_loss):
                operacion = {'fecha': df.index[i], 'tipo': 'venta SL', 'precio_entrada': precio_entrada, 'precio_salida': df['Close'][i], 'profit':(df['Close'][i]-precio_entrada)/precio_entrada}
                operaciones.append(operacion)
                en_posicion = False

    return df, operaciones        

if df_5m is not None:
    print(df_5m.head())

def registrar_operaciones(simbolo, intervalo, operaciones):
    nombre_archivo = f"registros/{simbolo}_{intervalo}.csv"
    os.makedirs(os.path.dirname(nombre_archivo), exist_ok=True) #Crea el directorio si no existe
    with open(nombre_archivo, 'w', newline='') as csvfile:
        fieldnames = ['fecha', 'tipo', 'precio_entrada','precio_salida', 'profit']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(operaciones)

simbolos = ["BTC/USDT", "ETH/USDT", "BNB/USDT"]
intervalos = ["5m", "15m", "1h", "4h"]
periodo = "5d" #Ajusta el periodo para descargar los datos

if __name__ == "__main__":
    for simbolo in simbolos:
        for intervalo in intervalos:
            print(f"Descargando datos de {simbolo} en {intervalo}...")
            df = obtener_datos_coinex(simbolo, intervalo, limit=1000)
            if df is not None:
                df = calcular_indicadores(df)
                if df is not None:
                    df, operaciones = aplicar_estrategia(df)
                    registrar_operaciones(simbolo, intervalo, operaciones)
                    print(f"Backtesting completado para {simbolo} en {intervalo}")
